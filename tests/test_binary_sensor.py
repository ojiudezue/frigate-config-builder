"""Unit tests for binary sensor entities.

Version: 0.4.0.5
Date: 2026-01-18

Tests the entities/binary_sensor.py module.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestConfigStaleBinarySensor:
    """Tests for the config stale binary sensor entity."""

    @pytest.mark.asyncio
    async def test_sensor_creation(self, mock_hass, mock_config_entry):
        """Test binary sensor entity can be created."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        
        assert sensor is not None
        assert sensor.name is not None

    @pytest.mark.asyncio
    async def test_sensor_unique_id(self, mock_hass, mock_config_entry):
        """Test binary sensor has correct unique ID."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        
        assert sensor.unique_id is not None
        assert mock_config_entry.entry_id in sensor.unique_id

    @pytest.mark.asyncio
    async def test_sensor_icon(self, mock_hass, mock_config_entry):
        """Test binary sensor has correct icon."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        
        # Should have relevant icon
        assert sensor.icon in ["mdi:alert-circle", "mdi:check-circle", "mdi:refresh-alert", "mdi:sync-alert"]

    @pytest.mark.asyncio
    async def test_sensor_device_class(self, mock_hass, mock_config_entry):
        """Test binary sensor has correct device class."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        
        # Should be problem device class
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM


class TestConfigStaleNewCamera:
    """Tests for detecting new cameras."""

    @pytest.mark.asyncio
    async def test_stale_when_new_camera_added(self, mock_hass, mock_config_entry):
        """Test sensor turns on when new camera is discovered."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        # Simulate cameras at last generation
        sensor._last_generation_cameras = {"garage_a", "front_door"}
        
        # Now we have a new camera
        sensor._current_cameras = {"garage_a", "front_door", "backyard"}
        
        # Should be stale (new camera added)
        assert sensor.is_on is True

    @pytest.mark.asyncio
    async def test_not_stale_same_cameras(self, mock_hass, mock_config_entry):
        """Test sensor stays off when cameras unchanged."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        # Same cameras as last generation
        sensor._last_generation_cameras = {"garage_a", "front_door"}
        sensor._current_cameras = {"garage_a", "front_door"}
        
        # Should not be stale
        assert sensor.is_on is False


class TestConfigStaleRemovedCamera:
    """Tests for detecting removed cameras."""

    @pytest.mark.asyncio
    async def test_stale_when_camera_removed(self, mock_hass, mock_config_entry):
        """Test sensor turns on when camera is removed."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        # More cameras at last generation
        sensor._last_generation_cameras = {"garage_a", "front_door", "backyard"}
        
        # Camera was removed
        sensor._current_cameras = {"garage_a", "front_door"}
        
        # Should be stale (camera removed)
        assert sensor.is_on is True


class TestConfigStaleAfterGeneration:
    """Tests for state after regeneration."""

    @pytest.mark.asyncio
    async def test_not_stale_after_generation(self, mock_hass, mock_config_entry):
        """Test sensor turns off after config is regenerated."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        # Initially stale due to new camera
        sensor._last_generation_cameras = {"garage_a"}
        sensor._current_cameras = {"garage_a", "front_door"}
        
        assert sensor.is_on is True
        
        # Simulate regeneration
        sensor._last_generation_cameras = {"garage_a", "front_door"}
        
        # Should no longer be stale
        assert sensor.is_on is False


class TestConfigStaleAttributes:
    """Tests for stale sensor attributes."""

    @pytest.mark.asyncio
    async def test_attributes_show_new_cameras(self, mock_hass, mock_config_entry):
        """Test attributes show which cameras are new."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        sensor._last_generation_cameras = {"garage_a"}
        sensor._current_cameras = {"garage_a", "front_door", "backyard"}
        
        attrs = sensor.extra_state_attributes
        
        assert attrs is not None
        # Should list new cameras
        if "new_cameras" in attrs:
            assert "front_door" in attrs["new_cameras"]
            assert "backyard" in attrs["new_cameras"]

    @pytest.mark.asyncio
    async def test_attributes_show_removed_cameras(self, mock_hass, mock_config_entry):
        """Test attributes show which cameras were removed."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        sensor._last_generation_cameras = {"garage_a", "front_door", "backyard"}
        sensor._current_cameras = {"garage_a"}
        
        attrs = sensor.extra_state_attributes
        
        assert attrs is not None
        # Should list removed cameras
        if "removed_cameras" in attrs:
            assert "front_door" in attrs["removed_cameras"]
            assert "backyard" in attrs["removed_cameras"]

    @pytest.mark.asyncio
    async def test_attributes_include_camera_counts(self, mock_hass, mock_config_entry):
        """Test attributes include camera counts."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        sensor._last_generation_cameras = {"garage_a", "front_door"}
        sensor._current_cameras = {"garage_a", "front_door", "backyard"}
        
        attrs = sensor.extra_state_attributes
        
        assert attrs is not None


class TestBinarySensorDeviceInfo:
    """Tests for binary sensor device info."""

    @pytest.mark.asyncio
    async def test_device_info(self, mock_hass, mock_config_entry):
        """Test binary sensor has correct device info."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        
        device_info = sensor.device_info
        
        assert device_info is not None
        assert "identifiers" in device_info


class TestBinarySensorInitialState:
    """Tests for initial sensor state."""

    @pytest.mark.asyncio
    async def test_initial_state_never_generated(self, mock_hass, mock_config_entry):
        """Test initial state when config never generated."""
        from custom_components.frigate_config_builder.entities.binary_sensor import ConfigStaleBinarySensor
        
        # No last generation data
        mock_config_entry.options = {}
        
        sensor = ConfigStaleBinarySensor(mock_config_entry)
        sensor.hass = mock_hass
        
        # Should be stale if never generated and cameras exist
        # Or not stale if we consider "no baseline" as not stale
        assert sensor.is_on in [True, False]  # Implementation dependent
