"""Updates that Ultimate Updater does not do through the integration API."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.components.update import UpdateEntityFeature
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.ultimate_updater.const import BULK_ALL, CONF_BULK_TARGETS, DOMAIN
from custom_components.ultimate_updater.helpers import capability_block, learned_block
from custom_components.ultimate_updater.repairs import ApiBlockedRepairFlow

from .conftest import FakeUu, setup_entry

CAPS_STOPPED_OFF = {
    "api_version": 1,
    "capabilities": {
        "stopped_container": {"update": {"configured": False, "behavior": "skipped"}},
        "stopped_vm": {"update": {"configured": True, "behavior": "lifecycle_update"}},
    },
}


async def _tick(hass: HomeAssistant, seconds: float = 31) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, f"api_update_blocked_{entry.entry_id}")


def _can_install(hass: HomeAssistant, entity_id: str) -> bool:
    return bool(hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES] & UpdateEntityFeature.INSTALL)


def test_helpers() -> None:
    failed = {"last_update": {"status": "failed", "exit_code": 42}}
    assert learned_block(failed) == "API_UNSAFE_SCRIPT_PATH"
    assert learned_block({"last_update": {"status": "failed", "exit_code": 43}}) == "API_PREFLIGHT_UNAVAILABLE"
    assert learned_block({"last_update": {"status": "failed", "exit_code": 1}}) is None
    assert learned_block({"last_update": {"status": "completed", "exit_code": 42}}) is None
    assert learned_block(None, "❌ API_UNSAFE_SCRIPT_PATH: custom update scripts") == "API_UNSAFE_SCRIPT_PATH"

    stopped_ct = {"id": "110", "type": "lxc", "skip_reason": {"code": "STOPPED_READ_ONLY"}}
    stopped_vm = {"id": "120", "type": "vm", "skip_reason": {"code": "STOPPED_READ_ONLY"}}
    assert capability_block(stopped_ct, CAPS_STOPPED_OFF) == "STOPPED_UPDATE_DISABLED"
    assert capability_block(stopped_vm, CAPS_STOPPED_OFF) is None
    assert capability_block({"id": "111", "type": "lxc"}, CAPS_STOPPED_OFF) is None
    assert capability_block(stopped_ct, {}) is None  # older Ultimate Updater without /capabilities


async def test_refused_at_start(hass: HomeAssistant, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    """409 API_UNSAFE_SCRIPT_PATH: no "Install" any more, hint and repair issue."""
    fake_uu.refuse["lxc:103"] = (409, "API_UNSAFE_SCRIPT_PATH")
    await setup_entry(hass, entry)
    assert _can_install(hass, "update.db_packages")
    assert _issue(hass, entry) is None

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("update", "install", {"entity_id": "update.db_packages"}, blocking=True)
    assert err.value.translation_key == "api_unsafe_script_path"
    await hass.async_block_till_done()

    state = hass.states.get("update.db_packages")
    assert state.attributes["api_update_blocked"] == "API_UNSAFE_SCRIPT_PATH"
    assert "Pi-hole" in state.attributes["api_update_hint"]
    assert "Not updatable via the API" in state.attributes["release_summary"]
    assert not _can_install(hass, "update.db_packages")
    assert _can_install(hass, "update.web_packages")
    issue = _issue(hass, entry)
    assert issue is not None and issue.is_fixable
    assert issue.translation_placeholders["targets"] == "103 · db"

    # the next attempt is refused by the integration itself
    posts = len(fake_uu.posts())
    with pytest.raises(HomeAssistantError):
        await entry.runtime_data.async_update("lxc:103")
    assert len(fake_uu.posts()) == posts

    # collective updates skip it
    fake_uu.auto_complete = True
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.ultimate_updater_update_vms_cts_with_security_updates"}, blocking=True
    )
    for _ in range(10):
        await _tick(hass, 3)
        if entry.runtime_data.bulk is None:
            break
    assert [p for p, _ in fake_uu.posts()[posts:]] == ["update/lxc:101"]
    assert entry.runtime_data.bulk_result == "1 ok, 0 failed, 0 not started, 1 not updatable via API"

    # repair flow: "configuration changed" → allowed again
    flow = ApiBlockedRepairFlow(entry.entry_id)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.issue_id = f"api_update_blocked_{entry.entry_id}"
    result = await flow.async_step_confirm({})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert _can_install(hass, "update.db_packages")
    assert _issue(hass, entry) is None


async def test_refused_by_job(hass: HomeAssistant, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    """The job fails with exit code 42 (guest-side check of Ultimate Updater)."""
    await setup_entry(hass, entry)
    await hass.services.async_call("update", "install", {"entity_id": "update.web_packages"}, blocking=True)
    fake_uu.finish_all("failed")
    fake_uu.targets[0]["last_update"] = {"status": "failed", "exit_code": 42}
    await _tick(hass, 3)
    assert hass.states.get("update.web_packages").attributes["api_update_blocked"] == "API_UNSAFE_SCRIPT_PATH"
    assert _issue(hass, entry) is not None

    # survives a restart
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert not _can_install(hass, "update.web_packages")

    # a new Ultimate Updater version may allow it again
    fake_uu.version = "5.3.0"
    await entry.runtime_data.async_refresh_status()
    await hass.async_block_till_done()
    assert _can_install(hass, "update.web_packages")
    assert _issue(hass, entry) is None


async def test_ordinary_failure_does_not_block(hass: HomeAssistant, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    await setup_entry(hass, entry)
    await hass.services.async_call("update", "install", {"entity_id": "update.web_packages"}, blocking=True)
    fake_uu.finish_all("failed")
    fake_uu.targets[0]["last_update"] = {"status": "failed", "exit_code": 1}
    await _tick(hass, 3)
    assert hass.states.get("update.web_packages").attributes["api_update_blocked"] is None
    assert _can_install(hass, "update.web_packages")


async def test_stopped_guest(hass: HomeAssistant, fake_uu: FakeUu, entry: MockConfigEntry) -> None:
    """STOPPED_CONTAINER="false": shut down CTs are not updatable, also not with "all" collective updates."""
    fake_uu.capabilities = CAPS_STOPPED_OFF
    fake_uu.targets[2]["skip_reason"] = {"code": "STOPPED_READ_ONLY"}
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={CONF_BULK_TARGETS: BULK_ALL})
    await setup_entry(hass, entry)

    coordinator = entry.runtime_data
    assert coordinator.update_block("lxc:103") == "STOPPED_UPDATE_DISABLED"
    assert coordinator.update_block("lxc:101") is None
    with pytest.raises(HomeAssistantError) as err:
        await coordinator.async_update("lxc:103")
    assert err.value.translation_key == "stopped_update_disabled"
    todo, stopped, blocked = coordinator.bulk_candidates(fake_uu.targets, security_only=False)
    assert [t["id"] for t in todo] == ["lxc:101", "vm:200"]
    assert (stopped, blocked) == (1, 0)
    # a configuration-based block needs no repair issue
    assert _issue(hass, entry) is None
