"""Support for Tech HVAC system."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PARAMS,
    CONF_TYPE,
    PERCENTAGE,
    STATE_OFF,
    STATE_ON,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import assets
from .const import (
    CONTROLLER,
    DOMAIN,
    OPENTHERM_CURRENT_TEMP,
    OPENTHERM_CURRENT_TEMP_DHW,
    OPENTHERM_MODULATION,
    OPENTHERM_SET_TEMP,
    OPENTHERM_SET_TEMP_DHW,
    TYPE_FAN,
    TYPE_FIRE_SENSOR,
    TYPE_FUEL_SUPPLY,
    TYPE_MIXING_VALVE,
    TYPE_OPEN_THERM,
    TYPE_TEMPERATURE,
    TYPE_TEMPERATURE_CH,
    TYPE_TEXT,
    TYPE_SW_VERSION,
    TYPE_VALVE,
    UDID,
    VALUE,
    VALVE_SENSOR_CURRENT_TEMPERATURE,
    VALVE_SENSOR_RETURN_TEMPERATURE,
    VALVE_SENSOR_SET_TEMPERATURE,
    VISIBILITY,
    WORKING_STATUS,
)
from .coordinator import TechCoordinator
from .entity import TileEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tech sensor entities for the provided config entry."""
    controller_udid = config_entry.data[CONTROLLER][UDID]
    _LOGGER.debug("Setting up sensor entry, controller udid: %s", controller_udid)

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tiles = coordinator.data.get("tiles", {})

    entities = [
        entity
        for tile in tiles.values()
        for entity in _build_tile_entities(tile, coordinator, config_entry)
    ]

    async_add_entities(entities, True)


# ---------------------------------------------------------------------------
# Tile entity builders
# ---------------------------------------------------------------------------

TileBuilder = Callable[
    [dict[str, Any], TechCoordinator, ConfigEntry], list[CoordinatorEntity]
]

# Config dicts for TileSimpleSensor — state_key, unit (eModul value type), icon, unique_suffix
_SIMPLE_SENSOR_CONFIG: dict[int, dict[str, Any]] = {
    TYPE_FIRE_SENSOR: {
        "state_key": VALUE,
        "unit": 0,
        "icon": "mdi:fire",
        "unique_suffix": "tile_fire_pulse",
    },
    TYPE_FAN: {
        "state_key": "gear",
        "unit": 8,
        "icon": assets.get_icon_by_type(TYPE_FAN),
        "unique_suffix": "tile_fan",
    },
    TYPE_FUEL_SUPPLY: {
        "state_key": "percentage",
        "unit": 8,
        "icon": None,
        "unique_suffix": "tile_fuel_supply",
    },
}


def _build_tile_entities(
    tile: dict[str, Any],
    coordinator: TechCoordinator,
    config_entry: ConfigEntry,
) -> list[CoordinatorEntity]:
    """Create coordinator entities for a single tile payload."""
    if not tile.get(VISIBILITY, False):
        return []

    # workingStatus=False means "currently inactive", not "doesn't exist".
    # TYPE_FIRE_SENSOR: False when boiler is off — always show.
    # TYPE_FAN: gear=0 when boiler is off — always show.
    # TYPE_SW_VERSION: never has workingStatus.
    always_show = {TYPE_FIRE_SENSOR, TYPE_SW_VERSION, TYPE_FAN}
    if tile[CONF_TYPE] not in always_show and not tile.get(WORKING_STATUS, True):
        return []

    builder = _TILE_ENTITY_BUILDERS.get(tile[CONF_TYPE])
    if builder is None:
        return []
    return builder(tile, coordinator, config_entry)


def _build_valve_tile(
    tile: dict[str, Any],
    coordinator: TechCoordinator,
    config_entry: ConfigEntry,
) -> list[CoordinatorEntity]:
    """Create valve entities: main opening sensor + temperature sub-sensors."""
    entities: list[CoordinatorEntity] = [
        TileValveSensor(tile, coordinator, config_entry, extra_attrs=True)
    ]
    valve_number = tile[CONF_PARAMS].get("valveNumber", "")
    name_prefix = f"{assets.get_text_by_type(tile[CONF_TYPE])} {valve_number}"
    for desc in (
        VALVE_SENSOR_RETURN_TEMPERATURE,
        VALVE_SENSOR_SET_TEMPERATURE,
        VALVE_SENSOR_CURRENT_TEMPERATURE,
    ):
        if tile[CONF_PARAMS].get(desc["state_key"]) is not None:
            entities.append(
                TileDescribedSensor(tile, coordinator, config_entry, desc, name_prefix=name_prefix)
            )
    return entities


