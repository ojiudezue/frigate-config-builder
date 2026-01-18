"""Reolink camera discovery adapter.

Version: 0.4.0.0
Date: 2026-01-17

Discovers cameras from the native Reolink integration.
Handles multi-lens cameras (like TrackMix) as separate Frigate cameras.
Supports both enabled and disabled camera entities.
Constructs RTSP URLs from Reolink integration data when stream_source unavailable.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class ReolinkAdapter(CameraAdapter):
    """Discover cameras from Reolink integration.

    Reolink cameras create multiple camera entities per device:
    - clear_lens_X: High resolution stream (for recording)
    - fluent_lens_X: Low resolution stream (for detection)
    - snapshots_*: Snapshot entities (ignored)

    Multi-lens cameras (like TrackMix) have lens_0 (wide) and lens_1 (PTZ).
    Each lens becomes a separate Frigate camera.

    Note: Clear (high-res) cameras are often disabled by default in HA.
    This adapter handles disabled entities by constructing RTSP URLs from
    the Reolink integration's stored credentials.
    """

    @property
    def integration_domain(self) -> str:
        """Return the HA integration domain."""
        return "reolink"

    def _get_reolink_host_data(self) -> dict[str, Any]:
        """Get Reolink integration host data for all configured devices."""
        hosts: dict[str, Any] = {}

        reolink_data = self.hass.data.get("reolink", {})
        for entry_id, data in reolink_data.items():
            if hasattr(data, "host"):
                host = data.host
                if hasattr(host, "unique_id"):
                    hosts[host.unique_id] = host
                    _LOGGER.debug(
                        "Found Reolink host: %s at %s",
                        host.unique_id,
                        getattr(host, "api_host", "unknown"),
                    )

        return hosts

    def _build_rtsp_url(
        self,
        host: Any,
        channel: int = 0,
        stream: str = "main",
    ) -> str | None:
        """Build RTSP URL from Reolink host object."""
        try:
            ip = getattr(host, "api_host", None)
            username = getattr(host, "username", "admin")
            password = getattr(host, "password", "")
            rtsp_port = getattr(host, "rtsp_port", 554)

            if not ip:
                return None

            channel_str = f"{channel + 1:02d}"
            url = f"rtsp://{username}:{password}@{ip}:{rtsp_port}/h264Preview_{channel_str}_{stream}"

            return url

        except Exception as err:
            _LOGGER.warning("Failed to build RTSP URL: %s", err)
            return None

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all Reolink cameras."""
        if not self.is_available():
            _LOGGER.debug("Reolink integration not configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        reolink_hosts = self._get_reolink_host_data()
        _LOGGER.debug("Found %d Reolink hosts", len(reolink_hosts))

        devices_cameras: dict[str, dict[str, list[er.RegistryEntry]]] = {}

        for entity in entity_reg.entities.values():
            if entity.domain != "camera" or entity.platform != "reolink":
                continue
            if not entity.device_id:
                continue

            if "snapshot" in entity.entity_id.lower():
                continue

            device_id = entity.device_id
            if device_id not in devices_cameras:
                devices_cameras[device_id] = {"clear": [], "fluent": []}

            entity_id_lower = entity.entity_id.lower()
            if "_clear" in entity_id_lower:
                devices_cameras[device_id]["clear"].append(entity)
            elif "_fluent" in entity_id_lower:
                devices_cameras[device_id]["fluent"].append(entity)
            else:
                devices_cameras[device_id]["clear"].append(entity)

        _LOGGER.debug(
            "Found %d Reolink devices with camera entities", len(devices_cameras)
        )

        for device_id, stream_entities in devices_cameras.items():
            device = device_reg.async_get(device_id)
            if not device:
                continue

            device_name = device.name_by_user or device.name or "Reolink Camera"

            device_serial = None
            for identifier in device.identifiers:
                if identifier[0] == "reolink":
                    device_serial = identifier[1]
                    break

            host = reolink_hosts.get(device_serial) if device_serial else None

            area = None
            if device.area_id:
                area_entry = area_reg.async_get_area(device.area_id)
                area = area_entry.name if area_entry else None

            clear_entities = stream_entities["clear"]
            fluent_entities = stream_entities["fluent"]

            _LOGGER.debug(
                "Device %s (serial=%s): %d clear, %d fluent entities, host=%s",
                device_name,
                device_serial,
                len(clear_entities),
                len(fluent_entities),
                "found" if host else "not found",
            )

            if not clear_entities and not fluent_entities:
                _LOGGER.debug("No camera entities for device %s", device_name)
                continue

            lens_count = max(len(clear_entities), len(fluent_entities), 1)

            for lens_idx in range(lens_count):
                try:
                    camera = await self._create_camera_for_lens(
                        device_name=device_name,
                        device=device,
                        lens_idx=lens_idx,
                        lens_count=lens_count,
                        clear_entities=clear_entities,
                        fluent_entities=fluent_entities,
                        host=host,
                        area=area,
                    )
                    if camera:
                        cameras.append(camera)
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to process Reolink camera %s lens %d: %s",
                        device_name,
                        lens_idx,
                        err,
                        exc_info=True,
                    )

        _LOGGER.info("Discovered %d Reolink cameras", len(cameras))
        return cameras

    def _extract_lens_number(self, entity_id: str) -> int | None:
        """Extract lens number from entity ID."""
        match = re.search(r"_lens_(\d+)", entity_id.lower())
        if match:
            return int(match.group(1))
        return None

    def _find_entity_for_lens(
        self,
        entities: list[er.RegistryEntry],
        lens_idx: int,
    ) -> er.RegistryEntry | None:
        """Find entity matching the given lens index."""
        for entity in entities:
            entity_lens = self._extract_lens_number(entity.entity_id)
            if entity_lens == lens_idx:
                return entity
            if entity_lens is None and lens_idx == 0:
                return entity
        return None

    async def _get_stream_url(self, entity_id: str) -> str | None:
        """Get RTSP stream URL from camera entity."""
        try:
            camera_component = self.hass.data.get("camera")
            if not camera_component:
                _LOGGER.debug("Camera component not available")
                return None

            camera_entity = camera_component.get_entity(entity_id)
            if not camera_entity:
                _LOGGER.debug("Camera entity %s not found in component", entity_id)
                return None

            stream_url = await camera_entity.stream_source()
            return stream_url

        except Exception as err:
            _LOGGER.debug("Failed to get stream URL for %s: %s", entity_id, err)
            return None

    async def _create_camera_for_lens(
        self,
        device_name: str,
        device: dr.DeviceEntry,
        lens_idx: int,
        lens_count: int,
        clear_entities: list[er.RegistryEntry],
        fluent_entities: list[er.RegistryEntry],
        host: Any | None,
        area: str | None,
    ) -> DiscoveredCamera | None:
        """Create a DiscoveredCamera for a specific lens."""
        is_multi_lens = lens_count > 1

        if is_multi_lens:
            lens_suffix = "wide" if lens_idx == 0 else "ptz" if lens_idx == 1 else f"lens{lens_idx}"
            friendly_name = f"{device_name} ({lens_suffix.upper()})"
            cam_name = self.normalize_name(f"{device_name}_{lens_suffix}")
        else:
            friendly_name = device_name
            cam_name = self.normalize_name(device_name)

        clear_entity = self._find_entity_for_lens(clear_entities, lens_idx)
        fluent_entity = self._find_entity_for_lens(fluent_entities, lens_idx)

        record_url = None
        detect_url = None

        if clear_entity and not clear_entity.disabled:
            record_url = await self._get_stream_url(clear_entity.entity_id)

        if fluent_entity and not fluent_entity.disabled:
            detect_url = await self._get_stream_url(fluent_entity.entity_id)

        if not record_url and host:
            record_url = self._build_rtsp_url(host, channel=lens_idx, stream="main")
            _LOGGER.debug("Built record URL from host data: %s", record_url[:50] + "..." if record_url else None)

        if not detect_url and host:
            detect_url = self._build_rtsp_url(host, channel=lens_idx, stream="sub")
            _LOGGER.debug("Built detect URL from host data: %s", detect_url[:50] + "..." if detect_url else None)

        if not record_url and detect_url:
            record_url = detect_url
        if not detect_url and record_url:
            detect_url = record_url

        if not record_url:
            _LOGGER.warning(
                "Could not get any stream URL for %s lens %d, skipping",
                device_name,
                lens_idx,
            )
            return None

        available = True
        if fluent_entity:
            state = self.hass.states.get(fluent_entity.entity_id)
            available = state is not None and state.state not in ("unavailable", "unknown")

        _LOGGER.info(
            "Created Reolink camera: %s (available=%s)",
            cam_name,
            available,
        )

        return DiscoveredCamera(
            id=f"reolink_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="reolink",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=record_url,
            width=640,
            height=360,
            area=area,
            available=available,
        )
