"""Base class for menu-backed Tech OPOP entities."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import assets
from .const import CONTROLLER, DOMAIN, MANUFACTURER, OPOP_DEFAULT_ENABLED_MENU_IDS, UDID
from .coordinator import TechCoordinator


def make_device_info(udid: str, title: str) -> DeviceInfo:
    """Build a DeviceInfo dict for the given controller."""
    return DeviceInfo(
        identifiers={(DOMAIN, udid)},
        name=title,
        manufacturer=MANUFACTURER,
    )


class MenuEntity(CoordinatorEntity):
    """Shared base for all menu-backed entities (button, number, select, switch)."""

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
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._menu_key = menu_key
        self._item_id = item["id"]
        self._menu_type = item["menuType"]
        self._attr_unique_id = f"{self._udid}_menu_{menu_key}"
        self._name = assets.menu_entity_name(item, group_names)
        self._attr_device_info = make_device_info(self._udid, config_entry.title)

    @property
    def suggested_object_id(self) -> str | None:
        name_slug = assets.slugify_name(self._name)
        menu_prefix = self._menu_type.lower()
        return f"{menu_prefix}_{self._item_id}_{name_slug}" if name_slug else f"{menu_prefix}_{self._item_id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._item_id in OPOP_DEFAULT_ENABLED_MENU_IDS

    def _update_from_item(self, item: dict[str, Any]) -> None:
        """Update entity state from menu item data - override in subclass."""

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        item = self.coordinator.data.get("menus", {}).get(self._menu_key)
        if item:
            self._update_from_item(item)
        self.async_write_ha_state()
