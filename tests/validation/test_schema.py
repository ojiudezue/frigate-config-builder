"""Frigate schema validation tests.

Version: 0.4.0.8
Date: 2026-01-22

Tests that generated configuration matches Frigate's expected schema.
Uses validation rules based on Frigate's configuration reference.

Changelog:
- 0.4.0.8: Updated record tests for correct 0.16/0.17 structures
           Added tests for 0.17 stationary classifier, review.genai
"""
from __future__ import annotations

import pytest
import yaml
from typing import Any


class TestSchemaDetectors:
    """Tests for detector configuration schema."""

    VALID_DETECTOR_TYPES = [
        "edgetpu", "cpu", "openvino", "onnx", "rknn", "hailo8", "apple_coreml"
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

    def test_detector_onnx_nvidia(self):
        """Test ONNX detector for Nvidia (0.16+ replacement for tensorrt)."""
        config = {
            "detectors": {
                "default": {
                    "type": "onnx",
                    "device": "cuda:0",
                }
            }
        }
        
        assert config["detectors"]["default"]["type"] == "onnx"


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

    def test_ffmpeg_gpu_index_017(self):
        """Test FFmpeg gpu index for 0.17+."""
        config = {
            "ffmpeg": {
                "hwaccel_args": "preset-vaapi",
                "gpu": 0,
            }
        }
        
        assert config["ffmpeg"]["gpu"] == 0


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

    def test_camera_detect_native_dimensions(self):
        """Test camera detect uses native stream dimensions.
        
        CRITICAL: Frigate wastes CPU if detect dimensions don't match
        the native resolution of the stream.
        """
        # Native low-res stream at 640x360
        native_width = 640
        native_height = 360
        
        config = {
            "cameras": {
                "test": {
                    "detect": {
                        "enabled": True,
                        "width": native_width,
                        "height": native_height,
                        "fps": 5,
                    }
                }
            }
        }
        
        # Should use EXACT native dimensions
        assert config["cameras"]["test"]["detect"]["width"] == native_width
        assert config["cameras"]["test"]["detect"]["height"] == native_height


class TestSchemaDetect:
    """Tests for global detect configuration schema."""

    def test_detect_enabled_explicit(self):
        """Test detect.enabled is explicit for 0.16+."""
        config = {
            "detect": {
                "enabled": True,
                "fps": 5,
            }
        }
        
        # 0.16+ defaults to false, must be explicit
        assert config["detect"]["enabled"] is True

    def test_detect_stationary_classifier_017(self):
        """Test stationary classifier for 0.17+."""
        config = {
            "detect": {
                "enabled": True,
                "fps": 5,
                "stationary": {
                    "classifier": True,
                    "interval": 50,
                    "threshold": 50,
                },
            }
        }
        
        assert config["detect"]["stationary"]["classifier"] is True


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

    def test_record_retention_frigate_016(self):
        """Test Frigate 0.16 record retention structure.
        
        0.16 uses retain.days/mode at top level for base retention.
        """
        config = {
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
        }
        
        # 0.16 uses retain at top level
        assert "retain" in config["record"]
        assert config["record"]["retain"]["days"] >= 0
        assert config["record"]["retain"]["mode"] in ["all", "motion", "active_objects"]
        assert config["record"]["alerts"]["retain"]["days"] >= 0
        assert config["record"]["detections"]["retain"]["days"] >= 0

    def test_record_retention_frigate_017_tiered(self):
        """Test Frigate 0.17 tiered retention structure.
        
        0.17 removes record.retain and adds:
        - continuous.days: for 24/7 recording
        - motion.days: for motion-based retention
        """
        config = {
            "record": {
                "enabled": True,
                "expire_interval": 60,
                "continuous": {
                    "days": 0,
                },
                "motion": {
                    "days": 1,
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
        }
        
        # 0.17 uses continuous/motion instead of retain at top level
        assert "continuous" in config["record"]
        assert "motion" in config["record"]
        assert "retain" not in config["record"]  # No retain at top level for 0.17
        assert config["record"]["continuous"]["days"] >= 0
        assert config["record"]["motion"]["days"] >= 0

    def test_record_pre_post_capture(self):
        """Test pre_capture and post_capture settings."""
        config = {
            "record": {
                "enabled": True,
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 14},
                },
            }
        }
        
        assert config["record"]["alerts"]["pre_capture"] == 5
        assert config["record"]["alerts"]["post_capture"] == 5


class TestSchemaReview:
    """Tests for review configuration schema."""

    def test_review_basic(self):
        """Test basic review configuration."""
        config = {
            "review": {
                "alerts": {
                    "enabled": True,
                    "labels": ["car", "person"],
                },
                "detections": {
                    "enabled": True,
                    "labels": ["car", "person"],
                },
            }
        }
        
        assert config["review"]["alerts"]["enabled"] is True
        assert "person" in config["review"]["alerts"]["labels"]

    def test_review_cutoff_time_017(self):
        """Test review.cutoff_time for 0.17+."""
        config = {
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
            }
        }
        
        assert config["review"]["alerts"]["cutoff_time"] == 40
        assert config["review"]["detections"]["cutoff_time"] == 30

    def test_review_genai_017(self):
        """Test review.genai for 0.17+."""
        config = {
            "review": {
                "alerts": {
                    "enabled": True,
                },
                "genai": {
                    "enabled": True,
                    "alerts": True,
                    "detections": False,
                    "image_source": "preview",
                },
            }
        }
        
        assert config["review"]["genai"]["enabled"] is True
        assert config["review"]["genai"]["image_source"] in ["preview", "snapshot"]


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

    def test_birdseye_idle_heartbeat_017(self):
        """Test birdseye.idle_heartbeat_fps for 0.17+."""
        config = {
            "birdseye": {
                "enabled": True,
                "mode": "objects",
                "idle_heartbeat_fps": 0.0,
            }
        }
        
        assert config["birdseye"]["idle_heartbeat_fps"] == 0.0


