"""Platform for number entities backed by Tech menu parameters."""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
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
    MENU_ITEM_TYPE_UNIVERSAL_VALUE,
    MENU_ITEM_TYPE_VALUE,
    OPOP_DEFAULT_ENABLED_MENU_IDS,
    UDID,
    VALUE_FORMAT_TENTH,
)
from .coordinator import TechCoordinator
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
    controller_udid = config_entry.data[CONTROLLER][UDID]

    menus = await coordinator.api.get_module_menus(controller_udid, options=config_entry.options)
    group_names = assets.build_menu_group_names(menus)
    depths = assets.compute_menu_depths(menus)

    entities = [
        MenuNumberEntity(item, key, coordinator, config_entry, group_names)
        for key, item in menus.items()
        if item.get("type") in _EDITABLE_TYPES
        and item.get("access", False)
        and depths[key] <= MENU_DEPTH_REGISTRATION_LIMIT
    ]
    async_add_entities(entities, True)


class MenuNumberEntity(CoordinatorEntity, NumberEntity):
    """A numeric menu parameter exposed as a Home Assistant number."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
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
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._menu_key = menu_key
        self._item_id = item["id"]
        self._menu_type = item["menuType"]
        self._unique_id = f"{self._udid}_menu_{menu_key}"
        self._name = assets.menu_entity_name(item, group_names)
        self._format = item.get("params", {}).get("format", 1)
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
        await self.coordinator.async_request_refresh()
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

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        item = self.coordinator.data.get("menus", {}).get(self._menu_key)
        if item:
            self._update_from_item(item)
        self.async_write_ha_state()
