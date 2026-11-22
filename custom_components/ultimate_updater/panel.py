"""Sidebar panel "Ultimate Updater": all systems with their state and buttons on one page."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "ultimate-updater"
PANEL_COMPONENT = "ultimate-updater-panel"
STATIC_URL = f"/{DOMAIN}_static"
JS_FILE = Path(__file__).parent / "frontend" / "ultimate-updater-panel.js"

DATA_STATIC = f"{DOMAIN}_static_registered"


def _panel_registered(hass: HomeAssistant) -> bool:
    return PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})


async def async_register_panel(hass: HomeAssistant) -> None:
    """Registers the panel (needs the frontend, which default_config loads).

    Looks at the panels the frontend really has instead of remembering its own state, so a panel left
    over from an earlier setup or reload is replaced. A problem with the panel never stops the
    integration from being set up.
    """
    if "frontend" not in hass.config.components:
        return
    try:
        if not hass.data.get(DATA_STATIC):
            await hass.http.async_register_static_paths(
                [StaticPathConfig(STATIC_URL, str(JS_FILE.parent), cache_headers=False)]
            )
            hass.data[DATA_STATIC] = True
        # cache busting: the browser loads a changed file after an update of the integration
        mtime = await hass.async_add_executor_job(lambda: int(JS_FILE.stat().st_mtime))
        if _panel_registered(hass):
            frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_COMPONENT,
            sidebar_title="Ultimate Updater",
            sidebar_icon="mdi:package-up",
            module_url=f"{STATIC_URL}/{JS_FILE.name}?v={mtime}",
            require_admin=True,
            config={"domain": DOMAIN},
        )
    except Exception:
        _LOGGER.exception("The Ultimate Updater page could not be added to the sidebar")


def async_remove_panel(hass: HomeAssistant, unloading_entry_id: str) -> None:
    """Removes the panel when the last Ultimate Updater instance is unloaded."""
    others = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != unloading_entry_id and e.state is ConfigEntryState.LOADED
    ]
    if not others and _panel_registered(hass):
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
