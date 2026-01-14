"""Discovery coordinator - orchestrates all camera adapters."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class DiscoveryCoordinator:
    """Orchestrates camera discovery across all adapters."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the discovery coordinator."""
        self.hass = hass
        self.entry = entry
        self._adapters: list[CameraAdapter] = []
        self._init_adapters()

    def _init_adapters(self) -> None:
        """Initialize all available camera adapters."""
        # Import adapters here to avoid circular imports
        from .unifiprotect import UniFiProtectAdapter
        from .amcrest import AmcrestAdapter
        from .reolink import ReolinkAdapter
        from .manual import ManualAdapter

        # Add all adapters - they self-check availability
        self._adapters = [
            UniFiProtectAdapter(self.hass, self.entry),
            AmcrestAdapter(self.hass, self.entry),
            ReolinkAdapter(self.hass, self.entry),
            ManualAdapter(self.hass, self.entry),
        ]

    async def discover_all(self) -> list[DiscoveredCamera]:
        """Run discovery on all available adapters.

        Returns:
            List of all discovered cameras from all sources.
        """
        all_cameras: list[DiscoveredCamera] = []
        discovered_ids: set[str] = set()

        for adapter in self._adapters:
            adapter_name = adapter.__class__.__name__
            domain = adapter.integration_domain

            # Check if adapter's integration is available
            if not adapter.is_available() and domain != "manual":
                _LOGGER.debug(
                    "%s: %s integration not configured, skipping",
                    adapter_name,
                    domain,
                )
                continue

            try:
                _LOGGER.debug("%s: Starting discovery", adapter_name)
                cameras = await adapter.discover_cameras()

                # Deduplicate by camera ID
                for camera in cameras:
                    if camera.id not in discovered_ids:
                        all_cameras.append(camera)
                        discovered_ids.add(camera.id)
                    else:
                        _LOGGER.warning(
                            "Duplicate camera ID %s from %s, skipping",
                            camera.id,
                            adapter_name,
                        )

                _LOGGER.info(
                    "%s: Discovered %d cameras",
                    adapter_name,
                    len(cameras),
                )

            except Exception as err:
                _LOGGER.error(
                    "%s: Discovery failed: %s",
                    adapter_name,
                    err,
                    exc_info=True,
                )

        # Sort cameras by friendly name for consistent ordering
        all_cameras.sort(key=lambda c: c.friendly_name.lower())

        _LOGGER.info(
            "Total discovered cameras: %d from %d adapters",
            len(all_cameras),
            len(self._adapters),
        )

        return all_cameras

    def get_available_adapters(self) -> list[str]:
        """Return list of adapter domains that are available."""
        return [
            adapter.integration_domain
            for adapter in self._adapters
            if adapter.is_available() or adapter.integration_domain == "manual"
        ]

    def get_adapter_status(self) -> dict[str, bool]:
        """Return availability status of each adapter."""
        return {
            adapter.integration_domain: (
                adapter.is_available() or adapter.integration_domain == "manual"
            )
            for adapter in self._adapters
        }
