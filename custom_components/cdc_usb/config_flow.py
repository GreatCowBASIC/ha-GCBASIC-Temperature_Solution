"""Config flow for the CDC USB Terminal integration."""
from __future__ import annotations

import logging
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PORT
from homeassistant.helpers.service_info.usb import UsbServiceInfo

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

_LOGGER = logging.getLogger(__name__)


async def _async_probe(port: str, baudrate: int) -> None:
    """Open the port and send the harmless '?' probe command."""
    client = CdcUsbClient(port, baudrate)
    await client.async_connect()
    try:
        await client.async_probe()
    finally:
        await client.async_disconnect()


class CdcUsbConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CDC USB Terminal."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_port: str | None = None

    async def async_step_usb(self, discovery_info: UsbServiceInfo) -> ConfigFlowResult:
        """Handle automatic discovery of a 1209:2008 USB-CDC device."""
        await self.async_set_unique_id(discovery_info.device)
        self._abort_if_unique_id_configured()
        self._discovered_port = discovery_info.device
        self.context["title_placeholders"] = {"port": discovery_info.device}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._discovered_port is not None

        if user_input is not None:
            try:
                await _async_probe(self._discovered_port, DEFAULT_BAUD_RATE)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Probe of discovered port failed", exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"CDC USB ({self._discovered_port})",
                    data={
                        CONF_PORT: self._discovered_port,
                        CONF_BAUD_RATE: DEFAULT_BAUD_RATE,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        CONF_TEMP_ADJUSTMENT: DEFAULT_TEMP_ADJUSTMENT,
                        CONF_GLITCH_WINDOW: DEFAULT_GLITCH_WINDOW,
                        CONF_GLITCH_JUMP: DEFAULT_GLITCH_JUMP,
                        CONF_GLITCH_BAND: DEFAULT_GLITCH_BAND,
                    },
                )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"port": self._discovered_port},
            errors=errors,
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        port_options = {p.device: f"{p.device} - {p.description}" for p in ports}

        if user_input is not None:
            port = user_input[CONF_PORT]
            baudrate = user_input[CONF_BAUD_RATE]

            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()

            try:
                await _async_probe(port, baudrate)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Probe of %s failed", port, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"CDC USB ({port})",
                    data={
                        CONF_PORT: port,
                        CONF_BAUD_RATE: baudrate,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                        CONF_TEMP_ADJUSTMENT: user_input[CONF_TEMP_ADJUSTMENT],
                        CONF_GLITCH_WINDOW: user_input[CONF_GLITCH_WINDOW],
                        CONF_GLITCH_JUMP: user_input[CONF_GLITCH_JUMP],
                        CONF_GLITCH_BAND: user_input[CONF_GLITCH_BAND],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_PORT): vol.In(port_options) if port_options else str,
                vol.Required(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE): int,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=1, max=3600)
                ),
                vol.Required(CONF_TEMP_ADJUSTMENT, default=DEFAULT_TEMP_ADJUSTMENT): vol.Coerce(float),
                vol.Required(CONF_GLITCH_WINDOW, default=DEFAULT_GLITCH_WINDOW): vol.All(
                    int, vol.Range(min=1, max=60)
                ),
                vol.Required(CONF_GLITCH_JUMP, default=DEFAULT_GLITCH_JUMP): vol.Coerce(float),
                vol.Required(CONF_GLITCH_BAND, default=DEFAULT_GLITCH_BAND): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> CdcUsbOptionsFlow:
        return CdcUsbOptionsFlow(config_entry)


class CdcUsbOptionsFlow(config_entries.OptionsFlow):
    """Let the polling interval be changed after setup without re-adding the device."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(int, vol.Range(min=1, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
