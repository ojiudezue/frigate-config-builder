"""Generic camera discovery adapter.

Version: 0.4.0.5
Date: 2026-01-18

Discovers cameras from the Home Assistant "Generic Camera" integration.
This integration is used for standalone RTSP cameras that aren't part of
a specific manufacturer's integration.

The generic integration stores RTSP URLs directly in config entries,
making discovery extremely fast (no API calls needed).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import quote, urlparse

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class GenericAdapter(CameraAdapter):
    """Discover cameras from Generic Camera integration.

    The Generic Camera integration allows users to add any RTSP camera
    directly via the Home Assistant UI. Camera URLs are stored in
    config entries, making discovery instant.

    Config entry data typically contains:
    - stream_source: RTSP URL for the stream
    - still_image_url: Optional snapshot URL
    - username: Optional username
    - password: Optional password
    - authentication: "basic" or "digest"
    """

    @property
    def integration_domain(self) -> str:
        """Return the HA integration domain."""
        return "generic"

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all Generic cameras (instant - no API calls)."""
        if not self.is_available():
            _LOGGER.debug("Generic camera integration not configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        # Get all generic camera config entries
        generic_entries = self.hass.config_entries.async_entries("generic")

        for config_entry in generic_entries:
            try:
                camera = self._create_camera_from_entry(
                    config_entry, entity_reg, device_reg, area_reg
                )
                if camera:
                    cameras.append(camera)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to process Generic camera %s: %s",
                    config_entry.title,
                    err,
                    exc_info=True,
                )

        _LOGGER.info("Discovered %d Generic cameras", len(cameras))
        return cameras

    def _create_camera_from_entry(
        self,
        config_entry,
        entity_reg: er.EntityRegistry,
        device_reg: dr.DeviceRegistry,
        area_reg: ar.AreaRegistry,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from generic config entry."""
        entry_data = config_entry.data
        entry_options = config_entry.options

        # Get stream URL - check both data and options
        stream_url = (
            entry_options.get("stream_source")
            or entry_data.get("stream_source")
        )

        if not stream_url:
            _LOGGER.debug(
                "Generic camera %s has no stream_source, skipping",
                config_entry.title,
            )
            return None

        # Get credentials if provided
        username = entry_options.get("username") or entry_data.get("username")
        password = entry_options.get("password") or entry_data.get("password")

        # Build authenticated URL if credentials provided
        record_url = self._build_authenticated_url(stream_url, username, password)

        # Use entry title as friendly name
        friendly_name = config_entry.title or "Generic Camera"

        # Normalize name for Frigate
        cam_name = self.normalize_name(friendly_name)

        # Find the camera entity for this config entry
        entity = self._find_entity_for_entry(config_entry.entry_id, entity_reg)

        # Get area
        area = None
        if entity and entity.area_id:
            area_entry = area_reg.async_get_area(entity.area_id)
            area = area_entry.name if area_entry else None

        # Check availability
        available = True
        if entity:
            state = self.hass.states.get(entity.entity_id)
            available = state is not None and state.state not in ("unavailable", "unknown")

        _LOGGER.debug(
            "Created Generic camera: %s (available=%s)",
            cam_name,
            available,
        )

        return DiscoveredCamera(
            id=f"generic_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="generic",
            record_url=record_url,
            detect_url=record_url,  # Same URL for both
            go2rtc_url=record_url,
            width=640,
            height=360,
            area=area,
            available=available,
        )

    def _build_authenticated_url(
        self,
        url: str,
        username: str | None,
        password: str | None,
    ) -> str:
        """Build RTSP URL with embedded credentials if provided."""
        if not username:
            return url

        # Parse the URL
        parsed = urlparse(url)

        # URL encode credentials
        encoded_user = quote(username, safe="")
        encoded_pass = quote(password or "", safe="")

        # Rebuild URL with credentials
        if parsed.port:
            netloc = f"{encoded_user}:{encoded_pass}@{parsed.hostname}:{parsed.port}"
        else:
            netloc = f"{encoded_user}:{encoded_pass}@{parsed.hostname}"

        # Reconstruct URL
        new_url = f"{parsed.scheme}://{netloc}{parsed.path}"
        if parsed.query:
            new_url += f"?{parsed.query}"

        return new_url

    def _find_entity_for_entry(
        self,
        entry_id: str,
        entity_reg: er.EntityRegistry,
    ) -> er.RegistryEntry | None:
        """Find the camera entity for a config entry."""
        for entity in entity_reg.entities.values():
            if (
                entity.config_entry_id == entry_id
                and entity.domain == "camera"
                and not entity.disabled
            ):
                return entity
        return None
