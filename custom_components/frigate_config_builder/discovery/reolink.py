"""Reolink camera discovery adapter.

Version: 0.3.0.2
Date: 2026-01-17

Discovers cameras from the native Reolink integration.
Handles multi-lens cameras (like TrackMix) as separate Frigate cameras.
Uses camera.stream_source() to get actual RTSP URLs.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class ReolinkAdapter(CameraAdapter):
    """Discover cameras from Reolink integration.

    Reolink cameras create multiple camera entities per device:
    - clear_lens_X: High resolution stream (for recording)
    - fluent_lens_X: Low resolution stream (for detection)
    - snapshots_*: Snapshot entities (ignored)

    Multi-lens cameras (like TrackMix) have lens_0 (wide) and lens_1 (PTZ).
    Each lens becomes a separate Frigate camera.
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
        device_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        # Group camera entities by device
        devices_cameras: dict[str, dict[str, list[er.RegistryEntry]]] = {}

        for entity in entity_reg.entities.values():
            if entity.domain != "camera" or entity.platform != "reolink":
                continue
            if entity.disabled:
                continue
            if not entity.device_id:
                continue

            # Skip snapshot entities
            if "snapshot" in entity.entity_id.lower():
                continue

            device_id = entity.device_id
            if device_id not in devices_cameras:
                devices_cameras[device_id] = {"clear": [], "fluent": []}

            # Categorize by stream type
            entity_id_lower = entity.entity_id.lower()
            if "_clear_" in entity_id_lower or entity_id_lower.endswith("_clear"):
                devices_cameras[device_id]["clear"].append(entity)
            elif "_fluent_" in entity_id_lower or entity_id_lower.endswith("_fluent"):
                devices_cameras[device_id]["fluent"].append(entity)
            else:
                # Single-stream camera (older models) - treat as clear
                devices_cameras[device_id]["clear"].append(entity)

        _LOGGER.debug(
            "Found %d Reolink devices with camera entities", len(devices_cameras)
        )

        # Process each device
        for device_id, stream_entities in devices_cameras.items():
            device = device_reg.async_get(device_id)
            if not device:
                continue

            # Get device name (user-defined or default)
            device_name = device.name_by_user or device.name or "Reolink Camera"

            # Get area from device
            area = None
            if device.area_id:
                area_entry = area_reg.async_get_area(device.area_id)
                area = area_entry.name if area_entry else None

            clear_entities = stream_entities["clear"]
            fluent_entities = stream_entities["fluent"]

            _LOGGER.debug(
                "Device %s (%s): %d clear, %d fluent entities",
                device_name,
                device_id,
                len(clear_entities),
                len(fluent_entities),
            )

            # Process each clear (high-res) entity as a separate Frigate camera
            for clear_entity in clear_entities:
                try:
                    camera = await self._create_camera_from_entity(
                        device_name=device_name,
                        device=device,
                        clear_entity=clear_entity,
                        fluent_entities=fluent_entities,
                        area=area,
                    )
                    if camera:
                        cameras.append(camera)
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to process Reolink camera %s: %s",
                        clear_entity.entity_id,
                        err,
                        exc_info=True,
                    )

        _LOGGER.info("Discovered %d Reolink cameras", len(cameras))
        return cameras

    def _extract_lens_number(self, entity_id: str) -> int | None:
        """Extract lens number from entity ID (e.g., '_lens_0' -> 0)."""
        import re

        match = re.search(r"_lens_(\d+)", entity_id.lower())
        if match:
            return int(match.group(1))
        return None

    def _find_matching_fluent(
        self,
        clear_entity: er.RegistryEntry,
        fluent_entities: list[er.RegistryEntry],
    ) -> er.RegistryEntry | None:
        """Find the fluent (low-res) entity matching a clear (high-res) entity."""
        clear_lens = self._extract_lens_number(clear_entity.entity_id)

        for fluent in fluent_entities:
            fluent_lens = self._extract_lens_number(fluent.entity_id)
            if clear_lens == fluent_lens:
                return fluent

        # No matching lens found - return first fluent if only one exists
        if len(fluent_entities) == 1 and clear_lens is None:
            return fluent_entities[0]

        return None

    async def _get_stream_url(self, entity_id: str) -> str | None:
        """Get RTSP stream URL from camera entity using stream_source()."""
        try:
            # Access camera component directly from hass.data
            camera_component = self.hass.data.get("camera")
            if not camera_component:
                _LOGGER.warning("Camera component not available")
                return None

            camera_entity = camera_component.get_entity(entity_id)
            if not camera_entity:
                _LOGGER.warning("Camera entity %s not found in component", entity_id)
                return None

            # Get stream source (this is the actual RTSP URL)
            stream_url = await camera_entity.stream_source()
            return stream_url

        except Exception as err:
            _LOGGER.warning(
                "Failed to get stream URL for %s: %s", entity_id, err
            )
            return None

    async def _create_camera_from_entity(
        self,
        device_name: str,
        device: dr.DeviceEntry,
        clear_entity: er.RegistryEntry,
        fluent_entities: list[er.RegistryEntry],
        area: str | None,
    ) -> DiscoveredCamera | None:
        """Create a DiscoveredCamera from Reolink entities."""
        # Determine lens info for multi-lens cameras
        lens_num = self._extract_lens_number(clear_entity.entity_id)
        is_multi_lens = lens_num is not None

        # Build camera name with lens suffix for multi-lens
        if is_multi_lens:
            # lens_0 = wide angle, lens_1 = PTZ/telephoto
            lens_suffix = "wide" if lens_num == 0 else f"ptz" if lens_num == 1 else f"lens{lens_num}"
            friendly_name = f"{device_name} ({lens_suffix.upper()})"
            cam_name = self.normalize_name(f"{device_name}_{lens_suffix}")
        else:
            friendly_name = device_name
            cam_name = self.normalize_name(device_name)

        # Get stream URLs
        record_url = await self._get_stream_url(clear_entity.entity_id)
        if not record_url:
            _LOGGER.warning(
                "Could not get stream URL for %s, skipping", clear_entity.entity_id
            )
            return None

        # Find matching fluent entity for detect stream
        fluent_entity = self._find_matching_fluent(clear_entity, fluent_entities)
        detect_url = None
        if fluent_entity:
            detect_url = await self._get_stream_url(fluent_entity.entity_id)

        # If no fluent stream, use clear stream for both
        if not detect_url:
            detect_url = record_url

        # Check availability
        state = self.hass.states.get(clear_entity.entity_id)
        available = state is not None and state.state != "unavailable"

        _LOGGER.debug(
            "Created Reolink camera: %s (record=%s, detect=%s)",
            cam_name,
            record_url[:50] + "..." if record_url else None,
            detect_url[:50] + "..." if detect_url else None,
        )

        return DiscoveredCamera(
            id=f"reolink_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="reolink",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=record_url,  # Use RTSP URL for go2rtc
            width=640,  # Will be auto-detected by Frigate
            height=360,
            area=area,
            available=available,
        )
