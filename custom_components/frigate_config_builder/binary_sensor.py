"""Binary sensor entities for Frigate Config Builder.

Version: 0.4.0.2
Date: 2026-01-17

Provides:
- Config Needs Update: Turns on when camera configuration has changed
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

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)

VERSION = "0.4.0.0"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        ConfigStaleBinarySensor(coordinator, entry),
    ])


class ConfigStaleBinarySensor(
    CoordinatorEntity["FrigateConfigBuilderCoordinator"], BinarySensorEntity
):
    """Binary sensor indicating if config needs regeneration."""

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
            device_class=BinarySensorDeviceClass.PROBLEM,
            icon="mdi:file-alert",
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
            sw_version=VERSION,
        )

    @property
    def is_on(self) -> bool:
        """Return true if config is stale (needs regeneration)."""
        return self.coordinator.config_stale

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self.coordinator.data:
            new_cameras = self.coordinator.data.get("new_cameras", [])
            if new_cameras:
                attrs["new_cameras"] = new_cameras
                attrs["reason"] = "New cameras discovered"

        if self.coordinator.last_generated:
            attrs["last_generated"] = self.coordinator.last_generated.isoformat()

        return attrs
