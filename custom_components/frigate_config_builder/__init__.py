"""Frigate Config Builder integration for Home Assistant.

Version: 0.3.0.0
Date: 2026-01-17

This integration auto-discovers cameras from various HA integrations
and generates complete Frigate NVR configuration files.

Milestone 3: Added button, sensor, and binary_sensor entities.
"""
from __future__ import annotations

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Frigate Config Builder component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Frigate Config Builder from a config entry."""
    _LOGGER.debug("Setting up Frigate Config Builder entry: %s", entry.entry_id)

    coordinator = FrigateConfigBuilderCoordinator(hass, entry)

    # Perform initial refresh
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Fire discovery complete event
    hass.bus.async_fire(
        f"{DOMAIN}_discovery_complete",
        {
            "camera_count": coordinator.cameras_discovered_count,
            "new_cameras": [c.name for c in coordinator.discovered_cameras if c.is_new],
        },
    )

    _LOGGER.info(
        "Frigate Config Builder set up successfully with %d cameras discovered",
        coordinator.cameras_discovered_count,
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
    # Reload the entry to apply new options
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    # Only register once
    if hass.services.has_service(DOMAIN, "generate"):
        return

    async def handle_generate(call: ServiceCall) -> None:
        """Handle the generate service call."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Frigate Config Builder entries configured")
            return

        # Use first entry (single instance design)
        coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entries[0].entry_id]
        push = call.data.get("push", False)

        try:
            await coordinator.async_generate_config(push=push)

            # Fire event for automations
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

        coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entries[0].entry_id]

        try:
            await coordinator.async_refresh()

            # Fire event for automations
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

    # Register services
    hass.services.async_register(
        DOMAIN,
        "generate",
        handle_generate,
    )

    hass.services.async_register(
        DOMAIN,
        "refresh_cameras",
        handle_refresh_cameras,
    )

    _LOGGER.debug("Registered Frigate Config Builder services")
