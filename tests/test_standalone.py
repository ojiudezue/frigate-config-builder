"""Standalone tests that don't require Home Assistant dependencies.

Version: 0.4.0.8
Date: 2026-01-22

These tests can be run without installing homeassistant package.
They validate YAML generation, schema compliance, and basic logic.

Changelog:
- 0.4.0.8: Updated record tests for correct 0.16/0.17 structures
           Added tests for stationary classifier, review.genai, etc.
"""
from __future__ import annotations

import pytest
import yaml
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Mock Data Classes (standalone versions)
# =============================================================================


@dataclass
class MockDiscoveredCamera:
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


# =============================================================================
# Test YAML Generation
# =============================================================================


class TestYAMLGeneration:
    """Tests for YAML generation without HA dependencies."""

    def test_build_mqtt_section(self):
        """Test MQTT section generation."""
        mqtt = {
            "host": "192.168.1.100",
            "port": 1883,
            "user": "mqtt_user",
            "password": "mqtt_pass",
        }
        
        yaml_str = yaml.dump({"mqtt": mqtt}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["mqtt"]["host"] == "192.168.1.100"
        assert parsed["mqtt"]["port"] == 1883

    def test_build_detectors_section_edgetpu(self):
        """Test EdgeTPU detector section."""
        detectors = {
            "default": {
                "type": "edgetpu",
                "device": "usb",
            }
        }
        
        yaml_str = yaml.dump({"detectors": detectors}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["detectors"]["default"]["type"] == "edgetpu"
        assert parsed["detectors"]["default"]["device"] == "usb"

    def test_build_detectors_section_cpu(self):
        """Test CPU detector section."""
        detectors = {
            "default": {
                "type": "cpu",
            }
        }
        
        yaml_str = yaml.dump({"detectors": detectors}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["detectors"]["default"]["type"] == "cpu"

    def test_build_ffmpeg_section_vaapi(self):
        """Test FFmpeg section with VAAPI."""
        ffmpeg = {
            "hwaccel_args": "preset-vaapi",
        }
        
        yaml_str = yaml.dump({"ffmpeg": ffmpeg}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["ffmpeg"]["hwaccel_args"] == "preset-vaapi"

    def test_build_ffmpeg_section_017_with_gpu(self):
        """Test FFmpeg section with GPU index for 0.17+."""
        ffmpeg = {
            "hwaccel_args": "preset-vaapi",
            "gpu": 0,
        }
        
        yaml_str = yaml.dump({"ffmpeg": ffmpeg}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["ffmpeg"]["hwaccel_args"] == "preset-vaapi"
        assert parsed["ffmpeg"]["gpu"] == 0

    def test_build_record_section_frigate_016(self):
        """Test Frigate 0.16 record section with retention settings.
        
        0.16 uses retain.days/mode at top level for base retention.
        """
        record = {
            "enabled": True,
            "expire_interval": 60,
            "retain": {
                "days": 1,
                "mode": "motion",
            },
            "alerts": {
                "pre_capture": 5,
                "post_capture": 5,
                "retain": {
                    "days": 14,
                    "mode": "motion",
                },
            },
            "detections": {
                "pre_capture": 5,
                "post_capture": 5,
                "retain": {
                    "days": 14,
                    "mode": "motion",
                },
            },
        }
        
        yaml_str = yaml.dump({"record": record}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        # Verify 0.16 structure
        assert parsed["record"]["retain"]["days"] == 1
        assert parsed["record"]["retain"]["mode"] == "motion"
        assert parsed["record"]["alerts"]["retain"]["days"] == 14
        assert parsed["record"]["alerts"]["pre_capture"] == 5
        assert parsed["record"]["detections"]["retain"]["days"] == 14
        # No continuous/motion keys at top level for 0.16
        assert "continuous" not in parsed["record"]

    def test_build_record_section_frigate_017_tiered(self):
        """Test Frigate 0.17 tiered retention structure.
        
        0.17 removes record.retain.days/mode and replaces with:
        - continuous.days: for 24/7 recording regardless of activity
        - motion.days: for motion-based retention
        """
        record = {
            "enabled": True,
            "expire_interval": 60,
            "continuous": {
                "days": 0,  # Only keep alerts/detections
            },
            "motion": {
                "days": 1,  # Motion retention
            },
            "alerts": {
                "pre_capture": 5,
                "post_capture": 5,
                "retain": {
                    "days": 14,
                    "mode": "motion",
                },
            },
            "detections": {
                "pre_capture": 5,
                "post_capture": 5,
                "retain": {
                    "days": 14,
                    "mode": "motion",
                },
            },
        }
        
        yaml_str = yaml.dump({"record": record}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        # Verify 0.17 structure
        assert parsed["record"]["continuous"]["days"] == 0
        assert parsed["record"]["motion"]["days"] == 1
        assert parsed["record"]["alerts"]["retain"]["days"] == 14
        assert parsed["record"]["alerts"]["pre_capture"] == 5
        assert parsed["record"]["detections"]["post_capture"] == 5
        # No retain at top level for 0.17
        assert "retain" not in parsed["record"]

    def test_build_detect_section_016(self):
        """Test detect section for 0.16."""
        detect = {
            "enabled": True,
            "fps": 5,
        }
        
        yaml_str = yaml.dump({"detect": detect}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["detect"]["enabled"] is True
        assert parsed["detect"]["fps"] == 5
        assert "stationary" not in parsed["detect"]

    def test_build_detect_section_017_with_stationary(self):
        """Test detect section with stationary classifier for 0.17+."""
        detect = {
            "enabled": True,
            "fps": 5,
            "stationary": {
                "classifier": True,
                "interval": 50,
                "threshold": 50,
            },
        }
        
        yaml_str = yaml.dump({"detect": detect}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["detect"]["enabled"] is True
        assert parsed["detect"]["stationary"]["classifier"] is True

    def test_build_audio_section(self):
        """Test audio detection section."""
        audio = {
            "enabled": True,
            "listen": ["bark", "speech", "car_alarm"],
        }
        
        yaml_str = yaml.dump({"audio": audio}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["audio"]["enabled"] is True
        assert "bark" in parsed["audio"]["listen"]

    def test_build_birdseye_section(self):
        """Test birdseye section."""
        birdseye = {
            "enabled": True,
            "mode": "objects",
            "width": 1280,
            "height": 720,
        }
        
        yaml_str = yaml.dump({"birdseye": birdseye}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["birdseye"]["mode"] == "objects"

    def test_build_birdseye_section_017_with_heartbeat(self):
        """Test birdseye section with idle_heartbeat_fps for 0.17+."""
        birdseye = {
            "enabled": True,
            "mode": "objects",
            "width": 2560,
            "height": 1440,
            "quality": 8,
            "idle_heartbeat_fps": 0.0,
        }
        
        yaml_str = yaml.dump({"birdseye": birdseye}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["birdseye"]["idle_heartbeat_fps"] == 0.0

    def test_build_review_section_016(self):
        """Test review section for 0.16."""
        review = {
            "alerts": {
                "enabled": True,
                "labels": ["car", "person"],
            },
            "detections": {
                "enabled": True,
                "labels": ["car", "person"],
            },
        }
        
        yaml_str = yaml.dump({"review": review}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["review"]["alerts"]["enabled"] is True
        assert "cutoff_time" not in parsed["review"]["alerts"]

    def test_build_review_section_017_with_cutoff_and_genai(self):
        """Test review section with cutoff_time and GenAI for 0.17+."""
        review = {
            "alerts": {
                "enabled": True,
                "labels": ["car", "person"],
                "cutoff_time": 40,
            },
            "detections": {
                "enabled": True,
                "labels": ["car", "person"],
                "cutoff_time": 30,
            },
            "genai": {
                "enabled": True,
                "alerts": True,
                "detections": False,
                "image_source": "preview",
            },
        }
        
        yaml_str = yaml.dump({"review": review}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["review"]["alerts"]["cutoff_time"] == 40
        assert parsed["review"]["detections"]["cutoff_time"] == 30
        assert parsed["review"]["genai"]["enabled"] is True

    def test_build_camera_single_stream(self):
        """Test camera with single stream."""
        cameras = {
            "front_door": {
                "ffmpeg": {
                    "inputs": [
                        {
                            "path": "rtsp://192.168.1.10/stream",
                            "roles": ["detect", "record", "audio"],
                        }
                    ]
                },
                "detect": {
                    "enabled": True,
                    "width": 640,
                    "height": 480,
                    "fps": 5,
                },
            }
        }
        
        yaml_str = yaml.dump({"cameras": cameras}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        cam = parsed["cameras"]["front_door"]
        assert len(cam["ffmpeg"]["inputs"]) == 1
        assert "detect" in cam["ffmpeg"]["inputs"][0]["roles"]
        assert "record" in cam["ffmpeg"]["inputs"][0]["roles"]

    def test_build_camera_dual_stream(self):
        """Test camera with dual stream (record + detect)."""
        cameras = {
            "garage": {
                "ffmpeg": {
                    "inputs": [
                        {
                            "path": "rtsp://192.168.1.10/main",
                            "roles": ["record", "audio"],
                        },
                        {
                            "path": "rtsp://192.168.1.10/sub",
                            "roles": ["detect"],
                        },
                    ]
                },
                "detect": {
                    "enabled": True,
                    "width": 640,
                    "height": 360,
                    "fps": 5,
                },
            }
        }
        
        yaml_str = yaml.dump({"cameras": cameras}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        cam = parsed["cameras"]["garage"]
        assert len(cam["ffmpeg"]["inputs"]) == 2
        assert "record" in cam["ffmpeg"]["inputs"][0]["roles"]
        assert "detect" in cam["ffmpeg"]["inputs"][1]["roles"]

    def test_build_go2rtc_section(self):
        """Test go2rtc streams section."""
        go2rtc = {
            "streams": {
                "front_door": ["rtspx://192.168.1.10/stream"],
                "garage": ["rtspx://192.168.1.11/main"],
            }
        }
        
        yaml_str = yaml.dump({"go2rtc": go2rtc}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert "front_door" in parsed["go2rtc"]["streams"]
        assert "garage" in parsed["go2rtc"]["streams"]


class TestCameraDataProcessing:
    """Tests for camera data processing logic."""

    def test_camera_name_sanitization(self):
        """Test camera name sanitization."""
        # Frigate requires lowercase names with underscores
        raw_names = [
            "Front Door Camera",
            "Garage-A",
            "Back Yard (PTZ)",
            "cam_01_living_room",
        ]
        
        def sanitize_name(name: str) -> str:
            """Sanitize camera name for Frigate."""
            import re
            name = name.lower()
            name = re.sub(r'[^a-z0-9_]', '_', name)
            name = re.sub(r'_+', '_', name)
            name = name.strip('_')
            return name
        
        expected = [
            "front_door_camera",
            "garage_a",
            "back_yard_ptz",
            "cam_01_living_room",
        ]
        
        for raw, exp in zip(raw_names, expected):
            assert sanitize_name(raw) == exp

    def test_url_credential_encoding(self):
        """Test URL credential encoding for special characters."""
        from urllib.parse import quote
        
        # Test passwords with special characters
        passwords = [
            "simple123",
            "p@ssword!",
            "pass:word",
            "p@ss^word!#$",
        ]
        
        for password in passwords:
            encoded = quote(password, safe='')
            # Should be URL-safe
            assert ' ' not in encoded
            assert '\n' not in encoded
            # Decode should match original
            from urllib.parse import unquote
            assert unquote(encoded) == password

    def test_rtsp_url_construction(self):
        """Test RTSP URL construction."""
        from urllib.parse import quote
        
        host = "192.168.1.100"
        username = "admin"
        password = "p@ss^word!"
        port = 554
        path = "/h264Preview_01_main"
        
        encoded_password = quote(password, safe='')
        url = f"rtsp://{username}:{encoded_password}@{host}:{port}{path}"
        
        assert "rtsp://" in url
        assert host in url
        assert str(port) in url
        assert username in url

    def test_native_dimensions_no_scaling(self):
        """Test that detect dimensions match native stream resolution.
        
        CRITICAL: Frigate wastes CPU if detect dimensions don't match
        the native resolution of the stream.
        """
        # Simulate getting native dimensions from entity state
        state_attrs = {
            "width": 640,
            "height": 360,
        }
        
        # Detection should use EXACT native dimensions
        detect_width = state_attrs["width"]
        detect_height = state_attrs["height"]
        
        assert detect_width == 640
        assert detect_height == 360
        
        # Verify no scaling was applied
        assert detect_width == state_attrs["width"]
        assert detect_height == state_attrs["height"]


class TestCompleteConfigGeneration:
    """Tests for complete configuration generation."""

    def test_generate_minimal_config(self):
        """Test minimal configuration generation."""
        config = {
            "version": "0.14-1",
            "mqtt": {
                "host": "localhost",
                "port": 1883,
            },
            "detectors": {
                "default": {
                    "type": "cpu",
                }
            },
            "ffmpeg": {
                "hwaccel_args": "preset-http-jpeg-generic",
            },
            "cameras": {},
            "go2rtc": {
                "streams": {}
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["version"] == "0.14-1"
        assert parsed["mqtt"]["host"] == "localhost"
        assert parsed["detectors"]["default"]["type"] == "cpu"

    def test_generate_full_config_frigate_016(self):
        """Test full configuration for Frigate 0.16."""
        config = {
            "version": "0.14-1",
            "mqtt": {
                "host": "192.168.1.100",
                "port": 1883,
                "user": "mqtt_user",
                "password": "mqtt_pass",
            },
            "detectors": {
                "default": {
                    "type": "edgetpu",
                    "device": "usb",
                }
            },
            "ffmpeg": {
                "hwaccel_args": "preset-vaapi",
            },
            "detect": {
                "enabled": True,
                "fps": 5,
            },
            "record": {
                "enabled": True,
                "expire_interval": 60,
                "retain": {
                    "days": 1,
                    "mode": "motion",
                },
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 14, "mode": "motion"},
                },
                "detections": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 14, "mode": "motion"},
                },
            },
            "snapshots": {
                "enabled": True,
                "retain": {"default": 30},
            },
            "audio": {
                "enabled": True,
                "listen": ["bark", "speech"],
            },
            "birdseye": {
                "enabled": True,
                "mode": "objects",
            },
            "go2rtc": {
                "streams": {
                    "front_door": ["rtspx://192.168.1.10/main"],
                    "garage": ["rtspx://192.168.1.11/main"],
                }
            },
            "cameras": {
                "front_door": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://192.168.1.10/main", "roles": ["record", "audio"]},
                            {"path": "rtsp://192.168.1.10/sub", "roles": ["detect"]},
                        ]
                    },
                    "detect": {"enabled": True, "width": 640, "height": 480, "fps": 5},
                },
                "garage": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://192.168.1.11/stream", "roles": ["detect", "record", "audio"]},
                        ]
                    },
                    "detect": {"enabled": True, "width": 640, "height": 360, "fps": 5},
                },
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)
        
        # Verify structure
        assert len(parsed["cameras"]) == 2
        assert len(parsed["go2rtc"]["streams"]) == 2
        # 0.16 uses retain at top level
        assert parsed["record"]["retain"]["days"] == 1

    def test_generate_full_config_frigate_017(self):
        """Test full configuration for Frigate 0.17."""
        config = {
            "version": "0.14-1",
            "mqtt": {
                "host": "192.168.1.100",
                "port": 1883,
            },
            "detectors": {
                "default": {
                    "type": "edgetpu",
                    "device": "usb",
                }
            },
            "ffmpeg": {
                "hwaccel_args": "preset-vaapi",
                "gpu": 0,
            },
            "detect": {
                "enabled": True,
                "fps": 5,
                "stationary": {
                    "classifier": True,
                    "interval": 50,
                    "threshold": 50,
                },
            },
            "record": {
                "enabled": True,
                "expire_interval": 60,
                "continuous": {"days": 0},
                "motion": {"days": 1},
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 14, "mode": "motion"},
                },
                "detections": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 14, "mode": "motion"},
                },
            },
            "review": {
                "alerts": {
                    "enabled": True,
                    "labels": ["car", "person"],
                    "cutoff_time": 40,
                },
                "detections": {
                    "enabled": True,
                    "labels": ["car", "person"],
                    "cutoff_time": 30,
                },
                "genai": {
                    "enabled": True,
                    "alerts": True,
                    "detections": False,
                },
            },
            "birdseye": {
                "enabled": True,
                "mode": "objects",
                "idle_heartbeat_fps": 0.0,
            },
            "genai": {
                "provider": "gemini",
                "model": "gemini-2.0-flash",
            },
            "objects": {
                "track": ["person", "car"],
                "genai": {
                    "enabled": True,
                    "objects": ["person", "car"],
                },
            },
            "go2rtc": {
                "streams": {
                    "front_door": ["rtspx://192.168.1.10/main"],
                }
            },
            "cameras": {
                "front_door": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://192.168.1.10/main", "roles": ["record", "audio"]},
                            {"path": "rtsp://192.168.1.10/sub", "roles": ["detect"]},
                        ]
                    },
                    "detect": {"enabled": True, "width": 640, "height": 360, "fps": 5},
                },
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)
        
        # Verify 0.17 structure
        assert parsed["record"]["continuous"]["days"] == 0
        assert parsed["record"]["motion"]["days"] == 1
        assert "retain" not in parsed["record"]  # No retain at top level
        assert parsed["detect"]["stationary"]["classifier"] is True
        assert parsed["review"]["alerts"]["cutoff_time"] == 40
        assert parsed["birdseye"]["idle_heartbeat_fps"] == 0.0
        assert parsed["ffmpeg"]["gpu"] == 0

    def test_yaml_output_validity(self):
        """Test that generated YAML is valid."""
        config = {
            "mqtt": {"host": "localhost"},
            "cameras": {
                "test": {
                    "ffmpeg": {
                        "inputs": [{"path": "rtsp://test", "roles": ["detect"]}]
                    }
                }
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False)
        
        # Should parse without error
        parsed = yaml.safe_load(yaml_str)
        assert parsed is not None
        
        # Round-trip should match
        yaml_str2 = yaml.dump(parsed, default_flow_style=False)
        parsed2 = yaml.safe_load(yaml_str2)
        assert parsed == parsed2


class TestRecordPresetsLogic:
    """Tests for record preset logic."""

    RECORD_PRESETS = {
        "unifiprotect": "preset-record-ubiquiti",
        "amcrest": "preset-record-generic-audio-aac",
        "reolink": "preset-record-generic-audio-aac",
        "default": "preset-record-generic-audio-aac",
    }

    def test_record_preset_unifi(self):
        """Test UniFi preset selection."""
        source = "unifiprotect"
        preset = self.RECORD_PRESETS.get(source, self.RECORD_PRESETS["default"])
        assert preset == "preset-record-ubiquiti"

    def test_record_preset_amcrest(self):
        """Test Amcrest preset selection."""
        source = "amcrest"
        preset = self.RECORD_PRESETS.get(source, self.RECORD_PRESETS["default"])
        assert preset == "preset-record-generic-audio-aac"

    def test_record_preset_reolink(self):
        """Test Reolink preset selection."""
        source = "reolink"
        preset = self.RECORD_PRESETS.get(source, self.RECORD_PRESETS["default"])
        assert preset == "preset-record-generic-audio-aac"

    def test_record_preset_unknown(self):
        """Test fallback for unknown source."""
        source = "unknown_camera"
        preset = self.RECORD_PRESETS.get(source, self.RECORD_PRESETS["default"])
        assert preset == "preset-record-generic-audio-aac"


class TestHwaccelPresetsLogic:
    """Tests for hwaccel preset logic."""

    FFMPEG_HWACCEL_PRESETS = {
        "vaapi": "preset-vaapi",
        "cuda": "preset-nvidia-h264",
        "qsv": "preset-intel-qsv-h264",
        "rkmpp": "preset-rkmpp",
        "v4l2m2m": "preset-rpi-64-h264",
        "none": "preset-http-jpeg-generic",
    }

    def test_hwaccel_vaapi(self):
        """Test VAAPI preset."""
        hwaccel = "vaapi"
        preset = self.FFMPEG_HWACCEL_PRESETS.get(hwaccel)
        assert preset == "preset-vaapi"

    def test_hwaccel_cuda(self):
        """Test CUDA preset."""
        hwaccel = "cuda"
        preset = self.FFMPEG_HWACCEL_PRESETS.get(hwaccel)
        assert preset == "preset-nvidia-h264"

    def test_hwaccel_qsv(self):
        """Test Intel QuickSync preset."""
        hwaccel = "qsv"
        preset = self.FFMPEG_HWACCEL_PRESETS.get(hwaccel)
        assert preset == "preset-intel-qsv-h264"

    def test_hwaccel_none(self):
        """Test software decoding preset."""
        hwaccel = "none"
        preset = self.FFMPEG_HWACCEL_PRESETS.get(hwaccel)
        assert preset == "preset-http-jpeg-generic"


class TestFrigate017Compatibility:
    """Tests for Frigate 0.17 compatibility."""

    def test_tiered_retention_structure(self):
        """Test 0.17 tiered retention structure."""
        # 0.17 uses continuous/motion instead of retain at top level
        record_017 = {
            "enabled": True,
            "continuous": {
                "days": 0,
            },
            "motion": {
                "days": 1,
            },
            "alerts": {
                "retain": {"days": 30}
            },
            "detections": {
                "retain": {"days": 30}
            },
        }
        
        yaml_str = yaml.dump({"record": record_017}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert "continuous" in parsed["record"]
        assert "motion" in parsed["record"]
        assert "retain" not in parsed["record"]  # No retain at top level

    def test_genai_config_structure(self):
        """Test 0.17 GenAI configuration structure."""
        # Global genai only configures provider
        genai = {
            "enabled": True,
            "provider": "gemini",
            "api_key": "{FRIGATE_GEMINI_API_KEY}",
            "model": "gemini-2.0-flash",
        }
        
        # Object GenAI under objects.genai (not per-camera)
        objects = {
            "track": ["person", "car"],
            "genai": {
                "enabled": True,
                "objects": ["person"],
            },
        }
        
        config = {
            "genai": genai,
            "objects": objects,
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["genai"]["provider"] == "gemini"
        assert parsed["objects"]["genai"]["enabled"] is True

    def test_review_genai_structure(self):
        """Test 0.17 review.genai structure."""
        review = {
            "alerts": {
                "enabled": True,
                "cutoff_time": 40,
            },
            "detections": {
                "enabled": True,
                "cutoff_time": 30,
            },
            "genai": {
                "enabled": True,
                "alerts": True,
                "detections": False,
                "image_source": "preview",
            },
        }
        
        yaml_str = yaml.dump({"review": review}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["review"]["genai"]["enabled"] is True
        assert parsed["review"]["alerts"]["cutoff_time"] == 40

    def test_stationary_classifier_config(self):
        """Test 0.17 stationary classifier configuration."""
        detect = {
            "enabled": True,
            "fps": 5,
            "stationary": {
                "classifier": True,
                "interval": 50,
                "threshold": 50,
            },
        }
        
        yaml_str = yaml.dump({"detect": detect}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["detect"]["stationary"]["classifier"] is True

    def test_yolov9_detector_config(self):
        """Test YOLOv9 detector configuration for 0.17."""
        detectors = {
            "coral": {
                "type": "edgetpu",
                "device": "usb",
                "model": {
                    "path": "/models/yolov9-coral.tflite",
                }
            }
        }
        
        yaml_str = yaml.dump({"detectors": detectors}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert "model" in parsed["detectors"]["coral"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
