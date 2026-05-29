"""Constants for the Tech OPOP integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN = "tech_opop"
CONTROLLER = "controller"
CONTROLLERS = "controllers"
UDID = "udid"
USER_ID = "user_id"
VISIBILITY = "visibility"
VALUE = "value"
MANUFACTURER = "TechControllers"
WORKING_STATUS = "workingStatus"

DEFAULT_ICON = "mdi:eye"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

SCAN_INTERVAL_MIN: Final = 60
SCAN_INTERVAL_DEFAULT: Final = 300
API_TIMEOUT: Final = 60

# Tile types
TYPE_TEMPERATURE = 1
TYPE_FIRE_SENSOR = 2
TYPE_TEMPERATURE_CH = 6
TYPE_RELAY = 11
TYPE_ADDITIONAL_PUMP = 21
TYPE_FAN = 22
TYPE_VALVE = 23
TYPE_MIXING_VALVE = 24
TYPE_FUEL_SUPPLY = 31
TYPE_TEXT = 40
TYPE_SW_VERSION = 50
TYPE_OPEN_THERM = 252

# icon_id -> MDI icon
ICON_BY_ID = {
    3: "mdi:animation-play",
    17: "mdi:arrow-right-drop-circle-outline",
    50: "mdi:tune-vertical",
    101: "mdi:cogs",
}

# tile type -> MDI icon
ICON_BY_TYPE = {
    TYPE_FIRE_SENSOR: "mdi:fire",
    TYPE_ADDITIONAL_PUMP: "mdi:arrow-right-drop-circle-outline",
    TYPE_FAN: "mdi:fan",
    TYPE_VALVE: "mdi:valve",
    TYPE_MIXING_VALVE: "mdi:valve",
    TYPE_OPEN_THERM: "mdi:home-thermometer",
}

# tile type -> txtId
TXT_ID_BY_TYPE = {
    TYPE_FIRE_SENSOR: 205,
    TYPE_FAN: 4135,
    TYPE_VALVE: 991,
    TYPE_MIXING_VALVE: 5731,
    TYPE_FUEL_SUPPLY: 961,
    TYPE_OPEN_THERM: 4633,
}

# Valve temperature sub-sensors
VALVE_SENSOR_RETURN_TEMPERATURE = {"txt_id": 747, "state_key": "returnTemp", "unit": 6}
VALVE_SENSOR_SET_TEMPERATURE = {"txt_id": 1065, "state_key": "setTemp", "unit": 6}
VALVE_SENSOR_CURRENT_TEMPERATURE = {"txt_id": 2010, "state_key": "currentTemp", "unit": 7}

# OpenTherm sub-sensors
OPENTHERM_CURRENT_TEMP = {"txt_id": 127, "state_key": "currentTemp", "unit": 7}
OPENTHERM_CURRENT_TEMP_DHW = {"txt_id": 128, "state_key": "currentTempDHW", "unit": 7}
OPENTHERM_SET_TEMP = {"txt_id": 1058, "state_key": "setCurrentTemp", "unit": 7}
OPENTHERM_SET_TEMP_DHW = {"txt_id": 1059, "state_key": "setTempDHW", "unit": 7}
OPENTHERM_MODULATION = {"txt_id": 428, "state_key": "modulationPercentage", "unit": 8}

# Menu types
MENU_TYPE_USER = "MU"
MENU_TYPE_INSTALLER = "MI"
MENU_TYPE_SERVICE = "MS"
MENU_TYPES = [MENU_TYPE_USER, MENU_TYPE_INSTALLER, MENU_TYPE_SERVICE]

# Options flow keys for PIN-protected menu sections
MENU_PIN_MS_SERVICE = "menu_pin_ms_service"
MENU_PIN_MI_CALIBRATION = "menu_pin_mi_calibration"
MENU_PIN_MS_FAN = "menu_pin_ms_fan"

# PIN-protected sections: {menu_type: {group_id: options_key}}
MENU_PIN_KEYS: Final = {
    MENU_TYPE_SERVICE: {
        0: MENU_PIN_MS_SERVICE,
        30350: MENU_PIN_MS_FAN,
    },
    MENU_TYPE_INSTALLER: {
        30297: MENU_PIN_MI_CALIBRATION,
    },
}

# Menu item types
MENU_ITEM_TYPE_GROUP = 0
MENU_ITEM_TYPE_VALUE = {1, 2, 3, 4, 5}
MENU_ITEM_TYPE_ON_OFF = 10
MENU_ITEM_TYPE_CHOICE = {11, 111, 112}
MENU_ITEM_TYPE_DIALOGUE = 20
MENU_ITEM_TYPE_UNIVERSAL_VALUE = 106

# Value format types for menu number items
VALUE_FORMAT_TENTH = 2

# Tile IDs enabled by default (shown on OPOP dashboard)
OPOP_DEFAULT_ENABLED_TILES: Final = frozenset({
    1006, 1007, 1008, 1009, 1010, 1011, 1012, 1016, 1017, 2000, 2040
})

# Menu item IDs enabled by default
# 252 = Zasobnik naplneny (button), 2089 = Zadana pokojova teplota (number)
OPOP_DEFAULT_ENABLED_MENU_IDS: Final = frozenset({252, 2089})

# Firing switch dialogue item IDs
OPOP_FIRING_SWITCH_ON_ID: Final = 250   # Roztapeni
OPOP_FIRING_SWITCH_OFF_ID: Final = 251  # Vyhasinani
