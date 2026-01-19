"""Sensor entities for Frigate Config Builder.

Version: 0.4.0.5
Date: 2026-01-18

Provides:
- Cameras Selected: Count of cameras selected for config generation
- Cameras Found: Total discovered cameras across all integrations
- Last Generated: Timestamp of last config generation
- Discovery Status: Per-adapter discovery stats and timing
- Frigate Status: Connection status to Frigate (if URL configured)
- Frigate Releases: Latest stable and beta releases from GitHub
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_FRIGATE_URL, CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION, DOMAIN

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FrigateConfigBuilderCoordinator

_LOGGER = logging.getLogger(__name__)

VERSION = "0.4.0.5"

# How often to poll Frigate status
FRIGATE_POLL_INTERVAL = timedelta(minutes=5)

# How often to auto-check for Frigate releases (once per day)
FRIGATE_RELEASES_POLL_INTERVAL = timedelta(hours=24)

# GitHub API endpoint for Frigate releases
FRIGATE_RELEASES_URL = "https://api.github.com/repos/blakeblackshear/frigate/releases"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: FrigateConfigBuilderCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create releases sensor and store reference for button access
    releases_sensor = FrigateReleasesSensor(coordinator, entry, hass)

    entities: list[SensorEntity] = [
        CamerasSelectedSensor(coordinator, entry),
        CamerasFoundSensor(coordinator, entry),
        LastGeneratedSensor(coordinator, entry),
        DiscoveryStatusSensor(coordinator, entry),
        releases_sensor,
    ]

    # Store releases sensor reference in hass.data for button to access
    hass.data[DOMAIN][f"{entry.entry_id}_releases_sensor"] = releases_sensor

    # Add Frigate status sensor if URL is configured
    if entry.data.get(CONF_FRIGATE_URL):
        entities.append(FrigateStatusSensor(coordinator, entry, hass))

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
    """Sensor showing Frigate connection status.

    This sensor polls the Frigate API independently of the coordinator
    to check connection status and version.
    """

    # Enable polling for this sensor (CoordinatorEntity disables it by default)
    _attr_should_poll = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
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
        self._hass = hass
        self._frigate_version: str | None = None
        self._frigate_uptime: str | None = None
        self._frigate_connected: bool = False
        self._last_check: datetime | None = None
        self._last_error: str | None = None

    @property
    def native_value(self) -> str:
        """Return Frigate connection status."""
        if self._frigate_connected and self._frigate_version:
            return f"v{self._frigate_version}"
        if self._last_error:
            return "error"
        return "disconnected"

    @property
    def icon(self) -> str:
        """Return icon based on connection status."""
        if self._frigate_connected:
            return "mdi:cctv"
        return "mdi:cctv-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Frigate details."""
        return {
            "url": self._entry.data.get(CONF_FRIGATE_URL),
            "connected": self._frigate_connected,
            "version": self._frigate_version,
            "uptime": self._frigate_uptime,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "last_error": self._last_error,
        }

    async def async_update(self) -> None:
        """Fetch Frigate status from API."""
        frigate_url = self._entry.data.get(CONF_FRIGATE_URL)
        if not frigate_url:
            self._frigate_connected = False
            self._last_error = "No Frigate URL configured"
            return

        try:
            session = async_get_clientsession(self._hass)
            async with session.get(
                f"{frigate_url.rstrip('/')}/api/stats",
                timeout=10,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._frigate_version = data.get("service", {}).get("version")
                    uptime_seconds = data.get("service", {}).get("uptime")
                    if uptime_seconds:
                        # Format uptime as human-readable
                        hours, remainder = divmod(int(uptime_seconds), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        if hours > 24:
                            days = hours // 24
                            hours = hours % 24
                            self._frigate_uptime = f"{days}d {hours}h {minutes}m"
                        else:
                            self._frigate_uptime = f"{hours}h {minutes}m {seconds}s"
                    self._frigate_connected = True
                    self._last_error = None
                    _LOGGER.debug(
                        "Frigate status: connected, version %s",
                        self._frigate_version,
                    )
                else:
                    self._frigate_connected = False
                    self._last_error = f"HTTP {response.status}"
                    _LOGGER.warning(
                        "Frigate API returned status %d", response.status
                    )

        except Exception as err:
            self._frigate_connected = False
            self._frigate_version = None
            self._last_error = str(err)
            _LOGGER.debug("Could not fetch Frigate status: %s", err)

        self._last_check = dt_util.utcnow()


class FrigateReleasesSensor(FrigateConfigBuilderBaseSensor):
    """Sensor showing latest Frigate releases from GitHub.

    Polls GitHub API to get the latest stable and beta releases.
    Updates once per day automatically, or on-demand via button.
    """

    # Enable polling for this sensor
    _attr_should_poll = True

    def __init__(
        self,
        coordinator: FrigateConfigBuilderCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="frigate_releases",
                translation_key="frigate_releases",
                icon="mdi:package-variant",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        )
        self._hass = hass
        self._latest_stable: str | None = None
        self._latest_beta: str | None = None
        self._stable_date: str | None = None
        self._beta_date: str | None = None
        self._stable_url: str | None = None
        self._beta_url: str | None = None
        self._recent_releases: list[dict[str, Any]] = []
        self._last_check: datetime | None = None
        self._last_error: str | None = None
        self._configured_version: str = entry.data.get(
            CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION
        )
        self._update_available: bool = False

    @property
    def native_value(self) -> str:
        """Return latest stable version."""
        if self._latest_stable:
            return self._latest_stable
        if self._last_error:
            return "error"
        return "unknown"

    @property
    def icon(self) -> str:
        """Return icon based on update availability."""
        if self._update_available:
            return "mdi:package-variant-closed-plus"
        return "mdi:package-variant"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed release information."""
        # Check if an update is available based on configured version
        configured = self._configured_version
        update_info = None

        if self._latest_stable and configured:
            # Simple version comparison (0.14 vs 0.17)
            if configured == "0.14" and self._latest_stable.startswith("0.17"):
                update_info = f"Frigate 0.17 available! You're configured for {configured}"
            elif configured == "0.17" and self._latest_stable.startswith("0.14"):
                update_info = f"You're on the latest branch ({configured})"

        return {
            "latest_stable": self._latest_stable,
            "latest_beta": self._latest_beta,
            "stable_release_date": self._stable_date,
            "beta_release_date": self._beta_date,
            "stable_url": self._stable_url,
            "beta_url": self._beta_url,
            "configured_version": configured,
            "update_available": self._update_available,
            "update_info": update_info,
            "recent_releases": self._recent_releases[:5],  # Last 5 releases
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "last_error": self._last_error,
        }

    async def async_update(self) -> None:
        """Fetch latest releases from GitHub API (respects poll interval)."""
        # Only check once per day (or on first load)
        if self._last_check:
            time_since_check = dt_util.utcnow() - self._last_check
            if time_since_check < FRIGATE_RELEASES_POLL_INTERVAL:
                return

        await self.async_force_refresh()

    async def async_force_refresh(self) -> None:
        """Force refresh releases from GitHub API (bypasses poll interval)."""
        _LOGGER.debug("Fetching Frigate releases from GitHub")

        try:
            session = async_get_clientsession(self._hass)
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "FrigateConfigBuilder-HomeAssistant",
            }

            async with session.get(
                FRIGATE_RELEASES_URL,
                headers=headers,
                timeout=15,
            ) as response:
                if response.status == 200:
                    releases = await response.json()
                    self._parse_releases(releases)
                    self._last_error = None
                    _LOGGER.info(
                        "Frigate releases updated: stable=%s, beta=%s",
                        self._latest_stable,
                        self._latest_beta,
                    )
                elif response.status == 403:
                    # Rate limited
                    self._last_error = "GitHub API rate limited"
                    _LOGGER.warning("GitHub API rate limited for Frigate releases")
                else:
                    self._last_error = f"HTTP {response.status}"
                    _LOGGER.warning(
                        "GitHub API returned status %d", response.status
                    )

        except Exception as err:
            self._last_error = str(err)
            _LOGGER.debug("Could not fetch Frigate releases: %s", err)

        self._last_check = dt_util.utcnow()
        
        # Trigger state update
        self.async_write_ha_state()

    def _parse_releases(self, releases: list[dict[str, Any]]) -> None:
        """Parse GitHub releases to find stable and beta versions."""
        self._latest_stable = None
        self._latest_beta = None
        self._stable_date = None
        self._beta_date = None
        self._stable_url = None
        self._beta_url = None
        self._recent_releases = []

        for release in releases:
            tag = release.get("tag_name", "")
            prerelease = release.get("prerelease", False)
            draft = release.get("draft", False)
            published = release.get("published_at", "")
            url = release.get("html_url", "")

            # Skip drafts
            if draft:
                continue

            # Clean up tag (remove 'v' prefix if present)
            version = tag.lstrip("v")

            # Build recent releases list
            if len(self._recent_releases) < 10:
                self._recent_releases.append({
                    "version": version,
                    "prerelease": prerelease,
                    "date": published[:10] if published else None,
                    "url": url,
                })

            # Determine if this is beta (prerelease flag or beta/rc/alpha in name)
            is_beta = prerelease or any(
                x in version.lower() for x in ["beta", "rc", "alpha", "dev"]
            )

            if is_beta:
                if not self._latest_beta:
                    self._latest_beta = version
                    self._beta_date = published[:10] if published else None
                    self._beta_url = url
            else:
                if not self._latest_stable:
                    self._latest_stable = version
                    self._stable_date = published[:10] if published else None
                    self._stable_url = url

            # Stop once we have both
            if self._latest_stable and self._latest_beta:
                break

        # Check if update is available
        self._check_update_available()

    def _check_update_available(self) -> None:
        """Check if a newer version is available than configured."""
        self._update_available = False

        if not self._latest_stable or not self._configured_version:
            return

        # Extract major.minor from configured version (e.g., "0.14" -> (0, 14))
        try:
            conf_parts = self._configured_version.split(".")
            conf_major = int(conf_parts[0])
            conf_minor = int(conf_parts[1]) if len(conf_parts) > 1 else 0
        except (ValueError, IndexError):
            return

        # Extract major.minor from latest stable
        try:
            stable_parts = self._latest_stable.split(".")
            stable_major = int(stable_parts[0])
            stable_minor = int(stable_parts[1]) if len(stable_parts) > 1 else 0
        except (ValueError, IndexError):
            return

        # Update available if stable is newer
        if (stable_major, stable_minor) > (conf_major, conf_minor):
            self._update_available = True
