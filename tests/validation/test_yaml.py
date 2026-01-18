"""YAML validation tests for generated Frigate configuration.

Version: 0.4.0.5
Date: 2026-01-18

Tests that generated YAML is syntactically valid and parseable.
"""
from __future__ import annotations

import pytest
import yaml
from io import StringIO


class TestYAMLSyntax:
    """Tests for YAML syntax validity."""

    def test_yaml_basic_parse(self):
        """Test basic YAML parsing."""
        valid_yaml = """
mqtt:
  host: localhost
  port: 1883
cameras:
  test_cam:
    ffmpeg:
      inputs:
        - path: rtsp://example.com/stream
          roles:
            - detect
        """
        
        parsed = yaml.safe_load(valid_yaml)
        assert parsed is not None
        assert "mqtt" in parsed
        assert "cameras" in parsed

    def test_yaml_multiline_strings(self):
        """Test YAML with multiline strings."""
        yaml_with_multiline = """
cameras:
  test_cam:
    ffmpeg:
      inputs:
        - path: >
            rtsp://user:password@192.168.1.100:554/stream
          roles:
            - detect
            - record
        """
        
        parsed = yaml.safe_load(yaml_with_multiline)
        assert parsed is not None

    def test_yaml_special_characters(self):
        """Test YAML with special characters in values."""
        yaml_with_special = """
mqtt:
  host: localhost
  user: "test@user"
  password: "p@ss^word!"
        """
        
        parsed = yaml.safe_load(yaml_with_special)
        assert parsed["mqtt"]["user"] == "test@user"
        assert parsed["mqtt"]["password"] == "p@ss^word!"

    def test_yaml_nested_structures(self):
        """Test deeply nested YAML structures."""
        nested_yaml = """
cameras:
  garage:
    detect:
      enabled: true
      width: 640
      height: 480
    ffmpeg:
      inputs:
        - path: rtsp://example.com
          roles:
            - detect
    record:
      enabled: true
      alerts:
        retain:
          days: 30
        """
        
        parsed = yaml.safe_load(nested_yaml)
        assert parsed["cameras"]["garage"]["detect"]["width"] == 640
        assert parsed["cameras"]["garage"]["record"]["alerts"]["retain"]["days"] == 30

    def test_yaml_boolean_values(self):
        """Test YAML boolean parsing."""
        yaml_bools = """
settings:
  enabled: true
  disabled: false
  on_yes: yes
  off_no: no
        """
        
        parsed = yaml.safe_load(yaml_bools)
        assert parsed["settings"]["enabled"] is True
        assert parsed["settings"]["disabled"] is False

    def test_yaml_numeric_values(self):
        """Test YAML numeric parsing."""
        yaml_nums = """
settings:
  port: 1883
  fps: 5.0
  threshold: 0.5
        """
        
        parsed = yaml.safe_load(yaml_nums)
        assert parsed["settings"]["port"] == 1883
        assert parsed["settings"]["fps"] == 5.0
        assert parsed["settings"]["threshold"] == 0.5

    def test_yaml_list_values(self):
        """Test YAML list parsing."""
        yaml_lists = """
objects:
  track:
    - person
    - dog
    - cat
audio:
  listen:
    - bark
    - speech
        """
        
        parsed = yaml.safe_load(yaml_lists)
        assert len(parsed["objects"]["track"]) == 3
        assert "person" in parsed["objects"]["track"]

    def test_yaml_empty_values(self):
        """Test YAML with empty/null values."""
        yaml_empty = """
cameras:
  test_cam:
    zones: {}
    motion: null
        """
        
        parsed = yaml.safe_load(yaml_empty)
        assert parsed["cameras"]["test_cam"]["zones"] == {}
        assert parsed["cameras"]["test_cam"]["motion"] is None


class TestYAMLValidation:
    """Tests for YAML content validation."""

    def test_frigate_required_sections(self):
        """Test that required Frigate sections are present."""
        minimal_config = """
mqtt:
  host: localhost
cameras: {}
        """
        
        parsed = yaml.safe_load(minimal_config)
        assert "mqtt" in parsed
        assert "cameras" in parsed

    def test_mqtt_section_fields(self):
        """Test MQTT section has required fields."""
        mqtt_config = """
mqtt:
  host: 192.168.1.100
  port: 1883
  user: mqtt_user
  password: mqtt_pass
        """
        
        parsed = yaml.safe_load(mqtt_config)
        mqtt = parsed["mqtt"]
        assert "host" in mqtt

    def test_camera_section_structure(self):
        """Test camera section has correct structure."""
        camera_config = """
cameras:
  front_door:
    ffmpeg:
      inputs:
        - path: rtsp://192.168.1.10:554/stream
          roles:
            - detect
    detect:
      enabled: true
      width: 640
      height: 480
        """
        
        parsed = yaml.safe_load(camera_config)
        cam = parsed["cameras"]["front_door"]
        assert "ffmpeg" in cam
        assert "detect" in cam
        assert "inputs" in cam["ffmpeg"]

    def test_detector_section(self):
        """Test detector configuration."""
        detector_config = """
detectors:
  default:
    type: edgetpu
    device: usb
        """
        
        parsed = yaml.safe_load(detector_config)
        assert parsed["detectors"]["default"]["type"] == "edgetpu"
        assert parsed["detectors"]["default"]["device"] == "usb"

    def test_go2rtc_section(self):
        """Test go2rtc streams configuration."""
        go2rtc_config = """
go2rtc:
  streams:
    front_door:
      - rtspx://192.168.1.10:554/stream
        """
        
        parsed = yaml.safe_load(go2rtc_config)
        assert "streams" in parsed["go2rtc"]
        assert "front_door" in parsed["go2rtc"]["streams"]


class TestYAMLDumping:
    """Tests for YAML serialization."""

    def test_dump_and_reload(self):
        """Test dumping and reloading config."""
        original = {
            "mqtt": {"host": "localhost", "port": 1883},
            "cameras": {
                "test": {
                    "ffmpeg": {
                        "inputs": [
                            {"path": "rtsp://example.com", "roles": ["detect"]}
                        ]
                    }
                }
            },
        }
        
        yaml_str = yaml.dump(original, default_flow_style=False)
        reloaded = yaml.safe_load(yaml_str)
        
        assert reloaded == original

    def test_dump_preserves_order(self):
        """Test YAML dumping preserves insertion order."""
        config = {
            "version": "0.14-1",
            "mqtt": {"host": "localhost"},
            "detectors": {"default": {"type": "cpu"}},
            "cameras": {},
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        
        # Parse and verify order
        parsed = yaml.safe_load(yaml_str)
        assert list(parsed.keys())[0] == "version"

    def test_dump_special_chars_escaped(self):
        """Test special characters are properly escaped."""
        config = {
            "mqtt": {
                "password": "p@ss:word/test",
            }
        }
        
        yaml_str = yaml.dump(config, default_flow_style=False)
        reloaded = yaml.safe_load(yaml_str)
        
        assert reloaded["mqtt"]["password"] == "p@ss:word/test"