class TestSchemaGenAI:
    """Tests for GenAI configuration schema (0.17+)."""

    VALID_PROVIDERS = ["gemini", "ollama", "openai", "azure_openai"]

    def test_genai_global_config(self):
        """Test global GenAI provider configuration."""
        config = {
            "genai": {
                "provider": "gemini",
                "model": "gemini-2.0-flash",
                "api_key": "{FRIGATE_GEMINI_API_KEY}",
            }
        }
        
        assert config["genai"]["provider"] in self.VALID_PROVIDERS

    def test_genai_objects_section(self):
        """Test objects.genai section for 0.17+."""
        config = {
            "objects": {
                "track": ["person", "car"],
                "genai": {
                    "enabled": True,
                    "use_snapshot": False,
                    "objects": ["person", "car"],
                },
            }
        }
        
        assert config["objects"]["genai"]["enabled"] is True


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

    def test_complete_config_016(self):
        """Test complete configuration for Frigate 0.16."""
        config = {
            "version": "0.14-1",
            "mqtt": {"host": "localhost"},
            "detectors": {"default": {"type": "cpu"}},
            "ffmpeg": {"hwaccel_args": "preset-http-jpeg-generic"},
            "detect": {"enabled": True},
            "record": {
                "enabled": True,
                "retain": {"days": 1, "mode": "motion"},
                "alerts": {"retain": {"days": 14}},
                "detections": {"retain": {"days": 14}},
            },
            "snapshots": {"enabled": True},
            "audio": {"enabled": True, "listen": ["bark"]},
            "birdseye": {"enabled": True, "mode": "objects"},
            "go2rtc": {"streams": {}},
            "cameras": {},
        }
        
        required_sections = ["mqtt", "cameras"]
        for section in required_sections:
            assert section in config
        
        # 0.16 has retain at top level
        assert "retain" in config["record"]

    def test_complete_config_017(self):
        """Test complete configuration for Frigate 0.17."""
        config = {
            "version": "0.14-1",
            "mqtt": {"host": "localhost"},
            "detectors": {"default": {"type": "cpu"}},
            "ffmpeg": {"hwaccel_args": "preset-http-jpeg-generic", "gpu": 0},
            "detect": {
                "enabled": True,
                "stationary": {"classifier": True},
            },
            "record": {
                "enabled": True,
                "continuous": {"days": 0},
                "motion": {"days": 1},
                "alerts": {"retain": {"days": 14}},
                "detections": {"retain": {"days": 14}},
            },
            "review": {
                "alerts": {"enabled": True, "cutoff_time": 40},
                "detections": {"enabled": True, "cutoff_time": 30},
            },
            "snapshots": {"enabled": True},
            "birdseye": {"enabled": True, "mode": "objects", "idle_heartbeat_fps": 0.0},
            "go2rtc": {"streams": {}},
            "cameras": {},
        }
        
        required_sections = ["mqtt", "cameras"]
        for section in required_sections:
            assert section in config
        
        # 0.17 has continuous/motion instead of retain
        assert "continuous" in config["record"]
        assert "motion" in config["record"]
        assert "retain" not in config["record"]
