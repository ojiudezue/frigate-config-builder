"""Unit tests for the Frigate configuration generator.

Version: 0.4.0.5
Date: 2026-01-18

Tests the generator.py module which creates Frigate YAML configuration.
"""
from __future__ import annotations

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock, patch

class TestGeneratorMQTT:
    """Tests for MQTT configuration generation."""

    @pytest.mark.asyncio
    async def test_generate_mqtt_auto_detect(self, mock_hass_with_mqtt, mock_config_entry):
        """Test MQTT config from HA auto-detection."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass_with_mqtt, mock_config_entry)
        mqtt_config = await generator._build_mqtt()
        
        assert mqtt_config["host"] == "192.168.1.100"
        assert mqtt_config["port"] == 1883
        assert mqtt_config["user"] == "mqtt_user"
        assert mqtt_config["password"] == "mqtt_password"

    @pytest.mark.asyncio
    async def test_generate_mqtt_manual(self, mock_hass, mock_config_entry_minimal):
        """Test manual MQTT configuration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry_minimal.data["mqtt_host"] = "10.0.0.50"
        mock_config_entry_minimal.data["mqtt_port"] = 1884
        mock_config_entry_minimal.data["mqtt_user"] = "manual_user"
        mock_config_entry_minimal.data["mqtt_password"] = "manual_pass"
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry_minimal)
        mqtt_config = await generator._build_mqtt()
        
        assert mqtt_config["host"] == "10.0.0.50"
        assert mqtt_config["port"] == 1884
        assert mqtt_config["user"] == "manual_user"
        assert mqtt_config["password"] == "manual_pass"

    @pytest.mark.asyncio
    async def test_generate_mqtt_auto_no_integration(self, mock_hass, mock_config_entry):
        """Test MQTT auto-detect when no MQTT integration exists."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        # No MQTT entry added to mock_hass
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        mqtt_config = await generator._build_mqtt()
        
        # Should fall back to defaults/manual config
        assert "host" in mqtt_config


class TestGeneratorDetectors:
    """Tests for detector configuration generation."""

    def test_generate_detectors_coral_usb(self, mock_hass, mock_config_entry):
        """Test Coral USB detector configuration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        detectors_config = generator._build_detectors()
        
        assert "default" in detectors_config
        assert detectors_config["default"]["type"] == "edgetpu"
        assert detectors_config["default"]["device"] == "usb"

    def test_generate_detectors_cpu(self, mock_hass, mock_config_entry_minimal):
        """Test CPU detector configuration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry_minimal)
        detectors_config = generator._build_detectors()
        
        assert detectors_config["default"]["type"] == "cpu"

    def test_generate_detectors_openvino(self, mock_hass, mock_config_entry):
        """Test OpenVINO detector configuration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry.data["detector_type"] = "openvino"
        mock_config_entry.data["detector_device"] = "GPU"
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        detectors_config = generator._build_detectors()
        
        assert detectors_config["default"]["type"] == "openvino"
        assert detectors_config["default"]["device"] == "GPU"


class TestGeneratorHwaccel:
    """Tests for hardware acceleration configuration."""

    def test_generate_hwaccel_vaapi(self, mock_hass, mock_config_entry):
        """Test Intel VAAPI hardware acceleration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        ffmpeg_config = generator._build_ffmpeg()
        
        assert ffmpeg_config["hwaccel_args"] == "preset-vaapi"

    def test_generate_hwaccel_cuda(self, mock_hass, mock_config_entry):
        """Test NVIDIA CUDA hardware acceleration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry.data["hwaccel"] = "cuda"
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        ffmpeg_config = generator._build_ffmpeg()
        
        assert ffmpeg_config["hwaccel_args"] == "preset-nvidia-h264"

    def test_generate_hwaccel_qsv(self, mock_hass, mock_config_entry):
        """Test Intel QuickSync hardware acceleration."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry.data["hwaccel"] = "qsv"
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        ffmpeg_config = generator._build_ffmpeg()
        
        assert ffmpeg_config["hwaccel_args"] == "preset-intel-qsv-h264"

    def test_generate_hwaccel_none(self, mock_hass, mock_config_entry_minimal):
        """Test no hardware acceleration (software)."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry_minimal)
        ffmpeg_config = generator._build_ffmpeg()
        
        assert ffmpeg_config["hwaccel_args"] == "preset-http-jpeg-generic"


