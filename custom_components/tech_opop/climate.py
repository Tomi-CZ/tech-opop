"""Climate platform for the Tech OPOP integration."""

import asyncio
import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONTROLLER, DOMAIN, MENU_TYPE_USER, OPOP_FIRING_SWITCH_OFF_ID, UDID
from .coordinator import TechCoordinator
from .menu_entity import make_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OPOP boiler climate entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        OPOPBoilerCH(coordinator, config_entry),
        OPOPBoilerDHW(coordinator, config_entry),
        OPOPBoilerIndoor(coordinator, config_entry),
    ], True)


def _opop_hvac_mode(coordinator_data: dict) -> HVACMode:
    """Derive HVACMode from firing switch state (menu items 250/251).

    Item 250 (Roztapeni) accessible = kotel netopi -> mozno zapnout -> OFF
    Item 251 (Vyhasinani) accessible = kotel topi -> mozno vypnout -> HEAT
    """
    off_item = coordinator_data.get("menus", {}).get(f"{MENU_TYPE_USER}_{OPOP_FIRING_SWITCH_OFF_ID}", {})
    return HVACMode.HEAT if off_item.get("access") else HVACMode.OFF


class OPOPBoilerClimate(ClimateEntity, CoordinatorEntity):
    """Base class for OPOP Biopel boiler climate entities."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
        self,
        coordinator: TechCoordinator,
        config_entry: ConfigEntry,
        unique_suffix: str,
        translation_key: str,
        min_temp: float,
        max_temp: float,
        target_step: float = 1.0,
    ) -> None:
        """Initialise the base boiler climate entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._udid = config_entry.data[CONTROLLER][UDID]
        self._unique_id = f"{self._udid}_{unique_suffix}"
        self._attr_translation_key = translation_key
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._attr_target_temperature_step = target_step
        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._hvac_mode = HVACMode.OFF
        self._debounce_task: asyncio.Task | None = None
        self._debounce_seconds = 5

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo | None:
        return make_device_info(self._udid, self._config_entry.title)

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction | None:
        return HVACAction.HEATING if self._hvac_mode == HVACMode.HEAT else HVACAction.OFF

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    def _refresh_hvac_mode(self, data: dict) -> None:
        self._hvac_mode = _opop_hvac_mode(data)

    async def _debounced_set_temperature(self, temperature: float) -> None:
        """Optimistically update UI, debounce API write by 5 s."""
        self._target_temperature = temperature
        self.async_write_ha_state()
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        async def _write() -> None:
            await asyncio.sleep(self._debounce_seconds)
            await self._do_set_temperature(temperature)
            await self.coordinator.async_request_refresh()

        self._debounce_task = self.hass.async_create_task(_write())

    async def _do_set_temperature(self, temperature: float) -> None:
        """Perform the actual API write - override in subclasses."""
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        self._refresh_from_data(self.coordinator.data or {})
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._debounced_set_temperature(temperature)

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending debounce task on unload."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()


class OPOPBoilerCH(OPOPBoilerClimate):
    """Central heating circuit.

    current_temp: tile 1012 currentTemp / 10
    target_temp:  MU/2060 value (°C integer)
    """

    def __init__(self, coordinator: TechCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry,
            unique_suffix="opop_ch", translation_key="boiler_ch",
            min_temp=55, max_temp=80)
        self._refresh_from_data(coordinator.data or {})

    def _refresh_from_data(self, data: dict) -> None:
        raw = data.get("tiles", {}).get(1012, {}).get("params", {}).get("currentTemp")
        self._current_temperature = raw / 10 if raw is not None else None
        menu = data.get("menus", {}).get("MU_2060", {})
        self._attr_assumed_state = menu.get("duringChange") == "t"
        if not self._attr_assumed_state:
            val = menu.get("params", {}).get("value")
            self._target_temperature = float(val) if val is not None else None
        self._refresh_hvac_mode(data)

    async def _do_set_temperature(self, temperature: float) -> None:
        await self.coordinator.api.set_menu_value(self._udid, "MU", 2060, {"value": int(temperature)})


class OPOPBoilerDHW(OPOPBoilerClimate):
    """Domestic hot water circuit.

    current_temp: tile 1007 value / 10
    target_temp:  MI/3532 value (°C integer)
    """

    def __init__(self, coordinator: TechCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry,
            unique_suffix="opop_dhw", translation_key="boiler_dhw",
            min_temp=40, max_temp=75)
        self._refresh_from_data(coordinator.data or {})

    def _refresh_from_data(self, data: dict) -> None:
        raw = data.get("tiles", {}).get(1007, {}).get("params", {}).get("value")
        self._current_temperature = raw / 10 if raw is not None else None
        menu = data.get("menus", {}).get("MI_3532", {})
        self._attr_assumed_state = menu.get("duringChange") == "t"
        if not self._attr_assumed_state:
            val = menu.get("params", {}).get("value")
            self._target_temperature = float(val) if val is not None else None
        self._refresh_hvac_mode(data)

    async def _do_set_temperature(self, temperature: float) -> None:
        await self.coordinator.api.set_menu_value(self._udid, "MI", 3532, {"value": int(temperature)})


class OPOPBoilerIndoor(OPOPBoilerClimate):
    """Indoor room setpoint.

    current_temp: tile 1017 widget2.value / 10
    target_temp:  MU/2089 value / 10 (API stores in tenths of °C)
    """

    def __init__(self, coordinator: TechCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry,
            unique_suffix="opop_indoor", translation_key="boiler_indoor",
            min_temp=5, max_temp=40, target_step=0.5)
        self._refresh_from_data(coordinator.data or {})

    def _refresh_from_data(self, data: dict) -> None:
        widget2 = data.get("tiles", {}).get(1017, {}).get("params", {}).get("widget2", {})
        raw = widget2.get("value")
        self._current_temperature = raw / 10 if raw is not None else None
        menu = data.get("menus", {}).get("MU_2089", {})
        self._attr_assumed_state = menu.get("duringChange") == "t"
        if not self._attr_assumed_state:
            val = menu.get("params", {}).get("value")
            self._target_temperature = val / 10 if val is not None else None
        self._refresh_hvac_mode(data)

    async def _do_set_temperature(self, temperature: float) -> None:
        await self.coordinator.api.set_menu_value(self._udid, "MU", 2089, {"value": int(temperature * 10)})
