# Frigate Config Builder - Build Plan

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Home Assistant                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    frigate_config_builder                          │  │
│  │                                                                    │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐│  │
│  │  │ Config Flow  │───▶│ Coordinator  │───▶│ Config Entry Storage ││  │
│  │  └──────────────┘    └──────┬───────┘    └──────────────────────┘│  │
│  │                             │                                      │  │
│  │                             ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │                   Discovery Engine                            ││  │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ ││  │
│  │  │  │  UniFi     │ │  Amcrest   │ │  Reolink   │ │  Manual   │ ││  │
│  │  │  │  Protect   │ │  Adapter   │ │  Adapter   │ │  Adapter  │ ││  │
│  │  │  │  Adapter   │ │            │ │            │ │           │ ││  │
│  │  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬─────┘ ││  │
│  │  │        │              │              │              │        ││  │
│  │  │        └──────────────┴──────────────┴──────────────┘        ││  │
│  │  │                              │                                ││  │
│  │  │                              ▼                                ││  │
│  │  │                    List[DiscoveredCamera]                     ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  │                             │                                      │  │
│  │                             ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │                      Generator                                ││  │
│  │  │                                                               ││  │
│  │  │  Static Config + Discovered Cameras + Selected = frigate.yml ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  │                             │                                      │  │
│  │                             ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │                    Output Handler                             ││  │
│  │  │                                                               ││  │
│  │  │  • Write to file (output_path)                                ││  │
│  │  │  • Optional: POST to Frigate API + restart                    ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  │                                                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │   Entities   │ │   Services   │ │      Options Flow        │  │  │
│  │  │              │ │              │ │                          │  │  │
│  │  │ • Button     │ │ • generate   │ │ • Camera selection       │  │  │
│  │  │ • Sensors    │ │ • refresh    │ │ • Manual cameras         │  │  │
│  │  │ • Binary Sen │ │              │ │ • Credential overrides   │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
custom_components/frigate_config_builder/
├── __init__.py                 # Entry point, setup coordinator
├── manifest.json               # HACS/HA metadata
├── const.py                    # Constants, defaults, enums
├── config_flow.py              # Multi-step setup wizard
├── options_flow.py             # Runtime camera selection
├── coordinator.py              # Data update coordinator
├── generator.py                # YAML config generator
├── output.py                   # File writer, API pusher
│
├── discovery/
│   ├── __init__.py             # Export all adapters
│   ├── base.py                 # Abstract CameraAdapter
│   ├── coordinator.py          # Runs all adapters
│   ├── unifiprotect.py         # UniFi Protect adapter
│   ├── amcrest.py              # Amcrest adapter
│   ├── reolink.py              # Reolink adapter
│   └── manual.py               # Manual camera handler
│
├── entities/
│   ├── __init__.py
│   ├── button.py               # Generate button
│   ├── sensor.py               # Status sensors
│   └── binary_sensor.py        # Stale config sensor
│
├── services.yaml               # Service definitions
├── strings.json                # UI strings (base)
└── translations/
    └── en.json                 # English translations
```

---

## Data Models

### Core Models (`const.py` or `models.py`)

```python
from dataclasses import dataclass, field
from typing import Literal
from enum import StrEnum


class DetectorType(StrEnum):
    EDGETPU = "edgetpu"
    CPU = "cpu"
    OPENVINO = "openvino"
    TENSORRT = "tensorrt"
    ONNX = "onnx"


class HwaccelType(StrEnum):
    VAAPI = "vaapi"
    CUDA = "cuda"
    QSV = "qsv"
    RKMPP = "rkmpp"
    V4L2M2M = "v4l2m2m"
    NONE = "none"


class CameraSource(StrEnum):
    UNIFIPROTECT = "unifiprotect"
    AMCREST = "amcrest"
    REOLINK = "reolink"
    MANUAL = "manual"


@dataclass
class DiscoveredCamera:
    """A camera discovered from HA or manually defined."""
    
    id: str                        # Unique key: "unifi_garage_a"
    name: str                      # Frigate name: "garage_a"
    friendly_name: str             # Display: "Garage A"
    source: CameraSource           # Where it came from
    
    record_url: str                # High-res RTSP for recording
    detect_url: str | None = None  # Low-res RTSP for detection (optional)
    go2rtc_url: str | None = None  # URL for go2rtc live view
    
    width: int = 640               # Detect resolution
    height: int = 360
    fps: int = 5
    
    area: str | None = None        # HA area for auto-grouping
    available: bool = True         # Entity availability
    is_new: bool = False           # Not in previous config
    
    def __post_init__(self):
        """Default detect_url to record_url if not set."""
        if self.detect_url is None:
            self.detect_url = self.record_url
        if self.go2rtc_url is None:
            self.go2rtc_url = self.record_url.replace("rtsps://", "rtspx://")


