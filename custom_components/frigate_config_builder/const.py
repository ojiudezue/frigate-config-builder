"""Constants for Frigate Config Builder."""
from __future__ import annotations

from enum import StrEnum
from typing import Final

DOMAIN: Final = "frigate_config_builder"

# =============================================================================
# Config Entry Keys
# =============================================================================

# Connection
CONF_OUTPUT_PATH: Final = "output_path"
CONF_FRIGATE_URL: Final = "frigate_url"
CONF_AUTO_PUSH: Final = "auto_push"

# Hardware
CONF_DETECTOR_TYPE: Final = "detector_type"
CONF_DETECTOR_DEVICE: Final = "detector_device"
CONF_HWACCEL: Final = "hwaccel"
CONF_NETWORK_INTERFACES: Final = "network_interfaces"

# MQTT
CONF_MQTT_AUTO: Final = "mqtt_auto"
CONF_MQTT_HOST: Final = "mqtt_host"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USER: Final = "mqtt_user"
CONF_MQTT_PASSWORD: Final = "mqtt_password"

# Features
CONF_AUDIO_DETECTION: Final = "audio_detection"
CONF_FACE_RECOGNITION: Final = "face_recognition"
CONF_FACE_RECOGNITION_MODEL: Final = "face_recognition_model"
CONF_SEMANTIC_SEARCH: Final = "semantic_search"
CONF_SEMANTIC_SEARCH_MODEL: Final = "semantic_search_model"
CONF_LPR: Final = "lpr"
CONF_BIRD_CLASSIFICATION: Final = "bird_classification"
CONF_BIRDSEYE_ENABLED: Final = "birdseye_enabled"
CONF_BIRDSEYE_MODE: Final = "birdseye_mode"

# Retention
CONF_RETAIN_ALERTS: Final = "retain_alerts"
CONF_RETAIN_DETECTIONS: Final = "retain_detections"
CONF_RETAIN_MOTION: Final = "retain_motion"
CONF_RETAIN_SNAPSHOTS: Final = "retain_snapshots"

# Camera Selection (Options)
CONF_SELECTED_CAMERAS: Final = "selected_cameras"
CONF_EXCLUDE_UNAVAILABLE: Final = "exclude_unavailable"
CONF_AUTO_GROUPS: Final = "auto_groups_from_areas"
CONF_MANUAL_GROUPS: Final = "manual_groups"
CONF_MANUAL_CAMERAS: Final = "manual_cameras"
CONF_CREDENTIAL_OVERRIDES: Final = "credential_overrides"

# =============================================================================
# Defaults
# =============================================================================

DEFAULT_OUTPUT_PATH: Final = "/config/www/frigate.yml"
DEFAULT_DETECTOR_TYPE: Final = "edgetpu"
DEFAULT_DETECTOR_DEVICE: Final = "usb"
DEFAULT_HWACCEL: Final = "vaapi"
DEFAULT_NETWORK_INTERFACE: Final = "eth0"
DEFAULT_MQTT_PORT: Final = 1883
DEFAULT_RETAIN_ALERTS: Final = 30
DEFAULT_RETAIN_DETECTIONS: Final = 30
DEFAULT_RETAIN_MOTION: Final = 7
DEFAULT_RETAIN_SNAPSHOTS: Final = 30
DEFAULT_BIRDSEYE_MODE: Final = "objects"
DEFAULT_MODEL_SIZE: Final = "large"

# =============================================================================
# Enums
# =============================================================================


class DetectorType(StrEnum):
    """Frigate detector types."""

    EDGETPU = "edgetpu"
    CPU = "cpu"
    OPENVINO = "openvino"
    TENSORRT = "tensorrt"
    ONNX = "onnx"


class HwaccelType(StrEnum):
    """Hardware acceleration types."""

    VAAPI = "vaapi"
    CUDA = "cuda"
    QSV = "qsv"
    RKMPP = "rkmpp"
    V4L2M2M = "v4l2m2m"
    NONE = "none"


class CameraSource(StrEnum):
    """Camera integration source types."""

    UNIFIPROTECT = "unifiprotect"
    AMCREST = "amcrest"
    REOLINK = "reolink"
    MANUAL = "manual"


class BirdseyeMode(StrEnum):
    """Birdseye view modes."""

    CONTINUOUS = "continuous"
    MOTION = "motion"
    OBJECTS = "objects"


class ModelSize(StrEnum):
    """Model size options for ML features."""

    SMALL = "small"
    LARGE = "large"


# =============================================================================
# Options for UI Selectors
# =============================================================================

DETECTOR_TYPES: Final = [e.value for e in DetectorType]

HWACCEL_OPTIONS: Final = [
    ("vaapi", "VAAPI (Intel)"),
    ("cuda", "CUDA (NVIDIA)"),
    ("qsv", "QuickSync (Intel)"),
    ("rkmpp", "RKMPP (Rockchip)"),
    ("v4l2m2m", "V4L2M2M (Raspberry Pi)"),
    ("none", "None (Software)"),
]

HWACCEL_TYPES: Final = [k for k, _ in HWACCEL_OPTIONS]

MODEL_SIZES: Final = [e.value for e in ModelSize]

BIRDSEYE_MODES: Final = [e.value for e in BirdseyeMode]

# =============================================================================
# FFMPEG Presets by Hardware Acceleration Type
# =============================================================================

FFMPEG_HWACCEL_PRESETS: Final = {
    "vaapi": "preset-vaapi",
    "cuda": "preset-nvidia-h264",
    "qsv": "preset-intel-qsv-h264",
    "rkmpp": "preset-rkmpp",
    "v4l2m2m": "preset-rpi-64-h264",
    "none": "preset-http-jpeg-generic",
}

# =============================================================================
# Record Output Args Presets by Camera Source
# =============================================================================

RECORD_PRESETS: Final = {
    "unifiprotect": "preset-record-ubiquiti",
    "amcrest": "preset-record-generic-audio-aac",
    "reolink": "preset-record-generic-audio-aac",
    "manual": "preset-record-generic",
}

# =============================================================================
# Frigate Config Version
# =============================================================================

FRIGATE_CONFIG_VERSION: Final = "0.14-1"
