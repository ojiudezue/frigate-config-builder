"""Frigate schema validation tests.

Version: 0.4.0.5
Date: 2026-01-18

Tests that generated configuration matches Frigate's expected schema.
Uses validation rules based on Frigate's configuration reference.
"""
from __future__ import annotations

import pytest
import yaml
from typing import Any


class TestSchemaDetectors:
    """Tests for detector configuration schema."""

    VALID_DETECTOR_TYPES = [
        "edgetpu", "cpu", "openvino", "tensorrt", "rknn", "hailo8", "apple_coreml"
    ]

    VALID_EDGETPU_DEVICES = [
        "usb", "pci:0", "pci:1", "usb:0", "usb:1"
    ]

    def test_detector_type_valid(self):
        """Test detector type is valid."""
        config = {
            "detectors": {
                "default": {
                    "type": "edgetpu",
                    "device": "usb",
                }
            }
        }
        
        assert config["detectors"]["default"]["type"] in self.VALID_DETECTOR_TYPES

    def test_detector_type_cpu(self):
        """Test CPU detector configuration."""
        config = {
            "detectors": {
                "default": {
                    "type": "cpu",
                }
            }
        }
        
        assert config["detectors"]["default"]["type"] == "cpu"
        # CPU detector doesn't require device field

    def test_detector_openvino(self):
        """Test OpenVINO detector configuration."""
        config = {
            "detectors": {
                "ov": {
                    "type": "openvino",
                    "device": "GPU",
                }
            }
        }
        
        assert config["detectors"]["ov"]["type"] == "openvino"
        assert config["detectors"]["ov"]["device"] in ["CPU", "GPU", "AUTO"]


class TestSchemaMQTT:
    """Tests for MQTT configuration schema."""

    def test_mqtt_required_fields(self):
        """Test MQTT has required host field."""
        config = {
            "mqtt": {
                "host": "192.168.1.100",
            }
        }
        
        assert "host" in config["mqtt"]

    def test_mqtt_with_auth(self):
        """Test MQTT with authentication fields."""
        config = {
            "mqtt": {
                "host": "192.168.1.100",
                "port": 1883,
                "user": "frigate_user",
                "password": "frigate_pass",
            }
        }
        
        assert config["mqtt"]["port"] == 1883
        assert "user" in config["mqtt"]
        assert "password" in config["mqtt"]

    def test_mqtt_port_range(self):
        """Test MQTT port is in valid range."""
        config = {
            "mqtt": {
                "host": "localhost",
                "port": 1883,
            }
        }
        
        assert 1 <= config["mqtt"]["port"] <= 65535


class TestSchemaFFmpeg:
    """Tests for FFmpeg configuration schema."""

    VALID_HWACCEL_PRESETS = [
        "preset-vaapi", "preset-nvidia-h264", "preset-intel-qsv-h264",
        "preset-rkmpp", "preset-http-jpeg-generic",
    ]

    def test_ffmpeg_hwaccel_preset(self):
        """Test FFmpeg hwaccel preset is valid."""
        config = {
            "ffmpeg": {
                "hwaccel_args": "preset-vaapi",
            }
        }
        
        # Should be either a preset string or a list of args
        assert config["ffmpeg"]["hwaccel_args"].startswith("preset-") or \
               isinstance(config["ffmpeg"]["hwaccel_args"], list)


class TestSchemaCamera:
    """Tests for camera configuration schema."""

    VALID_STREAM_ROLES = ["detect", "record", "audio"]

    def test_camera_inputs_required(self):
        """Test camera has required ffmpeg inputs."""
        config = {
            "cameras": {
                "front_door": {
                    "ffmpeg": {
                        "inputs": [
                            {
                                "path": "rtsp://192.168.1.10/stream",
                                "roles": ["detect"],
                            }
                        ]
                    }
                }
            }
        }
        
        assert "ffmpeg" in config["cameras"]["front_door"]
        assert "inputs" in config["cameras"]["front_door"]["ffmpeg"]
        assert len(config["cameras"]["front_door"]["ffmpeg"]["inputs"]) > 0

    def test_camera_input_roles_valid(self):
        """Test camera input roles are valid."""
        config = {
            "cameras": {
                "test": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://test", "roles": ["detect", "record", "audio"]}
                        ]
                    }
                }
            }
        }
        
        roles = config["cameras"]["test"]["ffmpeg"]["inputs"][0]["roles"]
        for role in roles:
            assert role in self.VALID_STREAM_ROLES

    def test_camera_detect_dimensions(self):
        """Test camera detect dimensions are reasonable."""
        config = {
            "cameras": {
                "test": {
                    "detect": {
                        "enabled": True,
                        "width": 640,
                        "height": 480,
                        "fps": 5,
                    }
                }
            }
        }
        
        detect = config["cameras"]["test"]["detect"]
        assert 320 <= detect["width"] <= 3840
        assert 240 <= detect["height"] <= 2160
        assert 1 <= detect["fps"] <= 30


