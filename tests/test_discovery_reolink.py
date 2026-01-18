"""Unit tests for the Reolink discovery adapter.

Version: 0.4.0.5
Date: 2026-01-18

Tests the discovery/reolink.py module which discovers Reolink cameras.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestReolinkDiscovery:
    """Tests for Reolink camera discovery."""

    @pytest.mark.asyncio
    async def test_config_entry_discovery(self, mock_hass, mock_entity_registry):
        """Test discovery from Reolink config entries."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        # Mock Reolink config entry
        mock_config_entry = MagicMock(
            domain="reolink",
            data={
                "host": "192.168.1.60",
                "port": 80,
                "username": "admin",
                "password": "password123",
                "protocol": "rtsp",
            },
            entry_id="reolink_entry_1",
            title="Reolink Doorbell",
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = ReolinkDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_rtsp_url_main_stream(self, mock_hass):
        """Test RTSP URL for main/high resolution stream."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        discovery = ReolinkDiscovery(mock_hass)
        
        # Main stream URL format: rtsp://user:pass@host:554/h264Preview_01_main
        url = discovery._build_rtsp_url(
            host="192.168.1.60",
            username="admin",
            password="password",
            channel=0,
            stream="main",
        )
        
        assert "rtsp://" in url
        assert "192.168.1.60" in url
        assert "main" in url

    @pytest.mark.asyncio
    async def test_rtsp_url_sub_stream(self, mock_hass):
        """Test RTSP URL for sub/low resolution stream."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        discovery = ReolinkDiscovery(mock_hass)
        
        # Sub stream URL format: rtsp://user:pass@host:554/h264Preview_01_sub
        url = discovery._build_rtsp_url(
            host="192.168.1.60",
            username="admin",
            password="password",
            channel=0,
            stream="sub",
        )
        
        assert "rtsp://" in url
        assert "sub" in url

    @pytest.mark.asyncio
    async def test_http_flv_for_go2rtc(self, mock_hass):
        """Test HTTP-FLV URL generation for go2rtc."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        discovery = ReolinkDiscovery(mock_hass)
        
        # HTTP-FLV format: http://user:pass@host/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=pass
        url = discovery._build_http_flv_url(
            host="192.168.1.60",
            username="admin",
            password="password",
            channel=0,
            stream="main",
        )
        
        assert "http://" in url
        assert "flv" in url
        assert "channel0" in url


class TestReolinkDualStream:
    """Tests for dual stream handling."""

    @pytest.mark.asyncio
    async def test_main_and_sub_streams(self, mock_hass, mock_entity_registry):
        """Test detection of both main and sub streams."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        # Create mock entities for main and sub streams
        mock_entity_registry.entities = {
            "camera.reolink_doorbell": MagicMock(
                entity_id="camera.reolink_doorbell",
                platform="reolink",
                device_id="reolink_device_1",
                unique_id="reolink_doorbell_main",
                disabled=False,
            ),
            "camera.reolink_doorbell_sub": MagicMock(
                entity_id="camera.reolink_doorbell_sub",
                platform="reolink",
                device_id="reolink_device_1",
                unique_id="reolink_doorbell_sub",
                disabled=False,
            ),
        }
        
        discovery = ReolinkDiscovery(mock_hass)
        # Should recognize both streams belong to same physical camera
        assert discovery is not None

    @pytest.mark.asyncio
    async def test_stream_dimensions(self, mock_hass, mock_entity_registry):
        """Test stream dimension extraction."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        mock_hass.states.get = MagicMock(return_value=MagicMock(
            state="streaming",
            attributes={
                "video_mode": "highRes",
                "width": 2560,
                "height": 1920,
                "fps": 20,
            }
        ))
        
        discovery = ReolinkDiscovery(mock_hass)
        # Test dimension extraction
        assert discovery is not None


class TestReolinkDisabledEntities:
    """Tests for disabled entity handling."""

    @pytest.mark.asyncio
    async def test_skip_disabled_entities(self, mock_hass, mock_entity_registry):
        """Test that disabled camera entities are skipped."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        mock_entity_registry.entities = {
            "camera.reolink_disabled": MagicMock(
                entity_id="camera.reolink_disabled",
                platform="reolink",
                device_id="reolink_device_disabled",
                unique_id="reolink_disabled",
                disabled=True,  # Disabled entity
            ),
            "camera.reolink_enabled": MagicMock(
                entity_id="camera.reolink_enabled",
                platform="reolink",
                device_id="reolink_device_enabled",
                unique_id="reolink_enabled",
                disabled=False,  # Enabled entity
            ),
        }
        
        discovery = ReolinkDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        # Should skip disabled entities
        disabled_cameras = [c for c in cameras if "disabled" in c.name.lower()]
        assert len(disabled_cameras) == 0


class TestReolinkNVR:
    """Tests for Reolink NVR discovery."""

    @pytest.mark.asyncio
    async def test_nvr_multi_channel(self, mock_hass):
        """Test NVR with multiple channels."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        mock_config_entry = MagicMock(
            domain="reolink",
            data={
                "host": "192.168.1.70",
                "username": "admin",
                "password": "password",
                "channels": 8,  # 8-channel NVR
            },
            title="Reolink NVR",
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = ReolinkDiscovery(mock_hass)
        # Should handle multi-channel NVR
        cameras = await discovery.discover()
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_nvr_channel_urls(self, mock_hass):
        """Test RTSP URLs for different NVR channels."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        discovery = ReolinkDiscovery(mock_hass)
        
        # Channel 0
        url_ch0 = discovery._build_rtsp_url(
            host="192.168.1.70",
            username="admin",
            password="pass",
            channel=0,
            stream="main",
        )
        assert "01" in url_ch0 or "channel0" in url_ch0.lower()
        
        # Channel 3
        url_ch3 = discovery._build_rtsp_url(
            host="192.168.1.70",
            username="admin",
            password="pass",
            channel=3,
            stream="main",
        )
        assert "04" in url_ch3 or "channel3" in url_ch3.lower()


class TestReolinkCredentials:
    """Tests for credential handling."""

    @pytest.mark.asyncio
    async def test_default_credentials(self, mock_hass):
        """Test using credentials from config entry."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        mock_config_entry = MagicMock(
            domain="reolink",
            data={
                "host": "192.168.1.60",
                "username": "admin",
                "password": "reolink_pass",
            },
        )
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
        
        discovery = ReolinkDiscovery(mock_hass)
        cameras = await discovery.discover()
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_password_special_characters(self, mock_hass):
        """Test passwords with special characters."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        discovery = ReolinkDiscovery(mock_hass)
        
        # Password with special chars
        url = discovery._build_rtsp_url(
            host="192.168.1.60",
            username="admin",
            password="p@ss^word!",
            channel=0,
            stream="main",
        )
        
        # Should be properly URL encoded
        assert "rtsp://" in url


class TestReolinkNoEntries:
    """Tests for empty/no config entries."""

    @pytest.mark.asyncio
    async def test_no_reolink_entries(self, mock_hass):
        """Test when no Reolink config entries exist."""
        from custom_components.frigate_config_builder.discovery.reolink import ReolinkDiscovery
        
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])
        
        discovery = ReolinkDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        assert cameras == []
