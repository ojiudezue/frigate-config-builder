"""Frigate configuration generator.

Version: 0.4.0.8
Date: 2026-01-22

Generates Frigate NVR configuration files optimized for the selected Frigate version.

Supported versions:
- 0.16.x (stable): Current stable release
- 0.17.x (latest): Latest with GenAI, tiered retention, stationary classifier

Key version differences handled:
- 0.16+: detect.enabled defaults to false (we always set true)
- 0.16+: TensorRT removed, use ONNX for Nvidia
- 0.16+: go2rtc accepts any audio codec
- 0.16+: record.retain for base retention, alerts/detections separate
- 0.17+: record.continuous/motion replaces record.retain
- 0.17+: detect.stationary.classifier added
- 0.17+: review.genai for AI review summaries
- 0.17+: GenAI config split: global provider + objects.genai
- 0.17+: birdseye.idle_heartbeat_fps added

Changelog:
- 0.4.0.8: FIXED - Correct 0.17 record structure (continuous/motion instead of retain)
           FIXED - Remove invalid events section from 0.16
           FIXED - Use native stream resolution for detect (no scaling)
           ADDED - detect.stationary.classifier for 0.17+
           ADDED - review.genai section for 0.17+
           ADDED - birdseye.idle_heartbeat_fps for 0.17+
           ADDED - alerts/detections pre_capture/post_capture
"""
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
    CONF_FRIGATE_VERSION,
    CONF_GENAI_API_KEY,
    CONF_GENAI_BASE_URL,
    CONF_GENAI_ENABLED,
    CONF_GENAI_MODEL,
    CONF_GENAI_PROVIDER,
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
    DEFAULT_FRIGATE_VERSION,
    DEFAULT_GENAI_PROVIDER,
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
    FrigateVersion,
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
        self._frigate_version = self._data.get(
            CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION
        )

    @property
    def is_017_or_later(self) -> bool:
        """Check if configured for Frigate 0.17 or later."""
        return self._frigate_version >= FrigateVersion.V017.value

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

        # CRITICAL for Frigate 0.16+: detect.enabled defaults to false
        # We MUST explicitly enable detection at the global level
        config["detect"] = self._build_detect()

        config["record"] = self._build_record()
        config["snapshots"] = self._build_snapshots()

        # Review configuration (with GenAI support for 0.17+)
        config["review"] = self._build_review()

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

        # GenAI (Frigate 0.17+ only - global provider config)
        if self.is_017_or_later and self._data.get(CONF_GENAI_ENABLED, False):
            config["genai"] = self._build_genai()
            # Also add objects.genai for object descriptions
            config["objects"] = self._build_objects_with_genai()

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

        # Version marker for generated config
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
        """Build detectors configuration section.

        Note: TensorRT was removed in Frigate 0.16 - use ONNX for Nvidia GPUs.
        """
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

        config: dict[str, Any] = {
            "hwaccel_args": preset,
        }

        # Frigate 0.17+ supports gpu index
        if self.is_017_or_later:
            config["gpu"] = 0

        return config

    def _build_detect(self) -> dict[str, Any]:
        """Build default detect configuration section.

        CRITICAL: In Frigate 0.16+, detection is DISABLED by default.
        We must explicitly set enabled: true for detection to work.

        Note: width/height here are global defaults. Camera-specific values
        should use the native stream resolution without scaling.
        """
        config: dict[str, Any] = {
            "enabled": True,
            "fps": 5,
        }

        # Frigate 0.17+ adds stationary object classifier
        if self.is_017_or_later:
            config["stationary"] = {
                "classifier": True,
                "interval": 50,
                "threshold": 50,
            }

        return config

    def _build_record(self) -> dict[str, Any]:
        """Build record configuration section.

        Frigate 0.17 changed the retention structure:
        - REMOVED: record.retain.days and record.retain.mode
        - ADDED: record.continuous.days (for 24/7 recording regardless of activity)
        - ADDED: record.motion.days (for motion-based retention)
        - alerts/detections now have pre_capture and post_capture

        Frigate 0.16 uses:
        - record.retain.days and record.retain.mode for base retention
        - alerts/detections with their own retain settings
        """
        retain_alerts = self._data.get(CONF_RETAIN_ALERTS, DEFAULT_RETAIN_ALERTS)
        retain_detections = self._data.get(CONF_RETAIN_DETECTIONS, DEFAULT_RETAIN_DETECTIONS)
        retain_motion = self._data.get(CONF_RETAIN_MOTION, DEFAULT_RETAIN_MOTION)

        if self.is_017_or_later:
            # Frigate 0.17+ tiered retention structure
            # Uses continuous/motion instead of retain at top level
            return {
                "enabled": True,
                "expire_interval": 60,
                "continuous": {
                    # Days to retain all recordings regardless of activity
                    # Set to 0 to only keep alerts/detections/motion
                    "days": 0,
                },
                "motion": {
                    # Days to retain recordings with any detected motion
                    "days": retain_motion,
                },
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {
                        "days": retain_alerts,
                        "mode": "motion",
                    },
                },
                "detections": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {
                        "days": retain_detections,
                        "mode": "motion",
                    },
                },
            }
        else:
            # Frigate 0.16 structure
            # Uses retain.days/mode at top level
            return {
                "enabled": True,
                "expire_interval": 60,
                "retain": {
                    "days": retain_motion,
                    "mode": "motion",
                },
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {
                        "days": retain_alerts,
                        "mode": "motion",
                    },
                },
                "detections": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {
                        "days": retain_detections,
                        "mode": "motion",
                    },
                },
            }

    def _build_review(self) -> dict[str, Any]:
        """Build review configuration section.

        Frigate 0.17 adds:
        - cutoff_time for alerts and detections
        - genai section for AI review summaries
        """
        config: dict[str, Any] = {
            "alerts": {
                "enabled": True,
                "labels": ["car", "person"],
            },
            "detections": {
                "enabled": True,
                "labels": ["car", "person"],
            },
        }

        if self.is_017_or_later:
            # Add cutoff_time for 0.17+
            config["alerts"]["cutoff_time"] = 40
            config["detections"]["cutoff_time"] = 30

            # Add GenAI review summaries if GenAI is enabled
            if self._data.get(CONF_GENAI_ENABLED, False):
                config["genai"] = {
                    "enabled": True,
                    "alerts": True,
                    "detections": False,
                    "image_source": "preview",
                }

        return config

    def _build_snapshots(self) -> dict[str, Any]:
        """Build snapshots configuration section."""
        retain_snapshots = self._data.get(CONF_RETAIN_SNAPSHOTS, DEFAULT_RETAIN_SNAPSHOTS)

        return {
            "enabled": True,
            "clean_copy": True,
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

        config: dict[str, Any] = {
            "enabled": True,
            "mode": mode,
            "width": 2560,
            "height": 1440,
            "quality": 8,
        }

        # Frigate 0.17+ adds idle_heartbeat_fps
        if self.is_017_or_later:
            config["idle_heartbeat_fps"] = 0.0

        return config

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

    def _build_genai(self) -> dict[str, Any]:
        """Build GenAI configuration section (Frigate 0.17+ only).

        In 0.17, the global genai config configures the AI provider.
        Object-specific GenAI settings are configured under objects -> genai.
        """
        provider = self._data.get(CONF_GENAI_PROVIDER, DEFAULT_GENAI_PROVIDER)
        model = self._data.get(CONF_GENAI_MODEL)
        api_key = self._data.get(CONF_GENAI_API_KEY)
        base_url = self._data.get(CONF_GENAI_BASE_URL)

        config: dict[str, Any] = {
            "provider": provider,
        }

        if model:
            config["model"] = model

        if api_key:
            config["api_key"] = api_key

        if base_url:
            config["base_url"] = base_url

        return config

    def _build_objects_with_genai(self) -> dict[str, Any]:
        """Build objects section with GenAI for object descriptions (0.17+)."""
        return {
            "track": ["person", "car", "dog", "cat"],
            "genai": {
                "enabled": True,
                "use_snapshot": False,
                "prompt": "Describe the {label} in the sequence of images with as much detail as possible. Do not describe the background.",
                "objects": ["person", "car"],
                "send_triggers": {
                    "tracked_object_end": True,
                },
            },
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
        """Build go2rtc streams section.

        Note: In Frigate 0.16+, go2rtc accepts any audio codec (not just AAC).
        This makes camera setup easier but recordings may still need AAC
        for broad playback compatibility.
        """
        streams: dict[str, list[str]] = {}

        for cam in cameras:
            if cam.go2rtc_url:
                streams[cam.name] = [cam.go2rtc_url]

        return {"streams": streams}

    def _build_cameras(self, cameras: list[DiscoveredCamera]) -> dict[str, Any]:
        """Build cameras configuration section.

        IMPORTANT: The detect width/height should match the NATIVE resolution
        of the stream assigned the detect role. Frigate will waste CPU if it
        has to resize the stream to different dimensions.
        """
        result: dict[str, Any] = {}
        hwaccel = self._data.get(CONF_HWACCEL, DEFAULT_HWACCEL)
        hwaccel_preset = FFMPEG_HWACCEL_PRESETS.get(hwaccel, "preset-vaapi")

        for cam in cameras:
            camera_config: dict[str, Any] = {
                "enabled": True,
                "ffmpeg": {
                    "inputs": [],
                },
                # CRITICAL for Frigate 0.16+: Must explicitly enable detection
                # Use native stream dimensions without scaling
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
            # Note: In 0.16+, use preset-record-generic-audio-aac for compatibility
            source = cam.source if isinstance(cam.source, str) else cam.source.value
            record_preset = RECORD_PRESETS.get(source, "preset-record-generic-audio-aac")
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
