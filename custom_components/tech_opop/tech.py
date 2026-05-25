"""Python wrapper for interacting with Tech devices via the eModul API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from aiohttp import ClientSession
else:  # pragma: no cover
    ClientSession = Any

from .const import MENU_PIN_KEYS, MENU_TYPES

_LOGGER = logging.getLogger(__name__)


class Tech:
    """Main class to perform Tech API requests."""

    TECH_API_URL = "https://emodul.eu/api/v1/"

    def __init__(
        self,
        session: ClientSession,
        user_id=None,
        token=None,
        base_url=TECH_API_URL,
    ) -> None:
        """Initialise the Tech API client."""
        self.headers = {"Accept": "application/json", "Accept-Encoding": "gzip"}
        self.base_url = base_url
        self.session = session
        if user_id and token:
            self.user_id = user_id
            self.token = token
            self.headers["Authorization"] = f"Bearer {token}"
            self.authenticated = True
        else:
            self.authenticated = False
        self.modules: dict[str, Any] = {}

    async def get(self, request_path: str) -> dict[str, Any]:
        """Perform a GET request against the Tech API."""
        url = self.base_url + request_path
        _LOGGER.debug("GET %s", url)
        async with self.session.get(url, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.warning("Tech API error: %s", response.status)
                raise TechError(response.status, await response.text())
            return await response.json()

    async def post(self, request_path: str, post_data: str) -> dict[str, Any]:
        """Perform a POST request against the Tech API."""
        url = self.base_url + request_path
        _LOGGER.debug("POST %s", url)
        async with self.session.post(url, data=post_data, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.warning("Tech API error: %s", response.status)
                raise TechError(response.status, await response.text())
            return await response.json()

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate and store bearer token."""
        post_data = json.dumps({"username": username, "password": password})
        try:
            result = await self.post("authentication", post_data)
            self.authenticated = result["authenticated"]
            if self.authenticated:
                self.user_id = str(result["user_id"])
                self.token = result["token"]
                self.headers = {
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "Authorization": f"Bearer {self.token}",
                }
        except TechError as err:
            raise TechLoginError(401, "Unauthorized") from err
        return result["authenticated"]

    async def list_modules(self) -> dict[str, Any]:
        """Return the list of modules for the authenticated user."""
        if not self.authenticated:
            raise TechError(401, "Unauthorized")
        return await self.get(f"users/{self.user_id}/modules")

    async def get_module_data(self, module_udid: str) -> dict[str, Any]:
        """Return a full module payload."""
        if not self.authenticated:
            raise TechError(401, "Unauthorized")
        return await self.get(f"users/{self.user_id}/modules/{module_udid}")

    async def get_module_tiles(self, module_udid: str) -> dict[int, dict[str, Any]]:
        """Return the cached tiles dict for module_udid."""
        return (await self.module_data(module_udid))["tiles"]

    async def get_module_menus(self, module_udid: str, options: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        """Return the cached menus dict for module_udid."""
        return (await self.module_data(module_udid, options=options))["menus"]

    async def module_data(
        self, module_udid: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch and cache zones, tiles and menu items for module_udid."""
        cache = self.modules.setdefault(
            module_udid, {"zones": {}, "tiles": {}, "menus": {}}
        )

        result = await self.get_module_data(module_udid)

        raw_zones = result.get("zones", {}).get("elements", [])
        visible_zones = [
            z for z in raw_zones
            if z and z.get("zone")
            and z["zone"].get("visibility")
            and z["zone"].get("zoneState") != "zoneUnregistered"
        ]
        cache["zones"] = {z["zone"]["id"]: z for z in visible_zones}

        raw_tiles = result.get("tiles", [])
        visible_tiles = [t for t in raw_tiles if t and t.get("visibility")]
        cache["tiles"] = {t["id"]: t for t in visible_tiles}

        menu_items = await self._fetch_menu_data(module_udid, options=options)
        cache["menus"] = menu_items

        _LOGGER.debug(
            "module_data %s: %d zones, %d tiles, %d menu items",
            module_udid, len(cache["zones"]), len(cache["tiles"]), len(cache["menus"]),
        )
        return cache

    async def _fetch_menu_data(
        self, module_udid: str, options: dict[str, Any] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Fetch menu items from all configured menu types.

        PIN-protected sections use path format {group_id}:{pin}.
        PINs come from options (config_entry.options).
        PIN-authenticated results take precedence over base results.
        """
        options = options or {}
        items: dict[str, dict[str, Any]] = {}
        for menu_type in MENU_TYPES:
            pin_groups = MENU_PIN_KEYS.get(menu_type, {})
            paths: list[str] = []
            for group_id, options_key in pin_groups.items():
                pin = options.get(options_key, "").strip()
                if pin:
                    paths.append(
                        f"users/{self.user_id}/modules/{module_udid}/menu/{menu_type}/{group_id}:{pin}"
                    )
            # Base (unauthenticated) path always last — PIN result takes precedence via setdefault
            paths.append(f"users/{self.user_id}/modules/{module_udid}/menu/{menu_type}/")
            for path in paths:
                try:
                    result = await self.get(path)
                    for element in result.get("data", {}).get("elements", []):
                        item_id = element.get("id")
                        if item_id is not None:
                            items.setdefault(f"{menu_type}_{item_id}", element)
                except TechError:
                    _LOGGER.debug("Menu path %s unavailable for %s", path, module_udid)
        return items

    async def set_menu_value(
        self,
        module_udid: str,
        menu_type: str,
        ido: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Write a menu parameter value via the Tech API."""
        if not self.authenticated:
            raise TechError(401, "Unauthorized")
        key = f"{menu_type}_{ido}"
        item = self.modules.get(module_udid, {}).get("menus", {}).get(key, {})
        if item.get("duringChange") == "t":
            raise TechDuringChangeError(key)
        path = f"users/{self.user_id}/modules/{module_udid}/menu/{menu_type}/ido/{ido}"
        return await self.post(path, json.dumps(data))


class TechDuringChangeError(Exception):
    """Raised when a menu parameter is currently being updated by the boiler."""

    def __init__(self, key: str) -> None:
        self.key = key


class TechError(Exception):
    """Raised when a Tech API request results in an error."""

    def __init__(self, status_code: int, status: str) -> None:
        self.status_code = status_code
        self.status = status


class TechLoginError(Exception):
    """Raised when a Tech API login attempt fails."""

    def __init__(self, status_code: int, status: str) -> None:
        self.status_code = status_code
        self.status = status