def _build_open_therm_tile(
    tile: dict[str, Any],
    coordinator: TechCoordinator,
    config_entry: ConfigEntry,
) -> list[CoordinatorEntity]:
    """Create OpenTherm entities for a tile payload."""
    return [
        TileDescribedSensor(tile, coordinator, config_entry, desc)
        for desc in (
            OPENTHERM_CURRENT_TEMP,
            OPENTHERM_SET_TEMP,
            OPENTHERM_CURRENT_TEMP_DHW,
            OPENTHERM_SET_TEMP_DHW,
            OPENTHERM_MODULATION,
        )
        if tile[CONF_PARAMS].get(desc["state_key"]) is not None
    ]


_TILE_ENTITY_BUILDERS: dict[int, TileBuilder] = {
    TYPE_TEMPERATURE: lambda tile, coord, entry: [TileTemperatureSensor(tile, coord, entry)],
    TYPE_TEMPERATURE_CH: lambda tile, coord, entry: [TileWidgetSensor(tile, coord, entry)],
    TYPE_FIRE_SENSOR: lambda tile, coord, entry: [TileSimpleSensor(tile, coord, entry, _SIMPLE_SENSOR_CONFIG[TYPE_FIRE_SENSOR])],
    TYPE_FAN: lambda tile, coord, entry: [TileSimpleSensor(tile, coord, entry, _SIMPLE_SENSOR_CONFIG[TYPE_FAN])],
    TYPE_VALVE: _build_valve_tile,
    TYPE_MIXING_VALVE: lambda tile, coord, entry: [TileValveSensor(tile, coord, entry, extra_attrs=False)],
    TYPE_FUEL_SUPPLY: lambda tile, coord, entry: [TileSimpleSensor(tile, coord, entry, _SIMPLE_SENSOR_CONFIG[TYPE_FUEL_SUPPLY])],
    TYPE_TEXT: lambda tile, coord, entry: [TileTextSensor(tile, coord, entry)],
    TYPE_SW_VERSION: lambda tile, coord, entry: [TileSwVersionSensor(tile, coord, entry)],
    TYPE_OPEN_THERM: _build_open_therm_tile,
}


# ---------------------------------------------------------------------------
# Tile sensor classes
# ---------------------------------------------------------------------------

class TileSensor(TileEntity):
    """Base class for tile sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def get_state(self, device) -> Any:
        """Extract state from tile payload."""


class TileTemperatureSensor(TileSensor, SensorEntity):
    """Temperature sensor tile (type 1)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_temperature"

    def get_state(self, device) -> Any:
        val = device[CONF_PARAMS].get(VALUE)
        return val / 10 if val is not None else None


class TileSimpleSensor(TileSensor, SensorEntity):
    """Generic tile sensor driven by a config dict (state_key, unit, icon, unique_suffix)."""

    def __init__(self, device, coordinator: TechCoordinator, config_entry, config: dict[str, Any]) -> None:
        """Initialize."""
        self._state_key = config["state_key"]
        self._unique_suffix = config["unique_suffix"]
        divisor, native_unit, device_class, state_class = assets.get_value_type_info(config.get("unit", 0))
        self._divisor = divisor
        self._attr_native_unit_of_measurement = native_unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if config.get("icon"):
            self._attr_icon = config["icon"]
        super().__init__(device, coordinator, config_entry)

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_{self._unique_suffix}"

    def get_state(self, device) -> Any:
        val = device[CONF_PARAMS].get(self._state_key)
        if val is None:
            return None
        return val / self._divisor if self._divisor != 1 else val


