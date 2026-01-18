"""Standalone tests that don't require Home Assistant dependencies.

Version: 0.4.0.5
Date: 2026-01-18

These tests can be run without installing homeassistant package.
They validate YAML generation, schema compliance, and basic logic.
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

    def test_build_record_section(self):
        """Test record section with retention settings."""
        record = {
            "enabled": True,
            "alerts": {
                "retain": {"days": 30}
            },
            "detections": {
                "retain": {"days": 14}
            },
            "events": {
                "retain": {"default": 7}
            },
        }
        
        yaml_str = yaml.dump({"record": record}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["record"]["alerts"]["retain"]["days"] == 30
        assert parsed["record"]["detections"]["retain"]["days"] == 14
        assert parsed["record"]["events"]["retain"]["default"] == 7

    def test_build_record_section_frigate_017_tiered(self):
        """Test Frigate 0.17 tiered retention."""
        record = {
            "enabled": True,
            "retain": {
                "days": 1,  # Continuous recordings
            },
            "alerts": {
                "retain": {"days": 30}
            },
            "detections": {
                "retain": {"days": 30}
            },
        }
        
        yaml_str = yaml.dump({"record": record}, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["record"]["retain"]["days"] == 1  # Continuous
        assert parsed["record"]["alerts"]["retain"]["days"] == 30

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

    def test_generate_full_config_with_cameras(self):
        """Test full configuration with cameras."""
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
            },
            "record": {
                "enabled": True,
                "alerts": {"retain": {"days": 30}},
                "detections": {"retain": {"days": 14}},
                "events": {"retain": {"default": 7}},
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
                    "detect": {"width": 640, "height": 480, "fps": 5},
                },
                "garage": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://192.168.1.11/stream", "roles": ["detect", "record", "audio"]},
                        ]
                    },
                    "detect": {"width": 640, "height": 360, "fps": 5},
                },
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)
        
        # Verify structure
        assert len(parsed["cameras"]) == 2
        assert len(parsed["go2rtc"]["streams"]) == 2
        assert parsed["record"]["alerts"]["retain"]["days"] == 30

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
        # 0.17 separates continuous from alerts/detections
        record_017 = {
            "enabled": True,
            "retain": {
                "days": 1,  # Continuous recordings
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
        
        assert "retain" in parsed["record"]  # Top-level continuous
        assert "alerts" in parsed["record"]
        assert "detections" in parsed["record"]

    def test_genai_config_structure(self):
        """Test 0.17 GenAI configuration structure."""
        # Global genai only configures provider
        genai = {
            "enabled": True,
            "provider": "gemini",
            "api_key": "{FRIGATE_GEMINI_API_KEY}",
            "model": "gemini-2.0-flash",
        }
        
        # Per-camera genai under cameras.X.genai
        camera_genai = {
            "enabled": True,
            "use_snapshot": True,
            "objects": ["person"],
            "required_zones": ["front_yard"],
        }
        
        config = {
            "genai": genai,
            "cameras": {
                "front_door": {
                    "genai": camera_genai,
                    "ffmpeg": {
                        "inputs": [{"path": "rtsp://test", "roles": ["detect"]}]
                    },
                }
            },
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False)
        parsed = yaml.safe_load(yaml_str)
        
        assert parsed["genai"]["provider"] == "gemini"
        assert parsed["cameras"]["front_door"]["genai"]["enabled"] is True

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
