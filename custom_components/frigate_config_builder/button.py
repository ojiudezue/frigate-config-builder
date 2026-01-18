"""Button entities for Frigate Config Builder.

Version: 0.3.0.3
Date: 2026-01-17

Provides:
- Generate Config button to trigger Frigate configuration generation
- Refresh Cameras button to trigger camera discovery
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frigate Config Builder button entities."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        FrigateConfigBuilderGenerateButton(coordinator, entry),
        FrigateConfigBuilderRefreshButton(coordinator, entry),
    ])


class FrigateConfigBuilderButtonBase(CoordinatorEntity, ButtonEntity):
    """Base button entity for Frigate Config Builder."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Frigate Config Builder",
            manufacturer="Community",
            model="Config Builder",
            sw_version="0.3.0.3",
        )


class FrigateConfigBuilderGenerateButton(FrigateConfigBuilderButtonBase):
    """Button to trigger Frigate config generation."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the generate button."""
        super().__init__(
            coordinator,
            entry,
            ButtonEntityDescription(
                key="generate",
                name="Generate Config",
                icon="mdi:file-cog",
            ),
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Generate Config button pressed")
        coordinator: FrigateConfigBuilderCoordinator = self.coordinator

        try:
            # Check if auto-push is enabled
            auto_push = self._entry.data.get("auto_push", False)

            # Generate the config
            config_yaml = await coordinator.async_generate_config(push=auto_push)

            # Fire an event for automations
            self.hass.bus.async_fire(
                f"{DOMAIN}_config_generated",
                {
                    "entry_id": self._entry.entry_id,
                    "camera_count": coordinator.cameras_selected_count,
                    "output_path": self._entry.data.get("output_path"),
                    "auto_pushed": auto_push,
                },
            )

            _LOGGER.info(
                "Generated Frigate config with %d cameras",
                coordinator.cameras_selected_count,
            )

        except Exception as err:
            _LOGGER.error("Failed to generate Frigate config: %s", err)
            # Fire error event
            self.hass.bus.async_fire(
                f"{DOMAIN}_config_generation_failed",
                {
                    "entry_id": self._entry.entry_id,
                    "error": str(err),
                },
            )
            raise


class FrigateConfigBuilderRefreshButton(FrigateConfigBuilderButtonBase):
    """Button to trigger camera discovery refresh."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the refresh button."""
        super().__init__(
            coordinator,
            entry,
            ButtonEntityDescription(
                key="refresh_cameras",
                name="Refresh Cameras",
                icon="mdi:camera-marker",
                entity_category=EntityCategory.CONFIG,
            ),
        )

    async def async_press(self) -> None:
        """Handle the button press - trigger camera discovery."""
        _LOGGER.info("Refresh Cameras button pressed")
        coordinator: FrigateConfigBuilderCoordinator = self.coordinator

        try:
            # Force a coordinator refresh which runs discovery
            await coordinator.async_refresh()

            # Fire an event for automations
            self.hass.bus.async_fire(
                f"{DOMAIN}_cameras_refreshed",
                {
                    "entry_id": self._entry.entry_id,
                    "camera_count": coordinator.cameras_discovered_count,
                    "new_cameras": coordinator.data.get("new_cameras", []) if coordinator.data else [],
                },
            )

            _LOGGER.info(
                "Refreshed camera discovery, found %d cameras",
                coordinator.cameras_discovered_count,
            )

        except Exception as err:
            _LOGGER.error("Failed to refresh cameras: %s", err)
            raise