class TileValveSensor(TileSensor, SensorEntity):
    """Valve or mixing-valve opening percentage (type 23 / 24)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device, coordinator: TechCoordinator, config_entry, extra_attrs: bool = False) -> None:
        """Initialize."""
        super().__init__(device, coordinator, config_entry)
        self._extra_attrs = extra_attrs
        valve_number = device[CONF_PARAMS].get("valveNumber", "")
        self._attr_icon = assets.get_icon_by_type(device[CONF_TYPE])
        self._name = f"{assets.get_text_by_type(device[CONF_TYPE])} {valve_number}".strip()
        self.attrs: dict[str, Any] = {}

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_valve"

    def get_state(self, device) -> Any:
        return device[CONF_PARAMS].get("openingPercentage")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self.attrs)

    def update_properties(self, device) -> None:
        self._state = self.get_state(device)
        if self._extra_attrs:
            p = device[CONF_PARAMS]
            self.attrs["setTempCorrection"] = p.get("setTempCorrection")
            self.attrs["valvePump"] = STATE_ON if p.get("valvePump") == 1 else STATE_OFF
            self.attrs["boilerProtection"] = STATE_ON if p.get("boilerProtection") == 1 else STATE_OFF
            self.attrs["returnProtection"] = STATE_ON if p.get("returnProtection") == 1 else STATE_OFF


class TileDescribedSensor(TileSensor, SensorEntity):
    """Sensor configured by a description dict {state_key, txt_id, unit}.

    unit maps to eModul API value type (api-v1.txt section 10) — determines
    divisor, native_unit, device_class, state_class via assets.get_value_type_info().
    """

    _attr_has_entity_name = True

    def __init__(self, device, coordinator: TechCoordinator, config_entry, description: dict, name_prefix: str | None = None) -> None:
        """Initialize."""
        self._txt_id = description["txt_id"]
        self._state_key = description["state_key"]
        divisor, native_unit, device_class, state_class = assets.get_value_type_info(description.get("unit", 0))
        self._divisor = divisor
        super().__init__(device, coordinator, config_entry)
        self._attr_native_unit_of_measurement = native_unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        base_name = assets.get_text(self._txt_id)
        self._name = f"{name_prefix} {base_name}" if name_prefix else base_name
        self.attrs: dict[str, Any] = {}

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_described_{self._state_key}"

    def get_state(self, device) -> Any:
        val = device[CONF_PARAMS].get(self._state_key)
        if val is None:
            return None
        return val / self._divisor if self._divisor != 1 else val

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self.attrs)

    def update_properties(self, device) -> None:
        self._state = self.get_state(device)

        def _set(key: str, flag: bool = False) -> None:
            try:
                self.attrs[key] = ("on" if device[CONF_PARAMS]["flags"][key] else "off") if flag else int(device[CONF_PARAMS][key])
            except (KeyError, ValueError, TypeError):
                pass

        _set("alarmCode")
        _set("activeDHW", flag=True)
        _set("activeHeating", flag=True)
        _set("communication", flag=True)
        _set("heatingCurve", flag=True)


class TileTextSensor(TileSensor, SensorEntity):
    """Text status tile (type 40)."""

    def __init__(self, device, coordinator: TechCoordinator, config_entry) -> None:
        """Initialize."""
        super().__init__(device, coordinator, config_entry)
        self._name = assets.get_text(device[CONF_PARAMS].get("headerId", 0))
        self._attr_icon = assets.get_icon(device[CONF_PARAMS].get("iconId", 0))

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_text"

    def get_state(self, device) -> Any:
        return assets.get_text(device[CONF_PARAMS].get("statusId", 0))


class TileWidgetSensor(TileSensor, SensorEntity):
    """Widget temperature tile (type 6).

    Tiles 1006/1017 carry the primary value in widget2 (widget1 is a correction
    offset). Falls back to widget1 when widget2 is absent.
    """

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device, coordinator: TechCoordinator, config_entry) -> None:
        """Initialize."""
        super().__init__(device, coordinator, config_entry)
        widget = device[CONF_PARAMS].get("widget2") or device[CONF_PARAMS].get("widget1")
        if widget:
            self._name = assets.get_text(widget["txtId"])

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_widget"

    def get_state(self, device) -> Any:
        widget = device[CONF_PARAMS].get("widget2") or device[CONF_PARAMS].get("widget1")
        if widget is None:
            return None
        return widget.get(VALUE, 0) / 10


class TileSwVersionSensor(TileSensor, SensorEntity):
    """Controller software version tile (type 50, tile 2000)."""

    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        return f"{self._unique_id}_tile_sw_version"

    def get_state(self, device) -> Any:
        params = device[CONF_PARAMS]
        name = params.get("controllerName", "")
        version = params.get("version", "")
        return f"{name} (v.{version})" if version else name
