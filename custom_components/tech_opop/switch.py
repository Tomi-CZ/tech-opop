"""Platform for switch entities backed by Tech menu on/off parameters."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import assets
from .const import (
    CONTROLLER,
    DOMAIN,
    MENU_ITEM_TYPE_ON_OFF,
    OPOP_FIRING_SWITCH_OFF_ID,
    OPOP_FIRING_SWITCH_ON_ID,
    UDID,
)
from .coordinator import TechCoordinator
from .menu_entity import MenuEntity, make_device_info
from .tech import TechDuringChangeError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech switch entities from menu on/off parameters."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    menus = coordinator.data.get("menus", {})
    group_names = assets.build_menu_group_names(menus)

    entities: list[CoordinatorEntity] = []

    on_key = f"MU_{OPOP_FIRING_SWITCH_ON_ID}"
    off_key = f"MU_{OPOP_FIRING_SWITCH_OFF_ID}"
    if on_key in menus and off_key in menus:
        entities.append(FiringSwitchEntity(menus[on_key], menus[off_key], coordinator, config_entry))

    for key, item in menus.items():
        if item.get("type") != MENU_ITEM_TYPE_ON_OFF:
            continue
        if not item.get("access", False):
            continue
        entities.append(MenuSwitchEntity(item, key, coordinator, config_entry, group_names))

    async_add_entities(entities, True)


class MenuSwitchEntity(MenuEntity, SwitchEntity):
    """An on/off menu parameter exposed as a Home Assistant switch."""

    @property
    def entity_registry_enabled_default(self) -> bool:
        return False

    def _update_from_item(self, item: dict[str, Any]) -> None:
        self._attr_is_on = item.get("params", {}).get("value", 0) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.coordinator.api.set_menu_value(self._udid, self._menu_type, self._item_id, {"value": 1})
        except TechDuringChangeError:
            raise HomeAssistantError(translation_domain="tech_opop", translation_key="during_change")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.coordinator.api.set_menu_value(self._udid, self._menu_type, self._item_id, {"value": 0})
        except TechDuringChangeError:
            raise HomeAssistantError(translation_domain="tech_opop", translation_key="during_change")
        await self.coordinator.async_request_refresh()


class FiringSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch controlling boiler firing state via dialogue items 250/251.

    ON  = boiler is firing   (item 251 Vyhasinani accessible)
    OFF = boiler not firing  (item 250 Roztapeni accessible)
    turn_on  -> triggers dialogue 250 (Roztapeni)
    turn_off -> triggers dialogue 251 (Vyhasinani)
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:fire"

    def __init__(
        self,
        item_on: dict[str, Any],
        item_off: dict[str, Any],
        coordinator: TechCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise the firing switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._menu_type = item_on["menuType"]
        self._on_id = item_on["id"]
        self._off_id = item_off["id"]
        self._on_dialogue_type = item_on.get("params", {}).get("type", 1)
        self._off_dialogue_type = item_off.get("params", {}).get("type", 1)
        self._unique_id = f"{self._udid}_firing_switch"
        self._attr_translation_key = "firing_switch"
        self._attr_device_info = make_device_info(self._udid, config_entry.title)
        self._update_from_menus(item_on, item_off)

    @property
    def suggested_object_id(self) -> str | None:
        return f"{self._config_entry.title}_firing"

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def entity_registry_enabled_default(self) -> bool:
        return True

    def _update_from_menus(self, item_on: dict[str, Any], item_off: dict[str, Any]) -> None:
        """item_off (251) accessible = firing = ON, item_on (250) accessible = not firing = OFF."""
        self._attr_is_on = item_off.get("access", False)
        self._attr_available = item_on.get("access", False) or item_off.get("access", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start firing - trigger dialogue 250 Roztapeni."""
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._on_id, {"type": self._on_dialogue_type, "value": 1}
            )
        except TechDuringChangeError:
            raise HomeAssistantError(translation_domain="tech_opop", translation_key="during_change")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop firing - trigger dialogue 251 Vyhasinani."""
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._off_id, {"type": self._off_dialogue_type, "value": 1}
            )
        except TechDuringChangeError:
            raise HomeAssistantError(translation_domain="tech_opop", translation_key="during_change")
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        menus = self.coordinator.data.get("menus", {})
        item_on = menus.get(f"{self._menu_type}_{self._on_id}")
        item_off = menus.get(f"{self._menu_type}_{self._off_id}")
        if item_on and item_off:
            self._update_from_menus(item_on, item_off)
        self.async_write_ha_state()
