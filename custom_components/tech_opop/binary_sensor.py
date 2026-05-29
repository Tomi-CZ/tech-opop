"""Platform for binary sensor integration."""

import logging

from homeassistant.components import binary_sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PARAMS,
    CONF_TYPE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import assets
from .coordinator import TechCoordinator
from .const import (
    DOMAIN,
    TYPE_ADDITIONAL_PUMP,
    TYPE_FIRE_SENSOR,
    TYPE_RELAY,
    VISIBILITY,
)
from .entity import TileEntity

_LOGGER = logging.getLogger(__name__)

_BINARY_TILE_TYPES = {
    TYPE_RELAY: None,
    TYPE_ADDITIONAL_PUMP: None,
    TYPE_FIRE_SENSOR: binary_sensor.BinarySensorDeviceClass.HEAT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech binary sensor entities."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    tiles = coordinator.data.get("tiles", {})

    entities = [
        RelaySensor(tile, coordinator, config_entry, _BINARY_TILE_TYPES[tile[CONF_TYPE]])
        for tile in tiles.values()
        if tile.get(VISIBILITY) and tile[CONF_TYPE] in _BINARY_TILE_TYPES
    ]
    async_add_entities(entities, True)


class TileBinarySensor(TileEntity, binary_sensor.BinarySensorEntity):
    """Base class for Tech tiles that expose binary sensor semantics."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def get_state(self, device):
        """Return the raw binary state."""

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_binary_sensor"

    @property
    def is_on(self) -> bool | None:
        return bool(self._state) if self._state is not None else None


class RelaySensor(TileBinarySensor):
    """Binary sensor backed by a relay/pump/fire tile."""

    def __init__(self, device, coordinator: TechCoordinator, config_entry, device_class=None) -> None:
        """Initialize the relay sensor."""
        super().__init__(device, coordinator, config_entry)
        self._attr_device_class = device_class
        icon_id = device[CONF_PARAMS].get("iconId")
        self._attr_icon = assets.get_icon(icon_id) if icon_id else assets.get_icon_by_type(device[CONF_TYPE])

    def get_state(self, device):
        return device[CONF_PARAMS].get("workingStatus")
