"""Sidebar panel and its websocket API."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ultimate_updater.const import CONF_ALLOW_REBOOT

from .conftest import FakeUu, setup_entry


async def test_systems(hass: HomeAssistant, hass_ws_client, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={CONF_ALLOW_REBOOT: True, "exclude_targets": ["lxc:103"]})
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ultimate_updater/systems"})
    msg = await client.receive_json()
    assert msg["success"]
    [instance] = msg["result"]
    assert instance["entry_id"] == entry.entry_id
    assert instance["url"] == "https://192.0.2.10:8765"
    assert instance["entities"]["check_all"] == "button.ultimate_updater_check_all"
    assert instance["entities"]["job_finished"] == "event.ultimate_updater_job_finished"
    web = next(t for t in instance["targets"] if t["id"] == "lxc:101")
    assert web["label"] == "101 · web"
    assert web["has_security"] is True
    assert web["entities"]["packages"] == "update.web_packages"
    assert web["entities"]["security_updates"] == "sensor.web_security_updates"
    assert web["entities"]["reboot"] == "button.web_reboot"
    host = next(t for t in instance["targets"] if t["id"] == "host:pve")
    assert host["host"] is True
    assert next(t for t in instance["targets"] if t["id"] == "lxc:103")["excluded"] is True


async def test_job_log(hass: HomeAssistant, hass_ws_client, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    fake_uu.jobs.append({"unit": "uu-9", "target": "lxc:101", "state": "failed", "exit_code": 100})
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "target_id": "lxc:101"}
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["unit"] == "uu-9"
    assert msg["result"]["log"] == "E: apt failed"

    await client.send_json_auto_id(
        {"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "target_id": "vm:200"}
    )
    assert (await client.receive_json())["result"] is None


async def test_panel_registered(hass: HomeAssistant, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    hass.config.components.add("frontend")
    with (
        patch("custom_components.ultimate_updater.panel.panel_custom.async_register_panel") as register,
        patch("custom_components.ultimate_updater.panel.frontend.async_remove_panel") as remove,
    ):
        await setup_entry(hass, entry)
        assert register.call_count == 1
        kwargs = register.call_args.kwargs
        assert kwargs["frontend_url_path"] == "ultimate-updater"
        assert kwargs["webcomponent_name"] == "ultimate-updater-panel"
        assert kwargs["require_admin"] is True
        assert kwargs["module_url"].startswith("/ultimate_updater_static/ultimate-updater-panel.js?v=")

        assert await hass.config_entries.async_unload(entry.entry_id)
        remove.assert_called_once_with(hass, "ultimate-updater")


async def test_jobs_and_logs_of_any_job(
    hass: HomeAssistant, hass_ws_client, fake_uu: FakeUu, entry: MockConfigEntry
) -> None:
    fake_uu.jobs.append(
        {"unit": "uu-7", "target": "host:pve", "state": "completed", "type": "update-node",
         "started_at": "2026-10-17T07:00:00Z", "finished_at": "2026-10-17T07:05:00Z"}
    )  # fmt: skip
    fake_uu.jobs.append(
        {
            "unit": "uu-8",
            "target": "lxc:101",
            "state": "running",
            "type": "update",
            "started_at": "2026-10-17T08:00:00Z",
        }
    )
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "ultimate_updater/jobs", "entry_id": entry.entry_id})
    jobs = (await client.receive_json())["result"]
    assert [j["unit"] for j in jobs] == ["uu-8", "uu-7", "uu-0"]
    assert jobs[1]["target_name"] == "pve" and jobs[1]["target_id"] == "host:pve"

    # log of a successful job (not only failed ones), cached once finished
    await client.send_json_auto_id({"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "unit": "uu-7"})
    result = (await client.receive_json())["result"]
    assert result["log"] == "E: apt failed" and result["state"] == "completed"
    assert entry.runtime_data.job_logs["uu-7"] == "E: apt failed"

    # a running job is read again on every call and not cached
    await client.send_json_auto_id({"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "unit": "uu-8"})
    assert (await client.receive_json())["result"]["state"] == "running"
    assert "uu-8" not in entry.runtime_data.job_logs

    # latest job of a host (runs as node job)
    await client.send_json_auto_id(
        {"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "target_id": "host:pve"}
    )
    assert (await client.receive_json())["result"]["unit"] == "uu-7"


async def test_job_log_without_permission(
    hass: HomeAssistant, hass_ws_client, fake_uu: FakeUu, entry: MockConfigEntry
) -> None:
    from http import HTTPStatus

    fake_uu.jobs.append({"unit": "uu-7", "target": "lxc:101", "state": "completed"})
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)
    fake_uu.status = HTTPStatus.FORBIDDEN
    await client.send_json_auto_id({"type": "ultimate_updater/job_log", "entry_id": entry.entry_id, "unit": "uu-7"})
    assert (await client.receive_json())["result"]["error"] == "no_permission"
