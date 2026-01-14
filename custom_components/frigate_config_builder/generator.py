"""Frigate configuration generator."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import yaml

from .const import (
    CONF_AUDIO_DETECTION,
    CONF_BIRD_CLASSIFICATION,
    CONF_BIRDSEYE_ENABLED,
    CONF_BIRDSEYE_MODE,
    CONF_DETECTOR_DEVICE,
    CONF_DETECTOR_TYPE,
    CONF_FACE_RECOGNITION,
    CONF_FACE_RECOGNITION_MODEL,
    CONF_HWACCEL,
    CONF_LPR,
    CONF_MQTT_AUTO,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_NETWORK_INTERFACES,
    CONF_RETAIN_ALERTS,
    CONF_RETAIN_DETECTIONS,
    CONF_RETAIN_MOTION,
    CONF_RETAIN_SNAPSHOTS,
    CONF_SEMANTIC_SEARCH,
    CONF_SEMANTIC_SEARCH_MODEL,
    DEFAULT_BIRDSEYE_MODE,
    DEFAULT_DETECTOR_DEVICE,
    DEFAULT_DETECTOR_TYPE,
    DEFAULT_HWACCEL,
    DEFAULT_MODEL_SIZE,
    DEFAULT_MQTT_PORT,
    DEFAULT_NETWORK_INTERFACE,
    DEFAULT_RETAIN_ALERTS,
    DEFAULT_RETAIN_DETECTIONS,
    DEFAULT_RETAIN_MOTION,
    DEFAULT_RETAIN_SNAPSHOTS,
    FFMPEG_HWACCEL_PRESETS,
    FRIGATE_CONFIG_VERSION,
    RECORD_PRESETS,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .models import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)


class FrigateConfigGenerator:
    """Generate Frigate YAML configuration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the generator."""
        self.hass = hass
        self.entry = entry
        self._data = entry.data
        self._options = entry.options

    async def generate(self, cameras: list[DiscoveredCamera] | None = None) -> str:
        """Generate complete Frigate configuration.

        Args:
            cameras: List of discovered cameras to include. If None, generates
                    static config sections only (for Milestone 1).

        Returns:
            YAML string of the complete Frigate configuration.
        """
        cameras = cameras or []

        config: dict[str, Any] = {}

        # Build all sections in order
        config["mqtt"] = await self._build_mqtt()
        config["detectors"] = self._build_detectors()
        config["ffmpeg"] = self._build_ffmpeg()
        config["detect"] = self._build_detect()
        config["record"] = self._build_record()
        config["snapshots"] = self._build_snapshots()

        # Audio detection
        if self._data.get(CONF_AUDIO_DETECTION, True):
            config["audio"] = self._build_audio()

        # Birdseye
        if self._data.get(CONF_BIRDSEYE_ENABLED, True):
            config["birdseye"] = self._build_birdseye()

        # Optional ML features
        if self._data.get(CONF_SEMANTIC_SEARCH, False):
            config["semantic_search"] = self._build_semantic_search()

        if self._data.get(CONF_FACE_RECOGNITION, False):
            config["face_recognition"] = self._build_face_recognition()

        if self._data.get(CONF_LPR, False):
            config["lpr"] = {"enabled": True}

        if self._data.get(CONF_BIRD_CLASSIFICATION, False):
            config["classification"] = {"bird": {"enabled": True}}

        # go2rtc streams
        if cameras:
            config["go2rtc"] = self._build_go2rtc(cameras)
            config["cameras"] = self._build_cameras(cameras)

            # Camera groups
            groups = await self._build_camera_groups(cameras)
            if groups:
                config["camera_groups"] = groups
        else:
            # Placeholder for M1 - no cameras yet
            config["go2rtc"] = {"streams": {}}
            config["cameras"] = {}

        # Telemetry
        config["telemetry"] = self._build_telemetry()

        # Version
        config["version"] = FRIGATE_CONFIG_VERSION

        # Generate YAML with custom representer for clean output
        return self._dump_yaml(config)

    def _dump_yaml(self, config: dict) -> str:
        """Dump config to YAML with clean formatting."""

        class CleanDumper(yaml.SafeDumper):
            """Custom YAML dumper for cleaner output."""

            pass

        # Don't use aliases
        CleanDumper.ignore_aliases = lambda self, data: True

        # Represent None as empty string (omit)
        def represent_none(dumper, data):
            return dumper.represent_scalar("tag:yaml.org,2002:null", "")

        CleanDumper.add_representer(type(None), represent_none)

        # Clean up None values from dict before dumping
        cleaned = self._clean_none_values(config)

        return yaml.dump(
            cleaned,
            Dumper=CleanDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def _clean_none_values(self, obj: Any) -> Any:
        """Recursively remove None values from dicts."""
        if isinstance(obj, dict):
            return {k: self._clean_none_values(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [self._clean_none_values(item) for item in obj]
        return obj

    # =========================================================================
    # Section Builders
    # =========================================================================

    async def _build_mqtt(self) -> dict[str, Any]:
        """Build MQTT configuration section."""
        if self._data.get(CONF_MQTT_AUTO, True):
            # Get from HA MQTT integration
            mqtt_entries = self.hass.config_entries.async_entries("mqtt")
            if mqtt_entries:
                mqtt_data = mqtt_entries[0].data
                return {
                    "host": mqtt_data.get("broker", "localhost"),
                    "port": mqtt_data.get("port", DEFAULT_MQTT_PORT),
                    "user": mqtt_data.get("username"),
                    "password": mqtt_data.get("password"),
                }
            _LOGGER.warning("MQTT auto-detect enabled but no MQTT integration found")

        # Manual config
        return {
            "host": self._data.get(CONF_MQTT_HOST, "localhost"),
            "port": self._data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
            "user": self._data.get(CONF_MQTT_USER),
            "password": self._data.get(CONF_MQTT_PASSWORD),
        }

    def _build_detectors(self) -> dict[str, Any]:
        """Build detectors configuration section."""
        detector_type = self._data.get(CONF_DETECTOR_TYPE, DEFAULT_DETECTOR_TYPE)
        detector_device = self._data.get(CONF_DETECTOR_DEVICE, DEFAULT_DETECTOR_DEVICE)

        return {
            "default": {
                "type": detector_type,
                "device": detector_device,
            }
        }

    def _build_ffmpeg(self) -> dict[str, Any]:
        """Build FFmpeg configuration section."""
        hwaccel = self._data.get(CONF_HWACCEL, DEFAULT_HWACCEL)
        preset = FFMPEG_HWACCEL_PRESETS.get(hwaccel, "preset-vaapi")

        return {
            "hwaccel_args": preset,
        }

    def _build_detect(self) -> dict[str, Any]:
        """Build default detect configuration section."""
        return {
            "enabled": True,
            "width": 640,
            "height": 360,
            "fps": 5,
        }

    def _build_record(self) -> dict[str, Any]:
        """Build record configuration section."""
        retain_alerts = self._data.get(CONF_RETAIN_ALERTS, DEFAULT_RETAIN_ALERTS)
        retain_detections = self._data.get(CONF_RETAIN_DETECTIONS, DEFAULT_RETAIN_DETECTIONS)
        retain_motion = self._data.get(CONF_RETAIN_MOTION, DEFAULT_RETAIN_MOTION)

        return {
            "enabled": True,
            "retain": {
                "days": 0,  # Don't retain all recordings
                "mode": "motion",
            },
            "alerts": {
                "retain": {
                    "days": retain_alerts,
                    "mode": "motion",
                }
            },
            "detections": {
                "retain": {
                    "days": retain_detections,
                    "mode": "motion",
                }
            },
            "events": {
                "retain": {
                    "default": retain_motion,
                    "mode": "motion",
                }
            },
        }

    def _build_snapshots(self) -> dict[str, Any]:
        """Build snapshots configuration section."""
        retain_snapshots = self._data.get(CONF_RETAIN_SNAPSHOTS, DEFAULT_RETAIN_SNAPSHOTS)

        return {
            "enabled": True,
            "timestamp": True,
            "bounding_box": True,
            "retain": {
                "default": retain_snapshots,
            },
        }

    def _build_audio(self) -> dict[str, Any]:
        """Build audio detection configuration section."""
        return {
            "enabled": True,
            "listen": [
                "bark",
                "fire_alarm",
                "scream",
                "speech",
                "yell",
            ],
        }

    def _build_birdseye(self) -> dict[str, Any]:
        """Build birdseye configuration section."""
        mode = self._data.get(CONF_BIRDSEYE_MODE, DEFAULT_BIRDSEYE_MODE)

        return {
            "enabled": True,
            "mode": mode,
            "width": 2560,
            "height": 1440,
            "quality": 80,
        }

    def _build_semantic_search(self) -> dict[str, Any]:
        """Build semantic search configuration section."""
        model_size = self._data.get(CONF_SEMANTIC_SEARCH_MODEL, DEFAULT_MODEL_SIZE)

        return {
            "enabled": True,
            "model_size": model_size,
        }

    def _build_face_recognition(self) -> dict[str, Any]:
        """Build face recognition configuration section."""
        model_size = self._data.get(CONF_FACE_RECOGNITION_MODEL, DEFAULT_MODEL_SIZE)

        return {
            "enabled": True,
            "model_size": model_size,
        }

    def _build_telemetry(self) -> dict[str, Any]:
        """Build telemetry configuration section."""
        network_interfaces = self._data.get(CONF_NETWORK_INTERFACES, DEFAULT_NETWORK_INTERFACE)

        # Handle string or list
        if isinstance(network_interfaces, str):
            interfaces = [iface.strip() for iface in network_interfaces.split(",")]
        else:
            interfaces = network_interfaces

        return {
            "network_interfaces": interfaces,
        }

    def _build_go2rtc(self, cameras: list[DiscoveredCamera]) -> dict[str, Any]:
        """Build go2rtc streams section."""
        streams: dict[str, list[str]] = {}

        for cam in cameras:
            if cam.go2rtc_url:
                streams[cam.name] = [cam.go2rtc_url]

        return {"streams": streams}

    def _build_cameras(self, cameras: list[DiscoveredCamera]) -> dict[str, Any]:
        """Build cameras configuration section."""
        result: dict[str, Any] = {}
        hwaccel = self._data.get(CONF_HWACCEL, DEFAULT_HWACCEL)
        hwaccel_preset = FFMPEG_HWACCEL_PRESETS.get(hwaccel, "preset-vaapi")

        for cam in cameras:
            camera_config: dict[str, Any] = {
                "enabled": True,
                "ffmpeg": {
                    "inputs": [],
                },
                "detect": {
                    "enabled": True,
                    "width": cam.width,
                    "height": cam.height,
                    "fps": cam.fps,
                },
            }

            # Separate record and detect streams if different
            if cam.record_url != cam.detect_url and cam.detect_url:
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

            # Set hwaccel preset
            camera_config["ffmpeg"]["hwaccel_args"] = hwaccel_preset

            # Set record preset based on source
            source = cam.source if isinstance(cam.source, str) else cam.source.value
            record_preset = RECORD_PRESETS.get(source, "preset-record-generic")
            camera_config["ffmpeg"]["output_args"] = {"record": record_preset}

            result[cam.name] = camera_config

        return result

    async def _build_camera_groups(self, cameras: list[DiscoveredCamera]) -> dict[str, Any]:
        """Build camera groups from HA areas or manual config."""
        groups: dict[str, Any] = {}

        if self._options.get("auto_groups_from_areas", True):
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
        manual = self._options.get("manual_groups", {})
        for name, cam_names in manual.items():
            groups[name] = {
                "order": len(groups) + 1,
                "icon": "LuCamera",
                "cameras": cam_names,
            }

        return groups
