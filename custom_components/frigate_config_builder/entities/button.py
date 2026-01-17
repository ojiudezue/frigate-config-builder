"""Button entity for Frigate Config Builder.

Version: 0.3.0.0
Date: 2026-01-17

Provides:
- Generate Config button to trigger Frigate configuration generation
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)

BUTTON_DESCRIPTIONS = [
    ButtonEntityDescription(
        key="generate",
        translation_key="generate",
        icon="mdi:file-cog-outline",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrigateConfigBuilderGenerateButton(coordinator, entry, description)
        for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)


class FrigateConfigBuilderGenerateButton(
    CoordinatorEntity["FrigateConfigBuilderCoordinator"], ButtonEntity
):
    """Button to trigger Frigate config generation."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Frigate Config Builder",
            manufacturer="Community",
            model="Config Builder",
            sw_version="0.3.0.0",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Generate Config button pressed")

        try:
            # Get auto_push setting from config
            auto_push = self._entry.data.get("auto_push", False)

            # Generate the config
            await self.coordinator.async_generate_config(push=auto_push)

            _LOGGER.info(
                "Config generated successfully with %d cameras",
                self.coordinator.cameras_selected_count,
            )

            # Fire event for automations
            self.hass.bus.async_fire(
                f"{DOMAIN}_config_generated",
                {
                    "camera_count": self.coordinator.cameras_selected_count,
                    "output_path": self._entry.data.get("output_path"),
                    "pushed": auto_push,
                },
            )

        except Exception as err:
            _LOGGER.error("Failed to generate config: %s", err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "cameras_selected": self.coordinator.cameras_selected_count,
            "cameras_discovered": self.coordinator.cameras_discovered_count,
            "output_path": self._entry.data.get("output_path"),
        }
