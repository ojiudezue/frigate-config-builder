"""Camera discovery package for Frigate Config Builder."""
from .base import CameraAdapter, DiscoveredCamera
from .coordinator import DiscoveryCoordinator
from .unifiprotect import UniFiProtectAdapter
from .amcrest import AmcrestAdapter
from .reolink import ReolinkAdapter
from .manual import ManualAdapter

__all__ = [
    "CameraAdapter",
    "DiscoveredCamera",
    "DiscoveryCoordinator",
    "UniFiProtectAdapter",
    "AmcrestAdapter",
    "ReolinkAdapter",
    "ManualAdapter",
]
