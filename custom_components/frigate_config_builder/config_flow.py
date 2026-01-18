"""Config flow for Frigate Config Builder.

Version: 0.3.0.3
Date: 2026-01-17

Features:
- Multi-step initial setup (connection, hardware, mqtt, features, retention)
- Options flow with camera selection and exclude unavailable toggle
- Comma-separated list of unavailable cameras with overflow handling
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    BIRDSEYE_MODES,
    CONF_AUDIO_DETECTION,
    CONF_AUTO_GROUPS,
    CONF_AUTO_PUSH,
    CONF_BIRD_CLASSIFICATION,
    CONF_BIRDSEYE_ENABLED,
    CONF_BIRDSEYE_MODE,
    CONF_DETECTOR_DEVICE,
    CONF_DETECTOR_TYPE,
    CONF_EXCLUDE_UNAVAILABLE,
    CONF_FACE_RECOGNITION,
    CONF_FACE_RECOGNITION_MODEL,
    CONF_FRIGATE_URL,
    CONF_HWACCEL,
    CONF_LPR,
    CONF_MQTT_AUTO,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_NETWORK_INTERFACES,
    CONF_OUTPUT_PATH,
    CONF_RETAIN_ALERTS,
    CONF_RETAIN_DETECTIONS,
    CONF_RETAIN_MOTION,
    CONF_RETAIN_SNAPSHOTS,
    CONF_SELECTED_CAMERAS,
    CONF_SEMANTIC_SEARCH,
    CONF_SEMANTIC_SEARCH_MODEL,
    DEFAULT_BIRDSEYE_MODE,
    DEFAULT_DETECTOR_DEVICE,
    DEFAULT_DETECTOR_TYPE,
    DEFAULT_HWACCEL,
    DEFAULT_MODEL_SIZE,
    DEFAULT_MQTT_PORT,
    DEFAULT_NETWORK_INTERFACE,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_RETAIN_ALERTS,
    DEFAULT_RETAIN_DETECTIONS,
    DEFAULT_RETAIN_MOTION,
    DEFAULT_RETAIN_SNAPSHOTS,
    DETECTOR_TYPES,
    DOMAIN,
    HWACCEL_OPTIONS,
    MODEL_SIZES,
)

_LOGGER = logging.getLogger(__name__)

# Maximum cameras to show in the unavailable list before truncating
MAX_UNAVAILABLE_DISPLAY = 5


class FrigateConfigBuilderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frigate Config Builder."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 1: Connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate output path
            output_path = user_input.get(CONF_OUTPUT_PATH, "")
            if not output_path or not output_path.endswith(".yml"):
                errors[CONF_OUTPUT_PATH] = "invalid_path"

            # Validate Frigate URL if provided
            frigate_url = user_input.get(CONF_FRIGATE_URL)
            if frigate_url and not frigate_url.startswith(("http://", "https://")):
                errors[CONF_FRIGATE_URL] = "invalid_url"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_hardware()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_OUTPUT_PATH,
                        default=DEFAULT_OUTPUT_PATH,
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Optional(CONF_FRIGATE_URL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                    vol.Optional(
                        CONF_AUTO_PUSH,
                        default=False,
                    ): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_hardware(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 2: Hardware settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_mqtt()

        return self.async_show_form(
            step_id="hardware",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DETECTOR_TYPE,
                        default=DEFAULT_DETECTOR_TYPE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=DETECTOR_TYPES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_DETECTOR_DEVICE,
                        default=DEFAULT_DETECTOR_DEVICE,
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Required(
                        CONF_HWACCEL,
                        default=DEFAULT_HWACCEL,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in HWACCEL_OPTIONS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_NETWORK_INTERFACES,
                        default=DEFAULT_NETWORK_INTERFACE,
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                }
            ),
            errors=errors,
        )

    async def async_step_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 3: MQTT settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate MQTT config if not using auto
            if not user_input.get(CONF_MQTT_AUTO, True):
                if not user_input.get(CONF_MQTT_HOST):
                    errors[CONF_MQTT_HOST] = "required"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_features()

        # Check if HA has MQTT configured
        mqtt_entries = self.hass.config_entries.async_entries("mqtt")
        has_mqtt = bool(mqtt_entries)

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MQTT_AUTO,
                        default=has_mqtt,
                    ): BooleanSelector(),
                    vol.Optional(CONF_MQTT_HOST): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_MQTT_PORT,
                        default=DEFAULT_MQTT_PORT,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=65535,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_MQTT_USER): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(CONF_MQTT_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"mqtt_detected": "Yes" if has_mqtt else "No"},
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 4: Feature settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_retention()

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUDIO_DETECTION,
                        default=True,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_FACE_RECOGNITION,
                        default=False,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_FACE_RECOGNITION_MODEL,
                        default=DEFAULT_MODEL_SIZE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=MODEL_SIZES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_SEMANTIC_SEARCH,
                        default=False,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_SEMANTIC_SEARCH_MODEL,
                        default=DEFAULT_MODEL_SIZE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=MODEL_SIZES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_LPR,
                        default=False,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_BIRD_CLASSIFICATION,
                        default=False,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_BIRDSEYE_ENABLED,
                        default=True,
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_BIRDSEYE_MODE,
                        default=DEFAULT_BIRDSEYE_MODE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=BIRDSEYE_MODES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_retention(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 5: Retention settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            # Check if we already have an entry
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Create the config entry
            return self.async_create_entry(
                title="Frigate Config Builder",
                data=self._data,
            )

        return self.async_show_form(
            step_id="retention",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_RETAIN_ALERTS,
                        default=DEFAULT_RETAIN_ALERTS,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=365,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                    vol.Optional(
                        CONF_RETAIN_DETECTIONS,
                        default=DEFAULT_RETAIN_DETECTIONS,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=365,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                    vol.Optional(
                        CONF_RETAIN_MOTION,
                        default=DEFAULT_RETAIN_MOTION,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=365,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                    vol.Optional(
                        CONF_RETAIN_SNAPSHOTS,
                        default=DEFAULT_RETAIN_SNAPSHOTS,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=365,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return FrigateConfigBuilderOptionsFlow(config_entry)


def _format_unavailable_cameras_list(
    unavailable_cameras: list[str],
    max_display: int = MAX_UNAVAILABLE_DISPLAY,
) -> str:
    """Format the list of unavailable cameras with overflow handling.

    Args:
        unavailable_cameras: List of unavailable camera friendly names
        max_display: Maximum cameras to display before truncating

    Returns:
        User-friendly formatted string like:
        - "Camera A, Camera B" (if 2 cameras)
        - "Camera A, Camera B, Camera C, +2 more" (if 5 cameras with max_display=3)
        - "None" (if empty)
    """
    if not unavailable_cameras:
        return "None"

    count = len(unavailable_cameras)

    if count <= max_display:
        return ", ".join(unavailable_cameras)

    # Show first (max_display - 1) cameras + "and X more"
    displayed = unavailable_cameras[: max_display]
    remaining = count - max_display
    return f"{', '.join(displayed)}, +{remaining} more"


class FrigateConfigBuilderOptionsFlow(OptionsFlow):
    """Handle options flow for camera selection."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle main options flow - camera selection."""
        # Get coordinator to access discovered cameras
        coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)

        if coordinator is None:
            _LOGGER.error("Coordinator not found for options flow")
            return self.async_abort(reason="coordinator_not_found")

        all_cameras = coordinator.discovered_cameras

        # Separate available and unavailable cameras
        available_cameras = [cam for cam in all_cameras if cam.available]
        unavailable_cameras = [cam for cam in all_cameras if not cam.available]
        unavailable_names = [cam.friendly_name for cam in unavailable_cameras]

        # Get current options
        current_exclude_unavailable = self._config_entry.options.get(
            CONF_EXCLUDE_UNAVAILABLE, True  # Default: exclude unavailable
        )
        current_auto_groups = self._config_entry.options.get(CONF_AUTO_GROUPS, True)

        if user_input is not None:
            # Process submission
            exclude_unavailable = user_input.get(CONF_EXCLUDE_UNAVAILABLE, True)
            selected_ids = user_input.get(CONF_SELECTED_CAMERAS, [])

            # If exclude_unavailable is True, ensure no unavailable cameras in selection
            if exclude_unavailable:
                unavailable_ids = {cam.id for cam in unavailable_cameras}
                selected_ids = [
                    cam_id for cam_id in selected_ids if cam_id not in unavailable_ids
                ]

            # Build final options
            options = {
                CONF_SELECTED_CAMERAS: selected_ids,
                CONF_EXCLUDE_UNAVAILABLE: exclude_unavailable,
                CONF_AUTO_GROUPS: user_input.get(CONF_AUTO_GROUPS, True),
            }

            return self.async_create_entry(title="", data=options)

        # Build camera selection options based on exclude setting
        # When showing the form, we show all cameras but mark unavailable ones
        camera_options: dict[str, str] = {}

        # Determine which cameras to show in selection
        if current_exclude_unavailable:
            # Only show available cameras
            cameras_to_show = available_cameras
        else:
            # Show all cameras
            cameras_to_show = all_cameras

        for cam in cameras_to_show:
            label = f"{cam.friendly_name} ({cam.source})"

            # Add badges for status
            badges = []
            if cam.is_new:
                badges.append("NEW")
            if not cam.available:
                badges.append("UNAVAIL")

            if badges:
                label = f"{label} [{', '.join(badges)}]"

            camera_options[cam.id] = label

        # Get currently selected cameras
        # Default: all available cameras if no selection exists
        current_selected = self._config_entry.options.get(CONF_SELECTED_CAMERAS)

        if current_selected is None:
            # First time - default to all available cameras
            default_selected = [cam.id for cam in available_cameras]
        else:
            # Filter current selection based on exclude setting
            if current_exclude_unavailable:
                unavailable_ids = {cam.id for cam in unavailable_cameras}
                default_selected = [
                    cam_id
                    for cam_id in current_selected
                    if cam_id not in unavailable_ids and cam_id in camera_options
                ]
            else:
                # Keep all that still exist
                all_ids = {cam.id for cam in all_cameras}
                default_selected = [
                    cam_id for cam_id in current_selected if cam_id in all_ids
                ]

        # Build description placeholders
        by_source = coordinator.get_cameras_by_source()
        source_summary = ", ".join(
            f"{source}: {len(cams)}" for source, cams in by_source.items()
        )

        # Format unavailable cameras list for display
        unavailable_list = _format_unavailable_cameras_list(unavailable_names)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_EXCLUDE_UNAVAILABLE,
                        default=current_exclude_unavailable,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_SELECTED_CAMERAS,
                        default=default_selected,
                    ): cv.multi_select(camera_options),
                    vol.Optional(
                        CONF_AUTO_GROUPS,
                        default=current_auto_groups,
                    ): BooleanSelector(),
                }
            ),
            description_placeholders={
                "camera_count": str(len(all_cameras)),
                "available_count": str(len(available_cameras)),
                "unavailable_count": str(len(unavailable_cameras)),
                "source_summary": source_summary,
                "unavailable_cameras": unavailable_list,
            },
        )
