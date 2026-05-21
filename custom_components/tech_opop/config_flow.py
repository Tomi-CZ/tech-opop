"""Config flow for Tech OPOP integration."""

import logging
from types import MappingProxyType
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.config_entries import SOURCE_USER, ConfigEntry, ConfigFlowResult
from homeassistant.const import (
    ATTR_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.helpers import aiohttp_client, config_validation as cv

from . import assets
from .const import (
    CONTROLLER,
    CONTROLLERS,
    DOMAIN,
    MENU_PIN_MI_CALIBRATION,
    MENU_PIN_MS_FAN,
    MENU_PIN_MS_SERVICE,
    MENU_TYPE_INSTALLER,
    MENU_TYPE_SERVICE,
    SCAN_INTERVAL_DEFAULT,
    SCAN_INTERVAL_MIN,
    UDID,
    USER_ID,
)
from .tech import Tech, TechError, TechLoginError

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


def controllers_schema(controllers) -> vol.Schema:
    """Build a selection form for the provided controller list."""
    return vol.Schema(
        {
            vol.Optional(CONTROLLERS): cv.multi_select(
                {
                    str(c[CONTROLLER][ATTR_ID]): c[CONTROLLER][CONF_NAME]
                    for c in controllers
                }
            ),
        }
    )


async def validate_input(hass: core.HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate credentials and return API metadata."""
    api = Tech(aiohttp_client.async_get_clientsession(hass))
    if not await api.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD]):
        raise InvalidAuth
    return {
        USER_ID: api.user_id,
        CONF_TOKEN: api.token,
        CONTROLLERS: await api.list_modules(),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tech OPOP."""

    VERSION = 3
    MINOR_VERSION = 0

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._init_info: dict[str, Any] | None = None
        self._controllers: list[dict] | None = None

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial credential entry step."""
        errors = {}
        if user_input is not None:
            try:
                self._init_info = await validate_input(self.hass, user_input)
                return await self.async_step_select_controllers()
            except TechLoginError:
                errors["base"] = "invalid_auth"
            except TechError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_select_controllers(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Display the controller selection form or persist the choice."""
        if not user_input:
            if self._init_info is not None:
                self._controllers = self._create_controllers_array(self._init_info)
            return self.async_show_form(
                step_id="select_controllers",
                data_schema=controllers_schema(self._controllers),
            )
        return await self._async_finish_controller(user_input)

    async def _async_finish_controller(self, user_input: dict[str, str]) -> ConfigFlowResult:
        """Create config entries for the selected controllers."""
        if not self._controllers or not user_input.get(CONTROLLERS):
            return self.async_abort(reason="no_modules")

        selected_ids = user_input[CONTROLLERS]

        def _find_controller(controller_id: str) -> dict | None:
            return next(
                (c for c in self._controllers if c[CONTROLLER].get(ATTR_ID) == int(controller_id)),
                None,
            )

        # Validate all selected controllers exist and are not already configured
        for controller_id in selected_ids:
            controller = _find_controller(controller_id)
            if controller is None:
                return self.async_abort(reason="no_modules")
            await self.async_set_unique_id(controller[CONTROLLER][UDID])
            self._abort_if_unique_id_configured()

        # Create entries for all controllers except the first (which is created via async_create_entry)
        for controller_id in selected_ids[1:]:
            controller = _find_controller(controller_id)
            if controller is None:
                continue
            await self.async_set_unique_id(controller[CONTROLLER][UDID])
            _LOGGER.debug("Adding config entry for: %s", assets.redact(controller, ["token"]))
            await self.hass.config_entries.async_add(self._create_config_entry(controller))

        first = _find_controller(selected_ids[0])
        if first is None:
            return self.async_abort(reason="no_modules")
        await self.async_set_unique_id(first[CONTROLLER][UDID])
        return self.async_create_entry(title=first[CONTROLLER][CONF_NAME], data=first)

    def _create_config_entry(self, controller: dict) -> ConfigEntry:
        """Instantiate an in-memory config entry for controller."""
        return ConfigEntry(
            data=controller,
            title=controller[CONTROLLER][CONF_NAME],
            entry_id=uuid.uuid4().hex,
            discovery_keys=MappingProxyType({}),
            domain=DOMAIN,
            version=ConfigFlow.VERSION,
            minor_version=ConfigFlow.MINOR_VERSION,
            source=SOURCE_USER,
            options={},
            unique_id=None,
            subentries_data=[],
        )

    def _create_controllers_array(self, validated_input: dict[str, Any]) -> list[dict]:
        """Convert API response into config-entry-ready controller payloads."""
        return [
            {
                USER_ID: validated_input[USER_ID],
                CONF_TOKEN: validated_input[CONF_TOKEN],
                CONTROLLER: c,
            }
            for c in validated_input[CONTROLLERS]
        ]


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Tech OPOP - PIN-protected menu sections."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and process the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    MENU_PIN_MS_SERVICE,
                    description={"suggested_value": current.get(MENU_PIN_MS_SERVICE, "")},
                ): str,
                vol.Optional(
                    MENU_PIN_MI_CALIBRATION,
                    description={"suggested_value": current.get(MENU_PIN_MI_CALIBRATION, "")},
                ): str,
                vol.Optional(
                    MENU_PIN_MS_FAN,
                    description={"suggested_value": current.get(MENU_PIN_MS_FAN, "")},
                ): str,
                vol.Required(
                    "scan_interval",
                    default=int(current.get("scan_interval", SCAN_INTERVAL_DEFAULT)),
                ): vol.All(int, vol.Range(min=SCAN_INTERVAL_MIN)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
