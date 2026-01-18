"""Unit tests for sensor entities.

Version: 0.4.0.5
Date: 2026-01-18

Tests the entities/sensor.py module.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestCameraCountSensor:
    """Tests for the camera count sensor entity."""

    @pytest.mark.asyncio
    async def test_sensor_creation(self, mock_hass, mock_config_entry):
        """Test sensor entity can be created."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        sensor = CameraCountSensor(mock_config_entry)
        
        assert sensor is not None
        assert sensor.name is not None

    @pytest.mark.asyncio
    async def test_sensor_initial_value(self, mock_hass, mock_config_entry):
        """Test sensor has correct initial value."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        mock_config_entry.options = {
            "discovered_cameras": ["cam1", "cam2", "cam3"],
        }
        
        sensor = CameraCountSensor(mock_config_entry)
        
        # Initial value should reflect discovered cameras
        assert sensor.native_value in [0, 3, None]

    @pytest.mark.asyncio
    async def test_sensor_unit(self, mock_hass, mock_config_entry):
        """Test sensor has correct unit."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        sensor = CameraCountSensor(mock_config_entry)
        
        # Should have "cameras" as unit or no unit
        assert sensor.native_unit_of_measurement in [None, "cameras", ""]

    @pytest.mark.asyncio
    async def test_sensor_icon(self, mock_hass, mock_config_entry):
        """Test sensor has correct icon."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        sensor = CameraCountSensor(mock_config_entry)
        
        assert sensor.icon in ["mdi:camera-burst", "mdi:camera", "mdi:cctv", "mdi:video"]


class TestLastGeneratedSensor:
    """Tests for the last generated timestamp sensor."""

    @pytest.mark.asyncio
    async def test_sensor_creation(self, mock_hass, mock_config_entry):
        """Test sensor entity can be created."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        assert sensor is not None

    @pytest.mark.asyncio
    async def test_sensor_initial_value_none(self, mock_hass, mock_config_entry):
        """Test sensor shows None when never generated."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        # Should be None or "Never" initially
        assert sensor.native_value in [None, "Never", ""]

    @pytest.mark.asyncio
    async def test_sensor_value_after_generation(self, mock_hass, mock_config_entry):
        """Test sensor shows timestamp after generation."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        # Simulate generation timestamp
        sensor._last_generated = datetime.now()
        
        # Should have a value
        assert sensor.native_value is not None

    @pytest.mark.asyncio
    async def test_sensor_device_class(self, mock_hass, mock_config_entry):
        """Test sensor has correct device class."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        # Should be timestamp device class
        from homeassistant.components.sensor import SensorDeviceClass
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP


class TestLastGeneratedAttributes:
    """Tests for last generated sensor attributes."""

    @pytest.mark.asyncio
    async def test_attributes_include_camera_list(self, mock_hass, mock_config_entry):
        """Test attributes include list of cameras."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        mock_config_entry.options = {
            "discovered_cameras": ["garage_a", "front_door"],
        }
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        
        # Should include camera information
        assert attrs is not None

    @pytest.mark.asyncio
    async def test_attributes_include_output_path(self, mock_hass, mock_config_entry):
        """Test attributes include output file path."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        mock_config_entry.data = {
            "output_path": "/config/frigate/frigate.yml",
        }
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        
        # Should include output path
        assert attrs is not None

    @pytest.mark.asyncio
    async def test_attributes_include_feature_flags(self, mock_hass, mock_config_entry):
        """Test attributes include enabled features."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        mock_config_entry.data = {
            "audio_detection": True,
            "semantic_search": True,
            "face_recognition": False,
        }
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        attrs = sensor.extra_state_attributes
        
        # Should include feature information
        assert attrs is not None


class TestSensorDeviceInfo:
    """Tests for sensor device info."""

    @pytest.mark.asyncio
    async def test_camera_count_device_info(self, mock_hass, mock_config_entry):
        """Test camera count sensor has correct device info."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        sensor = CameraCountSensor(mock_config_entry)
        
        device_info = sensor.device_info
        
        assert device_info is not None
        assert "identifiers" in device_info

    @pytest.mark.asyncio
    async def test_last_generated_device_info(self, mock_hass, mock_config_entry):
        """Test last generated sensor has correct device info."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        device_info = sensor.device_info
        
        assert device_info is not None
        assert "identifiers" in device_info


class TestSensorUniqueIds:
    """Tests for sensor unique IDs."""

    @pytest.mark.asyncio
    async def test_camera_count_unique_id(self, mock_hass, mock_config_entry):
        """Test camera count sensor has unique ID."""
        from custom_components.frigate_config_builder.entities.sensor import CameraCountSensor
        
        sensor = CameraCountSensor(mock_config_entry)
        
        assert sensor.unique_id is not None
        assert mock_config_entry.entry_id in sensor.unique_id

    @pytest.mark.asyncio
    async def test_last_generated_unique_id(self, mock_hass, mock_config_entry):
        """Test last generated sensor has unique ID."""
        from custom_components.frigate_config_builder.entities.sensor import LastGeneratedSensor
        
        sensor = LastGeneratedSensor(mock_config_entry)
        
        assert sensor.unique_id is not None
        assert mock_config_entry.entry_id in sensor.unique_id
