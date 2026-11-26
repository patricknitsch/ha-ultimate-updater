"""Repair flow: forget the systems that Ultimate Updater refused to update through the API.

Whether Ultimate Updater refuses an API update depends on its update.conf (extra/community/helper updates,
scripts.d) and on what is installed in the guest, which the API does not report. The integration remembers
a refusal; once the configuration has been changed, this flow lets the user try again.
"""

from __future__ import annotations

from typing import Any

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN


class ApiBlockedRepairFlow(ConfirmRepairFlow):
    """Confirm to allow API updates of the refused systems again."""

    def __init__(self, entry_id: str | None) -> None:
        super().__init__()
        self._entry_id = entry_id

    async def async_step_confirm(self, user_input: dict[str, str] | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id or "")
            if entry and entry.domain == DOMAIN and entry.state is ConfigEntryState.LOADED:
                entry.runtime_data.async_clear_blocks()
        return await super().async_step_confirm(user_input)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    return ApiBlockedRepairFlow((data or {}).get("entry_id"))
