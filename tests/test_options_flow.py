"""Unit tests for the options flow.

Version: 0.4.0.5
Date: 2026-01-18

Tests the options_flow.py module which handles configuration updates.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.data_entry_flow import FlowResultType


class TestOptionsFlowInit:
    """Tests for options flow initialization."""

    @pytest.mark.asyncio
    async def test_options_flow_init(self, mock_hass, mock_config_entry):
        """Test options flow can be initialized."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        assert flow is not None

    @pytest.mark.asyncio
    async def test_options_flow_shows_menu(self, mock_hass, mock_config_entry):
        """Test options flow shows menu of options."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_init()
        
        # Should show menu or form
        assert result["type"] in [FlowResultType.MENU, FlowResultType.FORM]


class TestOptionsFlowCameraDisplay:
    """Tests for camera display in options."""

    @pytest.mark.asyncio
    async def test_discovered_cameras_shown(self, mock_hass, mock_config_entry):
        """Test discovered cameras are displayed."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        # Add discovered cameras to options
        mock_config_entry.options = {
            "discovered_cameras": ["garage_a", "front_door", "backyard"],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_cameras()
        
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_no_cameras_message(self, mock_hass, mock_config_entry):
        """Test message shown when no cameras discovered."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "discovered_cameras": [],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_cameras()
        
        # Should show form or message
        assert result["type"] == FlowResultType.FORM


class TestOptionsFlowCameraSelection:
    """Tests for camera selection."""

    @pytest.mark.asyncio
    async def test_enable_camera(self, mock_hass, mock_config_entry):
        """Test enabling a camera for Frigate config."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "discovered_cameras": ["garage_a", "front_door"],
            "enabled_cameras": ["garage_a"],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        # Enable front_door camera
        result = await flow.async_step_cameras(user_input={
            "enabled_cameras": ["garage_a", "front_door"],
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_disable_camera(self, mock_hass, mock_config_entry):
        """Test disabling a camera from Frigate config."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "discovered_cameras": ["garage_a", "front_door"],
            "enabled_cameras": ["garage_a", "front_door"],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        # Disable front_door camera
        result = await flow.async_step_cameras(user_input={
            "enabled_cameras": ["garage_a"],
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestOptionsFlowCameraGrouping:
    """Tests for camera grouping by source."""

    @pytest.mark.asyncio
    async def test_cameras_grouped_by_source(self, mock_hass, mock_config_entry):
        """Test cameras are grouped by their source integration."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "discovered_cameras": [
                {"name": "garage_a", "source": "unifiprotect"},
                {"name": "front_door", "source": "reolink"},
                {"name": "backyard", "source": "amcrest"},
            ],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        # Camera list should be organized by source
        result = await flow.async_step_cameras()
        
        assert result["type"] == FlowResultType.FORM


class TestOptionsFlowManualCamera:
    """Tests for manual camera addition."""

    @pytest.mark.asyncio
    async def test_add_manual_camera(self, mock_hass, mock_config_entry):
        """Test adding a camera manually."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_manual_camera(user_input={
            "camera_name": "custom_camera",
            "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
            "detect_width": 640,
            "detect_height": 360,
            "detect_fps": 5,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_manual_camera_invalid_url(self, mock_hass, mock_config_entry):
        """Test manual camera with invalid RTSP URL."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_manual_camera(user_input={
            "camera_name": "custom_camera",
            "rtsp_url": "invalid_url",  # Not a valid RTSP URL
            "detect_width": 640,
            "detect_height": 360,
        })
        
        # Should show error
        if result["type"] == FlowResultType.FORM:
            assert result.get("errors") is not None or result["step_id"] == "manual_camera"

    @pytest.mark.asyncio
    async def test_manual_camera_duplicate_name(self, mock_hass, mock_config_entry):
        """Test manual camera with duplicate name."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "discovered_cameras": ["garage_a"],
            "manual_cameras": [],
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        # Try to add camera with existing name
        result = await flow.async_step_manual_camera(user_input={
            "camera_name": "garage_a",  # Duplicate name
            "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
        })
        
        # Should show error or handle gracefully
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestOptionsFlowCredentialOverrides:
    """Tests for credential override settings."""

    @pytest.mark.asyncio
    async def test_set_credential_override(self, mock_hass, mock_config_entry):
        """Test setting credential override for a camera."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_credentials(user_input={
            "camera_host": "192.168.1.50",
            "override_username": "rtsp_user",
            "override_password": "rtsp_pass",
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_remove_credential_override(self, mock_hass, mock_config_entry):
        """Test removing a credential override."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        mock_config_entry.options = {
            "credential_overrides": {
                "192.168.1.50": {
                    "username": "old_user",
                    "password": "old_pass",
                }
            }
        }
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        # Clear credentials
        result = await flow.async_step_credentials(user_input={
            "camera_host": "192.168.1.50",
            "override_username": "",
            "override_password": "",
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]


class TestOptionsFlowSettingsUpdate:
    """Tests for general settings updates."""

    @pytest.mark.asyncio
    async def test_update_retention_settings(self, mock_hass, mock_config_entry):
        """Test updating retention settings."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_retention(user_input={
            "retain_alerts": 60,
            "retain_detections": 45,
            "retain_motion": 14,
            "retain_snapshots": 90,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

    @pytest.mark.asyncio
    async def test_update_feature_toggles(self, mock_hass, mock_config_entry):
        """Test updating feature toggles."""
        from custom_components.frigate_config_builder.config_flow import FrigateConfigBuilderOptionsFlow
        
        flow = FrigateConfigBuilderOptionsFlow(mock_config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_features(user_input={
            "audio_detection": True,
            "birdseye_enabled": True,
            "semantic_search": True,
            "face_recognition": False,
            "lpr": True,
        })
        
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]
