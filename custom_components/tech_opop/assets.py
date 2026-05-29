"""Helper utilities for working with integration assets."""

from __future__ import annotations

from collections.abc import Iterable
import json
import logging
from pathlib import Path
import re
import unicodedata
from typing import Any

from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

from .const import (
    DEFAULT_ICON,
    ICON_BY_ID,
    ICON_BY_TYPE,
    MENU_ITEM_TYPE_GROUP,
    TXT_ID_BY_TYPE,
)

_LOGGER = logging.getLogger(__name__)

_REDACTED_VALUE = "***HIDDEN***"

# Mapping of eModul API value type (unit field) to (divisor, ha_unit, device_class, state_class)
# Based on api-v1.txt section 10. Data format
_VALUE_TYPE_INFO: dict[int, tuple[float, str | None, str | None, str | None]] = {
    # (divisor, native_unit, device_class, state_class)
    0:  (1,    None,                                   None,                              SensorStateClass.MEASUREMENT),
    1:  (1,    UnitOfTime.SECONDS,                     SensorDeviceClass.DURATION,        SensorStateClass.MEASUREMENT),
    2:  (1,    UnitOfTime.MINUTES,                     SensorDeviceClass.DURATION,        SensorStateClass.MEASUREMENT),
    3:  (1,    UnitOfTime.HOURS,                       SensorDeviceClass.DURATION,        SensorStateClass.MEASUREMENT),
    4:  (10,   None,                                   None,                              SensorStateClass.MEASUREMENT),
    5:  (100,  None,                                   None,                              SensorStateClass.MEASUREMENT),
    6:  (1,    UnitOfTemperature.CELSIUS,              SensorDeviceClass.TEMPERATURE,     SensorStateClass.MEASUREMENT),
    7:  (10,   UnitOfTemperature.CELSIUS,              SensorDeviceClass.TEMPERATURE,     SensorStateClass.MEASUREMENT),
    8:  (1,    PERCENTAGE,                             None,                              SensorStateClass.MEASUREMENT),
    9:  (1,    "‰",                                    None,                              SensorStateClass.MEASUREMENT),
    10: (1,    UnitOfPower.KILO_WATT,                  SensorDeviceClass.POWER,           SensorStateClass.MEASUREMENT),
    11: (1,    UnitOfEnergy.KILO_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    12: (1,    UnitOfElectricPotential.VOLT,           SensorDeviceClass.VOLTAGE,         SensorStateClass.MEASUREMENT),
    14: (1,    UnitOfTime.DAYS,                        SensorDeviceClass.DURATION,        SensorStateClass.MEASUREMENT),
    19: (10,   UnitOfEnergy.KILO_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    20: (1,    UnitOfEnergy.MEGA_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    21: (10,   UnitOfEnergy.MEGA_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    22: (10,   UnitOfVolumeFlowRate.LITERS_PER_MINUTE, SensorDeviceClass.VOLUME_FLOW_RATE,SensorStateClass.MEASUREMENT),
    23: (10,   UnitOfPressure.BAR,                     SensorDeviceClass.PRESSURE,        SensorStateClass.MEASUREMENT),
    26: (10,   UnitOfPower.KILO_WATT,                  SensorDeviceClass.POWER,           SensorStateClass.MEASUREMENT),
    27: (1,    "rpm",                                  None,                              SensorStateClass.MEASUREMENT),
    29: (1,    UnitOfPower.WATT,                       SensorDeviceClass.POWER,           SensorStateClass.MEASUREMENT),
    30: (10,   UnitOfVolumeFlowRate.LITERS_PER_MINUTE, SensorDeviceClass.VOLUME_FLOW_RATE,SensorStateClass.MEASUREMENT),
    32: (1,    "K",                                    SensorDeviceClass.TEMPERATURE,     SensorStateClass.MEASUREMENT),
    33: (10,   PERCENTAGE,                             None,                              SensorStateClass.MEASUREMENT),
    34: (1,    UnitOfEnergy.WATT_HOUR,                 SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    36: (100,  UnitOfEnergy.KILO_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
    38: (10,   None,                                   None,                              SensorStateClass.MEASUREMENT),
    40: (1000, UnitOfEnergy.KILO_WATT_HOUR,            SensorDeviceClass.ENERGY,          SensorStateClass.TOTAL_INCREASING),
}


def get_value_type_info(unit: int) -> tuple[float, str | None, str | None, str | None]:
    """Return (divisor, native_unit, device_class, state_class) for eModul value type.

    Args:
        unit: eModul value type number from API (field 'unit' in tile widget params).

    Returns:
        Tuple of (divisor, native_unit, device_class, state_class).
        Defaults to (1, None, None, None) for unknown types.

    """
    return _VALUE_TYPE_INFO.get(unit, (1, None, None, None))


def slugify_name(name: str) -> str:
    """Convert a human-readable name to a slug suitable for entity_id suffix.

    Normalises unicode, lowercases, replaces non-alphanumeric characters with
    underscores and collapses repeated underscores.

    Args:
        name: Human-readable label (e.g. "Teplota TUV").

    Returns:
        Slug string (e.g. "teplota_tuv").

    """
    # Normalise unicode (e.g. č → c)
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name

TranslationsType = dict[str, Any]

_I18N_DIR = Path(__file__).parent / "i18n"
_translations_cache: dict[str, TranslationsType] = {}

# Pre-load all available languages at import time (synchronous, outside event loop)
for _p in _I18N_DIR.glob("*.json"):
    try:
        _translations_cache[_p.stem] = json.loads(_p.read_text(encoding="utf-8"))
    except Exception as _exc:  # noqa: BLE001
        import logging as _logging
        _logging.getLogger(__name__).warning("Failed to load i18n file %s: %s", _p, _exc)


def _load_translations(language: str) -> TranslationsType:
    """Load translations from bundled i18n JSON file, falling back to 'en'."""
    if language in _translations_cache:
        return _translations_cache[language]
    for lang in (language, "en"):
        path = _I18N_DIR / f"{lang}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                _translations_cache[language] = data
                return data
            except Exception:  # noqa: BLE001
                _LOGGER.warning("Failed to load bundled i18n file: %s", path)
    _translations_cache[language] = {}
    return {}


# Active language - set once during integration setup
_active_language: str = "en"


def set_language(language: str) -> None:
    """Set the active language and pre-load translations into cache."""
    global _active_language  # noqa: PLW0603
    _active_language = language
    _load_translations(language)  # pre-load outside event loop via load_subtitles


def redact(entry_data: dict[str, Any], keys: Iterable[str]) -> str:
    """Return a string representation of ``entry_data`` with selected keys masked.

    Args:
        entry_data: Source mapping that may contain sensitive values.
        keys: Sequence of keys whose values should be replaced.

    Returns:
        Stringified version of ``entry_data`` with sensitive values replaced by
        ``***HIDDEN***``.

    """
    keys_set = set(keys)
    sanitized_data = {
        k: _REDACTED_VALUE if k in keys_set else v for k, v in entry_data.items()
    }
    return str(sanitized_data)


async def load_subtitles(language: str, api=None) -> None:  # noqa: ARG001
    """Set the active language for bundled i18n lookups (API client no longer used)."""
    set_language(language)


def get_text(text_id: int) -> str:
    """Return the translated string for a subtitle identifier."""
    try:
        text_id = int(text_id)
    except (TypeError, ValueError):
        return f"txtId {text_id}"
    if text_id > 0:
        translations = _load_translations(_active_language)
        return translations.get("data", {}).get(str(text_id), f"txtId {text_id}")
    return f"txtId {text_id}"


def get_text_by_type(text_type: int) -> str:
    """Return the translated label associated with a tile type."""
    text_id = TXT_ID_BY_TYPE.get(text_type)
    if text_id is None:
        return f"type {text_type}"
    return get_text(text_id)


def get_icon(icon_id: int) -> str:
    """Return the Material Design icon name mapped to ``icon_id``."""
    return ICON_BY_ID.get(icon_id, DEFAULT_ICON)


def get_icon_by_type(icon_type: int) -> str:
    """Return the default icon assigned to the provided tile type."""
    return ICON_BY_TYPE.get(icon_type, DEFAULT_ICON)

def build_menu_group_names(
    menus: dict[str, dict[str, Any]],
) -> dict[tuple[str, int], str]:
    """Build a mapping of ``(menu_type, group_id)`` to translated group name.

    Args:
        menus: Flat mapping of menu key to menu item payload (as returned by
            :meth:`Tech.get_module_menus`).

    Returns:
        Dictionary keyed by ``(menu_type, group_id)`` with the resolved group
        label as value.

    """
    groups: dict[tuple[str, int], str] = {}
    for item in menus.values():
        if item.get("type") != MENU_ITEM_TYPE_GROUP:
            continue
        txt_id = item.get("txtId", 0)
        name = get_text(txt_id) if txt_id else ""
        groups[(item["menuType"], item["id"])] = name
    return groups



def menu_entity_name(
    item: dict[str, Any],
    group_names: dict[tuple[str, int], str],
) -> str:
    """Return a human-readable entity name for a menu item.

    When the item belongs to a non-root parent group the group label is
    prepended so that ambiguous names like *On* gain context.

    Args:
        item: Menu item payload from the API.
        group_names: Lookup returned by :func:`build_menu_group_names`.

    Returns:
        Formatted entity name string.

    """
    txt_id = item.get("txtId", 0)
    label = get_text(txt_id) if txt_id else f"Menu {item['id']}"
    parent_id = item.get("parentId", 0)
    if parent_id != 0:
        parent_label = group_names.get((item["menuType"], parent_id), "")
        if parent_label:
            label = f"{parent_label} - {label}"
    return label