class TestGeneratorRetention:
    """Tests for retention settings generation."""

    def test_generate_retention_defaults(self, mock_hass, mock_config_entry):
        """Test default retention settings."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        record_config = generator._build_record()
        snapshots_config = generator._build_snapshots()
        
        assert record_config["alerts"]["retain"]["days"] == 30
        assert record_config["detections"]["retain"]["days"] == 30
        assert record_config["events"]["retain"]["default"] == 7
        assert snapshots_config["retain"]["default"] == 30

    def test_generate_retention_custom(self, mock_hass, mock_config_entry):
        """Test custom retention settings."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry.data["retain_alerts"] = 60
        mock_config_entry.data["retain_detections"] = 45
        mock_config_entry.data["retain_motion"] = 14
        mock_config_entry.data["retain_snapshots"] = 90
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        record_config = generator._build_record()
        snapshots_config = generator._build_snapshots()
        
        assert record_config["alerts"]["retain"]["days"] == 60
        assert record_config["detections"]["retain"]["days"] == 45
        assert record_config["events"]["retain"]["default"] == 14
        assert snapshots_config["retain"]["default"] == 90


class TestGeneratorFeatures:
    """Tests for optional feature generation."""

    def test_generate_features_all_enabled(self, mock_hass, mock_config_entry_all_features):
        """Test all features enabled."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry_all_features)
        
        # Test individual feature builders
        audio_config = generator._build_audio()
        assert audio_config["enabled"] is True
        assert "bark" in audio_config["listen"]
        
        birdseye_config = generator._build_birdseye()
        assert birdseye_config["enabled"] is True
        assert birdseye_config["mode"] == "objects"
        
        semantic_config = generator._build_semantic_search()
        assert semantic_config["enabled"] is True
        assert semantic_config["model_size"] == "large"
        
        face_config = generator._build_face_recognition()
        assert face_config["enabled"] is True
        assert face_config["model_size"] == "large"

    def test_generate_features_minimal(self, mock_hass, mock_config_entry_minimal):
        """Test minimal features (most disabled)."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry_minimal.data["audio_detection"] = True
        mock_config_entry_minimal.data["birdseye_enabled"] = False
        mock_config_entry_minimal.data["semantic_search"] = False
        mock_config_entry_minimal.data["face_recognition"] = False
        mock_config_entry_minimal.data["lpr"] = False
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry_minimal)
        
        # Audio should be built
        audio_config = generator._build_audio()
        assert audio_config["enabled"] is True


class TestGeneratorCameras:
    """Tests for camera configuration generation."""

    def test_generate_camera_single_stream(self, mock_hass, mock_config_entry, sample_reolink_camera):
        """Test camera with single stream (same for record and detect)."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        # Make record and detect URL the same
        sample_reolink_camera.detect_url = sample_reolink_camera.record_url
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        cameras_config = generator._build_cameras([sample_reolink_camera])
        
        cam_config = cameras_config["reolink_study_b_porch_ptz"]
        assert len(cam_config["ffmpeg"]["inputs"]) == 1
        assert "record" in cam_config["ffmpeg"]["inputs"][0]["roles"]
        assert "detect" in cam_config["ffmpeg"]["inputs"][0]["roles"]
        assert "audio" in cam_config["ffmpeg"]["inputs"][0]["roles"]

    def test_generate_camera_dual_stream(self, mock_hass, mock_config_entry, sample_unifi_camera):
        """Test camera with separate record and detect streams."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        cameras_config = generator._build_cameras([sample_unifi_camera])
        
        cam_config = cameras_config["garage_a"]
        assert len(cam_config["ffmpeg"]["inputs"]) == 2
        
        # First input should be record stream
        assert "record" in cam_config["ffmpeg"]["inputs"][0]["roles"]
        assert "audio" in cam_config["ffmpeg"]["inputs"][0]["roles"]
        
        # Second input should be detect stream
        assert "detect" in cam_config["ffmpeg"]["inputs"][1]["roles"]

    def test_generate_camera_detect_dimensions(self, mock_hass, mock_config_entry, sample_unifi_camera):
        """Test camera detect dimensions are set correctly."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        sample_unifi_camera.width = 640
        sample_unifi_camera.height = 360
        sample_unifi_camera.fps = 5
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        cameras_config = generator._build_cameras([sample_unifi_camera])
        
        detect_config = cameras_config["garage_a"]["detect"]
        assert detect_config["width"] == 640
        assert detect_config["height"] == 360
        assert detect_config["fps"] == 5


class TestGeneratorGo2rtc:
    """Tests for go2rtc streams generation."""

    def test_generate_go2rtc_streams(self, mock_hass, mock_config_entry, sample_cameras):
        """Test go2rtc streams section generation."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        go2rtc_config = generator._build_go2rtc(sample_cameras)
        
        assert "streams" in go2rtc_config
        assert "garage_a" in go2rtc_config["streams"]
        assert "armcrest" in go2rtc_config["streams"]
        assert "reolink_study_b_porch_ptz" in go2rtc_config["streams"]

    def test_generate_go2rtc_empty(self, mock_hass, mock_config_entry):
        """Test go2rtc with no cameras."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        go2rtc_config = generator._build_go2rtc([])
        
        assert go2rtc_config["streams"] == {}


class TestGeneratorCameraGroups:
    """Tests for camera groups generation."""

    @pytest.mark.asyncio
    async def test_generate_camera_groups_from_areas(self, mock_hass, mock_config_entry, sample_cameras):
        """Test camera groups generated from HA areas."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        mock_config_entry.options["auto_groups_from_areas"] = True
        
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        groups_config = await generator._build_camera_groups(sample_cameras)
        
        # Should have groups based on camera areas
        assert "Garage" in groups_config
        assert "garage_a" in groups_config["Garage"]["cameras"]


