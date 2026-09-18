"""Async serial client for the GCBASIC CDC/USB terminal device."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import re

import serial_asyncio_fast as serial_asyncio

from .const import (
    CMD_ALL_OFF,
    CMD_ALL_ON,
    CMD_PROBE,
    CMD_QUERY_STATUS,
    CMD_QUERY_TEMP,
    LED_COMMANDS,
    LED_NUMBERS,
)

_LOGGER = logging.getLogger(__name__)

_LED_RE = re.compile(r"LED([1-4])=(ON|OFF)", re.IGNORECASE)
_ADC_RE = re.compile(r"ADC=(\d+)", re.IGNORECASE)
_TEMP_KV_RE = re.compile(r"^TEMP=([+-]?\d+(?:\.\d+)?)", re.IGNORECASE)
_TEMP_BARE_RE = re.compile(r"^[+-]\d+(?:\.\d+)?$")


@dataclass
class CdcState:
    """Last known state of the device, built up from parsed reply lines."""

    leds: dict[int, bool] = field(default_factory=lambda: {n: False for n in LED_NUMBERS})
    adc_raw: int | None = None
    temperature_raw: float | None = None


class CdcUsbClient:
    """Owns the serial connection and speaks the device's wire protocol."""

    def __init__(self, port: str, baudrate: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._read_task: asyncio.Task | None = None
        self.state = CdcState()

    @property
    def is_connected(self) -> bool:
        return self._writer is not None

    async def async_connect(self) -> None:
        """Open the serial port and start the background read loop."""
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self._port, baudrate=self._baudrate
        )
        self._read_task = asyncio.create_task(self._read_loop())

    async def async_disconnect(self) -> None:
        if self._read_task is not None:
            self._read_task.cancel()
            self._read_task = None
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        self._reader = None

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while True:
                raw = await self._reader.readline()
                if not raw:
                    # EOF - the port went away (device unplugged).
                    break
                line = raw.decode("ascii", errors="ignore").strip()
                if line:
                    self._parse_line(line)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - any I/O error means the link is dead
            _LOGGER.debug("CDC USB read loop for %s ended", self._port, exc_info=True)
        finally:
            self._writer = None
            self._reader = None

    def _parse_line(self, line: str) -> None:
        for match in _LED_RE.finditer(line):
            led = int(match.group(1))
            self.state.leds[led] = match.group(2).upper() == "ON"

        adc_match = _ADC_RE.search(line)
        if adc_match:
            self.state.adc_raw = int(adc_match.group(1))

        temp_match = _TEMP_KV_RE.match(line)
        if temp_match:
            self.state.temperature_raw = float(temp_match.group(1))
        elif "=" not in line and _TEMP_BARE_RE.match(line):
            self.state.temperature_raw = float(line)

    async def _async_send(self, char: str) -> None:
        if self._writer is None:
            raise ConnectionError(f"CDC USB device on {self._port} is not connected")
        self._writer.write(char.encode("ascii"))
        await self._writer.drain()

    async def async_probe(self) -> None:
        await self._async_send(CMD_PROBE)

    async def async_query_temperature(self) -> None:
        await self._async_send(CMD_QUERY_TEMP)

    async def async_query_status(self) -> None:
        await self._async_send(CMD_QUERY_STATUS)

    async def async_all_on(self) -> None:
        await self._async_send(CMD_ALL_ON)

    async def async_all_off(self) -> None:
        await self._async_send(CMD_ALL_OFF)

    async def async_toggle_led(self, led: int) -> None:
        await self._async_send(LED_COMMANDS[led])
