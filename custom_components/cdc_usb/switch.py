"""Switch entities for the CDC USB Terminal integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LED_NUMBERS
from .coordinator import CdcUsbCoordinator
from .entity import CdcUsbEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CdcUsbCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [CdcLedSwitch(coordinator, entry, led) for led in LED_NUMBERS]
    entities.append(CdcDataLoggingSwitch(coordinator, entry))
    async_add_entities(entities)


class CdcLedSwitch(CdcUsbEntity, SwitchEntity):
    """One of the 4 toggleable LEDs.

    The device protocol only exposes a *toggle* command per LED (no
    explicit on/off), so turn_on/turn_off first check the last known state
    and only send the toggle if it actually needs to change, then confirm
    against the device's reply instead of assuming the toggle worked.
    """

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry, led: int) -> None:
        super().__init__(coordinator, entry)
        self._led = led
        self._attr_unique_id = f"{entry.entry_id}_led{led}"
        self._attr_name = f"LED {led}"
        self._attr_icon = "mdi:led-on"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.leds.get(self._led, False)

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set(False)

    async def _async_set(self, desired: bool) -> None:
        if self.is_on == desired:
            return
        await self.coordinator.client.async_toggle_led(self._led)
        await self.coordinator.async_nudge()
        if self.is_on != desired:
            # The toggle didn't self-report a new state in time - ask.
            await self.coordinator.client.async_query_status()
            await self.coordinator.async_nudge()


class CdcDataLoggingSwitch(CdcUsbEntity, SwitchEntity):
    """Mirrors the web UI's "Data Logging" toggle: pauses/resumes the
    coordinator's periodic t/x polling without touching manual commands.
    """

    _attr_name = "Data Logging"
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_logging"

    @property
    def is_on(self) -> bool:
        return self.coordinator.polling_enabled

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.polling_enabled = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.polling_enabled = False
        self.async_write_ha_state()
