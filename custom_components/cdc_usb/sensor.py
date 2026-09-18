"""Sensor entities for the CDC USB Terminal integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CdcUsbCoordinator
from .entity import CdcUsbEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CdcUsbCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CdcTemperatureSensor(coordinator, entry),
            CdcPotentiometerSensor(coordinator, entry),
        ]
    )


class CdcTemperatureSensor(CdcUsbEntity, SensorEntity):
    """Glitch-filtered temperature reading: a raw jump bigger than
    glitch_jump is held back at the last trusted value unless the last
    glitch_window raw readings already cluster within glitch_band of it,
    confirming a real trend rather than a one-off spike. Ported from the
    older gcbasic_temp YAML sensor this integration supersedes.
    """

    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_temperature"

    @property
    def native_value(self) -> float | None:
        filtered = self.coordinator.get_filtered_temperature()
        if filtered is None:
            return None
        return round(filtered + self.coordinator.temperature_adjustment, 1)


class CdcPotentiometerSensor(CdcUsbEntity, SensorEntity):
    """Raw 0-255 ADC reading. The web UI's 0K-10K scaling is exposed as an
    extra attribute rather than the primary state, since it's a display
    convenience, not a physical unit the device reports.
    """

    _attr_name = "Potentiometer"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:knob"

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_adc"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.adc_raw

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        raw = self.coordinator.data.adc_raw
        if raw is None:
            return None
        return {"scaled_kohm": round((raw / 255) * 10, 1)}
