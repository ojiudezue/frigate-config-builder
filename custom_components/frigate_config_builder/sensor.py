"""Sensor entities for Frigate Config Builder.

Version: 0.4.0.0
Date: 2026-01-17

Provides:
- Cameras Selected: Count of cameras selected for config generation
- Cameras Found: Total discovered cameras across all integrations
- Last Generated: Timestamp of last config generation
- Discovery Status: Per-adapter discovery stats and timing
- Frigate Status: Connection status to Frigate (if URL configured)
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FRIGATE_URL, DOMAIN

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
    """Set up sensor entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CamerasSelectedSensor(coordinator, entry),
        CamerasFoundSensor(coordinator, entry),
        LastGeneratedSensor(coordinator, entry),
        DiscoveryStatusSensor(coordinator, entry),
    ]

    # Add Frigate status sensor if URL is configured
    if entry.data.get(CONF_FRIGATE_URL):
        entities.append(FrigateStatusSensor(coordinator, entry))

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
            sw_version=VERSION,
        )


class CamerasSelectedSensor(FrigateConfigBuilderBaseSensor):
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
                state_class=SensorStateClass.MEASUREMENT,
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
            "by_source": {
                source: len([c for c in cams if c in selected])
                for source, cams in self.coordinator.get_cameras_by_source().items()
            },
        }


class CamerasFoundSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing total discovered cameras."""

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
                state_class=SensorStateClass.MEASUREMENT,
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the number of discovered cameras."""
        return self.coordinator.cameras_discovered_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return camera details."""
        cameras = self.coordinator.discovered_cameras
        by_source = self.coordinator.get_cameras_by_source()
        by_area = self.coordinator.get_cameras_by_area()

        available = [c for c in cameras if c.available]
        unavailable = [c for c in cameras if not c.available]
        new = [c for c in cameras if c.is_new]

        return {
            "available": len(available),
            "unavailable": len(unavailable),
            "new": len(new),
            "by_source": {source: len(cams) for source, cams in by_source.items()},
            "by_area": {area: len(cams) for area, cams in by_area.items()},
            "cameras": [
                {
                    "name": cam.name,
                    "source": cam.source,
                    "area": cam.area,
                    "available": cam.available,
                    "new": cam.is_new,
                }
                for cam in cameras
            ],
        }


class LastGeneratedSensor(FrigateConfigBuilderBaseSensor):
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
        """Return generation details."""
        attrs: dict[str, Any] = {
            "output_path": self._entry.data.get("output_path"),
        }

        if self.coordinator.last_generated:
            attrs["cameras_included"] = self.coordinator.cameras_selected_count
            attrs["generation_time_seconds"] = round(
                self.coordinator.last_generation_duration, 2
            )

        return attrs


class DiscoveryStatusSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing discovery status and timing."""

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
                key="discovery_status",
                translation_key="discovery_status",
                icon="mdi:magnify-scan",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        )

    @property
    def native_value(self) -> str:
        """Return current discovery status."""
        if not self.coordinator.data:
            return "pending"

        count = self.coordinator.cameras_discovered_count
        if count == 0:
            return "no cameras"
        return f"{count} cameras"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed discovery info."""
        adapter_status = {}
        if self.coordinator.data:
            adapter_status = self.coordinator.data.get("adapter_status", {})

        return {
            "adapters": adapter_status,
            "last_discovery": self.coordinator.last_updated.isoformat()
            if hasattr(self.coordinator, "last_updated") and self.coordinator.last_updated
            else None,
        }


class FrigateStatusSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing Frigate connection status."""

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
                key="frigate_status",
                translation_key="frigate_status",
                icon="mdi:cctv",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        )
        self._frigate_version: str | None = None
        self._frigate_uptime: str | None = None
        self._last_check: datetime | None = None

    @property
    def native_value(self) -> str:
        """Return Frigate connection status."""
        if self._frigate_version:
            return f"v{self._frigate_version}"
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Frigate details."""
        return {
            "url": self._entry.data.get(CONF_FRIGATE_URL),
            "version": self._frigate_version,
            "uptime": self._frigate_uptime,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }

    async def async_update(self) -> None:
        """Fetch Frigate status."""
        frigate_url = self._entry.data.get(CONF_FRIGATE_URL)
        if not frigate_url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{frigate_url.rstrip('/')}/api/stats",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._frigate_version = data.get("service", {}).get("version")
                        self._frigate_uptime = str(data.get("service", {}).get("uptime"))
                        self._last_check = datetime.now()
        except Exception as err:
            _LOGGER.debug("Could not fetch Frigate status: %s", err)
            self._frigate_version = None
