"""Config flow for Frigate Config Builder.

Version: 0.4.0.5
Date: 2026-01-18

Changelog:
- 0.4.0.5: Added Frigate version selection (0.14/0.17), GenAI config, YOLOv9 detector
- 0.4.0.4: Options flow camera selection improvements
- 0.4.0.3: Options flow now has multiple steps for editing connection, features, retention
- 0.4.0.2: Options flow runs fresh discovery when opened (fixes Reolink delay)
- 0.4.0.0: Multi-step initial setup with options flow camera selection
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
    CONF_FRIGATE_VERSION,
    CONF_GENAI_API_KEY,
    CONF_GENAI_BASE_URL,
    CONF_GENAI_ENABLED,
    CONF_GENAI_MODEL,
    CONF_GENAI_PROVIDER,
    CONF_HWACCEL,
    CONF_LPR,
    CONF_LPR_MODEL,
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
    DEFAULT_FRIGATE_VERSION,
    DEFAULT_GENAI_PROVIDER,
    DEFAULT_HWACCEL,
    DEFAULT_LPR_MODEL_014,
    DEFAULT_LPR_MODEL_017,
    DEFAULT_MODEL_SIZE,
    DEFAULT_MQTT_PORT,
    DEFAULT_NETWORK_INTERFACE,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_RETAIN_ALERTS,
    DEFAULT_RETAIN_DETECTIONS,
    DEFAULT_RETAIN_MOTION,
    DEFAULT_RETAIN_SNAPSHOTS,
    DETECTOR_TYPES_014,
    DETECTOR_TYPES_017,
    DOMAIN,
    FRIGATE_VERSIONS,
    GENAI_PROVIDER_OPTIONS,
    HWACCEL_OPTIONS,
    MODEL_SIZES,
)
from .discovery import DiscoveredCamera

_LOGGER = logging.getLogger(__name__)

MAX_UNAVAILABLE_DISPLAY = 5

# Internal key for select all toggle (not persisted)
CONF_SELECT_ALL = "select_all_cameras"


def get_detector_types_for_version(frigate_version: str) -> list[str]:
    """Get detector types available for a Frigate version."""
    if frigate_version == "0.17":
        return DETECTOR_TYPES_017
    return DETECTOR_TYPES_014


def get_default_lpr_model(frigate_version: str) -> str:
    """Get default LPR model for a Frigate version."""
    if frigate_version == "0.17":
        return DEFAULT_LPR_MODEL_017
    return DEFAULT_LPR_MODEL_014


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
            output_path = user_input.get(CONF_OUTPUT_PATH, "")
            if not output_path or not output_path.endswith((".yml", ".yaml")):
                errors[CONF_OUTPUT_PATH] = "invalid_path"

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
                        CONF_FRIGATE_VERSION,
                        default=DEFAULT_FRIGATE_VERSION,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "0.14", "label": "Frigate 0.14.x (Stable)"},
                                {"value": "0.17", "label": "Frigate 0.17.x (Latest)"},
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
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
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_mqtt()

        # Get detector types based on selected Frigate version
        frigate_version = self._data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
        detector_types = get_detector_types_for_version(frigate_version)

        return self.async_show_form(
            step_id="hardware",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DETECTOR_TYPE,
                        default=DEFAULT_DETECTOR_TYPE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=detector_types,
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
            description_placeholders={
                "frigate_version": frigate_version,
            },
        )

    async def async_step_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 3: MQTT settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_MQTT_AUTO, True):
                if not user_input.get(CONF_MQTT_HOST):
                    errors[CONF_MQTT_HOST] = "required"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_features()

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
            description_placeholders={
                "mqtt_detected": "✅ MQTT detected" if has_mqtt else "⚠️ No MQTT found"
            },
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 4: Feature settings."""
        if user_input is not None:
            self._data.update(user_input)
            
            # Check if we need GenAI step (0.17+ only)
            frigate_version = self._data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
            if frigate_version == "0.17" and user_input.get(CONF_GENAI_ENABLED, False):
                return await self.async_step_genai()
            
            return await self.async_step_retention()

        frigate_version = self._data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
        default_lpr_model = get_default_lpr_model(frigate_version)
        is_017 = frigate_version == "0.17"

        # Build schema based on Frigate version
        schema_dict = {
            vol.Optional(CONF_AUDIO_DETECTION, default=True): BooleanSelector(),
            vol.Optional(CONF_FACE_RECOGNITION, default=False): BooleanSelector(),
            vol.Optional(
                CONF_FACE_RECOGNITION_MODEL,
                default=DEFAULT_MODEL_SIZE,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_SEMANTIC_SEARCH, default=False): BooleanSelector(),
            vol.Optional(
                CONF_SEMANTIC_SEARCH_MODEL,
                default=DEFAULT_MODEL_SIZE,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_LPR, default=False): BooleanSelector(),
            vol.Optional(
                CONF_LPR_MODEL,
                default=default_lpr_model,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_BIRD_CLASSIFICATION, default=False): BooleanSelector(),
            vol.Optional(CONF_BIRDSEYE_ENABLED, default=True): BooleanSelector(),
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

        # Add GenAI option for Frigate 0.17+
        if is_017:
            schema_dict[vol.Optional(CONF_GENAI_ENABLED, default=False)] = BooleanSelector()

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "frigate_version": frigate_version,
                "lpr_note": "💡 In 0.17+, the 'small' LPR model performs better than the old 'large' model" if is_017 else "",
            },
        )

    async def async_step_genai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 4b: GenAI settings (Frigate 0.17+ only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            provider = user_input.get(CONF_GENAI_PROVIDER, DEFAULT_GENAI_PROVIDER)
            
            # Validate API key for cloud providers
            if provider in ("gemini", "openai", "azure_openai"):
                if not user_input.get(CONF_GENAI_API_KEY):
                    errors[CONF_GENAI_API_KEY] = "required"
            
            # Validate base URL for Azure OpenAI
            if provider == "azure_openai":
                if not user_input.get(CONF_GENAI_BASE_URL):
                    errors[CONF_GENAI_BASE_URL] = "required"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_retention()

        return self.async_show_form(
            step_id="genai",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GENAI_PROVIDER,
                        default=DEFAULT_GENAI_PROVIDER,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in GENAI_PROVIDER_OPTIONS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_GENAI_MODEL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(CONF_GENAI_API_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(CONF_GENAI_BASE_URL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "provider_help": "Ollama runs locally. Cloud providers (Gemini, OpenAI, Azure) require API keys.",
            },
        )

    async def async_step_retention(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 5: Retention settings."""
        if user_input is not None:
            self._data.update(user_input)

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

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
    """Format the list of unavailable cameras with overflow handling."""
    if not unavailable_cameras:
        return "None"

    count = len(unavailable_cameras)

    if count <= max_display:
        return f"⚠️ Offline: {', '.join(unavailable_cameras)}"

    displayed = unavailable_cameras[:max_display]
    remaining = count - max_display
    return f"⚠️ Offline: {', '.join(displayed)}, +{remaining} more"


class FrigateConfigBuilderOptionsFlow(OptionsFlow):
    """Handle options flow with multiple configuration steps.

    Steps:
    1. init - Camera selection
    2. connection - Frigate URL, output path, auto-push, Frigate version
    3. features - Audio, face recognition, LPR, GenAI, etc.
    4. genai - GenAI provider settings (if enabled, 0.17+ only)
    5. retention - Recording retention settings
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._discovered_cameras: list[DiscoveredCamera] = []
        self._available_cameras: list[DiscoveredCamera] = []
        self._unavailable_cameras: list[DiscoveredCamera] = []
        self._discovery_complete: bool = False
        # Store changes across steps
        self._options: dict[str, Any] = dict(config_entry.options)
        self._data_updates: dict[str, Any] = {}

    async def _run_discovery(self) -> None:
        """Run fresh camera discovery."""
        from .discovery import DiscoveryCoordinator

        try:
            _LOGGER.info("Options flow: Running fresh camera discovery")

            discovery = DiscoveryCoordinator(self.hass, self._config_entry)
            self._discovered_cameras = await discovery.discover_all()

            self._available_cameras = [
                c for c in self._discovered_cameras if c.available
            ]
            self._unavailable_cameras = [
                c for c in self._discovered_cameras if not c.available
            ]

            self._discovery_complete = True

            by_source: dict[str, int] = {}
            for cam in self._discovered_cameras:
                by_source[cam.source] = by_source.get(cam.source, 0) + 1

            _LOGGER.info(
                "Options flow: Discovered %d cameras (%d available, %d unavailable) - %s",
                len(self._discovered_cameras),
                len(self._available_cameras),
                len(self._unavailable_cameras),
                ", ".join(f"{k}: {v}" for k, v in sorted(by_source.items())),
            )

        except Exception as err:
            _LOGGER.error("Options flow: Discovery failed: %s", err, exc_info=True)
            self._discovered_cameras = []
            self._available_cameras = []
            self._unavailable_cameras = []
            self._discovery_complete = True

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Camera selection."""
        if not self._discovery_complete:
            await self._run_discovery()

        all_cameras = self._discovered_cameras
        available_cameras = self._available_cameras
        unavailable_cameras = self._unavailable_cameras
        unavailable_names = [cam.friendly_name for cam in unavailable_cameras]

        current_exclude_unavailable = self._options.get(CONF_EXCLUDE_UNAVAILABLE, True)
        current_auto_groups = self._options.get(CONF_AUTO_GROUPS, True)

        if user_input is not None:
            exclude_unavailable = user_input.get(CONF_EXCLUDE_UNAVAILABLE, True)
            select_all = user_input.get(CONF_SELECT_ALL, False)

            if select_all:
                if exclude_unavailable:
                    selected_ids = [cam.id for cam in available_cameras]
                else:
                    selected_ids = [cam.id for cam in all_cameras]
            else:
                selected_ids = user_input.get(CONF_SELECTED_CAMERAS, [])

            if exclude_unavailable:
                unavailable_ids = {cam.id for cam in unavailable_cameras}
                selected_ids = [
                    cam_id for cam_id in selected_ids if cam_id not in unavailable_ids
                ]

            self._options[CONF_SELECTED_CAMERAS] = selected_ids
            self._options[CONF_EXCLUDE_UNAVAILABLE] = exclude_unavailable
            self._options[CONF_AUTO_GROUPS] = user_input.get(CONF_AUTO_GROUPS, True)

            # Go to next step
            return await self.async_step_connection()

        # Build camera selection options
        camera_options: dict[str, str] = {}

        if current_exclude_unavailable:
            cameras_to_show = available_cameras
        else:
            cameras_to_show = all_cameras

        for cam in cameras_to_show:
            label = f"{cam.friendly_name} ({cam.source})"

            badges = []
            if cam.is_new:
                badges.append("✨ NEW")
            if not cam.available:
                badges.append("⚠️ OFFLINE")

            if badges:
                label = f"{label} {' '.join(badges)}"

            camera_options[cam.id] = label

        # Determine default selection
        current_selected = self._options.get(CONF_SELECTED_CAMERAS)

        if current_selected is None:
            default_selected = [cam.id for cam in cameras_to_show]
        else:
            if current_exclude_unavailable:
                unavailable_ids = {cam.id for cam in unavailable_cameras}
                default_selected = [
                    cam_id
                    for cam_id in current_selected
                    if cam_id not in unavailable_ids and cam_id in camera_options
                ]
            else:
                all_ids = {cam.id for cam in all_cameras}
                default_selected = [
                    cam_id for cam_id in current_selected if cam_id in all_ids
                ]

        by_source: dict[str, int] = {}
        for cam in all_cameras:
            by_source[cam.source] = by_source.get(cam.source, 0) + 1
        source_summary = ", ".join(
            f"{source}: {count}" for source, count in sorted(by_source.items())
        )

        unavailable_list = _format_unavailable_cameras_list(unavailable_names)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SELECT_ALL,
                        default=False,
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_SELECTED_CAMERAS,
                        default=default_selected,
                    ): cv.multi_select(camera_options),
                    vol.Optional(
                        CONF_EXCLUDE_UNAVAILABLE,
                        default=current_exclude_unavailable,
                    ): BooleanSelector(),
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
                "source_summary": source_summary or "No cameras discovered",
                "unavailable_cameras": unavailable_list,
            },
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Connection settings (Frigate version, URL, output path)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate output path
            output_path = user_input.get(CONF_OUTPUT_PATH, "")
            if output_path and not output_path.endswith((".yml", ".yaml")):
                errors[CONF_OUTPUT_PATH] = "invalid_path"

            # Validate Frigate URL
            frigate_url = user_input.get(CONF_FRIGATE_URL)
            if frigate_url and not frigate_url.startswith(("http://", "https://")):
                errors[CONF_FRIGATE_URL] = "invalid_url"

            if not errors:
                # Store data updates (these go to config_entry.data, not options)
                if CONF_FRIGATE_VERSION in user_input:
                    self._data_updates[CONF_FRIGATE_VERSION] = user_input[CONF_FRIGATE_VERSION]
                if CONF_OUTPUT_PATH in user_input:
                    self._data_updates[CONF_OUTPUT_PATH] = user_input[CONF_OUTPUT_PATH]
                if CONF_FRIGATE_URL in user_input:
                    self._data_updates[CONF_FRIGATE_URL] = user_input.get(CONF_FRIGATE_URL)
                if CONF_AUTO_PUSH in user_input:
                    self._data_updates[CONF_AUTO_PUSH] = user_input.get(CONF_AUTO_PUSH, False)

                return await self.async_step_features()

        # Current values from config_entry.data
        current_version = self._config_entry.data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
        current_output = self._config_entry.data.get(CONF_OUTPUT_PATH, DEFAULT_OUTPUT_PATH)
        current_url = self._config_entry.data.get(CONF_FRIGATE_URL, "")
        current_auto_push = self._config_entry.data.get(CONF_AUTO_PUSH, False)

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FRIGATE_VERSION,
                        default=current_version,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "0.14", "label": "Frigate 0.14.x (Stable)"},
                                {"value": "0.17", "label": "Frigate 0.17.x (Latest)"},
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_OUTPUT_PATH,
                        default=current_output,
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Optional(
                        CONF_FRIGATE_URL,
                        description={"suggested_value": current_url},
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    vol.Optional(
                        CONF_AUTO_PUSH,
                        default=current_auto_push,
                    ): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Feature settings."""
        if user_input is not None:
            # Store feature settings in data_updates
            for key in [
                CONF_AUDIO_DETECTION,
                CONF_FACE_RECOGNITION,
                CONF_FACE_RECOGNITION_MODEL,
                CONF_SEMANTIC_SEARCH,
                CONF_SEMANTIC_SEARCH_MODEL,
                CONF_LPR,
                CONF_LPR_MODEL,
                CONF_BIRD_CLASSIFICATION,
                CONF_BIRDSEYE_ENABLED,
                CONF_BIRDSEYE_MODE,
                CONF_GENAI_ENABLED,
            ]:
                if key in user_input:
                    self._data_updates[key] = user_input[key]

            # Check if we need GenAI step
            frigate_version = self._data_updates.get(
                CONF_FRIGATE_VERSION, 
                self._config_entry.data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
            )
            if frigate_version == "0.17" and user_input.get(CONF_GENAI_ENABLED, False):
                return await self.async_step_genai()

            return await self.async_step_retention()

        # Current values from config_entry.data
        data = self._config_entry.data
        
        # Determine Frigate version (prefer update if set)
        frigate_version = self._data_updates.get(
            CONF_FRIGATE_VERSION, 
            data.get(CONF_FRIGATE_VERSION, DEFAULT_FRIGATE_VERSION)
        )
        is_017 = frigate_version == "0.17"
        default_lpr_model = get_default_lpr_model(frigate_version)

        # Build schema based on Frigate version
        schema_dict = {
            vol.Optional(
                CONF_AUDIO_DETECTION,
                default=data.get(CONF_AUDIO_DETECTION, True),
            ): BooleanSelector(),
            vol.Optional(
                CONF_FACE_RECOGNITION,
                default=data.get(CONF_FACE_RECOGNITION, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_FACE_RECOGNITION_MODEL,
                default=data.get(CONF_FACE_RECOGNITION_MODEL, DEFAULT_MODEL_SIZE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SEMANTIC_SEARCH,
                default=data.get(CONF_SEMANTIC_SEARCH, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_SEMANTIC_SEARCH_MODEL,
                default=data.get(CONF_SEMANTIC_SEARCH_MODEL, DEFAULT_MODEL_SIZE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_LPR,
                default=data.get(CONF_LPR, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_LPR_MODEL,
                default=data.get(CONF_LPR_MODEL, default_lpr_model),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=MODEL_SIZES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_BIRD_CLASSIFICATION,
                default=data.get(CONF_BIRD_CLASSIFICATION, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_BIRDSEYE_ENABLED,
                default=data.get(CONF_BIRDSEYE_ENABLED, True),
            ): BooleanSelector(),
            vol.Optional(
                CONF_BIRDSEYE_MODE,
                default=data.get(CONF_BIRDSEYE_MODE, DEFAULT_BIRDSEYE_MODE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=BIRDSEYE_MODES,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # Add GenAI option for Frigate 0.17+
        if is_017:
            schema_dict[vol.Optional(
                CONF_GENAI_ENABLED,
                default=data.get(CONF_GENAI_ENABLED, False),
            )] = BooleanSelector()

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "frigate_version": frigate_version,
            },
        )

    async def async_step_genai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3b: GenAI settings (Frigate 0.17+ only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            provider = user_input.get(CONF_GENAI_PROVIDER, DEFAULT_GENAI_PROVIDER)
            
            # Validate API key for cloud providers
            if provider in ("gemini", "openai", "azure_openai"):
                if not user_input.get(CONF_GENAI_API_KEY):
                    errors[CONF_GENAI_API_KEY] = "required"
            
            # Validate base URL for Azure OpenAI
            if provider == "azure_openai":
                if not user_input.get(CONF_GENAI_BASE_URL):
                    errors[CONF_GENAI_BASE_URL] = "required"

            if not errors:
                # Store GenAI settings
                for key in [
                    CONF_GENAI_PROVIDER,
                    CONF_GENAI_MODEL,
                    CONF_GENAI_API_KEY,
                    CONF_GENAI_BASE_URL,
                ]:
                    if key in user_input:
                        self._data_updates[key] = user_input[key]
                
                return await self.async_step_retention()

        # Current values
        data = self._config_entry.data

        return self.async_show_form(
            step_id="genai",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GENAI_PROVIDER,
                        default=data.get(CONF_GENAI_PROVIDER, DEFAULT_GENAI_PROVIDER),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in GENAI_PROVIDER_OPTIONS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_GENAI_MODEL,
                        description={"suggested_value": data.get(CONF_GENAI_MODEL, "")},
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_GENAI_API_KEY,
                        description={"suggested_value": data.get(CONF_GENAI_API_KEY, "")},
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(
                        CONF_GENAI_BASE_URL,
                        description={"suggested_value": data.get(CONF_GENAI_BASE_URL, "")},
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "provider_help": "Ollama runs locally. Cloud providers require API keys.",
            },
        )

    async def async_step_retention(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 4: Retention settings - final step."""
        if user_input is not None:
            # Store retention settings in data_updates
            for key in [
                CONF_RETAIN_ALERTS,
                CONF_RETAIN_DETECTIONS,
                CONF_RETAIN_MOTION,
                CONF_RETAIN_SNAPSHOTS,
            ]:
                if key in user_input:
                    self._data_updates[key] = user_input[key]

            # Now save everything
            # Update config_entry.data with data_updates
            if self._data_updates:
                new_data = {**self._config_entry.data, **self._data_updates}
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=new_data,
                )

            # Return options (camera selection, exclude_unavailable, auto_groups)
            return self.async_create_entry(title="", data=self._options)

        # Current values from config_entry.data
        data = self._config_entry.data

        return self.async_show_form(
            step_id="retention",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_RETAIN_ALERTS,
                        default=data.get(CONF_RETAIN_ALERTS, DEFAULT_RETAIN_ALERTS),
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
                        default=data.get(CONF_RETAIN_DETECTIONS, DEFAULT_RETAIN_DETECTIONS),
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
                        default=data.get(CONF_RETAIN_MOTION, DEFAULT_RETAIN_MOTION),
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
                        default=data.get(CONF_RETAIN_SNAPSHOTS, DEFAULT_RETAIN_SNAPSHOTS),
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
        )
