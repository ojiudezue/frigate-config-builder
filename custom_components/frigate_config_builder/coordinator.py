"""Data coordinator for Frigate Config Builder."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_SELECTED_CAMERAS, DOMAIN
from .generator import FrigateConfigGenerator
from .output import push_to_frigate, write_config_file

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .models import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)


class FrigateConfigBuilderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage camera discovery and config generation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),  # Periodic discovery refresh
        )
        self.entry = entry
        self.generator = FrigateConfigGenerator(hass, entry)

        # State tracking
        self.discovered_cameras: list[DiscoveredCamera] = []
        self.last_generated: datetime | None = None
        self.last_generation_duration: float = 0
        self.config_stale: bool = False
        self._previous_camera_ids: set[str] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from all discovery adapters.

        For Milestone 1, this is a placeholder that returns empty data.
        Camera discovery will be implemented in Milestone 2.
        """
        _LOGGER.debug("Running camera discovery (M1: placeholder)")

        # M1: No discovery yet, return empty
        # M2: Will integrate discovery coordinator here
        self.discovered_cameras = []

        # Check if cameras changed (new or removed)
        current_ids = {cam.id for cam in self.discovered_cameras}
        selected = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))

        # Mark new cameras
        for cam in self.discovered_cameras:
            cam.is_new = cam.id not in self._previous_camera_ids

        # Detect staleness
        if self._previous_camera_ids and current_ids != self._previous_camera_ids:
            self.config_stale = True
            _LOGGER.info("Camera configuration has changed, config is stale")

        self._previous_camera_ids = current_ids

        return {
            "cameras": self.discovered_cameras,
            "camera_count": len(self.discovered_cameras),
            "selected_count": len(selected & current_ids),
        }

    async def async_generate_config(self, push: bool = False) -> str:
        """Generate Frigate configuration file.

        Args:
            push: Whether to push to Frigate API after writing file

        Returns:
            Generated YAML configuration string
        """
        import time

        start = time.monotonic()

        # Filter to selected cameras only
        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        cameras = [c for c in self.discovered_cameras if c.id in selected_ids]

        # Generate config
        config_yaml = await self.generator.generate(cameras)

        # Write to file
        output_path = self.entry.data.get("output_path", "/config/www/frigate.yml")
        await write_config_file(self.hass, output_path, config_yaml)

        # Optionally push to Frigate
        frigate_url = self.entry.data.get("frigate_url")
        if push and frigate_url:
            await push_to_frigate(frigate_url, config_yaml, restart=True)

        # Update state
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
        """Return only selected cameras."""
        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        return [c for c in self.discovered_cameras if c.id in selected_ids]

    @property
    def cameras_selected_count(self) -> int:
        """Return count of selected cameras."""
        return len(self.selected_cameras)

    @property
    def cameras_discovered_count(self) -> int:
        """Return count of discovered cameras."""
        return len(self.discovered_cameras)
