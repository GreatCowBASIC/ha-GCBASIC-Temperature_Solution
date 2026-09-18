"""Button entities for the CDC USB Terminal integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
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
            CdcQueryTemperatureButton(coordinator, entry),
            CdcQueryStatusButton(coordinator, entry),
            CdcAllOnButton(coordinator, entry),
            CdcAllOffButton(coordinator, entry),
        ]
    )


class _CdcCommandButton(CdcUsbEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: CdcUsbCoordinator,
        entry: ConfigEntry,
        name: str,
        unique_suffix: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_icon = icon

    async def _async_send(self) -> None:
        raise NotImplementedError

    async def async_press(self) -> None:
        await self._async_send()
        await self.coordinator.async_nudge()


class CdcQueryTemperatureButton(_CdcCommandButton):
    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "Query Temperature", "query_temp", "mdi:thermometer")

    async def _async_send(self) -> None:
        await self.coordinator.client.async_query_temperature()


class CdcQueryStatusButton(_CdcCommandButton):
    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "Query Status/ADC", "query_status", "mdi:refresh")

    async def _async_send(self) -> None:
        await self.coordinator.client.async_query_status()


class CdcAllOnButton(_CdcCommandButton):
    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "All LEDs On", "all_on", "mdi:lightbulb-group")

    async def _async_send(self) -> None:
        await self.coordinator.client.async_all_on()


class CdcAllOffButton(_CdcCommandButton):
    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "All LEDs Off", "all_off", "mdi:lightbulb-group-off")

    async def _async_send(self) -> None:
        await self.coordinator.client.async_all_off()
