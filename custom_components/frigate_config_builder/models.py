"""Data models for Frigate Config Builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .const import CameraSource


@dataclass
class DiscoveredCamera:
    """A camera discovered from Home Assistant or manually defined."""

    id: str  # Unique key: "unifi_garage_a"
    name: str  # Frigate camera name: "garage_a"
    friendly_name: str  # Display name: "Garage A"
    source: CameraSource | str  # Where it came from

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


@dataclass
class FrigateBuilderConfig:
    """Complete integration configuration."""

    # === Connection ===
    output_path: str = "/config/www/frigate.yml"
    frigate_url: str | None = None
    auto_push: bool = False

    # === Hardware ===
    detector_type: str = "edgetpu"
    detector_device: str = "usb"
    hwaccel: str = "vaapi"
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

    @classmethod
    def from_config_entry(cls, data: dict, options: dict | None = None) -> FrigateBuilderConfig:
        """Create config from HA config entry data and options."""
        config = cls(
            # Connection
            output_path=data.get("output_path", cls.output_path),
            frigate_url=data.get("frigate_url"),
            auto_push=data.get("auto_push", False),
            # Hardware
            detector_type=data.get("detector_type", cls.detector_type),
            detector_device=data.get("detector_device", cls.detector_device),
            hwaccel=data.get("hwaccel", cls.hwaccel),
            network_interfaces=data.get("network_interfaces", ["eth0"]),
            # MQTT
            mqtt_auto=data.get("mqtt_auto", True),
            mqtt_host=data.get("mqtt_host"),
            mqtt_port=data.get("mqtt_port", 1883),
            mqtt_user=data.get("mqtt_user"),
            mqtt_password=data.get("mqtt_password"),
            # Features
            audio_detection=data.get("audio_detection", True),
            face_recognition=data.get("face_recognition", False),
            face_recognition_model=data.get("face_recognition_model", "large"),
            semantic_search=data.get("semantic_search", False),
            semantic_search_model=data.get("semantic_search_model", "large"),
            lpr=data.get("lpr", False),
            bird_classification=data.get("bird_classification", False),
            birdseye_enabled=data.get("birdseye_enabled", True),
            birdseye_mode=data.get("birdseye_mode", "objects"),
            # Retention
            retain_alerts=data.get("retain_alerts", 30),
            retain_detections=data.get("retain_detections", 30),
            retain_motion=data.get("retain_motion", 7),
            retain_snapshots=data.get("retain_snapshots", 30),
        )

        # Apply options if provided
        if options:
            config.selected_cameras = options.get("selected_cameras", [])
            config.auto_groups_from_areas = options.get("auto_groups_from_areas", True)
            config.manual_groups = options.get("manual_groups", {})
            config.manual_cameras = options.get("manual_cameras", [])
            config.credential_overrides = options.get("credential_overrides", {})

        return config
