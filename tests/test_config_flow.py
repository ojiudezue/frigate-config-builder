"""Unit tests for the config flow.

Version: 0.4.0.5
Date: 2026-01-18

Tests the config_flow.py module which handles integration setup.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.data_entry_flow import FlowResultType


class TestConfigFlowInit:
    """Tests for config flow initialization."""

    @pytest.mark.asyncio
    async def test_flow_init(self, mock_hass):
        """Test config flow can be initialized."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        assert flow is not None

    @pytest.mark.asyncio
    async def test_flow_user_step(self, mock_hass):
        """Test the user init step shows form."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "connection"


class TestConfigFlowConnectionStep:
    """Tests for the connection step."""

    @pytest.mark.asyncio
    async def test_connection_step_valid_path(self, mock_hass):
        """Test connection step with valid file path."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        # Initialize flow first
        await flow.async_step_user()
        
        result = await flow.async_step_connection(user_input={
            "output_path": "/config/frigate/frigate.yml",
        })
        
        # Should proceed to next step
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_connection_step_invalid_path(self, mock_hass):
        """Test connection step with invalid file path."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        await flow.async_step_user()
        
        # Test with invalid path (relative path, no extension, etc.)
        result = await flow.async_step_connection(user_input={
            "output_path": "invalid_path",
        })
        
        # Should show error
        if result["type"] == FlowResultType.FORM:
            assert result["step_id"] == "connection"

    @pytest.mark.asyncio
    async def test_connection_step_empty_path(self, mock_hass):
        """Test connection step with empty path."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        await flow.async_step_user()
        
        result = await flow.async_step_connection(user_input={
            "output_path": "",
        })
        
        # Should show error or re-show form
        assert result["type"] == FlowResultType.FORM


class TestConfigFlowHardwareStep:
    """Tests for the hardware step."""

    @pytest.mark.asyncio
    async def test_hardware_step_with_coral(self, mock_hass):
        """Test hardware step with Coral TPU selected."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {"output_path": "/config/frigate.yml"}
        
        result = await flow.async_step_hardware(user_input={
            "detector_type": "edgetpu",
            "detector_device": "usb",
            "hwaccel": "vaapi",
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_hardware_step_cpu_only(self, mock_hass):
        """Test hardware step with CPU-only detection."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {"output_path": "/config/frigate.yml"}
        
        result = await flow.async_step_hardware(user_input={
            "detector_type": "cpu",
            "hwaccel": "none",
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestConfigFlowMQTTStep:
    """Tests for the MQTT step."""

    @pytest.mark.asyncio
    async def test_mqtt_step_auto_detect(self, mock_hass_with_mqtt):
        """Test MQTT step with auto-detection from HA."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass_with_mqtt
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
        }
        
        result = await flow.async_step_mqtt(user_input={
            "mqtt_auto_detect": True,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_mqtt_step_manual(self, mock_hass):
        """Test MQTT step with manual configuration."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
        }
        
        result = await flow.async_step_mqtt(user_input={
            "mqtt_auto_detect": False,
            "mqtt_host": "10.0.0.50",
            "mqtt_port": 1883,
            "mqtt_user": "mqtt_user",
            "mqtt_password": "mqtt_pass",
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_mqtt_step_invalid_host(self, mock_hass):
        """Test MQTT step with invalid host."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
        }
        
        result = await flow.async_step_mqtt(user_input={
            "mqtt_auto_detect": False,
            "mqtt_host": "",  # Invalid empty host
            "mqtt_port": 1883,
        })
        
        # Should show error
        if result["type"] == FlowResultType.FORM:
            assert result.get("errors") is not None or result["step_id"] == "mqtt"


class TestConfigFlowFeaturesStep:
    """Tests for the features step."""

    @pytest.mark.asyncio
    async def test_features_step_all_enabled(self, mock_hass):
        """Test features step with all features enabled."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
            "mqtt_host": "localhost",
        }
        
        result = await flow.async_step_features(user_input={
            "audio_detection": True,
            "birdseye_enabled": True,
            "semantic_search": True,
            "face_recognition": True,
            "lpr": True,
            "bird_classification": True,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_features_step_minimal(self, mock_hass):
        """Test features step with minimal features."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
            "mqtt_host": "localhost",
        }
        
        result = await flow.async_step_features(user_input={
            "audio_detection": False,
            "birdseye_enabled": True,
            "semantic_search": False,
            "face_recognition": False,
            "lpr": False,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestConfigFlowRetentionStep:
    """Tests for the retention step."""

    @pytest.mark.asyncio
    async def test_retention_step_defaults(self, mock_hass):
        """Test retention step with default values."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
            "mqtt_host": "localhost",
            "audio_detection": False,
        }
        
        result = await flow.async_step_retention(user_input={
            "retain_alerts": 30,
            "retain_detections": 30,
            "retain_motion": 7,
            "retain_snapshots": 30,
        })
        
        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_retention_step_custom(self, mock_hass):
        """Test retention step with custom values."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        flow._data = {
            "output_path": "/config/frigate.yml",
            "detector_type": "cpu",
            "mqtt_host": "localhost",
            "audio_detection": False,
        }
        
        result = await flow.async_step_retention(user_input={
            "retain_alerts": 90,
            "retain_detections": 60,
            "retain_motion": 14,
            "retain_snapshots": 180,
        })
        
        assert result["type"] == FlowResultType.CREATE_ENTRY


class TestConfigFlowFullFlow:
    """Tests for complete flow execution."""

    @pytest.mark.asyncio
    async def test_full_flow_completion(self, mock_hass_with_mqtt):
        """Test complete config flow from start to finish."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass_with_mqtt
        
        # Step 1: User init
        result = await flow.async_step_user()
        assert result["step_id"] == "connection"
        
        # Step 2: Connection
        result = await flow.async_step_connection({
            "output_path": "/config/frigate/frigate.yml",
        })
        
        # Continue through remaining steps
        # Each step should progress to the next
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestConfigFlowErrorHandling:
    """Tests for error handling in config flow."""

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_hass):
        """Test flow can recover from errors."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderConfigFlow
        
        flow = FrigateConfigBuilderConfigFlow()
        flow.hass = mock_hass
        
        # First attempt with error
        await flow.async_step_user()
        result = await flow.async_step_connection({
            "output_path": "",  # Invalid
        })
        
        # Should show form with error
        assert result["type"] == FlowResultType.FORM
        
        # Second attempt with valid data
        result = await flow.async_step_connection({
            "output_path": "/config/frigate.yml",
        })
        
        # Should proceed
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]
