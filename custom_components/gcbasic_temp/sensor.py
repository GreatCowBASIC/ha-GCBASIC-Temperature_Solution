"""Sensor platform that queries a GC-BASIC device over serial for temperature.

The device is request/response: it only replies with a temperature reading
after receiving a query character (default 't'). The built-in HA 'serial'
platform can only listen passively, so it can't drive this protocol.
"""
from __future__ import annotations

import logging

import serial
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_QUERY_CHAR = "query_char"

DEFAULT_NAME = "GCBASIC Temperature"
DEFAULT_BAUDRATE = 9600
DEFAULT_QUERY_CHAR = "t"
SERIAL_TIMEOUT = 2

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SERIAL_PORT): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
        vol.Optional(CONF_QUERY_CHAR, default=DEFAULT_QUERY_CHAR): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the GC-BASIC temperature sensor."""
    add_entities(
        [
            GcBasicTempSensor(
                config[CONF_SERIAL_PORT],
                config[CONF_BAUDRATE],
                config[CONF_QUERY_CHAR],
                config[CONF_NAME],
            )
        ],
        True,
    )


class GcBasicTempSensor(SensorEntity):
    """Representation of a GC-BASIC temperature sensor queried over serial."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, port: str, baudrate: int, query_char: str, name: str) -> None:
        self._port = port
        self._baudrate = baudrate
        self._query_char = query_char.encode()
        self._attr_name = name
        self._attr_unique_id = f"gcbasic_temp_{port}"
        self._serial: serial.Serial | None = None

    def _ensure_connected(self) -> None:
        if self._serial is not None and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=SERIAL_TIMEOUT,
        )

    def update(self) -> None:
        """Query the device and parse the reply. Runs in HA's executor thread."""
        try:
            self._ensure_connected()
            self._serial.reset_input_buffer()
            self._serial.write(self._query_char)
            lines = []
            while True:
                raw = self._serial.readline().decode("ascii", errors="ignore").strip()
                if not raw:
                    break
                lines.append(raw)
            if not lines:
                _LOGGER.warning("No response from %s within timeout", self._port)
                return
            temp_lines = [l for l in lines if l.startswith(("+", "-"))]
            if not temp_lines:
                _LOGGER.error(
                    "No temperature line (starting with '+' or '-') from %s. Raw response: %r",
                    self._port,
                    lines,
                )
                self._attr_available = False
                return
            try:
                self._attr_native_value = float(temp_lines[-1])
                self._attr_available = True
            except ValueError:
                _LOGGER.error(
                    "Could not parse temperature line %r from %s",
                    temp_lines[-1],
                    self._port,
                )
                self._attr_available = False
        except serial.SerialException as err:
            _LOGGER.error("Error reading from %s: %s", self._port, err)
            self._attr_available = False
            if self._serial is not None:
                self._serial.close()
            self._serial = None
