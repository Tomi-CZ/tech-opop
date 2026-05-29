"""Shared base entity helpers for Tech tile-derived devices."""

from abc import abstractmethod
from typing import Any

from homeassistant.const import CONF_DESCRIPTION, CONF_ID, CONF_PARAMS, CONF_TYPE
from homeassistant.core import callback
from homeassistant.helpers import entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import assets
from .const import CONTROLLER, OPOP_DEFAULT_ENABLED_TILES, UDID
from .coordinator import TechCoordinator
from .menu_entity import make_device_info


class TileEntity(CoordinatorEntity, entity.Entity):
    """Base class for Tech tile entities."""

    _attr_has_entity_name = True

    def __init__(self, device, coordinator: TechCoordinator, config_entry) -> None:
        """Initialise common tile entity attributes."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._id = device[CONF_ID]
        self._unique_id = f"{self._udid}_{device[CONF_ID]}"
        self._model = device[CONF_PARAMS].get(CONF_DESCRIPTION)
        txt_id = device[CONF_PARAMS].get("txtId")
        self._name = assets.get_text(txt_id) if (txt_id or 0) > 0 else assets.get_text_by_type(device[CONF_TYPE])
        self._attr_device_info = make_device_info(self._udid, config_entry.title)
        self._state = self.get_state(device)

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._id in OPOP_DEFAULT_ENABLED_TILES

    @property
    def suggested_object_id(self) -> str | None:
        name_slug = assets.slugify_name(self._name)
        return f"tile_{self._id}_{name_slug}" if name_slug else f"tile_{self._id}"

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def state(self):
        return self._state

    @abstractmethod
    def get_state(self, device):
        """Extract state from tile payload."""
        raise NotImplementedError

    def update_properties(self, device):
        """Refresh state from latest tile payload."""
        self._state = self.get_state(device)

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        tile = self.coordinator.data.get("tiles", {}).get(self._id)
        if tile is not None:
            self._attr_available = True
            self.update_properties(tile)
        else:
            self._attr_available = False
        self.async_write_ha_state()
