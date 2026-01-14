"""UniFi Protect camera discovery adapter."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

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

    This adapter discovers the high-res and low-res streams for each camera
    by accessing the UniFi Protect integration's internal camera objects directly.
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

        # Get RTSPS URLs from UniFi Protect integration data
        record_url = await self._get_stream_url_from_protect(high_entity.entity_id)
        if not record_url:
            _LOGGER.warning("Could not get stream URL for %s", high_entity.entity_id)
            return None

        # Get low-res URL for detection (falls back to high-res)
        detect_url = record_url
        if low_entity:
            low_url = await self._get_stream_url_from_protect(low_entity.entity_id)
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
        stream_url = await self._get_stream_url_from_protect(entity.entity_id)
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

    async def _get_stream_url_from_protect(self, entity_id: str) -> str | None:
        """Get RTSPS stream URL directly from UniFi Protect integration.

        Accesses the UniFi Protect integration's internal camera objects to get
        the RTSPS URL. This bypasses the need for expose-camera-stream-source.
        """
        try:
            # Access UniFi Protect integration data from hass.data
            protect_data = self.hass.data.get(UNIFI_PROTECT_DOMAIN)
            if not protect_data:
                _LOGGER.debug("UniFi Protect integration data not found in hass.data")
                return None

            # UniFi Protect stores data per config entry
            # Try to find the camera entity's platform
            entity_reg = er.async_get(self.hass)
            entity_entry = entity_reg.async_get(entity_id)
            
            if not entity_entry or not entity_entry.config_entry_id:
                _LOGGER.debug("Entity %s not found in registry", entity_id)
                return None

            config_entry_id = entity_entry.config_entry_id
            
            # Get the config entry data for this UniFi Protect instance
            entry_data = protect_data.get(config_entry_id)
            if not entry_data:
                _LOGGER.debug("No UniFi Protect data for config entry %s", config_entry_id)
                return None

            # The UniFi Protect integration stores a ProtectApiClient in entry_data
            # Try to access it (structure may vary by version)
            api_client = entry_data
            
            # Try different possible attribute names based on UniFi Protect integration structure
            for attr in ["api", "protect", "data"]:
                if hasattr(api_client, attr):
                    api_client = getattr(api_client, attr)
                    break
            
            # Get the camera object from the UniFi Protect API client
            # Camera objects have RTSPS channel URLs
            if hasattr(api_client, "bootstrap") and hasattr(api_client.bootstrap, "cameras"):
                # Extract camera name from entity_id (e.g., back_yard from camera.back_yard_high_resolution_channel)
                match = re.match(r"camera\.(.+?)_(high|medium|low)_resolution_channel", entity_id)
                if not match:
                    match = re.match(r"camera\.(.+?)_package_camera", entity_id)
                
                if not match:
                    _LOGGER.debug("Could not parse camera name from entity_id: %s", entity_id)
                    return None
                
                cam_name = match.group(1)
                
                # Find the camera object that matches this entity
                for camera in api_client.bootstrap.cameras.values():
                    # Camera has a 'name' attribute and 'channels' with RTSPS URLs
                    camera_name_normalized = camera.name.lower().replace(" ", "_").replace("-", "_")
                    
                    if camera_name_normalized == cam_name:
                        # Determine which channel we need
                        channel_index = 0  # default to main/high channel
                        
                        if "high_resolution" in entity_id or "package_camera" in entity_id:
                            channel_index = 0  # High res / package
                        elif "medium_resolution" in entity_id:
                            channel_index = 1  # Medium res
                        elif "low_resolution" in entity_id:
                            channel_index = 2  # Low res
                        
                        # Get the RTSPS URL from the channel
                        if hasattr(camera, "channels") and len(camera.channels) > channel_index:
                            channel = camera.channels[channel_index]
                            
                            # The channel has an rtsps_url attribute
                            if hasattr(channel, "rtsps_url"):
                                rtsps_url = channel.rtsps_url
                                _LOGGER.debug("Found RTSPS URL for %s: %s", entity_id, rtsps_url[:50] + "...")
                                return rtsps_url
                        
                        break
            
            _LOGGER.debug("Could not find RTSPS URL in UniFi Protect data structure for %s", entity_id)
            return None

        except Exception as err:
            _LOGGER.debug(
                "Failed to get stream URL from UniFi Protect data for %s: %s",
                entity_id,
                err,
                exc_info=True,
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
