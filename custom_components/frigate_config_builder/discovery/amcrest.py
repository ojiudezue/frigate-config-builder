"""Amcrest/Dahua camera discovery adapter.

Version: 0.4.0.5
Date: 2026-01-18

Changelog:
- 0.4.0.5: Added Dahua support (same protocol), fast path via hass.data
- 0.4.0.4: Initial version with entity registry approach

Discovers cameras from Amcrest and Dahua integrations.
Amcrest and Dahua cameras are interchangeable - they use the same:
- RTSP URL format
- API protocol
- Stream types (main/sub)

RTSP URL format (same for both):
    rtsp://{user}:{pass}@{host}/cam/realmonitor?channel={ch}&subtype={st}

Stream types:
- Main stream (subtype=0): High resolution for recording
- Sub stream (subtype=1): Low resolution for detection

Note: Some models (like ASH41-B baby monitors) use channel=0 instead of channel=1.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Both integrations use the same protocol
SUPPORTED_DOMAINS = ["amcrest", "dahua"]


class AmcrestAdapter(CameraAdapter):
    """Discover cameras from Amcrest and Dahua integrations.
    
    Amcrest and Dahua cameras are manufactured by the same company and use
    identical protocols. This adapter discovers cameras from both integrations.
    """

    @property
    def integration_domain(self) -> str:
        """Return the primary HA integration domain."""
        return "amcrest"

    def is_available(self) -> bool:
        """Check if Amcrest OR Dahua integration is configured."""
        for domain in SUPPORTED_DOMAINS:
            if self.hass.config_entries.async_entries(domain):
                return True
        return False

    def _get_devices_from_hass_data(self) -> list[dict[str, Any]]:
        """Get device info directly from hass.data for all supported integrations.
        
        Both Amcrest and Dahua integrations store device data in hass.data.
        This allows us to get camera info even before entities are fully loaded.
        """
        devices: list[dict[str, Any]] = []
        
        for domain in SUPPORTED_DOMAINS:
            domain_data = self.hass.data.get(domain)
            if not domain_data:
                continue

            _LOGGER.debug("Found %s data in hass.data", domain)

            if isinstance(domain_data, dict):
                for entry_id, hub in domain_data.items():
                    if entry_id in ("devices", "cameras"):
                        continue
                        
                    try:
                        device_info = self._extract_device_from_hub(hub, entry_id, domain)
                        if device_info:
                            devices.append(device_info)
                    except Exception as err:
                        _LOGGER.debug(
                            "Could not extract device from %s hub %s: %s",
                            domain,
                            entry_id,
                            err,
                        )

        _LOGGER.debug(
            "Found %d Amcrest/Dahua devices via hass.data fast path",
            len(devices),
        )
        return devices

    def _extract_device_from_hub(
        self,
        hub: Any,
        entry_id: str,
        domain: str,
    ) -> dict[str, Any] | None:
        """Extract device info from hub object (works for both Amcrest and Dahua)."""
        # The hub typically has an 'api' attribute with the camera object
        api = getattr(hub, "api", None)
        if not api:
            return None

        # Get connection details - check multiple attribute names
        host = (
            getattr(api, "_host", None)
            or getattr(hub, "host", None)
            or getattr(api, "host", None)
        )
        if not host:
            return None

        username = (
            getattr(api, "_user", None) 
            or getattr(hub, "username", None)
            or getattr(api, "username", None)
            or "admin"
        )
        password = (
            getattr(api, "_password", None) 
            or getattr(hub, "password", None)
            or getattr(api, "password", None)
            or ""
        )
        port = (
            getattr(api, "_port", None) 
            or getattr(hub, "port", None)
            or getattr(api, "rtsp_port", None)
            or 554
        )
        
        name = getattr(hub, "name", None) or host

        return {
            "host": host,
            "username": username,
            "password": password,
            "port": port,
            "name": name,
            "entry_id": entry_id,
            "source_domain": domain,
        }

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all Amcrest and Dahua cameras."""
        if not self.is_available():
            _LOGGER.debug("Neither Amcrest nor Dahua integration configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        area_reg = ar.async_get(self.hass)
        processed_hosts: set[str] = set()

        # FAST PATH: Try to get devices directly from hass.data
        fast_devices = self._get_devices_from_hass_data()
        for device_info in fast_devices:
            host = device_info.get("host")
            if host and host not in processed_hosts:
                camera = self._create_camera_from_device_info(
                    device_info, entity_reg, area_reg
                )
                if camera:
                    cameras.append(camera)
                    processed_hosts.add(host)

        # FALLBACK: Get config entries for any we missed
        for domain in SUPPORTED_DOMAINS:
            entries = self.hass.config_entries.async_entries(domain)
            
            for config_entry in entries:
                host = config_entry.data.get("host")
                if host and host not in processed_hosts:
                    try:
                        camera = await self._create_camera_from_entry(
                            config_entry, entity_reg, area_reg, domain
                        )
                        if camera:
                            cameras.append(camera)
                            processed_hosts.add(host)
                    except Exception as err:
                        _LOGGER.warning(
                            "Failed to process %s entry %s: %s",
                            domain,
                            config_entry.entry_id,
                            err,
                        )

        _LOGGER.info("Discovered %d Amcrest/Dahua cameras", len(cameras))
        return cameras

    def _create_camera_from_device_info(
        self,
        device_info: dict[str, Any],
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from fast-path device info."""
        host = device_info.get("host")
        username = device_info.get("username", "admin")
        password = device_info.get("password", "")
        port = device_info.get("port", 554)
        name = device_info.get("name", host)
        source_domain = device_info.get("source_domain", "amcrest")

        if not host:
            return None

        # URL encode password for special characters
        encoded_password = quote(password, safe="")

        # Build RTSP URLs (same format for Amcrest and Dahua)
        record_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/cam/realmonitor?channel=1&subtype=0"
        )
        detect_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/cam/realmonitor?channel=1&subtype=1"
        )

        # Normalize name for Frigate
        cam_name = self.normalize_name(name)

        # Try to get area and availability from entity registry
        area = self._find_area_for_device(entity_reg, area_reg, source_domain)
        available = self._check_availability(entity_reg, source_domain)

        # Use consistent source name for both
        source = "amcrest"  # Treat both as "amcrest" for consistency

        _LOGGER.debug(
            "Created %s camera via fast path: %s (host=%s, available=%s)",
            source_domain,
            cam_name,
            host,
            available,
        )

        return DiscoveredCamera(
            id=f"amcrest_{cam_name}",
            name=cam_name,
            friendly_name=name,
            source=source,
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=record_url,
            width=640,
            height=360,
            area=area,
            available=available,
        )

    async def _create_camera_from_entry(
        self,
        config_entry,
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
        domain: str,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from config entry (fallback path)."""
        entry_data = config_entry.data

        host = entry_data.get("host")
        username = entry_data.get("username", "admin")
        password = entry_data.get("password", "")
        port = entry_data.get("port", 554)

        if not host:
            _LOGGER.warning("%s config entry missing host", domain)
            return None

        # URL encode password
        encoded_password = quote(password, safe="")

        # Build RTSP URLs
        record_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/cam/realmonitor?channel=1&subtype=0"
        )
        detect_url = (
            f"rtsp://{username}:{encoded_password}@{host}:{port}"
            f"/cam/realmonitor?channel=1&subtype=1"
        )

        # Get friendly name
        friendly_name = entry_data.get("name", host)

        # Normalize name for Frigate
        cam_name = self.normalize_name(friendly_name)

        # Get area and availability
        area = self._find_area_for_device(entity_reg, area_reg, domain)
        available = self._check_availability(entity_reg, domain)

        _LOGGER.debug(
            "Created %s camera via entry: %s (host=%s)",
            domain,
            cam_name,
            host,
        )

        return DiscoveredCamera(
            id=f"amcrest_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="amcrest",  # Consistent source name
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=record_url,
            width=640,
            height=360,
            area=area,
            available=available,
        )

    def _find_area_for_device(
        self,
        entity_reg: er.EntityRegistry,
        area_reg: ar.AreaRegistry,
        domain: str,
    ) -> str | None:
        """Find area for a device by looking up related entities."""
        for entity in entity_reg.entities.values():
            if entity.platform != domain:
                continue
            if entity.area_id:
                area_entry = area_reg.async_get_area(entity.area_id)
                if area_entry:
                    return area_entry.name
        return None

    def _check_availability(
        self,
        entity_reg: er.EntityRegistry,
        domain: str,
    ) -> bool:
        """Check if camera is available by looking at entity states."""
        for entity in entity_reg.entities.values():
            if entity.domain != "camera" or entity.platform != domain:
                continue
            if entity.disabled:
                continue
            state = self.hass.states.get(entity.entity_id)
            if state:
                return state.state not in ("unavailable", "unknown")
        
        # Default to available if we can't determine
        return True
