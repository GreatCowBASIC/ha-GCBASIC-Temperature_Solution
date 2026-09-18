"""Data update coordinator for the CDC USB Terminal integration."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cdc_client import CdcState, CdcUsbClient
from .const import DOMAIN, REPLY_SETTLE_SECONDS

_LOGGER = logging.getLogger(__name__)


class CdcUsbCoordinator(DataUpdateCoordinator[CdcState]):
    """Polls the device (t then x, mirroring the desktop apps' "Data Logging")
    on a fixed interval, and lets entities push an out-of-band refresh right
    after they send a command so the UI reflects it quickly instead of
    waiting for the next scheduled poll.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: CdcUsbClient,
        scan_interval: int,
        temperature_adjustment: float,
        glitch_window: int,
        glitch_jump: float,
        glitch_band: float,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.temperature_adjustment = temperature_adjustment
        # Mirrors the "Data Logging" toggle in the web UI: when False the
        # scheduled poll is skipped, but manual commands/buttons still work.
        self.polling_enabled = True

        # Glitch rejection for the raw temperature reading, ported from the
        # older gcbasic_temp YAML sensor this integration supersedes: a big
        # jump off the last trusted reading is held back unless the last
        # glitch_window raw readings already cluster within glitch_band of
        # it, confirming it's a real trend rather than a one-off spike.
        self._glitch_jump = glitch_jump
        self._glitch_band = glitch_band
        self._glitch_window = glitch_window
        self._temp_history: deque[float] = deque(maxlen=glitch_window)
        self._last_trusted_temp: float | None = None
        self._last_raw_seen: float | None = None

    async def _async_update_data(self) -> CdcState:
        if not self.client.is_connected:
            try:
                await self.client.async_connect()
            except Exception as err:
                raise UpdateFailed(f"Unable to open serial port: {err}") from err

        if not self.polling_enabled:
            return self.client.state

        try:
            await self.client.async_query_temperature()
            await asyncio.sleep(REPLY_SETTLE_SECONDS)
            await self.client.async_query_status()
            await asyncio.sleep(REPLY_SETTLE_SECONDS)
        except ConnectionError as err:
            raise UpdateFailed(str(err)) from err

        return self.client.state

    async def async_nudge(self, delay: float = REPLY_SETTLE_SECONDS) -> None:
        """Give the device a moment to reply after a command, then push the
        latest (already-parsed) client state out to entities.
        """
        await asyncio.sleep(delay)
        self.async_set_updated_data(self.client.state)

    def set_temperature_adjustment(self, value: float) -> None:
        self.temperature_adjustment = value
        self.async_set_updated_data(self.client.state)

    def _is_temp_trending_toward(self, value: float) -> bool:
        if len(self._temp_history) < self._glitch_window:
            return False
        return all(abs(v - value) <= self._glitch_band for v in self._temp_history)

    def get_filtered_temperature(self) -> float | None:
        """Return the last trusted raw temperature, applying glitch rejection
        to any new raw reading that has arrived since the last call.
        """
        raw = self.client.state.temperature_raw
        if raw is None:
            return self._last_trusted_temp

        if raw != self._last_raw_seen:
            self._last_raw_seen = raw
            if (
                self._last_trusted_temp is not None
                and abs(raw - self._last_trusted_temp) > self._glitch_jump
                and not self._is_temp_trending_toward(raw)
            ):
                _LOGGER.debug(
                    "Ignoring out-of-trend temperature reading %.2f "
                    "(last trusted %.2f, recent raw readings %s)",
                    raw,
                    self._last_trusted_temp,
                    list(self._temp_history),
                )
            else:
                self._last_trusted_temp = raw
            self._temp_history.append(raw)

        return self._last_trusted_temp
