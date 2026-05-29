"""Platform for number entities backed by Tech menu parameters."""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import assets
from .const import (
    DOMAIN,
    MENU_ITEM_TYPE_UNIVERSAL_VALUE,
    MENU_ITEM_TYPE_VALUE,
    VALUE_FORMAT_TENTH,
)
from .coordinator import TechCoordinator
from .menu_entity import MenuEntity
from .tech import TechDuringChangeError

_LOGGER = logging.getLogger(__name__)

_EDITABLE_TYPES = MENU_ITEM_TYPE_VALUE | {MENU_ITEM_TYPE_UNIVERSAL_VALUE}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech number entities from menu parameters."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    menus = coordinator.data.get("menus", {})
    group_names = assets.build_menu_group_names(menus)

    entities = [
        MenuNumberEntity(item, key, coordinator, config_entry, group_names)
        for key, item in menus.items()
        if item.get("type") in _EDITABLE_TYPES
        and item.get("access", False)
    ]
    async_add_entities(entities, True)


class MenuNumberEntity(MenuEntity, NumberEntity):
    """A numeric menu parameter exposed as a Home Assistant number."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        item: dict[str, Any],
        menu_key: str,
        coordinator: TechCoordinator,
        config_entry: ConfigEntry,
        group_names: dict[tuple[str, int], str],
    ) -> None:
        """Initialise a menu number entity."""
        super().__init__(item, menu_key, coordinator, config_entry, group_names)
        self._update_from_item(item)

    def _update_from_item(self, item: dict[str, Any]) -> None:
        params = item.get("params", {})
        self._format = params.get("format", 1)
        raw = params.get("value", 0)
        raw_min = params.get("min", 0)
        raw_max = params.get("max", 100)
        step = params.get("jump", 1)
        if self._format == VALUE_FORMAT_TENTH:
            self._attr_native_value = raw / 10.0
            self._attr_native_min_value = raw_min / 10.0
            self._attr_native_max_value = raw_max / 10.0
            self._attr_native_step = step / 10.0
        else:
            self._attr_native_value = float(raw)
            self._attr_native_min_value = float(raw_min)
            self._attr_native_max_value = float(raw_max)
            self._attr_native_step = float(step)

    async def async_set_native_value(self, value: float) -> None:
        """Set the menu parameter to the requested value."""
        api_value = int(value * 10) if self._format == VALUE_FORMAT_TENTH else int(value)
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._item_id, {"value": api_value}
            )
        except TechDuringChangeError:
            raise HomeAssistantError(
                translation_domain="tech_opop", translation_key="during_change"
            )
        await self.coordinator.async_request_refresh()
