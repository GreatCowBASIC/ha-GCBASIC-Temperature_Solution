"""Sensor platform that queries a GC-BASIC device over serial for temperature.

The device is request/response: it only replies with a temperature reading
after receiving a query character (default 't'). The built-in HA 'serial'
platform can only listen passively, so it can't drive this protocol.
"""
from __future__ import annotations

import logging
from collections import deque

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
CONF_GLITCH_WINDOW = "glitch_window"
CONF_GLITCH_JUMP = "glitch_jump"
CONF_GLITCH_BAND = "glitch_band"

DEFAULT_NAME = "GCBASIC Temperature"
DEFAULT_BAUDRATE = 9600
DEFAULT_QUERY_CHAR = "t"
SERIAL_TIMEOUT = 2

# Real consecutive readings from this device move by a few hundredths of a
# degree at a time. A reading that jumps further than glitch_jump from the
# last trusted value is treated as a suspected glitch (garbled serial data
# can produce any wild value, not just 0.00) unless the last glitch_window
# raw readings already sit within glitch_band of it -- i.e. a real trend
# toward that value was already underway. All three are configurable per
# sensor since how "twitchy" a device is varies.
DEFAULT_GLITCH_WINDOW = 5
DEFAULT_GLITCH_JUMP = 3.0
DEFAULT_GLITCH_BAND = 1.0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SERIAL_PORT): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
        vol.Optional(CONF_QUERY_CHAR, default=DEFAULT_QUERY_CHAR): cv.string,
        vol.Optional(CONF_GLITCH_WINDOW, default=DEFAULT_GLITCH_WINDOW): cv.positive_int,
        vol.Optional(CONF_GLITCH_JUMP, default=DEFAULT_GLITCH_JUMP): vol.Coerce(float),
        vol.Optional(CONF_GLITCH_BAND, default=DEFAULT_GLITCH_BAND): vol.Coerce(float),
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
                config[CONF_GLITCH_WINDOW],
                config[CONF_GLITCH_JUMP],
                config[CONF_GLITCH_BAND],
            )
        ],
        True,
    )


class GcBasicTempSensor(SensorEntity):
    """Representation of a GC-BASIC temperature sensor queried over serial."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        port: str,
        baudrate: int,
        query_char: str,
        name: str,
        glitch_window: int,
        glitch_jump: float,
        glitch_band: float,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._query_char = query_char.encode()
        self._attr_name = name
        self._attr_unique_id = f"gcbasic_temp_{port}"
        self._serial: serial.Serial | None = None
        self._glitch_window = glitch_window
        self._glitch_jump = glitch_jump
        self._glitch_band = glitch_band
        self._history: deque[float] = deque(maxlen=glitch_window)
        self._last_trusted_value: float | None = None

    def _ensure_connected(self) -> None:
        if self._serial is not None and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=SERIAL_TIMEOUT,
        )

    def _is_trending_toward(self, value: float) -> bool:
        """True if the last glitch_window readings were already close to value."""
        if len(self._history) < self._glitch_window:
            return False
        return all(abs(v - value) <= self._glitch_band for v in self._history)

    def _filter_glitch(self, raw_value: float) -> float:
        """Return the value to report to HA, substituting sudden glitch readings.

        Any reading that jumps more than glitch_jump away from the last
        trusted value is only trusted if recent history was already trending
        toward it. Otherwise it's treated as a glitch (garbled serial data,
        which can land on 0.00 or any other stray value) and the last known
        trusted reading is reported instead.
        """
        if (
            self._last_trusted_value is not None
            and abs(raw_value - self._last_trusted_value) > self._glitch_jump
            and not self._is_trending_toward(raw_value)
        ):
            _LOGGER.warning(
                "Ignoring out-of-trend reading %.2f from %s "
                "(last trusted value %.2f, recent readings %s); "
                "reporting last known value instead",
                raw_value,
                self._port,
                self._last_trusted_value,
                list(self._history),
            )
            return self._last_trusted_value

        self._last_trusted_value = raw_value
        return raw_value

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
                raw_value = float(temp_lines[-1])
            except ValueError:
                _LOGGER.error(
                    "Could not parse temperature line %r from %s",
                    temp_lines[-1],
                    self._port,
                )
                self._attr_available = False
                return

            self._attr_native_value = self._filter_glitch(raw_value)
            # Track raw sensor readings (not the filtered value) so a genuine
            # trend toward a new value is still detected while a glitch is
            # suppressed.
            self._history.append(raw_value)
            self._attr_available = True
        except serial.SerialException as err:
            _LOGGER.error("Error reading from %s: %s", self._port, err)
            self._attr_available = False
            if self._serial is not None:
                self._serial.close()
            self._serial = None
