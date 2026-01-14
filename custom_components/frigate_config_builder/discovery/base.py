"""Base class for camera discovery adapters."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass
class DiscoveredCamera:
    """A camera discovered from Home Assistant."""

    id: str  # Unique key: "unifi_garage_a"
    name: str  # Frigate camera name: "garage_a"
    friendly_name: str  # Display name: "Garage A"
    source: str  # Where it came from: "unifiprotect", "amcrest", etc.

    record_url: str  # High-res RTSP for recording
    detect_url: str | None = None  # Low-res RTSP for detection (optional)
    go2rtc_url: str | None = None  # URL for go2rtc live view

    width: int = 640  # Detect resolution width
    height: int = 360  # Detect resolution height
    fps: int = 5  # Detect FPS

    area: str | None = None  # HA area for auto-grouping
    available: bool = True  # Entity availability
    is_new: bool = False  # Not in previous config

    def __post_init__(self) -> None:
        """Set defaults for optional URL fields."""
        if self.detect_url is None:
            self.detect_url = self.record_url
        if self.go2rtc_url is None:
            # Convert rtsps:// to rtspx:// for go2rtc
            self.go2rtc_url = self.record_url.replace("rtsps://", "rtspx://")
            # Remove query params for cleaner go2rtc URL
            if "?" in self.go2rtc_url:
                self.go2rtc_url = self.go2rtc_url.split("?")[0]


class CameraAdapter(ABC):
    """Abstract base class for camera discovery adapters."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the adapter."""
        self.hass = hass
        self.entry = entry

    @property
    @abstractmethod
    def integration_domain(self) -> str:
        """Return the HA integration domain this adapter handles."""
        ...

    @abstractmethod
    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover cameras from this integration."""
        ...

    def is_available(self) -> bool:
        """Check if this integration is configured in HA."""
        return bool(self.hass.config_entries.async_entries(self.integration_domain))

    @staticmethod
    def normalize_name(name: str) -> str:
        """Convert friendly name to Frigate-safe camera name.
        
        Frigate camera names must be lowercase alphanumeric with underscores.
        """
        # Lowercase
        name = name.lower()
        # Replace spaces and special chars with underscore
        name = re.sub(r"[^a-z0-9]+", "_", name)
        # Remove leading/trailing underscores
        name = name.strip("_")
        # Collapse multiple underscores
        name = re.sub(r"_+", "_", name)
        return name

    @staticmethod
    def url_encode_password(password: str) -> str:
        """URL encode special characters in password for RTSP URLs."""
        from urllib.parse import quote
        return quote(password, safe="")
