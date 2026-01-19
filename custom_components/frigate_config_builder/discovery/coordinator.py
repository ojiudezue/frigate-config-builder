"""Discovery coordinator - orchestrates all camera adapters.

Version: 0.4.0.5
Date: 2026-01-18

Changelog:
- 0.4.0.5: Run adapters in parallel, add Generic camera adapter
- 0.4.0.4: Initial version with sequential discovery
"""
from __future__ import annotations

import asyncio
import logging
import time
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
        self._adapter_timings: dict[str, float] = {}
        self._init_adapters()

    def _init_adapters(self) -> None:
        """Initialize all available camera adapters."""
        # Import adapters here to avoid circular imports
        from .unifiprotect import UniFiProtectAdapter
        from .amcrest import AmcrestAdapter
        from .reolink import ReolinkAdapter
        from .generic import GenericAdapter
        from .manual import ManualAdapter

        # Add all adapters - they self-check availability
        # Order doesn't matter since they run in parallel
        self._adapters = [
            UniFiProtectAdapter(self.hass, self.entry),
            AmcrestAdapter(self.hass, self.entry),
            ReolinkAdapter(self.hass, self.entry),
            GenericAdapter(self.hass, self.entry),
            ManualAdapter(self.hass, self.entry),
        ]

    async def _discover_from_adapter(
        self,
        adapter: CameraAdapter,
    ) -> tuple[str, list[DiscoveredCamera], float]:
        """Run discovery on a single adapter with timing.
        
        Returns:
            Tuple of (adapter_name, cameras, elapsed_seconds)
        """
        adapter_name = adapter.__class__.__name__
        domain = adapter.integration_domain
        start = time.monotonic()

        # Check if adapter's integration is available
        if not adapter.is_available() and domain != "manual":
            _LOGGER.debug(
                "%s: %s integration not configured, skipping",
                adapter_name,
                domain,
            )
            return (adapter_name, [], 0.0)

        try:
            _LOGGER.debug("%s: Starting discovery", adapter_name)
            cameras = await adapter.discover_cameras()
            elapsed = time.monotonic() - start

            _LOGGER.info(
                "%s: Discovered %d cameras in %.2fs",
                adapter_name,
                len(cameras),
                elapsed,
            )
            return (adapter_name, cameras, elapsed)

        except Exception as err:
            elapsed = time.monotonic() - start
            _LOGGER.error(
                "%s: Discovery failed after %.2fs: %s",
                adapter_name,
                elapsed,
                err,
                exc_info=True,
            )
            return (adapter_name, [], elapsed)

    async def discover_all(self) -> list[DiscoveredCamera]:
        """Run discovery on all available adapters in parallel.

        Returns:
            List of all discovered cameras from all sources.
        """
        all_cameras: list[DiscoveredCamera] = []
        discovered_ids: set[str] = set()
        self._adapter_timings = {}

        start_total = time.monotonic()

        # Run all adapters in parallel
        tasks = [
            self._discover_from_adapter(adapter)
            for adapter in self._adapters
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.error("Adapter task failed with exception: %s", result)
                continue
            
            adapter_name, cameras, elapsed = result
            self._adapter_timings[adapter_name] = elapsed

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

        # Sort cameras by friendly name for consistent ordering
        all_cameras.sort(key=lambda c: c.friendly_name.lower())

        total_elapsed = time.monotonic() - start_total
        _LOGGER.info(
            "Total discovered cameras: %d from %d adapters in %.2fs (parallel)",
            len(all_cameras),
            len(self._adapters),
            total_elapsed,
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

    def get_adapter_timings(self) -> dict[str, float]:
        """Return discovery timing for each adapter (in seconds)."""
        return self._adapter_timings.copy()
