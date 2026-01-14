"""Manual camera adapter for user-defined cameras."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import CameraAdapter, DiscoveredCamera
from ..const import CONF_MANUAL_CAMERAS

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class ManualAdapter(CameraAdapter):
    """Handle manually-defined cameras from integration options.

    Users can define cameras that aren't auto-discovered through the
    integration's options flow. Each manual camera requires:
    - name: Frigate camera name
    - record_url: RTSP URL for recording

    Optional fields:
    - friendly_name: Display name
    - detect_url: RTSP URL for detection (defaults to record_url)
    - go2rtc_url: URL for live view (defaults to record_url)
    - width: Detection width (default: 640)
    - height: Detection height (default: 360)
    - area: HA area name for grouping
    """

    @property
    def integration_domain(self) -> str:
        """Return 'manual' as the pseudo-domain."""
        return "manual"

    def is_available(self) -> bool:
        """Manual adapter is always available."""
        return True

    async def discover_cameras(self) -> list[DiscoveredCamera]:
        """Return manually-defined cameras from options."""
        cameras: list[DiscoveredCamera] = []

        # Get manual cameras from options
        manual_cameras = self.entry.options.get(CONF_MANUAL_CAMERAS, [])

        if not manual_cameras:
            _LOGGER.debug("No manual cameras configured")
            return []

        for idx, cam_config in enumerate(manual_cameras):
            try:
                camera = self._create_camera_from_config(cam_config, idx)
                if camera:
                    cameras.append(camera)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to process manual camera %d: %s",
                    idx,
                    err,
                )

        _LOGGER.info("Loaded %d manual cameras", len(cameras))
        return cameras

    def _create_camera_from_config(
        self,
        config: dict,
        index: int,
    ) -> DiscoveredCamera | None:
        """Create DiscoveredCamera from manual config dict."""
        # Required fields
        name = config.get("name")
        record_url = config.get("record_url")

        if not name:
            _LOGGER.warning("Manual camera %d missing 'name' field", index)
            return None

        if not record_url:
            _LOGGER.warning("Manual camera %d (%s) missing 'record_url' field", index, name)
            return None

        # Normalize name for Frigate
        cam_name = self.normalize_name(name)

        # Optional fields with defaults
        friendly_name = config.get("friendly_name", name)
        detect_url = config.get("detect_url", record_url)
        go2rtc_url = config.get("go2rtc_url", record_url)
        width = config.get("width", 640)
        height = config.get("height", 360)
        fps = config.get("fps", 5)
        area = config.get("area")

        return DiscoveredCamera(
            id=f"manual_{cam_name}",
            name=cam_name,
            friendly_name=friendly_name,
            source="manual",
            record_url=record_url,
            detect_url=detect_url,
            go2rtc_url=go2rtc_url,
            width=width,
            height=height,
            fps=fps,
            area=area,
            available=True,  # Manual cameras are always "available"
        )