@dataclass
class FrigateBuilderConfig:
    """Complete integration configuration."""
    
    # === Connection ===
    output_path: str = "/config/www/frigate.yml"
    frigate_url: str | None = None
    auto_push: bool = False
    
    # === Hardware ===
    detector_type: DetectorType = DetectorType.EDGETPU
    detector_device: str = "usb"
    hwaccel: HwaccelType = HwaccelType.VAAPI
    network_interfaces: list[str] = field(default_factory=lambda: ["eth0"])
    
    # === MQTT ===
    mqtt_auto: bool = True
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    mqtt_user: str | None = None
    mqtt_password: str | None = None
    
    # === Features ===
    audio_detection: bool = True
    face_recognition: bool = False
    face_recognition_model: Literal["small", "large"] = "large"
    semantic_search: bool = False
    semantic_search_model: Literal["small", "large"] = "large"
    lpr: bool = False
    bird_classification: bool = False
    birdseye_enabled: bool = True
    birdseye_mode: Literal["continuous", "motion", "objects"] = "objects"
    
    # === Retention (days) ===
    retain_alerts: int = 30
    retain_detections: int = 30
    retain_motion: int = 7
    retain_snapshots: int = 30
    
    # === Camera Selection ===
    selected_cameras: list[str] = field(default_factory=list)
    
    # === Groups ===
    auto_groups_from_areas: bool = True
    manual_groups: dict[str, list[str]] = field(default_factory=dict)
    
    # === Manual Cameras ===
    manual_cameras: list[dict] = field(default_factory=list)
    
    # === Credential Overrides ===
    credential_overrides: dict[str, dict] = field(default_factory=dict)
