"""Button entities for Frigate Config Builder.

Version: 0.4.0.3
Date: 2026-01-17

Provides:
- Generate Config: Create a new Frigate configuration file
- Push to Frigate: Send config to Frigate and restart
- Refresh Cameras: Re-scan for cameras from all integrations
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FRIGATE_URL, DOMAIN
from .output import push_to_frigate

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)

VERSION = "0.4.0.3"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frigate Config Builder button entities."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrigateConfigBuilderGenerateButton(coordinator, entry),
        FrigateConfigBuilderRefreshButton(coordinator, entry),
    ]

    # Only add Push button if Frigate URL is configured
    if entry.data.get(CONF_FRIGATE_URL):
        entities.append(FrigateConfigBuilderPushButton(coordinator, entry))

    async_add_entities(entities)


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
            sw_version=VERSION,
        )


class FrigateConfigBuilderGenerateButton(FrigateConfigBuilderButtonBase):
    """Button to generate Frigate configuration file."""

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
                translation_key="generate",
                icon="mdi:file-cog",
            ),
        )

    async def async_press(self) -> None:
        """Generate the Frigate configuration file."""
        _LOGGER.info("Generate Config button pressed")
        coordinator: FrigateConfigBuilderCoordinator = self.coordinator

        try:
            auto_push = self._entry.data.get("auto_push", False)
            await coordinator.async_generate_config(push=auto_push)

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
            _LOGGER.error("Failed to generate config: %s", err)
            self.hass.bus.async_fire(
                f"{DOMAIN}_error",
                {"error": str(err), "action": "generate"},
            )
            raise


class FrigateConfigBuilderPushButton(FrigateConfigBuilderButtonBase):
    """Button to push configuration to Frigate and restart."""

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the push button."""
        super().__init__(
            coordinator,
            entry,
            ButtonEntityDescription(
                key="push_to_frigate",
                translation_key="push_to_frigate",
                icon="mdi:upload-network",
            ),
        )

    async def async_press(self) -> None:
        """Push config to Frigate and restart."""
        _LOGGER.info("Push to Frigate button pressed")
        coordinator: FrigateConfigBuilderCoordinator = self.coordinator

        frigate_url = self._entry.data.get(CONF_FRIGATE_URL)
        if not frigate_url:
            _LOGGER.error("Frigate URL not configured")
            return

        try:
            # Generate fresh config first
            config_yaml = await coordinator.async_generate_config(push=False)

            # Push to Frigate
            success = await push_to_frigate(frigate_url, config_yaml, restart=True)

            if success:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_pushed_to_frigate",
                    {
                        "entry_id": self._entry.entry_id,
                        "frigate_url": frigate_url,
                        "camera_count": coordinator.cameras_selected_count,
                    },
                )
                _LOGGER.info("Successfully pushed config to Frigate")
            else:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_error",
                    {"error": "Failed to push config to Frigate", "action": "push"},
                )

        except Exception as err:
            _LOGGER.error("Failed to push to Frigate: %s", err)
            self.hass.bus.async_fire(
                f"{DOMAIN}_error",
                {"error": str(err), "action": "push"},
            )
            raise


class FrigateConfigBuilderRefreshButton(FrigateConfigBuilderButtonBase):
    """Button to refresh camera discovery."""

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
                translation_key="refresh_cameras",
                icon="mdi:camera-marker",
                entity_category=EntityCategory.CONFIG,
            ),
        )

    async def async_press(self) -> None:
        """Refresh camera discovery."""
        _LOGGER.info("Refresh Cameras button pressed")
        coordinator: FrigateConfigBuilderCoordinator = self.coordinator

        try:
            await coordinator.async_refresh()

            self.hass.bus.async_fire(
                f"{DOMAIN}_cameras_refreshed",
                {
                    "entry_id": self._entry.entry_id,
                    "camera_count": coordinator.cameras_discovered_count,
                    "new_cameras": coordinator.data.get("new_cameras", [])
                    if coordinator.data
                    else [],
                },
            )

            _LOGGER.info(
                "Refreshed cameras, found %d", coordinator.cameras_discovered_count
            )

        except Exception as err:
            _LOGGER.error("Failed to refresh cameras: %s", err)
            raise
