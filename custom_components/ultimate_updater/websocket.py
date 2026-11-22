"""WebSocket API for the Ultimate Updater panel.

The panel reads the live values from the entity states; this API only tells it which entity belongs
to which system (entity IDs can be renamed) and delivers the log of failed jobs.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import UuError
from .const import DOMAIN, FAILURE_STATES
from .coordinator import UuCoordinator
from .helpers import is_host, is_stopped, label, security_updates

HUB_KEYS = (
    "summary",
    "security_updates_total",
    "normal_updates_total",
    "targets_with_updates",
    "reboot_required_count",
    "unreachable_count",
    "bulk_progress",
    "updater_version",
    "job_running",
    "bulk_active",
    "updater_update",
    "job_finished",
    "check_all",
    "update_all",
    "update_security",
    "stop_bulk",
    "cancel_jobs",
)
TARGET_KEYS = (
    "packages",
    "security_updates",
    "normal_updates",
    "check_status",
    "last_check",
    "job_state",
    "reboot_required",
    "reachable",
    "check",
    "reboot",
)


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_systems)
    websocket_api.async_register_command(hass, ws_job_log)


def _coordinators(hass: HomeAssistant) -> list[UuCoordinator]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED and entry.runtime_data.data is not None
    ]


def _entities(registry: er.EntityRegistry, prefix: str, keys: tuple[str, ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for key in keys:
        for platform in ("binary_sensor", "button", "event", "sensor", "update"):
            if entity_id := registry.async_get_entity_id(platform, DOMAIN, f"{prefix}_{key}"):
                found[key] = entity_id
                break
    return found


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ultimate_updater/systems"})
@callback
def ws_systems(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """All Ultimate Updater instances with their systems and the entity IDs of both."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    result = []
    for coordinator in _coordinators(hass):
        entry = coordinator.config_entry
        data = coordinator.data
        targets = []
        for tid, t in data.targets.items():
            device = devices.async_get_device(identifiers={(DOMAIN, f"{entry.entry_id}_{tid}")})
            targets.append(
                {
                    "id": tid,
                    "name": str(t.get("name") or tid),
                    "label": label(t),
                    "type": str(t.get("type") or ""),
                    "node": str(t.get("node") or ""),
                    "os": t.get("os_display"),
                    "host": is_host(t),
                    "stopped": is_stopped(t),
                    "excluded": coordinator.is_excluded(t),
                    "has_security": (security_updates(t) or 0) > 0,
                    "device_id": device.id if device else None,
                    "device_name": (device.name_by_user or device.name) if device else None,
                    "entities": _entities(entities, f"{entry.entry_id}_{tid}", TARGET_KEYS),
                }
            )
        hub = devices.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
        result.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "url": coordinator.client.base,
                "device_id": hub.id if hub else None,
                "allow_reboot": coordinator.allow_reboot,
                "entities": _entities(entities, entry.entry_id, HUB_KEYS),
                "targets": targets,
            }
        )
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ultimate_updater/job_log",
        vol.Required("entry_id"): str,
        vol.Required("target_id"): str,
    }
)
@websocket_api.async_response
async def ws_job_log(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Latest job of a system and, if it failed, its last log lines."""
    coordinator = next((c for c in _coordinators(hass) if c.config_entry.entry_id == msg["entry_id"]), None)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Unknown Ultimate Updater instance")
        return
    jobs = coordinator.data.jobs_of(msg["target_id"])
    if not jobs:
        connection.send_result(msg["id"], None)
        return
    job = jobs[0]
    unit = str(job.get("unit") or "")
    log = coordinator.job_logs.get(unit)
    error = None
    if log is None and unit and job.get("state") in FAILURE_STATES:
        try:
            log = coordinator.job_logs[unit] = await coordinator.client.get_job_log(unit)
        except UuError as err:
            error = str(err)
    connection.send_result(
        msg["id"],
        {
            "unit": unit,
            "state": job.get("state"),
            "type": job.get("type"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "exit_code": job.get("exit_code"),
            "log": log,
            "error": error,
        },
    )