```

---

## Scaffolding: `manifest.json`

```json
{
  "domain": "frigate_config_builder",
  "name": "Frigate Config Builder",
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/yourusername/frigate-config-builder",
  "integration_type": "service",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/yourusername/frigate-config-builder/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

---

## Scaffolding: `__init__.py`

```python
"""Frigate Config Builder integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import FrigateConfigBuilderCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

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
    coordinator = FrigateConfigBuilderCoordinator(hass, entry)
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await async_register_services(hass)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    
    async def handle_generate(call):
        """Handle the generate service call."""
        # Get first (only) config entry
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Frigate Config Builder entries configured")
            return
        
        coordinator = hass.data[DOMAIN][entries[0].entry_id]
        await coordinator.async_generate_config(push=call.data.get("push", False))
    
    async def handle_refresh(call):
        """Handle the refresh_cameras service call."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            return
        
        coordinator = hass.data[DOMAIN][entries[0].entry_id]
        await coordinator.async_refresh()
    
    hass.services.async_register(DOMAIN, "generate", handle_generate)
    hass.services.async_register(DOMAIN, "refresh_cameras", handle_refresh)
```

---

## Scaffolding: `const.py`

```python
"""Constants for Frigate Config Builder."""
from typing import Final

DOMAIN: Final = "frigate_config_builder"

# Config entry keys
CONF_OUTPUT_PATH: Final = "output_path"
CONF_FRIGATE_URL: Final = "frigate_url"
CONF_AUTO_PUSH: Final = "auto_push"
CONF_DETECTOR_TYPE: Final = "detector_type"
CONF_DETECTOR_DEVICE: Final = "detector_device"
CONF_HWACCEL: Final = "hwaccel"
CONF_NETWORK_INTERFACES: Final = "network_interfaces"
CONF_MQTT_AUTO: Final = "mqtt_auto"
CONF_MQTT_HOST: Final = "mqtt_host"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USER: Final = "mqtt_user"
CONF_MQTT_PASSWORD: Final = "mqtt_password"
CONF_AUDIO_DETECTION: Final = "audio_detection"
CONF_FACE_RECOGNITION: Final = "face_recognition"
CONF_FACE_RECOGNITION_MODEL: Final = "face_recognition_model"
CONF_SEMANTIC_SEARCH: Final = "semantic_search"
CONF_SEMANTIC_SEARCH_MODEL: Final = "semantic_search_model"
CONF_LPR: Final = "lpr"
CONF_BIRD_CLASSIFICATION: Final = "bird_classification"
CONF_BIRDSEYE_ENABLED: Final = "birdseye_enabled"
CONF_BIRDSEYE_MODE: Final = "birdseye_mode"
CONF_RETAIN_ALERTS: Final = "retain_alerts"
CONF_RETAIN_DETECTIONS: Final = "retain_detections"
CONF_RETAIN_MOTION: Final = "retain_motion"
CONF_RETAIN_SNAPSHOTS: Final = "retain_snapshots"
CONF_SELECTED_CAMERAS: Final = "selected_cameras"
CONF_AUTO_GROUPS: Final = "auto_groups_from_areas"
CONF_MANUAL_GROUPS: Final = "manual_groups"
CONF_MANUAL_CAMERAS: Final = "manual_cameras"
CONF_CREDENTIAL_OVERRIDES: Final = "credential_overrides"

# Defaults
DEFAULT_OUTPUT_PATH: Final = "/config/www/frigate.yml"
DEFAULT_DETECTOR_TYPE: Final = "edgetpu"
DEFAULT_DETECTOR_DEVICE: Final = "usb"
DEFAULT_HWACCEL: Final = "vaapi"
DEFAULT_MQTT_PORT: Final = 1883
DEFAULT_RETAIN_ALERTS: Final = 30
DEFAULT_RETAIN_DETECTIONS: Final = 30
DEFAULT_RETAIN_MOTION: Final = 7
DEFAULT_RETAIN_SNAPSHOTS: Final = 30

# Detector options
DETECTOR_TYPES: Final = ["edgetpu", "cpu", "openvino", "tensorrt", "onnx"]

# Hardware acceleration options
HWACCEL_TYPES: Final = [
    ("vaapi", "VAAPI (Intel)"),
    ("cuda", "CUDA (NVIDIA)"),
    ("qsv", "QuickSync (Intel)"),
    ("rkmpp", "RKMPP (Rockchip)"),
    ("v4l2m2m", "V4L2M2M (Raspberry Pi)"),
    ("none", "None (Software)"),
]

# Feature model sizes
MODEL_SIZES: Final = ["small", "large"]

# Birdseye modes
BIRDSEYE_MODES: Final = ["continuous", "motion", "objects"]

# FFMPEG presets by hwaccel type
FFMPEG_PRESETS: Final = {
    "vaapi": "preset-vaapi",
    "cuda": "preset-nvidia-h264",
    "qsv": "preset-intel-qsv-h264",
    "rkmpp": "preset-rkmpp",
    "v4l2m2m": "preset-rpi-64-h264",
    "none": "preset-http-jpeg-generic",
}

# Record output args by camera type
RECORD_PRESETS: Final = {
    "unifiprotect": "preset-record-ubiquiti",
    "amcrest": "preset-record-generic-audio-aac",
    "reolink": "preset-record-generic-audio-aac",
    "manual": "preset-record-generic",
}
```

---

## Scaffolding: `coordinator.py`

```python
"""Data coordinator for Frigate Config Builder."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_SELECTED_CAMERAS
from .discovery import DiscoveryCoordinator
from .generator import FrigateConfigGenerator
from .output import write_config_file, push_to_frigate

if TYPE_CHECKING:
    from .discovery.base import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)


class FrigateConfigBuilderCoordinator(DataUpdateCoordinator):
    """Coordinator to manage camera discovery and config generation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),  # Periodic discovery refresh
        )
        self.entry = entry
        self.discovery = DiscoveryCoordinator(hass, entry)
        self.generator = FrigateConfigGenerator(hass, entry)
        
        # State tracking
        self.discovered_cameras: list[DiscoveredCamera] = []
        self.last_generated: datetime | None = None
        self.last_generation_duration: float = 0
        self.config_stale: bool = False
        self._previous_camera_ids: set[str] = set()

    async def _async_update_data(self) -> dict:
        """Fetch data from all discovery adapters."""
        _LOGGER.debug("Running camera discovery")
        
        # Run discovery
        self.discovered_cameras = await self.discovery.discover_all()
        
        # Check if cameras changed (new or removed)
        current_ids = {cam.id for cam in self.discovered_cameras}
        selected = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        
        # Mark new cameras
        for cam in self.discovered_cameras:
            cam.is_new = cam.id not in self._previous_camera_ids
        
        # Detect staleness
        if self._previous_camera_ids and current_ids != self._previous_camera_ids:
            self.config_stale = True
            _LOGGER.info("Camera configuration has changed, config is stale")
        
        self._previous_camera_ids = current_ids
        
        return {
            "cameras": self.discovered_cameras,
            "camera_count": len(self.discovered_cameras),
            "selected_count": len(selected & current_ids),
        }

    async def async_generate_config(self, push: bool = False) -> str:
        """Generate Frigate configuration file."""
        import time
        
        start = time.monotonic()
        
        # Filter to selected cameras only
        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        cameras = [c for c in self.discovered_cameras if c.id in selected_ids]
        
        # Generate config
        config_yaml = await self.generator.generate(cameras)
        
        # Write to file
        output_path = self.entry.data.get("output_path", "/config/www/frigate.yml")
        await write_config_file(self.hass, output_path, config_yaml)
        
        # Optionally push to Frigate
        if push and self.entry.data.get("frigate_url"):
            await push_to_frigate(
                self.entry.data["frigate_url"],
                config_yaml,
                restart=True,
            )
        
        # Update state
        self.last_generated = datetime.now()
        self.last_generation_duration = time.monotonic() - start
        self.config_stale = False
        
        _LOGGER.info(
            "Generated Frigate config with %d cameras in %.2fs",
            len(cameras),
            self.last_generation_duration,
        )
        
        return config_yaml

    @property
    def selected_cameras(self) -> list[DiscoveredCamera]:
        """Return only selected cameras."""
        selected_ids = set(self.entry.options.get(CONF_SELECTED_CAMERAS, []))
        return [c for c in self.discovered_cameras if c.id in selected_ids]
```

---

## Scaffolding: Discovery Base (`discovery/base.py`)

```python
"""Base class for camera discovery adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass
class DiscoveredCamera:
    """A camera discovered from Home Assistant."""
    
    id: str
    name: str
    friendly_name: str
    source: str
    record_url: str
    detect_url: str | None = None
    go2rtc_url: str | None = None
    width: int = 640
    height: int = 360
    fps: int = 5
    area: str | None = None
    available: bool = True
    is_new: bool = False
    
    def __post_init__(self):
        if self.detect_url is None:
            self.detect_url = self.record_url
        if self.go2rtc_url is None:
            # Convert rtsps:// to rtspx:// for go2rtc
            self.go2rtc_url = self.record_url.replace("rtsps://", "rtspx://")


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
        """Convert friendly name to Frigate-safe camera name."""
        import re
        # Lowercase, replace spaces/special chars with underscore
        name = name.lower()
        name = re.sub(r"[^a-z0-9]+", "_", name)
        name = name.strip("_")
        return name
```

---

## Scaffolding: UniFi Protect Adapter (`discovery/unifiprotect.py`)

```python
"""UniFi Protect camera discovery adapter."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er

from .base import CameraAdapter, DiscoveredCamera

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class UniFiProtectAdapter(CameraAdapter):
    """Discover cameras from UniFi Protect integration."""

    @property
    def integration_domain(self) -> str:
        return "unifiprotect"

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Discover all UniFi Protect cameras."""
        if not self.is_available():
            _LOGGER.debug("UniFi Protect integration not configured")
            return []

        cameras: list[DiscoveredCamera] = []
        entity_reg = er.async_get(self.hass)
        
        # Find all camera entities from unifiprotect
        camera_entities = [
            entry for entry in entity_reg.entities.values()
            if entry.domain == "camera" 
            and entry.platform == "unifiprotect"
            and "_low_res" not in entry.entity_id  # Skip low-res variants
            and "_package" not in entry.entity_id  # Handle package cameras separately
        ]
        
        for entity in camera_entities:
            try:
                camera = await self._create_camera_from_entity(entity, entity_reg)
                if camera:
                    cameras.append(camera)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to process UniFi camera %s: %s",
                    entity.entity_id,
                    err,
                )
        
        # Handle package cameras (e.g., G6 Doorbell)
        package_entities = [
            entry for entry in entity_reg.entities.values()
            if entry.domain == "camera"
            and entry.platform == "unifiprotect"
            and "_package" in entry.entity_id
        ]
        
        for entity in package_entities:
            try:
                camera = await self._create_camera_from_entity(entity, entity_reg, is_package=True)
                if camera:
                    cameras.append(camera)
            except Exception as err:
                _LOGGER.warning("Failed to process package camera %s: %s", entity.entity_id, err)
        
        _LOGGER.info("Discovered %d UniFi Protect cameras", len(cameras))
        return cameras

    async def _create_camera_from_entity(
        self,
        entity: er.RegistryEntry,
        entity_reg: er.EntityRegistry,
        is_package: bool = False,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from entity registry entry."""
        
        # Get RTSP URL via expose-camera-stream-source
        record_url = await self._get_rtsp_url(entity.entity_id)
        if not record_url:
            _LOGGER.warning("No RTSP URL for %s", entity.entity_id)
            return None
        
        # Try to find low-res stream for detection
        detect_url = record_url  # Default to same stream
        if not is_package:
            low_res_entity_id = entity.entity_id.replace("camera.", "camera.") + "_low_res"
            # Actually, UniFi uses different naming - need to find by device
            low_res_url = await self._get_low_res_url(entity, entity_reg)
            if low_res_url:
                detect_url = low_res_url
        
        # Get friendly name and area
        state = self.hass.states.get(entity.entity_id)
        friendly_name = state.attributes.get("friendly_name", entity.entity_id) if state else entity.entity_id
        
        # Determine availability
        available = state.state != "unavailable" if state else False
        
        # Get area
        area = None
        if entity.area_id:
            area_reg = self.hass.helpers.area_registry.async_get(self.hass)
            area_entry = area_reg.async_get_area(entity.area_id)
            if area_entry:
                area = area_entry.name
        
        # Generate Frigate-safe name
        name = self.normalize_name(friendly_name)
        if is_package:
            name = f"{name}_package"
        
        return DiscoveredCamera(
            id=f"unifi_{name}",
            name=name,
            friendly_name=friendly_name,
            source="unifiprotect",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=record_url.replace("rtsps://", "rtspx://").split("?")[0],
            width=640 if not is_package else 400,
            height=360 if not is_package else 300,
            area=area,
            available=available,
        )

    async def _get_rtsp_url(self, entity_id: str) -> str | None:
        """Get RTSP URL using expose-camera-stream-source service."""
        try:
            response = await self.hass.services.async_call(
                "camera",
                "expose_stream_source", 
                {"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
            return response.get("url") if response else None
        except Exception as err:
            _LOGGER.debug("Failed to get stream URL for %s: %s", entity_id, err)
            return None

    async def _get_low_res_url(
        self,
        entity: er.RegistryEntry,
        entity_reg: er.EntityRegistry,
    ) -> str | None:
        """Find and return the low-resolution stream URL."""
        # UniFi Protect creates separate entities for low-res streams
        # They share the same device_id but have different unique_ids
        
        if not entity.device_id:
            return None
        
        # Find sibling camera entity with "low" or "medium" in unique_id
        for sibling in entity_reg.entities.values():
            if (
                sibling.device_id == entity.device_id
                and sibling.domain == "camera"
                and sibling.entity_id != entity.entity_id
                and ("low" in sibling.unique_id.lower() or "medium" in sibling.unique_id.lower())
            ):
                return await self._get_rtsp_url(sibling.entity_id)
        
        return None
```

---

## Scaffolding: Generator (`generator.py`)

```python
"""Frigate configuration generator."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml

from .const import (
    FFMPEG_PRESETS,
    RECORD_PRESETS,
    CONF_DETECTOR_TYPE,
    CONF_DETECTOR_DEVICE,
    CONF_HWACCEL,
    # ... other consts
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from .discovery.base import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)


class FrigateConfigGenerator:
    """Generate Frigate YAML configuration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

    async def generate(self, cameras: list[DiscoveredCamera]) -> str:
        """Generate complete Frigate configuration."""
        config = {}
        
        # Build sections
        config["mqtt"] = await self._build_mqtt()
        config["detectors"] = self._build_detectors()
        config["ffmpeg"] = self._build_ffmpeg()
        config["record"] = self._build_record()
        config["snapshots"] = self._build_snapshots()
        config["detect"] = self._build_detect()
        config["audio"] = self._build_audio()
        config["birdseye"] = self._build_birdseye()
        config["go2rtc"] = self._build_go2rtc(cameras)
        config["cameras"] = self._build_cameras(cameras)
        config["telemetry"] = self._build_telemetry()
        config["version"] = "0.14-1"
        
        # Optional features
        if self.entry.data.get("semantic_search"):
            config["semantic_search"] = self._build_semantic_search()
        if self.entry.data.get("face_recognition"):
            config["face_recognition"] = self._build_face_recognition()
        if self.entry.data.get("lpr"):
            config["lpr"] = {"enabled": True}
        if self.entry.data.get("bird_classification"):
            config["classification"] = {"bird": {"enabled": True}}
        
        # Camera groups
        groups = await self._build_camera_groups(cameras)
        if groups:
            config["camera_groups"] = groups
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    async def _build_mqtt(self) -> dict:
        """Build MQTT configuration section."""
        if self.entry.data.get("mqtt_auto", True):
            # Get from HA MQTT integration
            mqtt_entry = self.hass.config_entries.async_entries("mqtt")
            if mqtt_entry:
                mqtt_data = mqtt_entry[0].data
                return {
                    "host": mqtt_data.get("broker", "localhost"),
                    "port": mqtt_data.get("port", 1883),
                    "user": mqtt_data.get("username"),
                    "password": mqtt_data.get("password"),
                }
        
        # Manual config
        return {
            "host": self.entry.data.get("mqtt_host", "localhost"),
            "port": self.entry.data.get("mqtt_port", 1883),
            "user": self.entry.data.get("mqtt_user"),
            "password": self.entry.data.get("mqtt_password"),
        }

    def _build_detectors(self) -> dict:
        """Build detectors configuration section."""
        detector_type = self.entry.data.get(CONF_DETECTOR_TYPE, "edgetpu")
        detector_device = self.entry.data.get(CONF_DETECTOR_DEVICE, "usb")
        
        return {
            "default": {
                "type": detector_type,
                "device": detector_device,
            }
        }

    def _build_ffmpeg(self) -> dict:
        """Build FFmpeg configuration section."""
        hwaccel = self.entry.data.get(CONF_HWACCEL, "vaapi")
        preset = FFMPEG_PRESETS.get(hwaccel, "preset-vaapi")
        
        return {
            "global_args": "-hide_banner -loglevel warning -threads 0",
            "hwaccel_args": preset,
            "output_args": {
                "record": "preset-record-ubiquiti",  # Default, cameras override
            }
        }

    def _build_cameras(self, cameras: list[DiscoveredCamera]) -> dict:
        """Build cameras configuration section."""
        result = {}
        
        for cam in cameras:
            camera_config = {
                "enabled": True,
                "ffmpeg": {
                    "inputs": [],
                    "hwaccel_args": FFMPEG_PRESETS.get(
                        self.entry.data.get(CONF_HWACCEL, "vaapi"),
                        "preset-vaapi"
                    ),
                },
                "detect": {
                    "enabled": True,
                    "width": cam.width,
                    "height": cam.height,
                },
            }
            
            # Separate record and detect streams if different
            if cam.record_url != cam.detect_url:
                camera_config["ffmpeg"]["inputs"] = [
                    {
                        "path": cam.record_url,
                        "roles": ["record", "audio"],
                    },
                    {
                        "path": cam.detect_url,
                        "roles": ["detect"],
                    },
                ]
            else:
                camera_config["ffmpeg"]["inputs"] = [
                    {
                        "path": cam.record_url,
                        "roles": ["record", "audio", "detect"],
                    },
                ]
            
            # Set record preset based on source
            record_preset = RECORD_PRESETS.get(cam.source, "preset-record-generic")
            camera_config["ffmpeg"]["output_args"] = {"record": record_preset}
            
            result[cam.name] = camera_config
        
        return result

    def _build_go2rtc(self, cameras: list[DiscoveredCamera]) -> dict:
        """Build go2rtc streams section."""
        streams = {}
        
        for cam in cameras:
            if cam.go2rtc_url:
                streams[cam.name] = [cam.go2rtc_url]
        
        return {"streams": streams}

    async def _build_camera_groups(self, cameras: list[DiscoveredCamera]) -> dict:
        """Build camera groups from HA areas or manual config."""
        groups = {}
        
        if self.entry.options.get("auto_groups_from_areas", True):
            # Group by HA area
            area_cameras: dict[str, list[str]] = {}
            for cam in cameras:
                area = cam.area or "Ungrouped"
                if area not in area_cameras:
                    area_cameras[area] = []
                area_cameras[area].append(cam.name)
            
            for idx, (area_name, cam_names) in enumerate(sorted(area_cameras.items())):
                groups[area_name] = {
                    "order": idx + 1,
                    "icon": "LuCamera",
                    "cameras": cam_names,
                }
        
        # Merge manual groups
        manual = self.entry.options.get("manual_groups", {})
        for name, cam_names in manual.items():
            groups[name] = {
                "order": len(groups) + 1,
                "icon": "LuCamera",
                "cameras": cam_names,
            }
        
        return groups

    # ... implement remaining _build_* methods similarly
```

---

## Scaffolding: Config Flow (`config_flow.py`)

```python
"""Config flow for Frigate Config Builder."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_OUTPUT_PATH,
    CONF_FRIGATE_URL,
    CONF_AUTO_PUSH,
    CONF_DETECTOR_TYPE,
    CONF_DETECTOR_DEVICE,
    CONF_HWACCEL,
    CONF_MQTT_AUTO,
    # ... other consts
    DEFAULT_OUTPUT_PATH,
    DETECTOR_TYPES,
    HWACCEL_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class FrigateConfigBuilderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frigate Config Builder."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 1: Connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_hardware()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_OUTPUT_PATH, default=DEFAULT_OUTPUT_PATH): str,
                vol.Optional(CONF_FRIGATE_URL): str,
                vol.Optional(CONF_AUTO_PUSH, default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_hardware(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 2: Hardware settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_mqtt()

        return self.async_show_form(
            step_id="hardware",
            data_schema=vol.Schema({
                vol.Required(CONF_DETECTOR_TYPE, default="edgetpu"): vol.In(DETECTOR_TYPES),
                vol.Required(CONF_DETECTOR_DEVICE, default="usb"): str,
                vol.Required(CONF_HWACCEL, default="vaapi"): vol.In(
                    [k for k, v in HWACCEL_TYPES]
                ),
                vol.Optional("network_interfaces", default="eth0"): str,
            }),
            errors=errors,
        )

    async def async_step_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 3: MQTT settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_features()

        # Check if HA has MQTT configured
        mqtt_entries = self.hass.config_entries.async_entries("mqtt")
        has_mqtt = bool(mqtt_entries)

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema({
                vol.Required(CONF_MQTT_AUTO, default=has_mqtt): bool,
                vol.Optional("mqtt_host"): str,
                vol.Optional("mqtt_port", default=1883): int,
                vol.Optional("mqtt_user"): str,
                vol.Optional("mqtt_password"): str,
            }),
            errors=errors,
            description_placeholders={"mqtt_detected": "Yes" if has_mqtt else "No"},
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 4: Feature settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_retention()

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema({
                vol.Optional("audio_detection", default=True): bool,
                vol.Optional("face_recognition", default=False): bool,
                vol.Optional("face_recognition_model", default="large"): vol.In(["small", "large"]),
                vol.Optional("semantic_search", default=False): bool,
                vol.Optional("semantic_search_model", default="large"): vol.In(["small", "large"]),
                vol.Optional("lpr", default=False): bool,
                vol.Optional("bird_classification", default=False): bool,
                vol.Optional("birdseye_enabled", default=True): bool,
                vol.Optional("birdseye_mode", default="objects"): vol.In(["continuous", "motion", "objects"]),
            }),
            errors=errors,
        )

    async def async_step_retention(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 5: Retention settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            
            # Create the config entry
            return self.async_create_entry(
                title="Frigate Config Builder",
                data=self._data,
            )

        return self.async_show_form(
            step_id="retention",
            data_schema=vol.Schema({
                vol.Optional("retain_alerts", default=30): int,
                vol.Optional("retain_detections", default=30): int,
                vol.Optional("retain_motion", default=7): int,
                vol.Optional("retain_snapshots", default=30): int,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return FrigateConfigBuilderOptionsFlow(config_entry)


class FrigateConfigBuilderOptionsFlow(OptionsFlow):
    """Handle options flow for camera selection."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        # This will show camera selection checkboxes
        # Implementation depends on discovered cameras
        
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        # Get discovered cameras from coordinator
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        cameras = coordinator.discovered_cameras
        
        # Build multi-select schema
        camera_options = {cam.id: f"{cam.friendly_name} ({cam.source})" for cam in cameras}
        current_selected = self.config_entry.options.get("selected_cameras", list(camera_options.keys()))
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "selected_cameras",
                    default=current_selected,
                ): vol.All(
                    cv.multi_select(camera_options),
                ),
                vol.Optional("auto_groups_from_areas", default=True): bool,
            }),
        )
```

---

## Scaffolding: `strings.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Frigate Config Builder",
        "description": "Configure where to save the generated Frigate configuration.",
        "data": {
          "output_path": "Output Path",
          "frigate_url": "Frigate URL (optional)",
          "auto_push": "Auto-push config to Frigate"
        },
        "data_description": {
          "output_path": "Path to save the generated frigate.yml file",
          "frigate_url": "Frigate API URL for pushing config (e.g., http://192.168.1.100:5000)",
          "auto_push": "Automatically push config and restart Frigate after generation"
        }
      },
      "hardware": {
        "title": "Hardware Configuration",
        "description": "Configure your detector and hardware acceleration.",
        "data": {
          "detector_type": "Detector Type",
          "detector_device": "Detector Device",
          "hwaccel": "Hardware Acceleration",
          "network_interfaces": "Network Interfaces"
        }
      },
      "mqtt": {
        "title": "MQTT Configuration",
        "description": "Configure MQTT broker connection. HA MQTT detected: {mqtt_detected}",
        "data": {
          "mqtt_auto": "Use Home Assistant MQTT",
          "mqtt_host": "MQTT Host",
          "mqtt_port": "MQTT Port",
          "mqtt_user": "MQTT Username",
          "mqtt_password": "MQTT Password"
        }
      },
      "features": {
        "title": "Feature Configuration",
        "description": "Enable Frigate features.",
        "data": {
          "audio_detection": "Audio Detection",
          "face_recognition": "Face Recognition",
          "face_recognition_model": "Face Recognition Model",
          "semantic_search": "Semantic Search",
          "semantic_search_model": "Semantic Search Model",
          "lpr": "License Plate Recognition",
          "bird_classification": "Bird Classification",
          "birdseye_enabled": "BirdsEye View",
          "birdseye_mode": "BirdsEye Mode"
        }
      },
      "retention": {
        "title": "Retention Settings",
        "description": "Configure how long to keep recordings.",
        "data": {
          "retain_alerts": "Alert Retention (days)",
          "retain_detections": "Detection Retention (days)",
          "retain_motion": "Motion Retention (days)",
          "retain_snapshots": "Snapshot Retention (days)"
        }
      }
    },
    "error": {
      "invalid_path": "Invalid output path",
      "invalid_url": "Invalid Frigate URL"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Camera Selection",
        "description": "Select which cameras to include in the Frigate configuration.",
        "data": {
          "selected_cameras": "Cameras",
          "auto_groups_from_areas": "Auto-generate groups from HA Areas"
        }
      }
    }
  },
  "entity": {
    "button": {
      "generate": {
        "name": "Generate Config"
      }
    },
    "sensor": {
      "cameras_selected": {
        "name": "Cameras Selected"
      },
      "last_generated": {
        "name": "Last Generated"
      }
    },
    "binary_sensor": {
      "config_stale": {
        "name": "Config Stale"
      }
    }
  }
}
```

---

## Reference: Working RTSP URL Patterns

### UniFi Protect
```
# High-res (record)
rtsps://192.168.15.173:7441/{stream_id}?enableSrtp