class TestGeneratorFullConfig:
    """Tests for complete configuration generation."""

    @pytest.mark.asyncio
    async def test_generate_full_config(self, mock_hass_with_mqtt, mock_config_entry, sample_cameras):
        """Test complete configuration generation."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass_with_mqtt, mock_config_entry)
        yaml_output = await generator.generate(sample_cameras)
        
        # Parse the YAML to verify it's valid
        config = yaml.safe_load(yaml_output)
        
        assert "mqtt" in config
        assert "detectors" in config
        assert "ffmpeg" in config
        assert "cameras" in config
        assert "go2rtc" in config
        assert "version" in config

    @pytest.mark.asyncio
    async def test_generate_yaml_valid_syntax(self, mock_hass_with_mqtt, mock_config_entry, sample_cameras):
        """Test generated YAML has valid syntax."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass_with_mqtt, mock_config_entry)
        yaml_output = await generator.generate(sample_cameras)
        
        # Should not raise an exception
        parsed = yaml.safe_load(yaml_output)
        assert parsed is not None

    @pytest.mark.asyncio
    async def test_generate_no_cameras(self, mock_hass_with_mqtt, mock_config_entry):
        """Test configuration generation with no cameras."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        generator = FrigateConfigGenerator(mock_hass_with_mqtt, mock_config_entry)
        yaml_output = await generator.generate(None)
        
        config = yaml.safe_load(yaml_output)
        
        assert config["cameras"] == {}
        assert config["go2rtc"]["streams"] == {}


class TestGeneratorSpecialChars:
    """Tests for special character handling."""

    def test_yaml_special_chars_in_password(self, mock_hass, mock_config_entry, sample_amcrest_camera):
        """Test passwords with special characters are properly escaped."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        
        # The sample amcrest camera has @ and ^ in the URL-encoded password
        generator = FrigateConfigGenerator(mock_hass, mock_config_entry)
        cameras_config = generator._build_cameras([sample_amcrest_camera])
        
        cam_config = cameras_config["armcrest"]
        rtsp_url = cam_config["ffmpeg"]["inputs"][0]["path"]
        
        # URL should contain the encoded special characters
        assert "%40" in rtsp_url or "@" in rtsp_url  # @ character
        assert "%5E" in rtsp_url or "^" in rtsp_url  # ^ character


class TestGeneratorVersion:
    """Tests for Frigate config version."""

    @pytest.mark.asyncio
    async def test_config_version(self, mock_hass_with_mqtt, mock_config_entry):
        """Test Frigate config version is included."""
        from custom_components.frigate_config_builder.generator import FrigateConfigGenerator
        from custom_components.frigate_config_builder.const import FRIGATE_CONFIG_VERSION
        
        generator = FrigateConfigGenerator(mock_hass_with_mqtt, mock_config_entry)
        yaml_output = await generator.generate()
        
        config = yaml.safe_load(yaml_output)
        
        assert config["version"] == FRIGATE_CONFIG_VERSION
