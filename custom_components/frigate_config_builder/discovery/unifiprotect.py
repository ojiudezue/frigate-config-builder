"""UniFi Protect camera discovery adapter.

Version: 0.2.2.0
Date: 2026-01-17

Changelog:
- 0.2.2.0: FIXED - Access camera entity's stream_source() method directly via
  hass.data["camera"].get_entity(). No HTTP calls needed since we're running
  inside Home Assistant. This is what expose-camera-stream-source does internally.
- 0.2.1.0: Attempted HTTP API call (FAILED - 401 auth, SUPERVISOR_TOKEN not available to integrations)
- 0.2.0.0: Attempted direct UniFi Protect data access (FAILED - internal structures vary)
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# UniFi Protect integration domain key
UNIFI_PROTECT_DOMAIN = "unifiprotect"

# Camera domain for accessing camera entities
CAMERA_DOMAIN = "camera"


class UniFiProtectAdapter(CameraAdapter):
    """Discover cameras from UniFi Protect integration.

    UniFi Protect creates multiple camera entities per device:
    - camera.{name}_high_resolution_channel (record quality)
    - camera.{name}_medium_resolution_channel
    - camera.{name}_low_resolution_channel (detect quality)
    - camera.{name}_package_camera (for doorbell package detection)

    This adapter retrieves RTSP URLs by directly accessing the camera entity's
    stream_source() method via hass.data["camera"].get_entity(). This is the
    same approach that expose-camera-stream-source uses internally.
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

        # Verify camera component is available
        camera_component = self.hass.data.get(CAMERA_DOMAIN)
        if camera_component is None:
            _LOGGER.error(
                "Camera component not found in hass.data. "
                "This should not happen - camera domain should be loaded."
            )
            return []

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

        # Get RTSPS URLs by directly accessing camera entity
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
        """Get RTSP stream URL by directly accessing the camera entity.
        
        This accesses the camera entity's stream_source() method directly via
        hass.data["camera"].get_entity(). This is what the expose-camera-stream-source
        integration does internally - no HTTP calls or authentication needed since
        we're running inside Home Assistant.
        """
        try:
            # Access the camera entity component from hass.data
            camera_component = self.hass.data.get(CAMERA_DOMAIN)
            if camera_component is None:
                _LOGGER.debug("Camera component not found in hass.data")
                return None
            
            # The camera component is an EntityComponent - get the specific entity
            # EntityComponent.get_entity() returns the actual entity object
            camera_entity = camera_component.get_entity(entity_id)
            if camera_entity is None:
                _LOGGER.debug(
                    "Camera entity %s not found in camera component. "
                    "Entity may be disabled or not yet loaded.",
                    entity_id
                )
                return None
            
            # Call the stream_source() method to get the RTSP URL
            # This is an async method on CameraEntity that returns the stream URL
            if hasattr(camera_entity, 'stream_source'):
                try:
                    stream_url = await camera_entity.stream_source()
                except Exception as source_err:
                    _LOGGER.debug(
                        "stream_source() raised exception for %s: %s",
                        entity_id,
                        source_err
                    )
                    return None
                
                if stream_url:
                    _LOGGER.debug(
                        "Got stream URL for %s via direct entity access: %s...",
                        entity_id,
                        stream_url[:60] if len(stream_url) > 60 else stream_url
                    )
                    return stream_url
                else:
                    _LOGGER.debug(
                        "stream_source() returned None/empty for %s. "
                        "Camera may not support streaming or RTSP may be disabled.",
                        entity_id
                    )
                    return None
            else:
                _LOGGER.debug(
                    "Camera entity %s does not have stream_source method. "
                    "Entity type: %s",
                    entity_id,
                    type(camera_entity).__name__
                )
                return None
            
        except Exception as err:
            _LOGGER.warning(
                "Error getting stream URL for %s: %s",
                entity_id,
                err,
                exc_info=True
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
