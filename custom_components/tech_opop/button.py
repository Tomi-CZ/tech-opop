"""Platform for button entities backed by Tech menu dialogue parameters."""

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    MENU_ITEM_TYPE_DIALOGUE,
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
    """Set up Tech button entities from menu dialogue parameters."""
    coordinator: TechCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    controller_udid = config_entry.data[CONTROLLER][UDID]

    menus = await coordinator.api.get_module_menus(controller_udid)
    group_names = assets.build_menu_group_names(menus)
    depths = assets.compute_menu_depths(menus)

    entities = [
        MenuButtonEntity(item, key, coordinator, config_entry, group_names)
        for key, item in menus.items()
        if item.get("type") == MENU_ITEM_TYPE_DIALOGUE
        and depths[key] <= MENU_DEPTH_REGISTRATION_LIMIT
    ]
    entities.append(RefreshButtonEntity(coordinator, config_entry))
    async_add_entities(entities, True)


class MenuButtonEntity(CoordinatorEntity, ButtonEntity):
    """A dialogue menu parameter exposed as a Home Assistant button."""

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
        """Initialise a menu button entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._menu_key = menu_key
        self._item_id = item["id"]
        self._menu_type = item["menuType"]
        self._unique_id = f"{self._udid}_menu_{menu_key}"
        self._name = assets.menu_entity_name(item, group_names)
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
        self._attr_available = item.get("access", False)
        self._dialogue_type = item.get("params", {}).get("type", 0)

    async def async_press(self) -> None:
        """Trigger the dialogue action."""
        await self.coordinator.async_request_refresh()
        try:
            await self.coordinator.api.set_menu_value(
                self._udid, self._menu_type, self._item_id,
                {"type": self._dialogue_type, "value": 1},
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


class RefreshButtonEntity(CoordinatorEntity, ButtonEntity):
    """A button that triggers an immediate coordinator data refresh."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: TechCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        udid = config_entry.data[CONTROLLER][UDID]
        self._attr_unique_id = f"{udid}_refresh"
        self._attr_suggested_object_id = "refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, udid)},
            name=config_entry.title,
            manufacturer=MANUFACTURER,
        )

    async def async_press(self) -> None:
        """Trigger an immediate data refresh."""
        await self.coordinator.async_request_refresh()
