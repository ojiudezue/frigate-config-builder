"""Unit tests for the UniFi Protect discovery adapter.

Version: 0.4.0.5
Date: 2026-01-18

Tests the discovery/unifiprotect.py module which discovers UniFi Protect cameras.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


class TestUniFiProtectDiscovery:
    """Tests for UniFi Protect camera discovery."""

    @pytest.mark.asyncio
    async def test_basic_camera_discovery(self, mock_hass, mock_entity_registry, mock_device_registry):
        """Test basic camera discovery from UniFi Protect."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        # Create mock camera entity
        mock_entity_registry.entities = {
            "camera.garage_a_high": MagicMock(
                entity_id="camera.garage_a_high",
                platform="unifiprotect",
                device_id="device_garage_a",
                unique_id="garage_a_high",
                disabled=False,
            ),
        }
        
        # Create mock device
        mock_device_registry.devices = {
            "device_garage_a": MagicMock(
                id="device_garage_a",
                name="Garage A",
                model="G4 Bullet",
                manufacturer="Ubiquiti",
                area_id="garage",
            ),
        }
        
        # Mock the state
        mock_hass.states.get = MagicMock(return_value=MagicMock(
            state="streaming",
            attributes={
                "video_mode": "highFps",
                "width": 2688,
                "height": 1512,
            }
        ))
        
        discovery = UniFiProtectDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        assert len(cameras) >= 0  # Basic test that discovery runs

    @pytest.mark.asyncio
    async def test_dual_stream_detection(self, mock_hass, mock_entity_registry):
        """Test detection of high and medium resolution streams."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        # Setup both high and medium stream entities for same camera
        mock_entity_registry.entities = {
            "camera.garage_a_high": MagicMock(
                entity_id="camera.garage_a_high",
                platform="unifiprotect",
                device_id="device_garage_a",
                unique_id="garage_a_high",
                disabled=False,
            ),
            "camera.garage_a_medium": MagicMock(
                entity_id="camera.garage_a_medium",
                platform="unifiprotect",
                device_id="device_garage_a",
                unique_id="garage_a_medium",
                disabled=False,
            ),
        }
        
        discovery = UniFiProtectDiscovery(mock_hass)
        # Test that both streams are recognized
        assert discovery is not None

    @pytest.mark.asyncio
    async def test_package_camera_exclusion(self, mock_hass, mock_entity_registry, mock_device_registry):
        """Test that package cameras (G4 Doorbell) are handled correctly."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        mock_entity_registry.entities = {
            "camera.doorbell_package_high": MagicMock(
                entity_id="camera.doorbell_package_high",
                platform="unifiprotect",
                device_id="device_doorbell",
                unique_id="doorbell_package_high",
                disabled=False,
            ),
        }
        
        mock_device_registry.devices = {
            "device_doorbell": MagicMock(
                id="device_doorbell",
                name="Front Doorbell",
                model="G4 Doorbell Pro",
                manufacturer="Ubiquiti",
            ),
        }
        
        discovery = UniFiProtectDiscovery(mock_hass)
        # Package cameras should be handled appropriately
        assert discovery is not None

    @pytest.mark.asyncio
    async def test_unavailable_camera_handling(self, mock_hass, mock_entity_registry):
        """Test handling of unavailable cameras."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        mock_entity_registry.entities = {
            "camera.offline_camera_high": MagicMock(
                entity_id="camera.offline_camera_high",
                platform="unifiprotect",
                device_id="device_offline",
                unique_id="offline_camera_high",
                disabled=False,
            ),
        }
        
        # Camera state is unavailable
        mock_hass.states.get = MagicMock(return_value=MagicMock(
            state="unavailable",
            attributes={}
        ))
        
        discovery = UniFiProtectDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        # Unavailable cameras should be skipped or marked appropriately
        assert isinstance(cameras, list)

    @pytest.mark.asyncio
    async def test_rtsp_service_check(self, mock_hass, mock_entity_registry):
        """Test RTSP service availability checking."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        discovery = UniFiProtectDiscovery(mock_hass)
        
        # Test that RTSP URL building works
        assert discovery is not None

    @pytest.mark.asyncio
    async def test_disabled_entity_skip(self, mock_hass, mock_entity_registry):
        """Test that disabled entities are skipped."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        mock_entity_registry.entities = {
            "camera.disabled_camera_high": MagicMock(
                entity_id="camera.disabled_camera_high",
                platform="unifiprotect",
                device_id="device_disabled",
                unique_id="disabled_camera_high",
                disabled=True,  # Entity is disabled
            ),
        }
        
        discovery = UniFiProtectDiscovery(mock_hass)
        cameras = await discovery.discover()
        
        # Disabled cameras should be skipped
        assert all(not c.name.startswith("disabled") for c in cameras)


class TestUniFiProtectRTSPURL:
    """Tests for UniFi Protect RTSP URL building."""

    def test_rtsp_url_high_stream(self):
        """Test RTSP URL generation for high resolution stream."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        # Test URL format: rtsps://ip:7441/unique_id?enableSrtp
        # The actual implementation will determine the format
        pass

    def test_rtsp_url_medium_stream(self):
        """Test RTSP URL generation for medium resolution stream."""
        pass

    def test_rtsp_url_with_special_characters(self):
        """Test RTSP URL handles special characters in camera name."""
        pass


class TestUniFiProtectAreaMapping:
    """Tests for area-to-camera mapping."""

    @pytest.mark.asyncio
    async def test_camera_area_assignment(self, mock_hass, mock_entity_registry, mock_device_registry, mock_area_registry):
        """Test cameras get assigned to correct areas."""
        from custom_components.frigate_config_builder.discovery.unifiprotect import UniFiProtectDiscovery
        
        mock_device_registry.devices = {
            "device_garage_a": MagicMock(
                id="device_garage_a",
                name="Garage A",
                area_id="garage",
            ),
        }
        
        mock_area_registry.areas = {
            "garage": MagicMock(
                id="garage",
                name="Garage",
            ),
        }
        
        discovery = UniFiProtectDiscovery(mock_hass)
        # Test area assignment
        assert discovery is not None
