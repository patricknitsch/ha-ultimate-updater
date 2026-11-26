"""Data coordinator of the Ultimate Updater integration.

One coordinator per config entry. It polls the light-weight job list (every 30 s when idle,
every 2 s while a job runs) and reads the full status of all targets every N minutes, right after
a job has finished and after every action. Actions and the collective update live here as well, so
that no two jobs are started at the same time.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UuAuthError, UuClient, UuError
from .const import (
    BULK_ALL,
    BUSY_STATES,
    CONF_ALLOW_REBOOT,
    CONF_BULK_TARGETS,
    CONF_EXCLUDE,
    CONF_POLL_BUSY,
    CONF_POLL_IDLE,
    CONF_REMOVE_STALE,
    CONF_STATUS_INTERVAL,
    DEFAULT_POLL_BUSY,
    DEFAULT_POLL_IDLE,
    DEFAULT_STATUS_INTERVAL,
    DOMAIN,
    FAILURE_STATES,
    JOB_TIMEOUT_S,
    SUCCESS_STATES,
)
from .helpers import (
    BLOCK_PREFLIGHT,
    BLOCK_UNSAFE_SCRIPT,
    Job,
    Target,
    capability_block,
    is_host,
    is_stopped,
    jobs_of,
    label,
    learned_block,
    security_updates,
    stopped_update_enabled,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
ISSUE_API_BLOCKED = "api_update_blocked"

# API error code → translation key of the exception (see docs/api-v1.md of Ultimate Updater)
ERROR_TRANSLATIONS = {
    BLOCK_UNSAFE_SCRIPT: "api_unsafe_script_path",
    BLOCK_PREFLIGHT: "api_preflight_unavailable",
    "BACKUP_REQUIRED": "backup_required",
    "REBOOT_NOT_REQUIRED": "reboot_not_required",
    "REBOOT_UNSUPPORTED": "reboot_unsupported",
    "TARGET_OFFLINE": "target_offline",
    "JOB_CONFLICT": "job_running",
    "JOB_ALREADY_RUNNING": "job_running",
}
BLOCK_TRANSLATIONS = {
    BLOCK_UNSAFE_SCRIPT: "api_unsafe_script_path",
    BLOCK_PREFLIGHT: "api_preflight_unavailable",
    "STOPPED_UPDATE_DISABLED": "stopped_update_disabled",
}

type UuConfigEntry = ConfigEntry[UuCoordinator]


@dataclass
class UuData:
    """Snapshot of the Ultimate Updater state."""

    targets: dict[str, Target] = field(default_factory=dict)
    jobs: list[Job] = field(default_factory=list)
    version: dict[str, Any] = field(default_factory=dict)
    generated_at: str | None = None

    @property
    def job_running(self) -> bool:
        return any(j.get("state") in BUSY_STATES for j in self.jobs)

    def busy_jobs(self) -> list[Job]:
        return [j for j in self.jobs if j.get("state") in BUSY_STATES]

    def jobs_of(self, target_id: str) -> list[Job]:
        t = self.targets.get(target_id)
        return jobs_of(t, self.jobs) if t else []


@dataclass
class BulkRun:
    """Running collective update."""

    security_only: bool
    total: int = 0
    index: int = 0
    current: str | None = None  # target id that is being updated
    stop: bool = False


@dataclass
class BulkResult:
    ok: int = 0
    unchanged: int = 0
    failed: int = 0
    not_started: int = 0
    stopped_skipped: int = 0
    blocked: int = 0  # not updatable through the API

    def __str__(self) -> str:
        text = f"{self.ok} ok"
        if self.unchanged:
            text += f", {self.unchanged} unchanged"
        text += f", {self.failed} failed, {self.not_started} not started"
        if self.stopped_skipped:
            text += f", {self.stopped_skipped} shut down skipped"
        if self.blocked:
            text += f", {self.blocked} not updatable via API"
        return text


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.api_blocks")


async def async_remove_store(hass: HomeAssistant, entry_id: str) -> None:
    await _store(hass, entry_id).async_remove()
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_API_BLOCKED}_{entry_id}")


class UuCoordinator(DataUpdateCoordinator[UuData]):
    """Polls Ultimate Updater and runs its actions."""

    config_entry: UuConfigEntry

    def __init__(self, hass: HomeAssistant, entry: UuConfigEntry, client: UuClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._opt(entry, CONF_POLL_IDLE, DEFAULT_POLL_IDLE)),
        )
        self.client = client
        self._last_status = 0.0  # monotonic time of the last full status read
        self._force_status = True
        self._version: dict[str, Any] = {}
        self._targets: dict[str, Target] = {}
        self._generated_at: str | None = None
        # unit → state of the previous poll; None until the first poll (nothing is reported then)
        self._known_jobs: dict[str, str] | None = None
        self._action_lock = asyncio.Lock()
        self._job_listeners: list[Callable[[Job, Target | None], None]] = []
        self._target_listeners: list[Callable[[], None]] = []
        self.job_logs: dict[str, str] = {}
        self._log_tried: set[str] = set()
        self._no_log_permission = False
        self.bulk: BulkRun | None = None
        self.bulk_result: str | None = None
        # device of the instance itself, parent of the system devices
        self.hub_device_id: str | None = None
        # GET /capabilities (empty if the Ultimate Updater version does not have it)
        self.capabilities: dict[str, Any] = {}
        # systems whose API update Ultimate Updater refused: target id → {"code", "stopped", "version"}
        self.api_blocks: dict[str, dict[str, Any]] = {}
        self._store = _store(hass, entry.entry_id)
        self._blocks_dirty = False

    # ── options ──
    @staticmethod
    def _opt(entry: ConfigEntry, key: str, default: Any) -> Any:
        return entry.options.get(key, default)

    def option(self, key: str, default: Any = None) -> Any:
        return self._opt(self.config_entry, key, default)

    @property
    def allow_reboot(self) -> bool:
        return bool(self.option(CONF_ALLOW_REBOOT, False))

    def is_excluded(self, t: Target) -> bool:
        return str(t.get("id")) in (self.option(CONF_EXCLUDE, []) or [])

    # ── updates that Ultimate Updater does not do through the API ──
    async def async_load_blocks(self) -> None:
        stored = await self._store.async_load() or {}
        blocks = stored.get("blocks") if isinstance(stored, dict) else None
        self.api_blocks = {str(k): v for k, v in (blocks or {}).items() if isinstance(v, dict) and v.get("code")}

    def _save_blocks(self) -> None:
        self._blocks_dirty = True
        self._store.async_delay_save(self._blocks_data, 1)
        self._sync_issue()

    def _blocks_data(self) -> dict[str, Any]:
        self._blocks_dirty = False
        return {"blocks": self.api_blocks}

    async def async_shutdown(self) -> None:
        """Write pending changes right away (the store of a reloaded entry is a new one)."""
        await super().async_shutdown()
        if self._blocks_dirty:
            await self._store.async_save(self._blocks_data())

    @callback
    def async_sync_issue(self) -> None:
        self._sync_issue()

    def _sync_issue(self) -> None:
        """Repair issue that lists the systems the API cannot update."""
        issue_id = f"{ISSUE_API_BLOCKED}_{self.config_entry.entry_id}"
        if not self.api_blocks:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        targets = self.data.targets if self.data else self._targets
        names = sorted(label(targets[tid]) if tid in targets else tid for tid in self.api_blocks)
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_API_BLOCKED,
            translation_placeholders={"targets": ", ".join(names), "title": self.config_entry.title},
            data={"entry_id": self.config_entry.entry_id},
        )

    def _set_block(self, target_id: str, code: str) -> None:
        t = self._targets.get(target_id) or {}
        old = self.api_blocks.get(target_id)
        self.api_blocks[target_id] = {
            "code": code,
            "stopped": is_stopped(t),
            "version": self._version.get("installed"),
        }
        if old != self.api_blocks[target_id]:
            _LOGGER.warning(
                "Ultimate Updater does not update %s through the API (%s) – update it in its Web UI, CLI or schedule",
                t.get("name") or target_id,
                code,
            )
            self._save_blocks()

    @callback
    def async_clear_blocks(self) -> None:
        """Forget the refused API updates (e.g. after the configuration of Ultimate Updater was changed)."""
        self.api_blocks = {}
        self._save_blocks()
        self.async_update_listeners()

    def update_block(self, target_id: str) -> str | None:
        """Why Ultimate Updater would refuse an API update of this system, None if it is possible."""
        t = self._targets.get(target_id)
        block = self.api_blocks.get(target_id)
        if block:
            # "could not be inspected while the guest is shut down" no longer applies once it runs
            if block.get("code") == BLOCK_PREFLIGHT and block.get("stopped") and t and not is_stopped(t):
                del self.api_blocks[target_id]
                self._save_blocks()
            else:
                return str(block["code"])
        return capability_block(t, self.capabilities) if t else None

    def _learn_blocks(self, finished: list[Job]) -> None:
        """A finished, failed API update tells whether Ultimate Updater refused it (exit code 42/43)."""
        for job in finished:
            if job.get("state") not in FAILURE_STATES or "update" not in str(job.get("type") or "update"):
                continue
            target = self._job_target(job)
            if target is None:
                continue
            code = learned_block(target, self.job_logs.get(str(job.get("unit") or "")))
            if code:
                self._set_block(str(target["id"]), code)

    def _check_version(self) -> None:
        """A new version of Ultimate Updater may update these systems: forget the refusals of older ones."""
        installed = self._version.get("installed")
        if not installed or not self.api_blocks:
            return
        if any(b.get("version") and b.get("version") != installed for b in self.api_blocks.values()):
            _LOGGER.info("Ultimate Updater %s installed – retrying API updates that were refused before", installed)
            self.api_blocks = {k: v for k, v in self.api_blocks.items() if v.get("version") in (None, installed)}
            self._save_blocks()

    # ── listeners ──
    @callback
    def async_add_job_listener(self, cb: Callable[[Job, Target | None], None]) -> Callable[[], None]:
        """Called for every job that has finished (not for jobs known at startup)."""
        self._job_listeners.append(cb)
        return lambda: self._job_listeners.remove(cb)

    # ── polling ──
    async def _async_update_data(self) -> UuData:
        try:
            jobs = await self.client.get_jobs()
            prev = self.data
            busy = any(j.get("state") in BUSY_STATES for j in jobs)
            finished = self._finished_jobs(jobs)
            status_due = time.monotonic() - self._last_status >= 60 * float(
                self.option(CONF_STATUS_INTERVAL, DEFAULT_STATUS_INTERVAL)
            )
            # a job that has finished changes counters/reboot flags → read the status right away
            if self._force_status or status_due or finished or (prev and prev.job_running and not busy):
                status = await self.client.get_status()
                self._targets = {
                    str(t["id"]): t
                    for t in status.get("targets") or []
                    if isinstance(t, dict) and t.get("id") not in (None, "")
                }
                self._generated_at = status.get("generated_at")
                self._last_status = time.monotonic()
                self._force_status = False
                try:
                    self._version = await self.client.get_updater_version()
                except UuError as err:
                    _LOGGER.debug("Updater version not available: %s", err)
                try:
                    self.capabilities = await self.client.get_capabilities()
                except UuAuthError:
                    raise
                except UuError as err:
                    _LOGGER.debug("Capabilities not available: %s", err)
                    self.capabilities = {}
        except UuAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except UuError as err:
            raise UpdateFailed(str(err)) from err

        await self._fetch_failure_logs(jobs)
        self._check_version()
        self._learn_blocks(finished)
        self._set_interval(busy)
        data = UuData(targets=self._targets, jobs=jobs, version=self._version, generated_at=self._generated_at)
        self._report_finished(finished, data)
        self._remove_stale_devices(data)
        return data

    def _set_interval(self, busy: bool) -> None:
        seconds = (
            self.option(CONF_POLL_BUSY, DEFAULT_POLL_BUSY)
            if busy or self.bulk
            else self.option(CONF_POLL_IDLE, DEFAULT_POLL_IDLE)
        )
        self.update_interval = timedelta(seconds=max(1, float(seconds)))

    def _finished_jobs(self, jobs: list[Job]) -> list[Job]:
        """Jobs that reached a final state since the previous poll."""
        known = self._known_jobs
        self._known_jobs = {str(j.get("unit")): str(j.get("state")) for j in jobs if j.get("unit")}
        if known is None:
            return []
        return [
            j
            for j in jobs
            if j.get("unit")
            and j.get("state") not in BUSY_STATES
            and (str(j["unit"]) not in known or known[str(j["unit"])] in BUSY_STATES)
        ]

    def _job_target(self, job: Job) -> Target | None:
        """Target of a job (host jobs run as node jobs)."""
        target = self._targets.get(str(job.get("target")))
        if target is None:
            target = next((t for t in self._targets.values() if job in jobs_of(t, [job])), None)
        return target

    def _report_finished(self, finished: list[Job], data: UuData) -> None:
        for job in finished:
            target = self._job_target(job)
            for cb in list(self._job_listeners):
                cb(job, target)

    async def _fetch_failure_logs(self, jobs: list[Job]) -> None:
        """Last log lines of failed jobs (each job once; needs the "logs" permission)."""
        if self._no_log_permission:
            return
        for job in jobs:
            unit = str(job.get("unit") or "")
            if not unit or job.get("state") not in FAILURE_STATES or unit in self._log_tried:
                continue
            self._log_tried.add(unit)
            try:
                self.job_logs[unit] = await self.client.get_job_log(unit)
            except UuAuthError:
                self._no_log_permission = True
                _LOGGER.info('The API token has no "logs" permission – logs of failed jobs are not fetched')
                return
            except UuError as err:
                _LOGGER.debug("Log of job %s not available: %s", unit, err)
        units = {str(j.get("unit")) for j in jobs}
        for unit in [u for u in self.job_logs if u not in units]:
            del self.job_logs[unit]

    def _remove_stale_devices(self, data: UuData) -> None:
        """Devices of targets that Ultimate Updater no longer reports (e.g. deleted in Proxmox)."""
        if not data.targets or not self.option(CONF_REMOVE_STALE, True):
            return
        registry = dr.async_get(self.hass)
        entry_id = self.config_entry.entry_id
        for device in dr.async_entries_for_config_entry(registry, entry_id):
            for domain, ident in device.identifiers:
                if domain != DOMAIN or not ident.startswith(f"{entry_id}_"):
                    continue
                if ident.removeprefix(f"{entry_id}_") not in data.targets:
                    _LOGGER.info("Removing %s: no longer reported by Ultimate Updater", device.name)
                    registry.async_update_device(device.id, remove_config_entry_id=entry_id)

    async def async_refresh_status(self) -> None:
        """Read the full status at the next poll and poll right away."""
        self._force_status = True
        await self.async_request_refresh()

    # ── actions ──
    def _action_error(self, err: UuError, target_id: str | None = None) -> HomeAssistantError:
        """Translated error for a refused action; remembers refused API updates."""
        if target_id and err.code in (BLOCK_UNSAFE_SCRIPT, BLOCK_PREFLIGHT):
            self._set_block(target_id, err.code)
        key = ERROR_TRANSLATIONS.get(err.code or "")
        if key is None:
            key = "permission_denied" if err.status == 403 else "action_failed"
        t = self._targets.get(target_id or "") or {}
        return HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={"error": str(err), "target": str(t.get("name") or target_id or "")},
        )

    async def _run_action(self, fn: Callable[[], Awaitable[Any]], target_id: str | None = None) -> None:
        """Starts a job unless one is running (Ultimate Updater runs one job at a time)."""
        if self.bulk:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="bulk_running")
        async with self._action_lock:
            try:
                jobs = await self.client.get_jobs()
                if any(j.get("state") in BUSY_STATES for j in jobs):
                    raise HomeAssistantError(translation_domain=DOMAIN, translation_key="job_running")
                await fn()
            except UuError as err:
                raise self._action_error(err, target_id) from err
        self._set_interval(True)
        await self.async_refresh_status()

    def _target(self, target_id: str) -> Target:
        t = self.data.targets.get(target_id) if self.data else None
        if t is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_target",
                translation_placeholders={"target": target_id},
            )
        return t

    async def async_check(self, target_id: str) -> None:
        t = self._target(target_id)
        if is_host(t):
            await self._run_action(lambda: self.client.check_node(str(t.get("node"))))
        else:
            await self._run_action(lambda: self.client.check(target_id))

    async def async_update(self, target_id: str) -> None:
        """Hosts via node update (guests are not touched)."""
        t = self._target(target_id)
        if block := self.update_block(target_id):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=BLOCK_TRANSLATIONS[block],
                translation_placeholders={"target": str(t.get("name") or target_id), "error": block},
            )
        if is_host(t):
            await self._run_action(lambda: self.client.update_node(str(t.get("node"))), target_id)
        else:
            await self._run_action(lambda: self.client.update(target_id), target_id)

    async def async_reboot(self, target_id: str) -> None:
        self._target(target_id)
        if not self.allow_reboot:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="reboot_disabled")
        await self._run_action(lambda: self.client.reboot(target_id), target_id)

    async def async_check_all(self) -> None:
        await self._run_action(self.client.check_all)

    async def async_cancel_jobs(self) -> None:
        """Requests cancellation of all running jobs."""
        try:
            for job in self.data.busy_jobs() if self.data else []:
                await self.client.cancel_job(str(job.get("unit")))
        except UuError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="permission_denied" if err.status == 403 else "action_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.async_request_refresh()

    # ── collective update ──
    def bulk_candidates(self, targets: list[Target], security_only: bool) -> tuple[list[Target], int, int]:
        """VMs/CTs for a collective update, the number of shut down ones left out and the number of those
        that Ultimate Updater does not update through the API."""
        candidates = [
            t
            for t in targets
            if not is_host(t) and not self.is_excluded(t) and (not security_only or (security_updates(t) or 0) > 0)
        ]
        stopped = 0
        if self.option(CONF_BULK_TARGETS) != BULK_ALL:
            # "running" (default): Ultimate Updater only updates shut down guests if STOPPED_CONTAINER /
            # STOPPED_VM is enabled in its update.conf, otherwise the job fails
            running = [t for t in candidates if not is_stopped(t)]
            stopped, candidates = len(candidates) - len(running), running
        else:
            # "all": still leave out shut down guests if Ultimate Updater reports that it skips them
            keep = [
                t for t in candidates if not is_stopped(t) or stopped_update_enabled(t, self.capabilities) is not False
            ]
            stopped, candidates = len(candidates) - len(keep), keep
        possible = [t for t in candidates if not self.update_block(str(t["id"]))]
        return possible, stopped, len(candidates) - len(possible)

    async def async_start_bulk(self, security_only: bool) -> None:
        if self.bulk:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="bulk_running")
        if self.data and self.data.job_running:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="job_running")
        self.bulk = BulkRun(security_only=security_only)
        self.bulk_result = None
        self.async_update_listeners()
        self.config_entry.async_create_background_task(self.hass, self._run_bulk(self.bulk), f"{DOMAIN}_bulk_update")

    @callback
    def async_stop_bulk(self) -> None:
        if self.bulk:
            self.bulk.stop = True
            _LOGGER.info("Collective update will stop after the current target")

    async def _wait_for_jobs(self, unit: str | None = None) -> str:
        """Waits until no job is running (or the given job has finished); returns its final state."""
        deadline = time.monotonic() + JOB_TIMEOUT_S
        missing = 0
        while True:
            jobs = await self.client.get_jobs()
            if unit:
                job = next((j for j in jobs if j.get("unit") == unit), None)
                if job and job.get("state") not in BUSY_STATES:
                    return str(job.get("state"))
                missing = missing + 1 if job is None else 0
                if missing >= 3:  # a job that does not appear (anymore) counts as finished
                    return "unknown"
            elif not any(j.get("state") in BUSY_STATES for j in jobs):
                return ""
            if time.monotonic() > deadline:
                raise UuError(f"job {unit or ''} did not finish within 3 hours")
            await asyncio.sleep(max(1, float(self.option(CONF_POLL_BUSY, DEFAULT_POLL_BUSY))))

    async def _refused_by_job(self, target_id: str, unit: str) -> bool:
        """Whether a failed update job was refused because the API may not update this system."""
        try:
            status = await self.client.get_status()
        except UuError:
            return False
        targets = [t for t in status.get("targets") or [] if isinstance(t, dict)]
        target = next((t for t in targets if str(t.get("id")) == target_id), None)
        log = self.job_logs.get(unit)
        if log is None and not self._no_log_permission:
            try:
                log = self.job_logs[unit] = await self.client.get_job_log(unit)
            except UuError:
                log = None
        code = learned_block(target, log)
        if code:
            self._set_block(target_id, code)
        return code is not None

    async def _run_bulk(self, bulk: BulkRun) -> None:
        """Updates the VMs/CTs one after the other: Ultimate Updater answers 202 when a job has
        started, so the next update is only started when the previous job has finished."""
        result = BulkResult()
        label = "Update of the VMs/CTs with security updates" if bulk.security_only else "Update of all VMs/CTs"
        try:
            status = await self.client.get_status()
            targets = [t for t in status.get("targets") or [] if isinstance(t, dict) and t.get("id")]
            todo, result.stopped_skipped, result.blocked = self.bulk_candidates(targets, bulk.security_only)
            bulk.total = len(todo)
            _LOGGER.info("%s: %d targets, one after the other", label, len(todo))
            for i, t in enumerate(todo):
                name = t.get("name") or t.get("id")
                if bulk.stop:
                    result.not_started = len(todo) - i
                    _LOGGER.info("%s stopped – %d targets not updated", label, result.not_started)
                    break
                bulk.index, bulk.current = i + 1, str(t["id"])
                self.async_update_listeners()
                # another job (e.g. started in the Web UI) must not overlap with ours
                await self._wait_for_jobs()
                try:
                    res = await self.client.update(str(t["id"]))
                except UuError as err:
                    if err.code in (BLOCK_UNSAFE_SCRIPT, BLOCK_PREFLIGHT):
                        self._set_block(str(t["id"]), err.code)
                        result.blocked += 1
                    else:
                        result.failed += 1
                    _LOGGER.warning("Update of %s could not be started: %s", name, err)
                    continue
                await self.async_request_refresh()
                unit = str(res.get("job") or "") if isinstance(res, dict) else ""
                state = await self._wait_for_jobs(unit or None)
                if not unit or state in (*SUCCESS_STATES, "unknown"):
                    result.ok += 1
                elif state == "skipped":
                    result.unchanged += 1
                elif await self._refused_by_job(str(t["id"]), unit):  # refused by the job itself (exit 42/43)
                    result.blocked += 1
                else:
                    result.failed += 1
                _LOGGER.info("Update of %s: %s (%d/%d)", name, state or "finished", i + 1, len(todo))
            _LOGGER.info("%s finished: %s", label, result)
        except asyncio.CancelledError:
            _LOGGER.info("%s aborted: integration is unloading", label)
            raise
        except UuError as err:
            _LOGGER.error("%s aborted: %s", label, err)
        finally:
            self.bulk = None
            self.bulk_result = str(result)
        await self.async_refresh_status()
