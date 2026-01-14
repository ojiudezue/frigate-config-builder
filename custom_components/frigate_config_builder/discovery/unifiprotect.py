"""UniFi Protect camera discovery adapter."""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING
from urllib.parse import quote

import aiohttp

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class UniFiProtectAdapter(CameraAdapter):
    """Discover cameras from UniFi Protect integration.

    UniFi Protect creates multiple camera entities per device:
    - camera.{name}_high_resolution_channel (record quality)
    - camera.{name}_medium_resolution_channel
    - camera.{name}_low_resolution_channel (detect quality)
    - camera.{name}_package_camera (for doorbell package detection)

    This adapter discovers the high-res and low-res streams for each camera,
    using expose-camera-stream-source to get the RTSP URLs.
    """

    @property
    def integration_domain(self) -> str:
        """Return the HA integration domain."""
        return "unifiprotect"

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all UniFi Protect cameras."""
        if not self.is_available():
            _LOGGER.debug("UniFi Protect integration not configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        # Group entities by camera device
        camera_groups = self._group_camera_entities(entity_reg)

        for cam_name, resolutions in camera_groups.items():
            try:
                # Create main camera (high + low res)
                main_camera = await self._create_camera(
                    cam_name, resolutions, entity_reg, area_reg
                )
                if main_camera:
                    cameras.append(main_camera)

                # Create package camera if present (e.g., G6 Doorbell)
                if resolutions.get("package"):
                    pkg_camera = await self._create_package_camera(
                        cam_name, resolutions["package"], entity_reg, area_reg
                    )
                    if pkg_camera:
                        cameras.append(pkg_camera)

            except Exception as err:
                _LOGGER.warning(
                    "Failed to process UniFi camera %s: %s",
                    cam_name,
                    err,
                    exc_info=True,
                )

        _LOGGER.info("Discovered %d UniFi Protect cameras", len(cameras))
        return cameras

    def _group_camera_entities(
        self,
        entity_reg: er.EntityRegistry,
    ) -> dict[str, dict[str, er.RegistryEntry | None]]:
        """Group camera entities by device name and resolution.

        Returns:
            Dict mapping camera names to resolution entity entries:
            {
                "front_door": {
                    "high": <RegistryEntry>,
                    "medium": <RegistryEntry>,
                    "low": <RegistryEntry>,
                    "package": <RegistryEntry or None>,
                },
                ...
            }
        """
        camera_groups: dict[str, dict[str, er.RegistryEntry | None]] = {}

        for entity in entity_reg.entities.values():
            # Skip non-cameras and non-unifiprotect
            if entity.domain != "camera" or entity.platform != "unifiprotect":
                continue

            # Skip disabled and insecure entities
            if entity.disabled or "_insecure" in entity.entity_id:
                continue

            entity_id = entity.entity_id

            # Match resolution pattern: camera.{name}_{resolution}_resolution_channel
            match = re.match(
                r"camera\.(.+?)_(high|medium|low)_resolution_channel$",
                entity_id,
            )
            if match:
                cam_name = match.group(1)
                resolution = match.group(2)
            elif entity_id.endswith("_package_camera"):
                cam_name = entity_id.replace("camera.", "").replace("_package_camera", "")
                resolution = "package"
            else:
                # Unknown pattern, skip
                continue

            if cam_name not in camera_groups:
                camera_groups[cam_name] = {
                    "high": None,
                    "medium": None,
                    "low": None,
                    "package": None,
                }

            camera_groups[cam_name][resolution] = entity

        return camera_groups

    async def _create_camera(
        self,
        cam_name: str,
        resolutions: dict[str, er.RegistryEntry | None],
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from grouped resolution entities."""
        high_entity = resolutions.get("high")
        low_entity = resolutions.get("low")

        if not high_entity:
            _LOGGER.debug("Camera %s has no high-res entity, skipping", cam_name)
            return None

        # Get RTSP URLs using expose-camera-stream-source
        record_url = await self._get_stream_url(high_entity.entity_id)
        if not record_url:
            _LOGGER.warning("Could not get stream URL for %s", high_entity.entity_id)
            return None

        # Get low-res URL for detection (falls back to high-res)
        detect_url = record_url
        if low_entity:
            low_url = await self._get_stream_url(low_entity.entity_id)
            if low_url:
                detect_url = low_url

        # Get friendly name from state attributes
        state = self.hass.states.get(high_entity.entity_id)
        friendly_name = cam_name.replace("_", " ").title()
        if state and state.attributes.get("friendly_name"):
            # Clean up " High resolution channel" suffix
            friendly_name = (
                state.attributes["friendly_name"]
                .replace(" High resolution channel", "")
                .replace(" high resolution channel", "")
            )

        # Check availability
        available = state.state != "unavailable" if state else False

        # Get area
        area = self._get_entity_area(high_entity, area_reg)

        # Get detect dimensions from low-res entity attributes
        detect_width, detect_height = self._get_detect_dimensions(low_entity or high_entity)

        # Ensure URL has enableSrtp param for Frigate
        record_url = self._format_rtsp_url(record_url)
        detect_url = self._format_rtsp_url(detect_url)

        # Build go2rtc URL (rtspx:// without enableSrtp)
        go2rtc_url = record_url.replace("rtsps://", "rtspx://")
        if "?" in go2rtc_url:
            go2rtc_url = go2rtc_url.split("?")[0]

        return DiscoveredCamera(
            id=f"unifi_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="unifiprotect",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=go2rtc_url,
            width=detect_width,
            height=detect_height,
            area=area,
            available=available,
        )

    async def _create_package_camera(
        self,
        cam_name: str,
        entity: er.RegistryEntry,
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera for a package camera (e.g., G6 Doorbell)."""
        stream_url = await self._get_stream_url(entity.entity_id)
        if not stream_url:
            _LOGGER.warning("Could not get package stream URL for %s", entity.entity_id)
            return None

        # Get friendly name
        state = self.hass.states.get(entity.entity_id)
        friendly_name = f"{cam_name.replace('_', ' ').title()} Package"
        if state and state.attributes.get("friendly_name"):
            friendly_name = state.attributes["friendly_name"].replace(" package camera", " Package")

        available = state.state != "unavailable" if state else False
        area = self._get_entity_area(entity, area_reg)

        stream_url = self._format_rtsp_url(stream_url)
        go2rtc_url = stream_url.replace("rtsps://", "rtspx://")
        if "?" in go2rtc_url:
            go2rtc_url = go2rtc_url.split("?")[0]

        pkg_name = f"{cam_name}_package"

        return DiscoveredCamera(
            id=f"unifi_{pkg_name}",
            name=pkg_name,
            friendly_name=friendly_name,
            source="unifiprotect",
            record_url=stream_url,
            detect_url=stream_url,
            go2rtc_url=go2rtc_url,
            width=400,  # Package cameras are smaller
            height=300,
            area=area,
            available=available,
        )

    async def _get_stream_url(self, entity_id: str) -> str | None:
        """Get RTSP stream URL using expose-camera-stream-source API.

        The expose-camera-stream-source HACS integration creates an API endpoint
        at /api/camera_stream_source/{entity_id} that returns the stream URL.
        """
        # Try to get the stream URL via HTTP API call
        try:
            # FIXED: Use the proper import instead of self.hass.helpers
            session = async_get_clientsession(self.hass)
            
            # For internal HA API calls in HA OS, use supervisor endpoint
            supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
            
            # URL-encode the entity_id to handle dots properly
            encoded_entity_id = quote(entity_id, safe='')
            
            if supervisor_token:
                # Running in HA OS - use supervisor endpoint
                url = f"http://supervisor/core/api/camera_stream_source/{encoded_entity_id}"
                headers = {"Authorization": f"Bearer {supervisor_token}"}
            else:
                # Running in other modes - use external API
                # Get a long-lived access token from hass.data if available
                # This is a fallback and may not work in all setups
                base_url = str(self.hass.config.api.base_url) if self.hass.config.api else "http://localhost:8123"
                url = f"{base_url}/api/camera_stream_source/{encoded_entity_id}"
                
                # Try to get access token from auth (may not work)
                headers = {}
                # Without a token, this will likely fail, but we have a fallback below
            
            _LOGGER.debug("Attempting to get stream URL from: %s", url)
            
            try:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        stream_url = await response.text()
                        # Remove quotes if present
                        return stream_url.strip().strip('"')
                    elif response.status == 404:
                        _LOGGER.debug(
                            "expose-camera-stream-source not installed or entity not found: %s",
                            entity_id,
                        )
                    else:
                        _LOGGER.debug(
                            "API returned status %d for %s",
                            response.status,
                            entity_id,
                        )
            except aiohttp.ClientError as err:
                _LOGGER.debug(
                    "HTTP request failed for %s: %s",
                    entity_id,
                    err,
                )

        except Exception as err:
            _LOGGER.debug(
                "expose-camera-stream-source API call failed for %s: %s",
                entity_id,
                err,
            )

        # Fallback: try getting stream URL from entity attributes
        # This won't work for UniFi Protect but might for other cameras
        try:
            state = self.hass.states.get(entity_id)
            if state and state.attributes:
                # Some integrations expose stream_source in attributes
                if "stream_source" in state.attributes:
                    return state.attributes["stream_source"]
                # Check for entity_picture with stream token
                if "entity_picture" in state.attributes:
                    # Some cameras expose the stream this way
                    pass
        except Exception as err:
            _LOGGER.debug("Attribute fallback failed for %s: %s", entity_id, err)

        # If we get here, expose-camera-stream-source is probably not installed
        _LOGGER.warning(
            "Could not get stream URL for %s. "
            "Please install the 'expose-camera-stream-source' HACS integration.",
            entity_id,
        )
        return None

    def _format_rtsp_url(self, url: str) -> str:
        """Format RTSP URL for Frigate (add enableSrtp if needed)."""
        if url and "rtsps://" in url and "?enableSrtp" not in url:
            return f"{url}?enableSrtp"
        return url

    def _get_entity_area(
        self,
        entity: er.RegistryEntry,
        area_reg: ar.AreaRegistry,
    ) -> str | None:
        """Get area name for an entity."""
        if entity.area_id:
            area = area_reg.async_get_area(entity.area_id)
            return area.name if area else None
        return None

    def _get_detect_dimensions(
        self,
        entity: er.RegistryEntry,
    ) -> tuple[int, int]:
        """Get detection dimensions from entity attributes.

        Returns reasonable dimensions for Frigate detection (max 640px wide).
        """
        state = self.hass.states.get(entity.entity_id) if entity else None
        if not state:
            return 640, 360

        attrs = state.attributes
        width = attrs.get("width", 640)
        height = attrs.get("height", 360)

        # Scale down if too large (Frigate detect shouldn't exceed ~640px)
        if width > 1280:
            ratio = height / width
            width = 640
            height = int(640 * ratio)
        elif width > 640:
            ratio = height / width
            width = 640
            height = int(640 * ratio)

        return width, height
