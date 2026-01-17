"""Sensor entities for Frigate Config Builder.

Version: 0.3.0.2
Date: 2026-01-17

Provides:
- Cameras Selected: Count of cameras selected for config generation
- Cameras Discovered: Count of all discovered cameras
- Last Generated: Timestamp of last config generation
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrigateConfigBuilderCamerasSelectedSensor(coordinator, entry),
        FrigateConfigBuilderCamerasDiscoveredSensor(coordinator, entry),
        FrigateConfigBuilderLastGeneratedSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class FrigateConfigBuilderBaseSensor(
    CoordinatorEntity["FrigateConfigBuilderCoordinator"], SensorEntity
):
    """Base class for Frigate Config Builder sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
            sw_version="0.3.0.2",
        )


class FrigateConfigBuilderCamerasSelectedSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing count of selected cameras."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="cameras_selected",
                translation_key="cameras_selected",
                icon="mdi:camera-iris",
                native_unit_of_measurement="cameras",
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the number of selected cameras."""
        return self.coordinator.cameras_selected_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        selected = self.coordinator.selected_cameras
        return {
            "cameras": [cam.name for cam in selected],
            "cameras_by_source": {
                source: [c.name for c in cams]
                for source, cams in self.coordinator.get_cameras_by_source().items()
                if any(c.id in {s.id for s in selected} for c in cams)
            },
        }


class FrigateConfigBuilderCamerasDiscoveredSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing count of discovered cameras."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="cameras_discovered",
                translation_key="cameras_discovered",
                icon="mdi:camera-wireless",
                native_unit_of_measurement="cameras",
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the number of discovered cameras."""
        return self.coordinator.cameras_discovered_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with camera details."""
        cameras = self.coordinator.discovered_cameras
        by_source = self.coordinator.get_cameras_by_source()
        by_area = self.coordinator.get_cameras_by_area()

        return {
            "cameras": [
                {
                    "id": cam.id,
                    "name": cam.name,
                    "friendly_name": cam.friendly_name,
                    "source": cam.source,
                    "area": cam.area,
                    "available": cam.available,
                    "is_new": cam.is_new,
                }
                for cam in cameras
            ],
            "by_source": {source: len(cams) for source, cams in by_source.items()},
            "by_area": {area: len(cams) for area, cams in by_area.items()},
            "new_cameras": [cam.name for cam in cameras if cam.is_new],
            "unavailable_cameras": [cam.name for cam in cameras if not cam.available],
        }


class FrigateConfigBuilderLastGeneratedSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing when config was last generated."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="last_generated",
                translation_key="last_generated",
                icon="mdi:clock-check-outline",
                device_class=SensorDeviceClass.TIMESTAMP,
            ),
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of last generation."""
        return self.coordinator.last_generated

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            "output_path": self._entry.data.get("output_path"),
        }

        if self.coordinator.last_generated:
            attrs["camera_count"] = self.coordinator.cameras_selected_count
            attrs["duration_seconds"] = round(
                self.coordinator.last_generation_duration, 2
            )

        return attrs
