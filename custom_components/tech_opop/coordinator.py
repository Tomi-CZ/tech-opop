"""Tech DataUpdateCoordinator."""

import asyncio
import logging
from datetime import timedelta

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_TIMEOUT, CONTROLLER, DOMAIN, SCAN_INTERVAL_DEFAULT, SCAN_INTERVAL_MIN, UDID
from .tech import Tech, TechError, TechLoginError

_LOGGER = logging.getLogger(__name__)


class TechCoordinator(DataUpdateCoordinator):
    """Coordinate periodic refreshes from the Tech HTTP API."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, session: ClientSession, user_id: str, token: str, config_entry: ConfigEntry | None = None
    ) -> None:
        """Initialise the coordinator."""
        interval = max(
            SCAN_INTERVAL_MIN,
            int(config_entry.options.get("scan_interval", SCAN_INTERVAL_DEFAULT) if config_entry else SCAN_INTERVAL_DEFAULT),
        )
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=interval))
        self.api = Tech(session, user_id, token)

    async def _async_update_data(self) -> dict:
        """Fetch the latest module data."""
        _LOGGER.debug("Updating data for: %s", self.config_entry.data[CONTROLLER][CONF_NAME])
        try:
            async with asyncio.timeout(API_TIMEOUT):
                return await self.api.module_data(
                    self.config_entry.data[CONTROLLER][UDID],
                    options=self.config_entry.options,
                )
        except TechLoginError as err:
            raise ConfigEntryAuthFailed from err
        except TechError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
