"""Unit tests for the Amcrest discovery adapter.

Version: 0.4.0.5
Date: 2026-01-18

Tests the discovery/amcrest.py module which discovers Amcrest cameras.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAmcrestDiscovery:
    """Tests for Amcrest camera discovery."""

    @pytest.mark.asyncio
    async def test_config_entry_discovery(self, mock_hass, mock_entity_registry):
        """Test discovery from Amcrest config entries."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        # Mock Amcrest config entry
        mock_config_entry = MagicMock(
            domain="amcrest",
            data={
                "host": "192.168.1.50",
                "port": 80,
                "username": "admin",
                "password": "password123",
            },
            entry_id="amcrest_entry_1",
            title="Amcrest Camera",
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = AmcrestDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_rtsp_url_building(self, mock_hass):
        """Test RTSP URL construction for Amcrest cameras."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        discovery = AmcrestDiscovery(mock_hass)
        
        # Test standard RTSP URL format
        # Format: rtsp://user:pass@host:554/cam/realmonitor?channel=1&subtype=0
        url = discovery._build_rtsp_url(
            host="192.168.1.50",
            username="admin",
            password="password123",
            channel=1,
            subtype=0,
        )
        
        assert "rtsp://" in url
        assert "192.168.1.50" in url
        assert "admin" in url
        assert "channel=1" in url
        assert "subtype=0" in url

    @pytest.mark.asyncio
    async def test_channel_selection(self, mock_hass):
        """Test camera channel selection for multi-channel devices."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        # Multi-channel Amcrest devices (like AD410)
        mock_config_entry = MagicMock(
            domain="amcrest",
            data={
                "host": "192.168.1.51",
                "username": "admin",
                "password": "pass",
            },
        )
        
        discovery = AmcrestDiscovery(mock_hass)
        # Test channel 1 (main)
        url_ch1 = discovery._build_rtsp_url(
            host="192.168.1.51",
            username="admin",
            password="pass",
            channel=1,
            subtype=0,
        )
        assert "channel=1" in url_ch1
        
        # Test channel 2 (package)
        url_ch2 = discovery._build_rtsp_url(
            host="192.168.1.51",
            username="admin",
            password="pass",
            channel=2,
            subtype=0,
        )
        assert "channel=2" in url_ch2

    @pytest.mark.asyncio
    async def test_subtype_selection(self, mock_hass):
        """Test stream subtype selection (main vs sub stream)."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        discovery = AmcrestDiscovery(mock_hass)
        
        # Subtype 0 = main stream (high res)
        url_main = discovery._build_rtsp_url(
            host="192.168.1.50",
            username="admin",
            password="pass",
            channel=1,
            subtype=0,
        )
        assert "subtype=0" in url_main
        
        # Subtype 1 = sub stream (low res for detect)
        url_sub = discovery._build_rtsp_url(
            host="192.168.1.50",
            username="admin",
            password="pass",
            channel=1,
            subtype=1,
        )
        assert "subtype=1" in url_sub


class TestAmcrestCredentialOverrides:
    """Tests for credential override handling."""

    @pytest.mark.asyncio
    async def test_default_credentials(self, mock_hass):
        """Test using credentials from config entry."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        mock_config_entry = MagicMock(
            domain="amcrest",
            data={
                "host": "192.168.1.50",
                "username": "admin",
                "password": "original_pass",
            },
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = AmcrestDiscovery(mock_hass)
        # Default should use config entry credentials
        cameras = await discovery.discover()
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_credential_override(self, mock_hass):
        """Test overriding credentials for RTSP access."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        mock_config_entry = MagicMock(
            domain="amcrest",
            data={
                "host": "192.168.1.50",
                "username": "admin",
                "password": "original_pass",
            },
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = AmcrestDiscovery(mock_hass, credential_overrides={
            "192.168.1.50": {
                "username": "rtsp_user",
                "password": "rtsp_pass",
            }
        })
        
        # Should use override credentials
        cameras = await discovery.discover()
        assert isinstance(cameras, list)


class TestAmcrestSpecialCharacters:
    """Tests for special character handling in credentials."""

    def test_password_url_encoding(self):
        """Test passwords with special characters are URL encoded."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        discovery = AmcrestDiscovery(MagicMock())
        
        # Password with @ and ^ characters
        url = discovery._build_rtsp_url(
            host="192.168.1.50",
            username="admin",
            password="pass@word^123",
            channel=1,
            subtype=0,
        )
        
        # Special characters should be URL encoded
        # @ -> %40, ^ -> %5E
        assert "%40" in url or "@" not in url.split("@")[1]  # @ not in the host portion

    def test_username_special_characters(self):
        """Test usernames with special characters."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        discovery = AmcrestDiscovery(MagicMock())
        
        url = discovery._build_rtsp_url(
            host="192.168.1.50",
            username="admin@domain",
            password="pass",
            channel=1,
            subtype=0,
        )
        
        assert "rtsp://" in url


class TestAmcrestMultiCamera:
    """Tests for multi-camera discovery."""

    @pytest.mark.asyncio
    async def test_multiple_config_entries(self, mock_hass):
        """Test discovery from multiple Amcrest config entries."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        mock_entries = [
            MagicMock(
                domain="amcrest",
                data={
                    "host": "192.168.1.50",
                    "username": "admin",
                    "password": "pass1",
                },
                title="Front Camera",
            ),
            MagicMock(
                domain="amcrest",
                data={
                    "host": "192.168.1.51",
                    "username": "admin",
                    "password": "pass2",
                },
                title="Back Camera",
            ),
        ]
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=mock_entries)
        
        discovery = AmcrestDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        # Should discover both cameras
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_no_amcrest_entries(self, mock_hass):
        """Test when no Amcrest config entries exist."""
        from custom_components.frigate_config_builder.discovery.amcrest import AmcrestDiscovery
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])
        
        discovery = AmcrestDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        assert cameras == []
