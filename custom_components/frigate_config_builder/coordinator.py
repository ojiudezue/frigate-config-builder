"""Data coordinator for Frigate Config Builder.

Version: 0.4.0.0
Date: 2026-01-17
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_EXCLUDE_UNAVAILABLE, CONF_SELECTED_CAMERAS, DOMAIN
from .discovery import DiscoveryCoordinator
from .generator import FrigateConfigGenerator
from .output import push_to_frigate, write_config_file

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .discovery import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)


class FrigateConfigBuilderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage camera discovery and config generation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )
        self.entry = entry
        self.discovery = DiscoveryCoordinator(hass, entry)
        self.generator = FrigateConfigGenerator(hass, entry)

        # State tracking
        self.discovered_cameras: list[DiscoveredCamera] = []
        self.last_generated: datetime | None = None
        self.last_generation_duration: float = 0
        self.config_stale: bool = False
        self._previous_camera_ids: set[str] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from all discovery adapters."""
        _LOGGER.debug("Running camera discovery")

        self.discovered_cameras = await self.discovery.discover_all()

        current_ids = {cam.id for cam in self.discovered_cameras}
        selected = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))

        for cam in self.discovered_cameras:
            cam.is_new = cam.id not in self._previous_camera_ids

        if self._previous_camera_ids and current_ids != self._previous_camera_ids:
            self.config_stale = True
            _LOGGER.info("Camera configuration has changed, config is stale")

        self._previous_camera_ids = current_ids

        adapter_status = self.discovery.get_adapter_status()

        return {
            "cameras": self.discovered_cameras,
            "camera_count": len(self.discovered_cameras),
            "selected_count": len(selected & current_ids),
            "adapter_status": adapter_status,
            "new_cameras": [c.id for c in self.discovered_cameras if c.is_new],
        }

    async def async_generate_config(self, push: bool = False) -> str:
        """Generate Frigate configuration file."""
        import time

        start = time.monotonic()

        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        exclude_unavailable = self.entry.options.get(CONF_EXCLUDE_UNAVAILABLE, True)

        if selected_ids:
            cameras = [c for c in self.discovered_cameras if c.id in selected_ids]
        else:
            cameras = self.discovered_cameras
            _LOGGER.info(
                "No cameras explicitly selected, using all %d discovered cameras",
                len(cameras),
            )

        if exclude_unavailable:
            original_count = len(cameras)
            cameras = [c for c in cameras if c.available]
            if original_count != len(cameras):
                _LOGGER.info(
                    "Excluded %d unavailable cameras from generation",
                    original_count - len(cameras),
                )

        config_yaml = await self.generator.generate(cameras)

        output_path = self.entry.data.get("output_path", "/config/www/frigate.yml")
        await write_config_file(self.hass, output_path, config_yaml)

        frigate_url = self.entry.data.get("frigate_url")
        if push and frigate_url:
            await push_to_frigate(frigate_url, config_yaml, restart=True)

        self.last_generated = datetime.now()
        self.last_generation_duration = time.monotonic() - start
        self.config_stale = False

        _LOGGER.info(
            "Generated Frigate config with %d cameras in %.2fs",
            len(cameras),
            self.last_generation_duration,
        )

        return config_yaml

    @property
    def selected_cameras(self) -> list[DiscoveredCamera]:
        """Return only selected cameras (respecting exclude_unavailable)."""
        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        exclude_unavailable = self.entry.options.get(CONF_EXCLUDE_UNAVAILABLE, True)

        if selected_ids:
            cameras = [c for c in self.discovered_cameras if c.id in selected_ids]
        else:
            cameras = self.discovered_cameras

        if exclude_unavailable:
            cameras = [c for c in cameras if c.available]

        return cameras

    @property
    def cameras_selected_count(self) -> int:
        """Return count of selected cameras."""
        return len(self.selected_cameras)

    @property
    def cameras_discovered_count(self) -> int:
        """Return count of discovered cameras."""
        return len(self.discovered_cameras)

    def get_cameras_by_source(self) -> dict[str, list[DiscoveredCamera]]:
        """Return discovered cameras grouped by source."""
        by_source: dict[str, list[DiscoveredCamera]] = {}
        for camera in self.discovered_cameras:
            source = camera.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(camera)
        return by_source

    def get_cameras_by_area(self) -> dict[str, list[DiscoveredCamera]]:
        """Return discovered cameras grouped by HA area."""
        by_area: dict[str, list[DiscoveredCamera]] = {}
        for camera in self.discovered_cameras:
            area = camera.area or "Ungrouped"
            if area not in by_area:
                by_area[area] = []
            by_area[area].append(camera)
        return by_area
