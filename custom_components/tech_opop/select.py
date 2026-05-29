"""Platform for select entities backed by Tech menu choice parameters."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import assets
from .const import (
    DOMAIN,
    MENU_ITEM_TYPE_CHOICE,
)
from .coordinator import TechCoordinator
from .menu_entity import MenuEntity
from .tech import TechDuringChangeError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech select entities from menu choice parameters."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    menus = coordinator.data.get("menus", {})
    group_names = assets.build_menu_group_names(menus)

    entities = [
        MenuSelectEntity(item, key, coordinator, config_entry, group_names)
        for key, item in menus.items()
        if item.get("type") in MENU_ITEM_TYPE_CHOICE
        and item.get("access", False)
        and item.get("params", {}).get("options")
    ]
    async_add_entities(entities, True)


class MenuSelectEntity(MenuEntity, SelectEntity):
    """A choice menu parameter exposed as a Home Assistant select."""

    def __init__(
        self,
        item: dict[str, Any],
        menu_key: str,
        coordinator: TechCoordinator,
        config_entry: ConfigEntry,
        group_names: dict[tuple[str, int], str],
    ) -> None:
        """Initialise a menu select entity."""
        self._value_to_label: dict[int, str] = {}
        self._label_to_value: dict[str, int] = {}
        super().__init__(item, menu_key, coordinator, config_entry, group_names)
        self._update_from_item(item)

    def _build_option_maps(self, options: list[dict[str, Any]]) -> None:
        self._value_to_label = {}
        self._label_to_value = {}
        ha_options: list[str] = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            val = opt.get("value", 0)
            txt_id = opt.get("txtId", 0)
            label = assets.get_text(txt_id) if txt_id else str(val)
            if label in self._label_to_value:
                label = f"{label} ({val})"
            self._value_to_label[val] = label
            self._label_to_value[label] = val
            ha_options.append(label)
        self._attr_options = ha_options

    def _update_from_item(self, item: dict[str, Any]) -> None:
        params = item.get("params", {})
        self._build_option_maps(params.get("options", []))
        current_label = self._value_to_label.get(params.get("value", 0))
        if current_label and current_label in self._attr_options:
            self._attr_current_option = current_label
        elif self._attr_options:
            self._attr_current_option = self._attr_options[0]
        else:
            self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self._label_to_value.get(option)
        if value is None:
            _LOGGER.warning("Unknown option %s for menu item %s", option, self._item_id)
            return
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._item_id, {"value": value}
            )
        except TechDuringChangeError:
            raise HomeAssistantError(
                translation_domain="tech_opop", translation_key="during_change"
            )
        await self.coordinator.async_request_refresh()
