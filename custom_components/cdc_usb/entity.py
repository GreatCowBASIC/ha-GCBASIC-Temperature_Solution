"""Common entity base for the CDC USB Terminal platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CdcUsbCoordinator


class CdcUsbEntity(CoordinatorEntity[CdcUsbCoordinator]):
    """Base class wiring every entity to the same device and coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CdcUsbCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="CDC USB Terminal",
            manufacturer="GCBASIC",
            model="CDC/USB Terminal (1209:2008)",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.client.is_connected
