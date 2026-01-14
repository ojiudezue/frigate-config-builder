"""Reolink camera discovery adapter."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import quote

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class ReolinkAdapter(CameraAdapter):
    """Discover cameras from Reolink integration.

    Reolink cameras typically have two stream types:
    - Main stream: High resolution for recording
    - Sub stream: Low resolution for detection

    RTSP URL formats vary by model:
    - Standard: rtsp://{user}:{pass}@{host}:554/h264Preview_01_{main|sub}
    - Newer: rtsp://{user}:{pass}@{host}:554/Preview_01_{main|sub}

    go2rtc can also use HTTP FLV for better compatibility:
    - ffmpeg:http://{host}/flv?port=1935&app=bcs&stream=channel0_main.bcs&...
    """

    @property
    def integration_domain(self) -> str:
        """Return the HA integration domain."""
        return "reolink"

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all Reolink cameras."""
        if not self.is_available():
            _LOGGER.debug("Reolink integration not configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        # Get config entries for credentials
        reolink_entries = self.hass.config_entries.async_entries("reolink")

        # Track processed devices to avoid duplicates (Reolink creates many entities per device)
        processed_devices: set[str] = set()

        # Find camera entities from reolink integration
        for entity in entity_reg.entities.values():
            if entity.domain != "camera" or entity.platform != "reolink":
                continue

            if entity.disabled:
                continue

            # Skip if we already processed this device
            if entity.device_id and entity.device_id in processed_devices:
                continue

            # Skip non-main streams (like _fluent, _sub, etc.)
            if "_fluent" in entity.entity_id or "_sub" in entity.entity_id:
                continue

            try:
                # Find matching config entry
                config_entry = self._find_config_entry_for_entity(
                    entity, reolink_entries
                )
                if not config_entry:
                    _LOGGER.warning(
                        "Could not find config entry for Reolink camera %s",
                        entity.entity_id,
                    )
                    continue

                camera = await self._create_camera(
                    entity, config_entry, entity_reg, area_reg
                )
                if camera:
                    cameras.append(camera)
                    if entity.device_id:
                        processed_devices.add(entity.device_id)

            except Exception as err:
                _LOGGER.warning(
                    "Failed to process Reolink camera %s: %s",
                    entity.entity_id,
                    err,
                    exc_info=True,
                )

        _LOGGER.info("Discovered %d Reolink cameras", len(cameras))
        return cameras

    def _find_config_entry_for_entity(
        self,
        entity: er.RegistryEntry,
        entries: list,
    ):
        """Find the config entry associated with an entity."""
        if entity.config_entry_id:
            for entry in entries:
                if entry.entry_id == entity.config_entry_id:
                    return entry

        # Fallback: try to match by device
        if entity.device_id:
            device_reg = dr.async_get(self.hass)
            device = device_reg.async_get(entity.device_id)
            if device:
                for entry_id in device.config_entries:
                    for entry in entries:
                        if entry.entry_id == entry_id:
                            return entry

        # If only one entry, use it
        if len(entries) == 1:
            return entries[0]

        return None

    async def _create_camera(
        self,
        entity: er.RegistryEntry,
        config_entry,
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from Reolink entity and config entry."""
        entry_data = config_entry.data

        # Get credentials from config entry
        host = entry_data.get("host")
        username = entry_data.get("username", "admin")
        password = entry_data.get("password", "")
        port = entry_data.get("port", 554)

        if not host:
            _LOGGER.warning("Reolink config entry missing host")
            return None

        # URL encode password for special characters
        encoded_password = quote(password, safe="")

        # Determine channel number (usually 01 for single-channel cameras)
        channel = "01"

        # Build RTSP URLs
        # Main stream (high res) for recording
        record_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/h264Preview_{channel}_main"
        )

        # Sub stream (low res) for detection
        detect_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/h264Preview_{channel}_sub"
        )

        # go2rtc URL using HTTP FLV for better compatibility
        go2rtc_url = (
            f"ffmpeg:http://{host}/flv?port=1935&app=bcs&stream=channel0_main.bcs"
            f"&user={username}&password={encoded_password}"
        )

        # Get friendly name
        state = self.hass.states.get(entity.entity_id)
        friendly_name = entry_data.get("name") or host
        if state and state.attributes.get("friendly_name"):
            friendly_name = state.attributes["friendly_name"]

        # Normalize name for Frigate
        cam_name = self.normalize_name(friendly_name)

        # Check availability
        available = state.state != "unavailable" if state else False

        # Get area
        area = None
        if entity.area_id:
            area_entry = area_reg.async_get_area(entity.area_id)
            area = area_entry.name if area_entry else None

        return DiscoveredCamera(
            id=f"reolink_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="reolink",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=go2rtc_url,
            width=640,
            height=360,
            area=area,
            available=available,
        )
