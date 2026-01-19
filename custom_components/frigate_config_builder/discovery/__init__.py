"""Camera discovery package for Frigate Config Builder.

Version: 0.4.0.5
Date: 2026-01-18

Supported adapters:
- UniFiProtectAdapter: UniFi Protect cameras
- AmcrestAdapter: Amcrest/Dahua cameras
- ReolinkAdapter: Reolink cameras (including multi-lens)
- GenericAdapter: Generic RTSP cameras (any standalone RTSP stream)
- ManualAdapter: User-defined cameras via options
"""
from .base import CameraAdapter, DiscoveredCamera
from .coordinator import DiscoveryCoordinator
from .unifiprotect import UniFiProtectAdapter
from .amcrest import AmcrestAdapter
from .reolink import ReolinkAdapter
from .generic import GenericAdapter
from .manual import ManualAdapter

__all__ = [
    "CameraAdapter",
    "DiscoveredCamera",
    "DiscoveryCoordinator",
    "UniFiProtectAdapter",
    "AmcrestAdapter",
    "ReolinkAdapter",
    "GenericAdapter",
    "ManualAdapter",
]
