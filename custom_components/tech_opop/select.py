"""Platform for select entities backed by Tech menu choice parameters."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    CONF_NAME,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import assets
from .const import (
    CONTROLLER,
    DOMAIN,
    MANUFACTURER,
    MENU_DEPTH_REGISTRATION_LIMIT,
    MENU_ITEM_TYPE_CHOICE,
    OPOP_DEFAULT_ENABLED_MENU_IDS,
    UDID,
)
from .coordinator import TechCoordinator
from .tech import TechDuringChangeError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech select entities from menu choice parameters."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    controller_udid = config_entry.data[CONTROLLER][UDID]

    menus = await coordinator.api.get_module_menus(controller_udid)
    group_names = assets.build_menu_group_names(menus)
    depths = assets.compute_menu_depths(menus)

    entities = [
        MenuSelectEntity(item, key, coordinator, config_entry, group_names)
        for key, item in menus.items()
        if item.get("type") in MENU_ITEM_TYPE_CHOICE
        and item.get("access", False)
        and item.get("params", {}).get("options")
        and depths[key] <= MENU_DEPTH_REGISTRATION_LIMIT
    ]
    async_add_entities(entities, True)


class MenuSelectEntity(CoordinatorEntity, SelectEntity):
    """A choice menu parameter exposed as a Home Assistant select."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        item: dict[str, Any],
        menu_key: str,
        coordinator: TechCoordinator,
        config_entry: ConfigEntry,
        group_names: dict[tuple[str, int], str],
    ) -> None:
        """Initialise a menu select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._menu_key = menu_key
        self._item_id = item["id"]
        self._menu_type = item["menuType"]
        self._unique_id = f"{self._udid}_menu_{menu_key}"
        self._name = assets.menu_entity_name(item, group_names)
        self._value_to_label: dict[int, str] = {}
        self._label_to_value: dict[str, int] = {}
        self._update_from_item(item)

    @property
    def suggested_object_id(self) -> str | None:
        name_slug = assets.slugify_name(self._name)
        menu_prefix = self._menu_type.lower()
        return f"{menu_prefix}_{self._item_id}_{name_slug}" if name_slug else f"{menu_prefix}_{self._item_id}"

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._item_id in OPOP_DEFAULT_ENABLED_MENU_IDS

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self._udid)},
            CONF_NAME: self._config_entry.title,
            ATTR_MANUFACTURER: MANUFACTURER,
        }

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
        await self.coordinator.async_request_refresh()
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._item_id, {"value": value}
            )
        except TechDuringChangeError:
            raise HomeAssistantError(
                translation_domain="tech_opop", translation_key="during_change"
            )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        item = self.coordinator.data.get("menus", {}).get(self._menu_key)
        if item:
            self._update_from_item(item)
        self.async_write_ha_state()
