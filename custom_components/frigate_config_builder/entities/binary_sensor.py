"""Binary sensor entities for Frigate Config Builder.

Version: 0.3.0.0
Date: 2026-01-17

Provides:
- Config Stale: Indicates when the generated config is out of date
  (new cameras discovered or cameras removed since last generation)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrigateConfigBuilderConfigStaleSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class FrigateConfigBuilderConfigStaleSensor(
    CoordinatorEntity["FrigateConfigBuilderCoordinator"], BinarySensorEntity
):
    """Binary sensor indicating if the config is stale."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = BinarySensorEntityDescription(
            key="config_stale",
            translation_key="config_stale",
            icon="mdi:alert-circle-outline",
            device_class=BinarySensorDeviceClass.PROBLEM,
        )
        self._attr_unique_id = f"{entry.entry_id}_config_stale"

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

    @property
    def is_on(self) -> bool:
        """Return True if config is stale (needs regeneration)."""
        return self.coordinator.config_stale

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            "last_generated": (
                self.coordinator.last_generated.isoformat()
                if self.coordinator.last_generated
                else None
            ),
        }

        # Include info about what changed
        if self.coordinator.config_stale:
            new_cameras = [
                cam.name
                for cam in self.coordinator.discovered_cameras
                if cam.is_new
            ]
            if new_cameras:
                attrs["new_cameras"] = new_cameras
                attrs["reason"] = "new_cameras_discovered"
            else:
                attrs["reason"] = "cameras_changed"

        return attrs
