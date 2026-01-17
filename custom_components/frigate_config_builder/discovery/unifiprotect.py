"""UniFi Protect camera discovery adapter.

Version: 0.2.1.0
Date: 2026-01-17

Changelog:
- 0.2.1.0: FIXED - Use expose-camera-stream-source HTTP API endpoint instead of
  trying to access internal UniFi Protect data structures. This matches the
  approach that successfully worked in the standalone script.
- 0.2.0.0: Attempted direct UniFi Protect data access (FAILED - internal structures vary)
"""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING

import aiohttp

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# UniFi Protect integration domain key
UNIFI_PROTECT_DOMAIN = "unifiprotect"


class UniFiProtectAdapter(CameraAdapter):
    """Discover cameras from UniFi Protect integration.

    UniFi Protect creates multiple camera entities per device:
    - camera.{name}_high_resolution_channel (record quality)
    - camera.{name}_medium_resolution_channel
    - camera.{name}_low_resolution_channel (detect quality)
    - camera.{name}_package_camera (for doorbell package detection)

    This adapter uses the expose-camera-stream-source HACS integration
    to retrieve RTSP URLs via its HTTP API endpoint at:
    /api/camera_stream_source/{entity_id}
    """

    @property
    def integration_domain(self) -> str:
        """Return the HA integration domain."""
        return UNIFI_PROTECT_DOMAIN

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
        _LOGGER.info("Found %d UniFi Protect camera groups to process", len(camera_groups))

        for cam_name, resolutions in camera_groups.items():
            try:
                # Create main camera (high + low res)
                main_camera = await self._create_camera(
                    cam_name, resolutions, entity_reg, area_reg
                )
                if main_camera:
                    cameras.append(main_camera)
                    _LOGGER.debug("Successfully discovered camera: %s", cam_name)

                # Create package camera if present (e.g., G6 Doorbell)
                if resolutions.get("package"):
                    pkg_camera = await self._create_package_camera(
                        cam_name, resolutions["package"], entity_reg, area_reg
                    )
                    if pkg_camera:
                        cameras.append(pkg_camera)
                        _LOGGER.debug("Successfully discovered package camera: %s_package", cam_name)

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
            if entity.domain != "camera" or entity.platform != UNIFI_PROTECT_DOMAIN:
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

        # Get RTSPS URLs using expose-camera-stream-source HTTP API
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
            else:
                _LOGGER.debug("Could not get low-res stream URL for %s, using high-res", cam_name)

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
        """Get RTSP stream URL using expose-camera-stream-source HTTP API.
        
        This calls the HTTP endpoint provided by the expose-camera-stream-source
        HACS integration: /api/camera_stream_source/{entity_id}
        
        This is the same approach that worked successfully in the standalone script.
        """
        try:
            # Determine the base URL and auth token based on environment
            # Priority: SUPERVISOR_TOKEN (HA OS) > internal HA API
            
            supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
            
            if supervisor_token:
                # Running on HA OS - use Supervisor API proxy
                base_url = "http://supervisor/core"
                headers = {
                    "Authorization": f"Bearer {supervisor_token}",
                    "Content-Type": "application/json",
                }
                _LOGGER.debug("Using Supervisor API for %s", entity_id)
            else:
                # Not on HA OS - try to use internal HA API
                # Get the internal URL from HA config
                internal_url = None
                
                # Try different ways to get the HA URL
                if hasattr(self.hass, 'config') and hasattr(self.hass.config, 'internal_url'):
                    internal_url = self.hass.config.internal_url
                elif hasattr(self.hass, 'config') and hasattr(self.hass.config, 'api'):
                    if hasattr(self.hass.config.api, 'base_url'):
                        internal_url = self.hass.config.api.base_url
                
                if not internal_url:
                    # Fallback to localhost
                    internal_url = "http://localhost:8123"
                
                base_url = internal_url.rstrip("/")
                
                # For internal calls, we need a long-lived access token
                # This should be configured or we use the HA context
                # For now, try without auth (may work for local calls)
                headers = {"Content-Type": "application/json"}
                _LOGGER.debug("Using internal HA API at %s for %s", base_url, entity_id)

            # Build the API URL
            # The expose-camera-stream-source creates: /api/camera_stream_source/{entity_id}
            api_url = f"{base_url}/api/camera_stream_source/{entity_id}"
            
            _LOGGER.debug("Calling expose-camera-stream-source API: %s", api_url)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        # The API returns the stream URL as plain text
                        stream_url = await response.text()
                        stream_url = stream_url.strip().strip('"')  # Remove any quotes/whitespace
                        
                        if stream_url and ("rtsp" in stream_url or "rtsps" in stream_url):
                            _LOGGER.debug("Got stream URL for %s: %s...", entity_id, stream_url[:50])
                            return stream_url
                        else:
                            _LOGGER.warning("Unexpected response format from API for %s: %s", entity_id, stream_url[:100] if stream_url else "empty")
                            return None
                    elif response.status == 404:
                        _LOGGER.warning(
                            "expose-camera-stream-source API not found for %s (404). "
                            "Is the expose-camera-stream-source integration installed and enabled?",
                            entity_id
                        )
                        return None
                    elif response.status == 401:
                        _LOGGER.warning(
                            "Authentication failed for expose-camera-stream-source API (401). "
                            "Check SUPERVISOR_TOKEN or API access."
                        )
                        return None
                    else:
                        body = await response.text()
                        _LOGGER.warning(
                            "Failed to get stream URL for %s: HTTP %d - %s",
                            entity_id,
                            response.status,
                            body[:200] if body else "no body"
                        )
                        return None
                        
        except aiohttp.ClientError as err:
            _LOGGER.warning("HTTP error getting stream URL for %s: %s", entity_id, err)
            return None
        except Exception as err:
            _LOGGER.warning("Error getting stream URL for %s: %s", entity_id, err, exc_info=True)
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
