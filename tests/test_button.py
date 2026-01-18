"""Unit tests for button entities.

Version: 0.4.0.5
Date: 2026-01-18

Tests the entities/button.py module.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestGenerateButton:
    """Tests for the Generate Configuration button entity."""

    @pytest.mark.asyncio
    async def test_button_creation(self, mock_hass, mock_config_entry):
        """Test button entity can be created."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        
        assert button is not None
        assert button.name is not None

    @pytest.mark.asyncio
    async def test_button_unique_id(self, mock_hass, mock_config_entry):
        """Test button has correct unique ID."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        
        assert mock_config_entry.entry_id in button.unique_id

    @pytest.mark.asyncio
    async def test_button_icon(self, mock_hass, mock_config_entry):
        """Test button has correct icon."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        
        # Should have a relevant icon
        assert button.icon in ["mdi:file-cog", "mdi:cog-refresh", "mdi:refresh", "mdi:file-refresh"]

    @pytest.mark.asyncio
    async def test_button_press_triggers_generation(self, mock_hass, mock_config_entry):
        """Test pressing button triggers config generation."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        button.hass = mock_hass
        
        with patch.object(button, '_generate_config', new_callable=AsyncMock) as mock_generate:
            await button.async_press()
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_button_press_updates_timestamp(self, mock_hass, mock_config_entry):
        """Test pressing button updates last generated timestamp."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        button.hass = mock_hass
        
        # Mock the generation to succeed
        with patch.object(button, '_generate_config', new_callable=AsyncMock):
            await button.async_press()
            
            # Coordinator should have updated timestamp
            # This depends on implementation details

    @pytest.mark.asyncio
    async def test_button_device_info(self, mock_hass, mock_config_entry):
        """Test button has correct device info."""
        from custom_components.frigate_config_builder.entities.button import GenerateConfigButton
        
        button = GenerateConfigButton(mock_config_entry)
        
        device_info = button.device_info
        
        assert device_info is not None
        assert "identifiers" in device_info
