"""The CDC USB Terminal integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .cdc_client import CdcUsbClient
from .const import (
    CONF_BAUD_RATE,
    CONF_GLITCH_BAND,
    CONF_GLITCH_JUMP,
    CONF_GLITCH_WINDOW,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_ADJUSTMENT,
    DEFAULT_BAUD_RATE,
    DEFAULT_GLITCH_BAND,
    DEFAULT_GLITCH_JUMP,
    DEFAULT_GLITCH_WINDOW,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMP_ADJUSTMENT,
    DOMAIN,
)
from .coordinator import CdcUsbCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SENSOR, Platform.BUTTON, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data[CONF_PORT]
    baudrate = entry.data.get(CONF_BAUD_RATE, DEFAULT_BAUD_RATE)
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    temp_adjustment = entry.data.get(CONF_TEMP_ADJUSTMENT, DEFAULT_TEMP_ADJUSTMENT)
    glitch_window = entry.data.get(CONF_GLITCH_WINDOW, DEFAULT_GLITCH_WINDOW)
    glitch_jump = entry.data.get(CONF_GLITCH_JUMP, DEFAULT_GLITCH_JUMP)
    glitch_band = entry.data.get(CONF_GLITCH_BAND, DEFAULT_GLITCH_BAND)

    client = CdcUsbClient(port, baudrate)

    try:
        await client.async_connect()
    except Exception as err:
        raise ConfigEntryNotReady(f"Could not open {port}: {err}") from err

    coordinator = CdcUsbCoordinator(
        hass, client, scan_interval, temp_adjustment, glitch_window, glitch_jump, glitch_band
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: CdcUsbCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.async_disconnect()
    return unload_ok
