"""Sidebar panel "Ultimate Updater": all systems with their state and buttons on one page."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "ultimate-updater"
PANEL_COMPONENT = "ultimate-updater-panel"
STATIC_URL = f"/{DOMAIN}_static"
JS_FILE = Path(__file__).parent / "frontend" / "ultimate-updater-panel.js"

DATA_STATIC = f"{DOMAIN}_static_registered"
DATA_PANEL = f"{DOMAIN}_panel_registered"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Registers the panel once (needs the frontend, which default_config loads)."""
    if hass.data.get(DATA_PANEL) or "frontend" not in hass.config.components:
        return
    if not hass.data.get(DATA_STATIC):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(JS_FILE.parent), cache_headers=False)]
        )
        hass.data[DATA_STATIC] = True
    # cache busting: the browser loads a changed file after an update of the integration
    mtime = await hass.async_add_executor_job(lambda: int(JS_FILE.stat().st_mtime))
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
    hass.data[DATA_PANEL] = True


def async_remove_panel(hass: HomeAssistant) -> None:
    if hass.data.pop(DATA_PANEL, False):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
