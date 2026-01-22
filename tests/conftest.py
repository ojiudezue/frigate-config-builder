"""Pytest configuration and fixtures for Frigate Config Builder tests.

Version: 0.4.0.8
Date: 2026-01-22

Changelog:
- 0.4.0.8: Added fixtures for 0.17 testing (mock_config_entry_017, mock_config_entry_017_genai)
"""
from __future__ import annotations

import os
import sys

# Add the project root to Python path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Mock Data Classes
# =============================================================================


@dataclass
class MockConfigEntry:
    """Mock Home Assistant config entry."""
    
    entry_id: str = "test_entry_id"
    domain: str = "frigate_config_builder"
    title: str = "Test Frigate Config Builder"
    data: dict = field(default_factory=lambda: {
        "output_path": "/config/www/frigate.yml",
        "detector_type": "edgetpu",
        "detector_device": "usb",
        "hwaccel": "vaapi",
        "mqtt_auto": True,
        "audio_detection": True,
        "birdseye_enabled": True,
        "birdseye_mode": "objects",
        "retain_alerts": 30,
        "retain_detections": 30,
        "retain_motion": 7,
        "retain_snapshots": 30,
        "frigate_version": "0.16",  # Default to 0.16
    })
    options: dict = field(default_factory=dict)
    state: str = "loaded"
    

@dataclass
class MockEntityRegistryEntry:
    """Mock Home Assistant entity registry entry."""
    
    entity_id: str
    platform: str
    unique_id: str = ""
    domain: str = "camera"
    disabled: bool = False
    device_id: str | None = None
    area_id: str | None = None
    
    @property
    def disabled_by(self) -> str | None:
        return "user" if self.disabled else None


@dataclass 
class MockDeviceRegistryEntry:
    """Mock Home Assistant device registry entry."""
    
    id: str
    name: str
    name_by_user: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    area_id: str | None = None
    identifiers: set = field(default_factory=set)


@dataclass
class MockAreaRegistryEntry:
    """Mock Home Assistant area registry entry."""
    
    id: str
    name: str


@dataclass
class MockState:
    """Mock Home Assistant state object."""
    
    entity_id: str
    state: str = "idle"
    attributes: dict = field(default_factory=dict)


class MockCameraEntity:
    """Mock camera entity with stream_source method."""
    
    def __init__(self, entity_id: str, stream_url: str | None = None):
        self.entity_id = entity_id
        self._stream_url = stream_url
    
    async def stream_source(self) -> str | None:
        return self._stream_url


class MockEntityRegistry:
    """Mock entity registry."""
    
    def __init__(self, entities: list[MockEntityRegistryEntry] | None = None):
        self._entities = {e.entity_id: e for e in (entities or [])}
    
    @property
    def entities(self) -> dict[str, MockEntityRegistryEntry]:
        return self._entities
    
    @entities.setter
    def entities(self, value: dict):
        self._entities = value
    
    def async_get(self, entity_id: str) -> MockEntityRegistryEntry | None:
        return self._entities.get(entity_id)


class MockDeviceRegistry:
    """Mock device registry."""
    
    def __init__(self, devices: list[MockDeviceRegistryEntry] | None = None):
        self._devices = {d.id: d for d in (devices or [])}
    
    @property
    def devices(self) -> dict:
        return self._devices
    
    @devices.setter
    def devices(self, value: dict):
        self._devices = value
    
    def async_get(self, device_id: str) -> MockDeviceRegistryEntry | None:
        return self._devices.get(device_id)


class MockAreaRegistry:
    """Mock area registry."""
    
    def __init__(self, areas: list[MockAreaRegistryEntry] | None = None):
        self._areas = {a.id: a for a in (areas or [])}
    
    @property
    def areas(self) -> dict:
        return self._areas
    
    @areas.setter
    def areas(self, value: dict):
        self._areas = value
    
    def async_get_area(self, area_id: str) -> MockAreaRegistryEntry | None:
        return self._areas.get(area_id)


class MockCameraComponent:
    """Mock camera component for hass.data['camera']."""
    
    def __init__(self, cameras: dict[str, MockCameraEntity] | None = None):
        self._cameras = cameras or {}
    
    def get_entity(self, entity_id: str) -> MockCameraEntity | None:
        return self._cameras.get(entity_id)


class MockHomeAssistant:
    """Mock Home Assistant core object."""
    
    def __init__(self):
        self.data: dict[str, Any] = {}
        self.states = MockStatesMachine()
        self.config_entries = MockConfigEntries()
        self.config = MockConfig()
    
    def async_create_task(self, coro):
        """Create a task."""
        return asyncio.create_task(coro)


class MockStatesMachine:
    """Mock states machine."""
    
    def __init__(self):
        self._states: dict[str, MockState] = {}
    
    def get(self, entity_id: str) -> MockState | None:
        return self._states.get(entity_id)
    
    def set_state(self, entity_id: str, state: MockState):
        self._states[entity_id] = state


