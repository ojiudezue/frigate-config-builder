"""Output handlers for Frigate Config Builder."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def write_config_file(hass: HomeAssistant, output_path: str, config_yaml: str) -> None:
    """Write the generated Frigate config to a file.

    Args:
        hass: Home Assistant instance
        output_path: Path to write the config file
        config_yaml: YAML string to write

    Raises:
        OSError: If the file cannot be written
    """
    path = Path(output_path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(config_yaml)
        _LOGGER.info("Wrote Frigate config to %s", output_path)
    except OSError as err:
        _LOGGER.error("Failed to write Frigate config to %s: %s", output_path, err)
        raise


async def push_to_frigate(
    frigate_url: str,
    config_yaml: str,
    restart: bool = True,
) -> bool:
    """Push configuration to Frigate API and optionally restart.

    Args:
        frigate_url: Frigate API base URL (e.g., http://192.168.1.100:5000)
        config_yaml: YAML configuration string
        restart: Whether to restart Frigate after pushing config

    Returns:
        True if successful, False otherwise
    """
    import aiohttp

    # Normalize URL
    base_url = frigate_url.rstrip("/")
    config_url = f"{base_url}/api/config/save"
    restart_url = f"{base_url}/api/restart"

    try:
        async with aiohttp.ClientSession() as session:
            # Push config
            _LOGGER.debug("Pushing config to Frigate at %s", config_url)
            async with session.post(
                config_url,
                data=config_yaml,
                headers={"Content-Type": "text/plain"},
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Failed to push config to Frigate: %s - %s",
                        response.status,
                        error_text,
                    )
                    return False

            # Restart if requested
            if restart:
                _LOGGER.debug("Restarting Frigate at %s", restart_url)
                async with session.post(restart_url) as response:
                    if response.status != 200:
                        _LOGGER.warning(
                            "Config pushed but restart failed: %s",
                            response.status,
                        )
                        return False

            _LOGGER.info("Successfully pushed config to Frigate and restarted")
            return True

    except aiohttp.ClientError as err:
        _LOGGER.error("Failed to connect to Frigate API: %s", err)
        return False
