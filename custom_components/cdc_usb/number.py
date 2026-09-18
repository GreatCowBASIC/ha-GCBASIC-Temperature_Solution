"""Number entities for the CDC USB Terminal integration.

These mirror the two client-side settings in the web UI's settings popup
(logging period, temperature adjustment) - values the device itself has no
concept of, so they live purely in Home Assistant and are restored across
restarts via RestoreEntity rather than read back from the hardware.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import CdcUsbCoordinator
from .entity import CdcUsbEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CdcUsbCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CdcTempAdjustmentNumber(coordinator, entry),
            CdcLogPeriodNumber(coordinator, entry),
        ]
    )


class CdcTempAdjustmentNumber(CdcUsbEntity, NumberEntity, RestoreEntity):
    _attr_name = "Temperature Adjustment"
    _attr_native_min_value = -10
    _attr_native_max_value = 10
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:thermometer-lines"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_temp_adjustment"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self.coordinator.temperature_adjustment = float(last_state.state)
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        return self.coordinator.temperature_adjustment

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_temperature_adjustment(value)


class CdcLogPeriodNumber(CdcUsbEntity, NumberEntity):
    _attr_name = "Logging Period"
    _attr_native_min_value = 1
    _attr_native_max_value = 3600
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_log_period"

    @property
    def native_value(self) -> float:
        interval = self.coordinator.update_interval
        return interval.total_seconds() if interval else 0

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.update_interval = timedelta(seconds=value)
        self.async_write_ha_state()