class MockConfigEntries:
    """Mock config entries."""
    
    def __init__(self):
        self._entries: dict[str, list[MockConfigEntry]] = {}
    
    def async_entries(self, domain: str | None = None) -> list[MockConfigEntry]:
        if domain:
            return self._entries.get(domain, [])
        return [e for entries in self._entries.values() for e in entries]
    
    def add_entry(self, domain: str, entry: MockConfigEntry):
        if domain not in self._entries:
            self._entries[domain] = []
        self._entries[domain].append(entry)


class MockConfig:
    """Mock HA config."""
    
    config_dir: str = "/config"


# =============================================================================
# Sample Camera Data (Simple Dictionaries)
# =============================================================================


MOCK_UNIFI_CAMERA_DATA = {
    "id": "unifi_garage_a",
    "name": "garage_a",
    "friendly_name": "Garage A",
    "source": "unifiprotect",
    "record_url": "rtsps://192.168.15.173:7441/LimzvgUEin7vTGsf?enableSrtp",
    "detect_url": "rtsps://192.168.15.173:7441/0tE6FgeTPUfbWNqj?enableSrtp",
    "go2rtc_url": "rtspx://192.168.15.173:7441/LimzvgUEin7vTGsf",
    "width": 640,
    "height": 360,
    "fps": 5,
    "area": "Garage",
    "available": True,
}

MOCK_AMCREST_CAMERA_DATA = {
    "id": "amcrest_192_168_15_96",
    "name": "armcrest",
    "friendly_name": "ArmCrest",
    "source": "amcrest",
    "record_url": "rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=0",
    "detect_url": "rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=1",
    "go2rtc_url": "rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=0",
    "width": 704,
    "height": 480,
    "fps": 5,
    "available": True,
}

MOCK_REOLINK_CAMERA_DATA = {
    "id": "reolink_study_porch",
    "name": "reolink_study_b_porch_ptz",
    "friendly_name": "Study B Porch PTZ",
    "source": "reolink",
    "record_url": "rtsp://admin:Verycool9277@192.168.12.170:554/h264Preview_01_main",
    "detect_url": "rtsp://admin:Verycool9277@192.168.12.170:554/h264Preview_01_sub",
    "go2rtc_url": "rtsp://admin:Verycool9277@192.168.12.170:554/h264Preview_01_main",
    "width": 640,
    "height": 480,
    "fps": 5,
    "available": True,
}


# =============================================================================
# Mock DiscoveredCamera Dataclass (Local copy for testing)
# =============================================================================