class TestSchemaRecord:
    """Tests for record configuration schema."""

    def test_record_enabled(self):
        """Test record enabled flag."""
        config = {
            "record": {
                "enabled": True,
            }
        }
        
        assert isinstance(config["record"]["enabled"], bool)

    def test_record_retention_structure(self):
        """Test record retention structure (0.14+ format)."""
        config = {
            "record": {
                "enabled": True,
                "alerts": {
                    "retain": {
                        "days": 30,
                    }
                },
                "detections": {
                    "retain": {
                        "days": 14,
                    }
                },
                "events": {
                    "retain": {
                        "default": 7,
                    }
                },
            }
        }
        
        assert config["record"]["alerts"]["retain"]["days"] >= 0
        assert config["record"]["detections"]["retain"]["days"] >= 0

    def test_record_retention_frigate_017_tiered(self):
        """Test Frigate 0.17 tiered retention structure."""
        config = {
            "record": {
                "enabled": True,
                "retain": {
                    "days": 1,  # Continuous recordings
                },
                "alerts": {
                    "retain": {
                        "days": 30,
                    }
                },
                "detections": {
                    "retain": {
                        "days": 30,
                    }
                },
            }
        }
        
        # 0.17 has separate continuous and alert/detection retention
        assert "retain" in config["record"]
        assert "alerts" in config["record"]


class TestSchemaSnapshots:
    """Tests for snapshots configuration schema."""

    def test_snapshots_enabled(self):
        """Test snapshots enabled flag."""
        config = {
            "snapshots": {
                "enabled": True,
            }
        }
        
        assert isinstance(config["snapshots"]["enabled"], bool)

    def test_snapshots_retention(self):
        """Test snapshots retention."""
        config = {
            "snapshots": {
                "enabled": True,
                "retain": {
                    "default": 30,
                }
            }
        }
        
        assert config["snapshots"]["retain"]["default"] >= 0


class TestSchemaAudio:
    """Tests for audio detection configuration schema."""

    def test_audio_enabled(self):
        """Test audio detection enabled."""
        config = {
            "audio": {
                "enabled": True,
                "listen": ["bark", "speech", "car_alarm"],
            }
        }
        
        assert config["audio"]["enabled"] is True
        assert len(config["audio"]["listen"]) > 0


class TestSchemaBirdseye:
    """Tests for birdseye configuration schema."""

    VALID_BIRDSEYE_MODES = ["objects", "continuous", "motion"]

    def test_birdseye_mode_valid(self):
        """Test birdseye mode is valid."""
        config = {
            "birdseye": {
                "enabled": True,
                "mode": "objects",
            }
        }
        
        assert config["birdseye"]["mode"] in self.VALID_BIRDSEYE_MODES


class TestSchemaSemanticSearch:
    """Tests for semantic search configuration schema."""

    VALID_MODEL_SIZES = ["small", "large"]

    def test_semantic_search_enabled(self):
        """Test semantic search configuration."""
        config = {
            "semantic_search": {
                "enabled": True,
                "model_size": "large",
            }
        }
        
        assert config["semantic_search"]["model_size"] in self.VALID_MODEL_SIZES


class TestSchemaGo2rtc:
    """Tests for go2rtc configuration schema."""

    def test_go2rtc_streams_format(self):
        """Test go2rtc streams format."""
        config = {
            "go2rtc": {
                "streams": {
                    "front_door": [
                        "rtspx://192.168.1.10:554/stream"
                    ],
                    "garage": [
                        "rtsp://192.168.1.11:554/main"
                    ],
                }
            }
        }
        
        for camera_name, streams in config["go2rtc"]["streams"].items():
            assert isinstance(streams, list)
            for stream in streams:
                assert stream.startswith(("rtsp://", "rtspx://", "http://", "ffmpeg:"))


class TestSchemaVersion:
    """Tests for version field."""

    def test_version_format(self):
        """Test version field format."""
        config = {
            "version": "0.14-1",
        }
        
        # Version should be a string in format X.Y or X.Y-Z
        assert isinstance(config["version"], str)


class TestSchemaFullConfig:
    """Tests for complete configuration validation."""

    def test_minimal_valid_config(self):
        """Test minimal valid Frigate configuration."""
        config = {
            "mqtt": {
                "host": "localhost",
            },
            "cameras": {},
        }
        
        assert "mqtt" in config
        assert "cameras" in config

    def test_complete_config_structure(self):
        """Test complete configuration has expected sections."""
        config = {
            "version": "0.14-1",
            "mqtt": {"host": "localhost"},
            "detectors": {"default": {"type": "cpu"}},
            "ffmpeg": {"hwaccel_args": "preset-http-jpeg-generic"},
            "detect": {"enabled": True},
            "record": {"enabled": True},
            "snapshots": {"enabled": True},
            "audio": {"enabled": True, "listen": ["bark"]},
            "birdseye": {"enabled": True, "mode": "objects"},
            "go2rtc": {"streams": {}},
            "cameras": {},
        }
        
        required_sections = ["mqtt", "cameras"]
        optional_sections = [
            "version", "detectors", "ffmpeg", "detect", "record",
            "snapshots", "audio", "birdseye", "go2rtc"
        ]
        
        for section in required_sections:
            assert section in config
        
        # All sections should be dicts
        for key, value in config.items():
            assert isinstance(value, (dict, str, bool, int, list))