# Low-res (detect)
rtsps://192.168.15.173:7441/{low_stream_id}?enableSrtp

# go2rtc (live view)
rtspx://192.168.15.173:7441/{stream_id}
```

### Amcrest
```
# High-res (record) - subtype=0
rtsp://{user}:{pass}@{host}/cam/realmonitor?channel={ch}&subtype=0

# Low-res (detect) - subtype=1
rtsp://{user}:{pass}@{host}/cam/realmonitor?channel={ch}&subtype=1

# Note: channel is usually 1, but some models (ASH41-B) use channel 0
```

### Reolink
```
# High-res (record)
rtsp://{user}:{pass}@{host}:554/h264Preview_01_main

# Low-res (detect)
rtsp://{user}:{pass}@{host}:554/h264Preview_01_sub

# go2rtc (HTTP FLV for better compatibility)
ffmpeg:http://{host}/flv?port=1935&app=bcs&stream=channel0_main.bcs&user={user}&password={pass}
```

---

## Notes for Implementation

1. **Start with `const.py`** - All magic strings centralized
2. **Test generator in isolation** - Can unit test without HA
3. **Mock `hass.services.async_call`** for expose-camera-stream-source
4. **URL encode passwords** - Special chars like `@^` need encoding in RTSP URLs
5. **Handle unavailable entities** - Don't fail, mark as unavailable
6. **Preserve camera order** - Dict ordering matters for YAML readability