@dataclass
class MockDiscoveredCamera:
    """A camera discovered from Home Assistant (test mock)."""

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

    def __post_init__(self) -> None:
        """Set defaults for optional URL fields."""
        if self.detect_url is None:
            self.detect_url = self.record_url
        if self.go2rtc_url is None:
            self.go2rtc_url = self.record_url.replace("rtsps://", "rtspx://")
            if "?" in self.go2rtc_url:
                self.go2rtc_url = self.go2rtc_url.split("?")[0]


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_hass() -> MockHomeAssistant:
    """Create a mock Home Assistant instance."""
    return MockHomeAssistant()


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry with default values (Frigate 0.16)."""
    return MockConfigEntry()


@pytest.fixture
def mock_config_entry_minimal() -> MockConfigEntry:
    """Create a minimal config entry."""
    return MockConfigEntry(
        data={
            "output_path": "/config/www/frigate.yml",
            "detector_type": "cpu",
            "hwaccel": "none",
            "mqtt_auto": False,
            "mqtt_host": "localhost",
            "mqtt_port": 1883,
            "frigate_version": "0.16",
        }
    )


@pytest.fixture
def mock_config_entry_all_features() -> MockConfigEntry:
    """Create a config entry with all features enabled."""
    return MockConfigEntry(
        data={
            "output_path": "/config/www/frigate.yml",
            "detector_type": "edgetpu",
            "detector_device": "usb",
            "hwaccel": "vaapi",
            "mqtt_auto": True,
            "audio_detection": True,
            "birdseye_enabled": True,
            "birdseye_mode": "objects",
            "semantic_search": True,
            "semantic_search_model": "large",
            "face_recognition": True,
            "face_recognition_model": "large",
            "lpr": True,
            "bird_classification": True,
            "retain_alerts": 30,
            "retain_detections": 30,
            "retain_motion": 7,
            "retain_snapshots": 30,
            "frigate_version": "0.16",
        }
    )


@pytest.fixture
def mock_config_entry_017() -> MockConfigEntry:
    """Create a config entry for Frigate 0.17."""
    return MockConfigEntry(
        data={
            "output_path": "/config/www/frigate.yml",
            "detector_type": "edgetpu",
            "detector_device": "usb",
            "hwaccel": "vaapi",
            "mqtt_auto": True,
            "audio_detection": True,
            "birdseye_enabled": True,
            "birdseye_mode": "objects",
            "retain_alerts": 30,
            "retain_detections": 30,
            "retain_motion": 7,
            "retain_snapshots": 30,
            "frigate_version": "0.17",  # Frigate 0.17
        }
    )


@pytest.fixture
def mock_config_entry_017_genai() -> MockConfigEntry:
    """Create a config entry for Frigate 0.17 with GenAI enabled."""
    return MockConfigEntry(
        data={
            "output_path": "/config/www/frigate.yml",
            "detector_type": "edgetpu",
            "detector_device": "usb",
            "hwaccel": "vaapi",
            "mqtt_auto": True,
            "audio_detection": True,
            "birdseye_enabled": True,
            "birdseye_mode": "objects",
            "retain_alerts": 30,
            "retain_detections": 30,
            "retain_motion": 7,
            "retain_snapshots": 30,
            "frigate_version": "0.17",  # Frigate 0.17
            "genai_enabled": True,  # GenAI enabled
            "genai_provider": "gemini",
            "genai_model": "gemini-2.0-flash",
        }
    )


@pytest.fixture
def mock_entity_registry() -> MockEntityRegistry:
    """Create a mock entity registry with sample entities."""
    entities = [
        # UniFi Protect cameras
        MockEntityRegistryEntry(
            entity_id="camera.garage_a_high_resolution_channel",
            platform="unifiprotect",
            unique_id="garage_a_high",
            device_id="unifi_device_1",
        ),
        MockEntityRegistryEntry(
            entity_id="camera.garage_a_low_resolution_channel",
            platform="unifiprotect",
            unique_id="garage_a_low",
            device_id="unifi_device_1",
        ),
        # Reolink cameras
        MockEntityRegistryEntry(
            entity_id="camera.study_b_porch_clear_lens_0",
            platform="reolink",
            unique_id="reolink_clear",
            device_id="reolink_device_1",
        ),
        MockEntityRegistryEntry(
            entity_id="camera.study_b_porch_fluent_lens_0",
            platform="reolink",
            unique_id="reolink_fluent",
            device_id="reolink_device_1",
        ),
    ]
    return MockEntityRegistry(entities)


@pytest.fixture
def mock_device_registry() -> MockDeviceRegistry:
    """Create a mock device registry."""
    devices = [
        MockDeviceRegistryEntry(
            id="unifi_device_1",
            name="Garage A",
            manufacturer="Ubiquiti",
            model="G4 Bullet",
            area_id="garage",
        ),
        MockDeviceRegistryEntry(
            id="reolink_device_1",
            name="Study B Porch PTZ",
            manufacturer="Reolink",
            model="E1 Outdoor",
            area_id="outdoor",
            identifiers={("reolink", "ABC123")},
        ),
    ]
    return MockDeviceRegistry(devices)


@pytest.fixture
def mock_area_registry() -> MockAreaRegistry:
    """Create a mock area registry."""
    areas = [
        MockAreaRegistryEntry(id="garage", name="Garage"),
        MockAreaRegistryEntry(id="outdoor", name="Outdoor"),
        MockAreaRegistryEntry(id="living_room", name="Living Room"),
    ]
    return MockAreaRegistry(areas)


@pytest.fixture
def sample_unifi_camera() -> MockDiscoveredCamera:
    """Create a sample UniFi Protect discovered camera."""
    return MockDiscoveredCamera(**MOCK_UNIFI_CAMERA_DATA)


@pytest.fixture
def sample_amcrest_camera() -> MockDiscoveredCamera:
    """Create a sample Amcrest discovered camera."""
    return MockDiscoveredCamera(**MOCK_AMCREST_CAMERA_DATA)


@pytest.fixture
def sample_reolink_camera() -> MockDiscoveredCamera:
    """Create a sample Reolink discovered camera."""
    return MockDiscoveredCamera(**MOCK_REOLINK_CAMERA_DATA)


@pytest.fixture
def sample_cameras(sample_unifi_camera, sample_amcrest_camera, sample_reolink_camera) -> list:
    """Create a list of sample cameras from different sources."""
    return [sample_unifi_camera, sample_amcrest_camera, sample_reolink_camera]


# =============================================================================
# MQTT Fixtures
# =============================================================================


@pytest.fixture
def mock_mqtt_config_entry() -> MockConfigEntry:
    """Create a mock MQTT config entry."""
    return MockConfigEntry(
        entry_id="mqtt_entry",
        domain="mqtt",
        title="MQTT",
        data={
            "broker": "192.168.1.100",
            "port": 1883,
            "username": "mqtt_user",
            "password": "mqtt_password",
        },
    )


@pytest.fixture
def mock_hass_with_mqtt(mock_hass, mock_mqtt_config_entry) -> MockHomeAssistant:
    """Create a mock HA instance with MQTT configured."""
    mock_hass.config_entries.add_entry("mqtt", mock_mqtt_config_entry)
    return mock_hass
