"""Frigate Config Builder integration for Home Assistant.

Version: 0.4.0.0
Date: 2026-01-17

Automatically discovers cameras from your Home Assistant integrations
(UniFi Protect, Reolink, generic RTSP, etc.) and generates a complete
Frigate NVR configuration file with one click.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import FrigateConfigBuilderCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# Platforms to set up
PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

# Discovery timing - allow other integrations to fully initialize
DISCOVERY_STARTUP_DELAY = 5  # seconds - fast initial attempt
DISCOVERY_RETRY_DELAY = 15  # seconds - retry if no cameras found


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Frigate Config Builder component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Frigate Config Builder from a config entry."""
    _LOGGER.debug("Setting up Frigate Config Builder entry: %s", entry.entry_id)

    coordinator = FrigateConfigBuilderCoordinator(hass, entry)

    # Store coordinator early so platforms can access it
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms first (they'll show "loading" state)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Schedule delayed discovery to allow other integrations to fully load
    async def delayed_first_discovery():
        """Run first discovery after a short delay."""
        await asyncio.sleep(DISCOVERY_STARTUP_DELAY)

        _LOGGER.info("Running initial camera discovery...")
        await coordinator.async_refresh()

        # If no cameras found, retry with longer delay
        if coordinator.cameras_discovered_count == 0:
            _LOGGER.info(
                "No cameras found initially, retrying in %ds...",
                DISCOVERY_RETRY_DELAY,
            )
            await asyncio.sleep(DISCOVERY_RETRY_DELAY)
            await coordinator.async_refresh()

        # Fire discovery complete event
        hass.bus.async_fire(
            f"{DOMAIN}_discovery_complete",
            {
                "camera_count": coordinator.cameras_discovered_count,
                "sources": list(coordinator.get_cameras_by_source().keys()),
            },
        )

        _LOGGER.info(
            "Camera discovery complete: found %d cameras",
            coordinator.cameras_discovered_count,
        )

    # Start background discovery
    entry.async_create_background_task(
        hass,
        delayed_first_discovery(),
        "frigate_config_builder_discovery",
    )

    _LOGGER.info(
        "Frigate Config Builder initialized, discovery starting in %ds",
        DISCOVERY_STARTUP_DELAY,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Frigate Config Builder entry: %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Options updated for Frigate Config Builder")
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, "generate"):
        return

    async def handle_generate(call: ServiceCall) -> None:
        """Handle the generate service call."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Frigate Config Builder entries configured")
            return

        coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][
            entries[0].entry_id
        ]
        push = call.data.get("push", False)

        try:
            await coordinator.async_generate_config(push=push)
            hass.bus.async_fire(
                f"{DOMAIN}_config_generated",
                {
                    "camera_count": coordinator.cameras_selected_count,
                    "output_path": entries[0].data.get("output_path"),
                    "pushed": push,
                },
            )
        except Exception as err:
            _LOGGER.error("Failed to generate Frigate config: %s", err)
            raise

    async def handle_refresh_cameras(call: ServiceCall) -> None:
        """Handle the refresh_cameras service call."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Frigate Config Builder entries configured")
            return

        coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][
            entries[0].entry_id
        ]

        try:
            await coordinator.async_refresh()
            hass.bus.async_fire(
                f"{DOMAIN}_cameras_refreshed",
                {
                    "camera_count": coordinator.cameras_discovered_count,
                    "new_cameras": [
                        c.name for c in coordinator.discovered_cameras if c.is_new
                    ],
                },
            )
        except Exception as err:
            _LOGGER.error("Failed to refresh cameras: %s", err)
            raise

    hass.services.async_register(DOMAIN, "generate", handle_generate)
    hass.services.async_register(DOMAIN, "refresh_cameras", handle_refresh_cameras)
    _LOGGER.debug("Registered Frigate Config Builder services")
