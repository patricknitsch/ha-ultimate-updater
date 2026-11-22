/* <ultimate-updater-panel>: sidebar page of the Ultimate Updater integration.
 *
 * All hosts, VMs and containers of every Ultimate Updater instance with pending updates, reboot hint,
 * reachability, last check, latest job and the buttons. The live values come from the entity states
 * (hass.states); the websocket command "ultimate_updater/systems" only maps systems to their entity IDs.
 * Plain web component without dependencies, styled with the theme variables of Home Assistant.
 */

const TXT = {
	de: {
		title: "Ultimate Updater",
		system: "System",
		security: "Sicherheit",
		other: "Weitere",
		lastCheck: "Geprüft",
		job: "Letzter Job",
		actions: "Aktionen",
		checkAll: "Alle prüfen",
		updateAll: "Alle VMs/CTs aktualisieren",
		updateSec: "VMs/CTs mit Sicherheitsupdates",
		stop: "Sammel-Update stoppen",
		cancel: "Job abbrechen",
		check: "Prüfen",
		update: "Aktualisieren",
		reboot: "Neustart",
		details: "Details",
		search: "Suchen …",
		onlyUpdates: "Nur mit Updates",
		showStopped: "Ausgeschaltete zeigen",
		showHosts: "Hosts zeigen",
		jobRunning: "Ein Job läuft",
		bulkRunning: "Sammel-Update",
		bulkLast: "Letztes Sammel-Update",
		rebootNeeded: "Neustart nötig",
		unreachable: "nicht erreichbar",
		stopped: "ausgeschaltet",
		excluded: "von Sammel-Updates ausgenommen",
		updating: "wird aktualisiert …",
		noSystems: "Keine Systeme gefunden.",
		noEntries: "Keine Ultimate-Updater-Instanz eingerichtet.",
		loading: "Lade …",
		log: "Log",
		noLog: "Kein Log vorhanden.",
		yes: "Ja",
		no: "Abbrechen",
		confirmUpdate: n => `${n} aktualisieren? Es werden alle offenen Updates installiert.`,
		confirmHost: n => `Proxmox-Host ${n} aktualisieren? Die Gäste werden dabei nicht angefasst.`,
		confirmReboot: n => `${n} jetzt neu starten?`,
		confirmAll: "Alle laufenden VMs/CTs nacheinander komplett aktualisieren (Hosts und ausgenommene übersprungen)?",
		confirmSec: "Alle VMs/CTs mit Sicherheitsupdates nacheinander aktualisieren? Dort werden ALLE offenen Updates installiert.",
		stoppedHint: " Es ist ausgeschaltet – Ultimate Updater startet es dafür nur mit STOPPED_CONTAINER/STOPPED_VM in seiner update.conf.",
		version: "Version",
		updaterUpdate: "Update für Ultimate Updater verfügbar",
		openWebUi: "Web-UI öffnen",
		types: { host: "Host", lxc: "CT", vm: "VM" },
		jobStates: {
			none: "–",
			running: "läuft",
			pending: "wartet",
			starting: "startet",
			completed: "fertig",
			completed_with_warnings: "fertig mit Warnungen",
			skipped: "nichts zu tun",
			failed: "fehlgeschlagen",
			interrupted: "abgebrochen",
		},
		systems: n => `${n} ${n === 1 ? "System" : "Systeme"}`,
		summary: (u, s) => (u ? `${u} ${u === 1 ? "Update" : "Updates"} auf ${s} ${s === 1 ? "System" : "Systemen"}` : "Keine Updates"),
		summaryReboot: n => `${n} ${n === 1 ? "Neustart" : "Neustarts"} nötig`,
	},
	en: {
		title: "Ultimate Updater",
		system: "System",
		security: "Security",
		other: "Other",
		lastCheck: "Checked",
		job: "Latest job",
		actions: "Actions",
		checkAll: "Check all",
		updateAll: "Update all VMs/CTs",
		updateSec: "VMs/CTs with security updates",
		stop: "Stop collective update",
		cancel: "Cancel job",
		check: "Check",
		update: "Update",
		reboot: "Reboot",
		details: "Details",
		search: "Search …",
		onlyUpdates: "Only with updates",
		showStopped: "Show switched off",
		showHosts: "Show hosts",
		jobRunning: "A job is running",
		bulkRunning: "Collective update",
		bulkLast: "Last collective update",
		rebootNeeded: "reboot required",
		unreachable: "unreachable",
		stopped: "switched off",
		excluded: "excluded from collective updates",
		updating: "updating …",
		noSystems: "No systems found.",
		noEntries: "No Ultimate Updater instance is set up.",
		loading: "Loading …",
		log: "Log",
		noLog: "No log available.",
		yes: "Yes",
		no: "Cancel",
		confirmUpdate: n => `Update ${n}? All pending updates are installed.`,
		confirmHost: n => `Update Proxmox host ${n}? Its guests are not touched.`,
		confirmReboot: n => `Reboot ${n} now?`,
		confirmAll: "Update all running VMs/CTs completely, one after the other (hosts and excluded ones skipped)?",
		confirmSec: "Update all VMs/CTs with security updates, one after the other? ALL pending updates are installed there.",
		stoppedHint: " It is switched off – Ultimate Updater only starts it for this with STOPPED_CONTAINER/STOPPED_VM in its update.conf.",
		version: "Version",
		updaterUpdate: "Update for Ultimate Updater available",
		openWebUi: "Open Web UI",
		types: { host: "Host", lxc: "CT", vm: "VM" },
		jobStates: {
			none: "–",
			running: "running",
			pending: "pending",
			starting: "starting",
			completed: "completed",
			completed_with_warnings: "completed with warnings",
			skipped: "nothing to do",
			failed: "failed",
			interrupted: "interrupted",
		},
		systems: n => `${n} ${n === 1 ? "system" : "systems"}`,
		summary: (u, s) => (u ? `${u} ${u === 1 ? "update" : "updates"} on ${s} ${s === 1 ? "system" : "systems"}` : "No updates"),
		summaryReboot: n => `${n} ${n === 1 ? "reboot" : "reboots"} required`,
	},
};

// Material Design Icons (paths)
const MDI = {
	check: "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
	update: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
	reboot: "M12,4C14.1,4 16.1,4.8 17.6,6.3C20.7,9.4 20.7,14.5 17.6,17.6C15.8,19.5 13.3,20.2 10.9,19.9L11.4,17.9C13.1,18.1 14.9,17.5 16.2,16.2C18.5,13.9 18.5,10.1 16.2,7.7C15.1,6.6 13.5,6 12,6V10.6L7,5.6L12,0.6V4M6.3,17.6C3.7,15 3.3,11 5.1,7.9L6.6,9.4C5.5,11.6 5.9,14.4 7.8,16.2C8.3,16.7 8.9,17.1 9.6,17.4L9,19.4C8,19 7.1,18.4 6.3,17.6Z",
	shield: "M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M11,7H13V13H11V7M11,15H13V17H11V15Z",
	stop: "M18,18H6V6H18V18Z",
	cancel: "M12,2C17.53,2 22,6.47 22,12C22,17.53 17.53,22 12,22C6.47,22 2,17.53 2,12C2,6.47 6.47,2 12,2M15.59,7L12,10.59L8.41,7L7,8.41L10.59,12L7,15.59L8.41,17L12,13.41L15.59,17L17,15.59L13.41,12L17,8.41L15.59,7Z",
	info: "M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
	open: "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z",
	alert: "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
	sleep: "M23,12H17V10L20.39,6H17V4H23V6L19.62,10H23V12M15,16H9V14L12.39,10H9V8H15V10L11.62,14H15V16M7,20H1V18L4.39,14H1V12H7V14L3.62,18H7V20Z",
	menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
};

const BUSY = ["running", "pending", "starting"];
const FAILED = ["failed", "interrupted"];
const TYPE_ORDER = { host: 0, lxc: 1, vm: 2 };

const esc = s =>
	String(s == null ? "" : s).replace(
		/[&<>"']/g,
		c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
	);
const icon = (path, cls = "") => `<svg class="mdi ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;
const numId = id => {
	const m = /(\d+)$/.exec(String(id));
	return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
};

// log without the ASCII banner, systemd lines and empty lines
function cleanLog(log) {
	const lines = String(log || "").split("\n");
	const bannerEnd = lines.findIndex(l => /Ultimate Updater \d+\.\d+/.test(l));
	return lines
		.slice(bannerEnd >= 0 ? bannerEnd + 1 : 0)
		.map(l => l.replace(/\s+$/, ""))
		.filter(l => l.trim() && !/\.service[: ]/.test(l))
		.slice(-40)
		.join("\n");
}

const CSS = `
:host {
	display: block;
	min-height: 100vh;
	background: var(--primary-background-color);
	color: var(--primary-text-color);
	font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, sans-serif));
	--uu-ok: var(--success-color, #43a047);
	--uu-warn: var(--warning-color, #ffa600);
	--uu-err: var(--error-color, #db4437);
	--uu-muted: var(--secondary-text-color);
	--uu-line: var(--divider-color, rgba(127,127,127,.25));
}
.toolbar {
	display: flex; align-items: center; gap: 8px; height: var(--header-height, 56px); padding: 0 12px;
	background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
	position: sticky; top: 0; z-index: 2; box-sizing: border-box;
	border-bottom: var(--app-header-border-bottom, none);
}
.toolbar .title { font-size: 20px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-left: 4px; }
.menu { display: none; background: none; border: 0; color: inherit; padding: 8px; cursor: pointer; border-radius: 50%; }
.menu.show { display: inline-flex; }
.content { max-width: 1280px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
.filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-bottom: 16px; }
.filters input[type=search] {
	flex: 1 1 220px; min-width: 0; padding: 10px 12px; border-radius: 8px; font: inherit;
	border: 1px solid var(--uu-line); background: var(--card-background-color); color: inherit;
}
.filters label { display: inline-flex; gap: 6px; align-items: center; color: var(--uu-muted); cursor: pointer; white-space: nowrap; }
.card {
	background: var(--ha-card-background, var(--card-background-color, #fff));
	border-radius: var(--ha-card-border-radius, 12px);
	border: 1px solid var(--ha-card-border-color, var(--uu-line));
	box-shadow: var(--ha-card-box-shadow, none);
	margin-bottom: 16px; overflow: hidden;
}
.card-head { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; justify-content: space-between; padding: 16px 16px 8px; }
.card-head h2 { margin: 0; font-size: 20px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.card-head .sub { color: var(--uu-muted); margin-top: 4px; }
.tiles { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 8px; }
.tile { border: 1px solid var(--uu-line); border-radius: 10px; padding: 8px 12px; min-width: 96px; }
.tile b { display: block; font-size: 22px; font-weight: 500; }
.tile span { color: var(--uu-muted); font-size: 12px; }
.tile.warn b { color: var(--uu-warn); } .tile.err b { color: var(--uu-err); }
.bar-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.status { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 8px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 13px;
	background: rgba(var(--rgb-primary-color, 3,169,244), .12); color: var(--primary-text-color); }
.chip.warn { background: rgba(255,166,0,.16); } .chip.err { background: rgba(219,68,55,.14); }
button.btn {
	display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 14px; font-weight: 500; cursor: pointer;
	padding: 7px 12px; border-radius: 8px; border: 1px solid var(--uu-line);
	background: transparent; color: var(--primary-color);
}
button.btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
button.btn.danger { color: var(--uu-err); }
button.btn:disabled, button.ib:disabled { opacity: .38; cursor: default; }
button.ib {
	display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; padding: 0;
	border: 0; border-radius: 50%; background: transparent; color: var(--primary-color); cursor: pointer;
}
button.ib:not(:disabled):hover, button.btn:not(:disabled):hover { background: rgba(var(--rgb-primary-color, 3,169,244), .1); }
button.ib.danger { color: var(--uu-err); }
.mdi { width: 20px; height: 20px; fill: currentColor; flex: none; }
.mdi.small { width: 16px; height: 16px; }
.mdi.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-weight: 500; color: var(--uu-muted); font-size: 13px; padding: 8px; border-bottom: 1px solid var(--uu-line); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid var(--uu-line); vertical-align: middle; }
tr:last-child td { border-bottom: 0; }
th.num, td.num { text-align: right; width: 1%; white-space: nowrap; }
td.num b { font-weight: 500; }
td.acts { text-align: right; white-space: nowrap; width: 1%; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: var(--uu-muted); }
.dot.ok { background: var(--uu-ok); } .dot.warn { background: var(--uu-warn); } .dot.err { background: var(--uu-err); }
.sys { display: flex; align-items: center; gap: 10px; min-width: 0; }
.sys .name { font-weight: 500; cursor: pointer; }
.sys .name:hover { text-decoration: underline; }
.sys .meta { color: var(--uu-muted); font-size: 12px; }
.badge { font-size: 11px; font-weight: 600; letter-spacing: .03em; padding: 2px 6px; border-radius: 4px;
	background: var(--secondary-background-color, rgba(127,127,127,.15)); color: var(--uu-muted); }
.flags { display: inline-flex; gap: 4px; margin-left: 4px; vertical-align: middle; }
.flag { display: inline-flex; color: var(--uu-warn); } .flag.err { color: var(--uu-err); } .flag.muted { color: var(--uu-muted); }
.sec { color: var(--uu-err); } .zero { color: var(--uu-muted); }
.job { white-space: nowrap; font-size: 13px; }
.job.failed { color: var(--uu-err); } .job.busy { color: var(--primary-color); }
a.link { color: var(--primary-color); cursor: pointer; text-decoration: underline; margin-left: 6px; }
.muted { color: var(--uu-muted); }
.confirm { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 16px;
	background: rgba(255,166,0,.12); border-top: 1px solid var(--uu-line); border-bottom: 1px solid var(--uu-line); }
.confirm span { flex: 1 1 240px; }
td.inner { padding: 0; }
pre.log { margin: 0; padding: 12px 16px; max-height: 320px; overflow: auto; font-size: 12px; line-height: 1.45;
	background: var(--code-editor-background-color, rgba(127,127,127,.08)); white-space: pre-wrap; word-break: break-word; }
.empty { padding: 24px 16px; color: var(--uu-muted); }
.hidden-sm { }
@media (max-width: 760px) {
	.content { padding: 8px; }
	.hidden-sm { display: none; }
	thead { display: none; }
	table, tbody, tr, td { display: block; width: auto; }
	tr.row { display: grid; grid-template-columns: 1fr auto; gap: 2px 8px; padding: 8px 12px; border-bottom: 1px solid var(--uu-line); }
	tr.row td { border: 0; padding: 0; }
	tr.row td.c-sys { grid-column: 1 / -1; }
	tr.row td.num { text-align: left; display: inline-block; }
	tr.row td.num::before { content: attr(data-label) ": "; color: var(--uu-muted); }
	tr.row td.c-job { grid-column: 1; }
	tr.row td.acts { grid-column: 2; grid-row: 2 / span 3; align-self: center; }
	td.inner { border-bottom: 1px solid var(--uu-line); }
}
`;

class UltimateUpdaterPanel extends HTMLElement {
	constructor() {
		super();
		this.attachShadow({ mode: "open" });
		this._systems = null; // result of ultimate_updater/systems
		this._entityCount = -1;
		this._sig = "";
		this._confirm = null; // { key, text, run }
		this._logs = {}; // "entry|target" → { loading, data }
		this._open = new Set(); // expanded logs
		this._filters = { q: "", onlyUpdates: false, showStopped: true, showHosts: true };
		try {
			Object.assign(this._filters, JSON.parse(localStorage.getItem("ultimate-updater-panel") || "{}"));
		} catch {
			// private mode – defaults
		}
	}

	set hass(hass) {
		const first = !this._hass;
		this._hass = hass;
		if (first) {
			this._lang = String(hass.language || "en").startsWith("de") ? "de" : "en";
			this._build();
		}
		// new or removed entities of the integration → read the mapping again
		const count = Object.values(hass.entities || {}).filter(e => e.platform === "ultimate_updater").length;
		if (count !== this._entityCount) {
			this._entityCount = count;
			this._loadSystems();
		}
		const menu = this.shadowRoot.querySelector(".menu");
		if (menu) {
			menu.classList.toggle("show", !!this._narrow);
		}
		this._render();
	}

	get hass() {
		return this._hass;
	}

	set narrow(value) {
		this._narrow = value;
		const menu = this.shadowRoot.querySelector(".menu");
		if (menu) {
			menu.classList.toggle("show", !!value);
		}
	}

	set panel(value) {
		this._panel = value;
	}

	get t() {
		return TXT[this._lang || "en"];
	}

	async _loadSystems() {
		try {
			this._systems = await this._hass.callWS({ type: "ultimate_updater/systems" });
			this._error = null;
		} catch (e) {
			this._error = (e && e.message) || String(e);
		}
		this._sig = "";
		this._render();
	}

	_build() {
		const t = this.t;
		const f = this._filters;
		this.shadowRoot.innerHTML = `<style>${CSS}</style>
			<div class="toolbar">
				<button class="menu" title="Menu">${icon(MDI.menu)}</button>
				<div class="title">${esc(t.title)}</div>
			</div>
			<div class="content">
				<div class="filters">
					<input type="search" placeholder="${esc(t.search)}" value="${esc(f.q)}">
					<label><input type="checkbox" data-filter="onlyUpdates" ${f.onlyUpdates ? "checked" : ""}>${esc(t.onlyUpdates)}</label>
					<label><input type="checkbox" data-filter="showStopped" ${f.showStopped ? "checked" : ""}>${esc(t.showStopped)}</label>
					<label><input type="checkbox" data-filter="showHosts" ${f.showHosts ? "checked" : ""}>${esc(t.showHosts)}</label>
				</div>
				<div id="body"><div class="empty">${esc(t.loading)}</div></div>
			</div>`;
		const root = this.shadowRoot;
		root.querySelector(".menu").addEventListener("click", () =>
			this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })),
		);
		root.querySelector("input[type=search]").addEventListener("input", ev => {
			this._filters.q = ev.target.value;
			this._saveFilters();
		});
		root.querySelectorAll("input[data-filter]").forEach(el =>
			el.addEventListener("change", ev => {
				this._filters[ev.target.dataset.filter] = ev.target.checked;
				this._saveFilters();
			}),
		);
		root.querySelector("#body").addEventListener("click", ev => this._onClick(ev));
	}

	_saveFilters() {
		try {
			localStorage.setItem("ultimate-updater-panel", JSON.stringify(this._filters));
		} catch {
			// ignore
		}
		this._sig = "";
		this._render();
	}

	// ── state helpers ──
	_st(entityId) {
		return entityId ? this._hass.states[entityId] : undefined;
	}
	_val(entityId) {
		const s = this._st(entityId);
		return s ? s.state : undefined;
	}
	_on(entityId) {
		return this._val(entityId) === "on";
	}
	_num(entityId) {
		const raw = this._val(entityId);
		const v = raw == null || raw === "" ? NaN : Number(raw);
		return Number.isFinite(v) ? v : null;
	}
	_usable(entityId) {
		const v = this._val(entityId);
		return v !== undefined && v !== "unavailable";
	}

	_relTime(iso) {
		const d = Date.parse(iso || "");
		if (!d) {
			return "–";
		}
		const s = Math.round((d - Date.now()) / 1000);
		const rtf = new Intl.RelativeTimeFormat(this._hass.locale?.language || this._lang, { numeric: "auto" });
		const abs = Math.abs(s);
		if (abs < 60) return rtf.format(s, "second");
		if (abs < 3600) return rtf.format(Math.round(s / 60), "minute");
		if (abs < 86400) return rtf.format(Math.round(s / 3600), "hour");
		return rtf.format(Math.round(s / 86400), "day");
	}

	// ── rendering ──
	_signature() {
		const ids = [];
		for (const sys of this._systems || []) {
			ids.push(...Object.values(sys.entities));
			for (const tg of sys.targets) {
				ids.push(...Object.values(tg.entities));
			}
		}
		const parts = ids.map(id => {
			const s = this._hass.states[id];
			return s ? `${s.state}|${s.last_updated}` : "-";
		});
		return `${parts.join(",")}#${this._confirm ? this._confirm.key : ""}#${[...this._open].join(",")}#${Object.keys(this._logs).map(k => `${k}:${this._logs[k].loading}`).join(",")}#${Math.floor(Date.now() / 60000)}`;
	}

	_render() {
		if (!this._hass || !this.shadowRoot.querySelector("#body")) {
			return;
		}
		const sig = this._signature();
		if (sig === this._sig) {
			return;
		}
		this._sig = sig;
		const t = this.t;
		const body = this.shadowRoot.querySelector("#body");
		if (this._error) {
			body.innerHTML = `<div class="card"><div class="empty">${esc(this._error)}</div></div>`;
			return;
		}
		if (!this._systems) {
			body.innerHTML = `<div class="empty">${esc(t.loading)}</div>`;
			return;
		}
		if (!this._systems.length) {
			body.innerHTML = `<div class="card"><div class="empty">${esc(t.noEntries)}</div></div>`;
			return;
		}
		body.innerHTML = this._systems.map(sys => this._renderInstance(sys)).join("");
	}

	_renderInstance(sys) {
		const t = this.t;
		const e = sys.entities;
		const jobRunning = this._on(e.job_running);
		const bulk = this._on(e.bulk_active);
		const blocked = jobRunning || bulk;
		const withUpdates = this._num(e.targets_with_updates);
		let summary = this._val(e.summary);
		if (withUpdates !== null && this._num(e.security_updates_total) !== null) {
			const total = this._num(e.security_updates_total) + (this._num(e.normal_updates_total) || 0);
			const rb = this._num(e.reboot_required_count) || 0;
			summary = [t.summary(total, withUpdates), rb ? t.summaryReboot(rb) : ""].filter(Boolean).join(", ");
		}
		const version = this._val(e.updater_version);
		const sec = this._num(e.security_updates_total);
		const other = this._num(e.normal_updates_total);
		const reboots = this._num(e.reboot_required_count);
		const unreachable = this._num(e.unreachable_count);
		const progress = this._val(e.bulk_progress);
		const key = sys.entry_id;

		let html = `<section class="card">
			<div class="card-head">
				<div>
					<h2>${esc(sys.title)}<a class="ib" href="${esc(sys.url)}" target="_blank" rel="noreferrer" title="${esc(t.openWebUi)}" style="display:inline-flex">${icon(MDI.open, "small")}</a></h2>
					<div class="sub">${esc(summary && summary !== "unknown" ? summary : "")}${version && version !== "unknown" ? ` · ${esc(t.version)} ${esc(version)}` : ""}${this._on(e.updater_update) ? ` · <span class="sec">${esc(t.updaterUpdate)}</span>` : ""}</div>
				</div>
				<div class="bar-actions">
					<button class="btn" data-act="press" data-entity="${esc(e.check_all)}" ${blocked || !this._usable(e.check_all) ? "disabled" : ""}>${icon(MDI.check)}${esc(t.checkAll)}</button>
					<button class="btn primary" data-act="confirm" data-key="${key}|all" data-entity="${esc(e.update_all)}" ${blocked || !this._usable(e.update_all) ? "disabled" : ""}>${icon(MDI.update)}${esc(t.updateAll)}</button>
					<button class="btn" data-act="confirm" data-key="${key}|sec" data-entity="${esc(e.update_security)}" ${blocked || !this._usable(e.update_security) || !sec ? "disabled" : ""}>${icon(MDI.shield)}${esc(t.updateSec)}</button>
				</div>
			</div>
			<div class="tiles">
				${this._tile(sec, t.security, sec ? "err" : "")}
				${this._tile(other, t.other, other ? "warn" : "")}
				${this._tile(reboots, t.rebootNeeded, reboots ? "warn" : "")}
				${this._tile(unreachable, t.unreachable, unreachable ? "err" : "")}
				${this._tile(sys.targets.length, t.systems(sys.targets.length).replace(/^\d+ /, ""), "")}
			</div>`;

		if (jobRunning || bulk || (progress && progress !== "unknown")) {
			html += `<div class="status">`;
			if (jobRunning) {
				html += `<span class="chip">${icon(MDI.reboot, "small spin")}${esc(t.jobRunning)}
					<button class="btn danger" style="padding:2px 8px" data-act="press" data-entity="${esc(e.cancel_jobs)}">${esc(t.cancel)}</button></span>`;
			}
			if (progress && progress !== "unknown") {
				html += `<span class="chip ${bulk ? "" : "warn"}">${esc(bulk ? t.bulkRunning : t.bulkLast)}: ${esc(progress)}
					${bulk ? `<button class="btn danger" style="padding:2px 8px" data-act="press" data-entity="${esc(e.stop_bulk)}">${icon(MDI.stop, "small")}${esc(t.stop)}</button>` : ""}</span>`;
			}
			html += `</div>`;
		}
		if (this._confirm && this._confirm.key.startsWith(`${key}|`) && ["all", "sec"].includes(this._confirm.key.split("|")[1])) {
			html += this._confirmBar();
		}

		const rows = this._filterTargets(sys.targets);
		if (!rows.length) {
			return `${html}<div class="empty">${esc(t.noSystems)}</div></section>`;
		}
		html += `<table><thead><tr>
			<th style="width:1%"></th><th>${esc(t.system)}</th>
			<th class="num">${esc(t.security)}</th><th class="num">${esc(t.other)}</th>
			<th class="hidden-sm">${esc(t.lastCheck)}</th><th>${esc(t.job)}</th><th class="num">${esc(t.actions)}</th>
		</tr></thead><tbody>`;
		for (const tg of rows) {
			html += this._renderRow(sys, tg, blocked);
		}
		return `${html}</tbody></table></section>`;
	}

	_tile(value, label, cls) {
		return `<div class="tile ${value ? cls : ""}"><b>${value == null ? "–" : esc(value)}</b><span>${esc(label)}</span></div>`;
	}

	_filterTargets(targets) {
		const f = this._filters;
		const q = f.q.trim().toLowerCase();
		return targets
			.filter(tg => {
				const e = tg.entities;
				if (!f.showHosts && tg.host) return false;
				if (!f.showStopped && tg.stopped) return false;
				if (f.onlyUpdates && !((this._num(e.security_updates) || 0) + (this._num(e.normal_updates) || 0))) return false;
				if (q && ![tg.name, tg.label, tg.id, tg.node, tg.device_name].some(v => String(v || "").toLowerCase().includes(q))) return false;
				return true;
			})
			.sort(
				(a, b) =>
					a.node.localeCompare(b.node) ||
					(TYPE_ORDER[a.type] ?? 9) - (TYPE_ORDER[b.type] ?? 9) ||
					numId(a.id) - numId(b.id) ||
					a.name.localeCompare(b.name),
			);
	}

	_renderRow(sys, tg, blocked) {
		const t = this.t;
		const e = tg.entities;
		const key = `${sys.entry_id}|${tg.id}`;
		const sec = this._num(e.security_updates);
		const other = this._num(e.normal_updates);
		const reachable = this._val(e.reachable);
		const reboot = this._on(e.reboot_required);
		const job = this._val(e.job_state) || "none";
		const upd = this._st(e.packages);
		const updating = !!(upd && upd.attributes.in_progress);
		const busy = BUSY.includes(job) || updating;
		const known = sec !== null || other !== null;

		let dot = "";
		if (reachable === "off" || FAILED.includes(job)) dot = "err";
		else if ((sec || 0) > 0) dot = "err";
		else if ((other || 0) > 0 || reboot) dot = "warn";
		else if (known) dot = "ok";

		const flags = [];
		if (reboot) flags.push(`<span class="flag" title="${esc(t.rebootNeeded)}">${icon(MDI.reboot, "small")}</span>`);
		if (reachable === "off") flags.push(`<span class="flag err" title="${esc(t.unreachable)}">${icon(MDI.alert, "small")}</span>`);
		if (tg.stopped) flags.push(`<span class="flag muted" title="${esc(t.stopped)}">${icon(MDI.sleep, "small")}</span>`);
		if (tg.excluded) flags.push(`<span class="flag muted" title="${esc(t.excluded)}">${icon(MDI.info, "small")}</span>`);

		const meta = [tg.host ? "" : tg.id.replace(/^(lxc|vm|guest|external):/, ""), tg.host ? "" : tg.node, tg.os]
			.filter(Boolean)
			.join(" · ");
		const jobText = busy && updating ? t.updating : t.jobStates[job] || job;
		const jobCls = FAILED.includes(job) ? "failed" : busy ? "busy" : "";
		const canUpdate = this._usable(e.packages) && upd && upd.state === "on" && !blocked;
		const canReboot = e.reboot && this._usable(e.reboot) && !blocked;

		let html = `<tr class="row">
			<td class="hidden-sm"><span class="dot ${dot}"></span></td>
			<td class="c-sys"><div class="sys">
				<span class="badge">${esc(t.types[tg.type] || tg.type || "?")}</span>
				<div><span class="name" data-act="more" data-entity="${esc(e.packages)}" title="${esc(t.details)}">${esc(tg.device_name || tg.name)}</span><span class="flags">${flags.join("")}</span>
				${meta ? `<div class="meta">${esc(meta)}</div>` : ""}</div>
			</div></td>
			<td class="num" data-label="${esc(t.security)}">${sec == null ? `<span class="zero">–</span>` : `<b class="${sec ? "sec" : "zero"}">${sec}</b>`}</td>
			<td class="num" data-label="${esc(t.other)}">${other == null ? `<span class="zero">–</span>` : `<b class="${other ? "" : "zero"}">${other}</b>`}</td>
			<td class="hidden-sm muted">${esc(this._relTime(this._val(e.last_check)))}</td>
			<td class="c-job"><span class="job ${jobCls}">${busy ? icon(MDI.reboot, "small spin") : ""} ${esc(jobText)}</span>${
				FAILED.includes(job) ? `<a class="link" data-act="log" data-key="${esc(key)}">${esc(t.log)}</a>` : ""
			}</td>
			<td class="acts">
				<button class="ib" title="${esc(t.check)}" data-act="press" data-entity="${esc(e.check)}" ${blocked || !this._usable(e.check) ? "disabled" : ""}>${icon(MDI.check)}</button>
				<button class="ib" title="${esc(t.update)}" data-act="confirm" data-key="${esc(key)}|update" data-entity="${esc(e.packages)}" ${canUpdate ? "" : "disabled"}>${icon(MDI.update)}</button>
				${e.reboot ? `<button class="ib danger" title="${esc(t.reboot)}" data-act="confirm" data-key="${esc(key)}|reboot" data-entity="${esc(e.reboot)}" ${canReboot ? "" : "disabled"}>${icon(MDI.reboot)}</button>` : ""}
			</td>
		</tr>`;
		if (this._confirm && this._confirm.key.startsWith(`${key}|`)) {
			html += `<tr><td class="inner" colspan="7">${this._confirmBar()}</td></tr>`;
		}
		if (this._open.has(key)) {
			const log = this._logs[key];
			let text = t.loading;
			if (log && !log.loading) {
				const d = log.data;
				text = d && (d.log || d.error) ? cleanLog(d.log) || d.error : t.noLog;
				if (d && d.exit_code != null) text = `exit code ${d.exit_code}\n${text}`;
			}
			html += `<tr><td class="inner" colspan="7"><pre class="log">${esc(text)}</pre></td></tr>`;
		}
		return html;
	}

	_confirmBar() {
		const t = this.t;
		return `<div class="confirm"><span>${esc(this._confirm.text)}</span>
			<button class="btn primary" data-act="yes">${esc(t.yes)}</button>
			<button class="btn" data-act="no">${esc(t.no)}</button></div>`;
	}

	// ── actions ──
	_target(key) {
		const [entryId, targetId] = key.split("|");
		const sys = (this._systems || []).find(s => s.entry_id === entryId);
		return { sys, tg: sys && sys.targets.find(x => x.id === targetId) };
	}

	async _onClick(ev) {
		const el = ev.target.closest("[data-act]");
		if (!el || el.disabled) {
			return;
		}
		const t = this.t;
		const act = el.dataset.act;
		const entity = el.dataset.entity;
		if (act === "more") {
			this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: entity }, bubbles: true, composed: true }));
		} else if (act === "press") {
			await this._call("button", "press", entity);
		} else if (act === "confirm") {
			const key = el.dataset.key;
			const kind = key.split("|").pop();
			let text;
			if (kind === "all") text = t.confirmAll;
			else if (kind === "sec") text = t.confirmSec;
			else {
				const { tg } = this._target(key);
				const name = tg ? tg.device_name || tg.name : "";
				text = kind === "reboot" ? t.confirmReboot(name) : tg && tg.host ? t.confirmHost(name) : t.confirmUpdate(name);
				if (kind === "update" && tg && tg.stopped) text += t.stoppedHint;
			}
			const run =
				kind === "update" ? () => this._call("update", "install", entity) : () => this._call("button", "press", entity);
			this._confirm = { key, text, run };
			this._render();
		} else if (act === "yes") {
			const c = this._confirm;
			this._confirm = null;
			this._render();
			if (c) await c.run();
		} else if (act === "no") {
			this._confirm = null;
			this._render();
		} else if (act === "log") {
			const key = el.dataset.key;
			if (this._open.has(key)) {
				this._open.delete(key);
				this._render();
				return;
			}
			this._open.add(key);
			this._logs[key] = { loading: true };
			this._render();
			const [entryId, targetId] = key.split("|");
			let data = null;
			try {
				data = await this._hass.callWS({ type: "ultimate_updater/job_log", entry_id: entryId, target_id: targetId });
			} catch (e) {
				data = { error: (e && e.message) || String(e) };
			}
			this._logs[key] = { loading: false, data };
			this._render();
		}
	}

	async _call(domain, service, entityId) {
		if (!entityId) {
			return;
		}
		try {
			await this._hass.callService(domain, service, { entity_id: entityId });
		} catch (e) {
			this.dispatchEvent(
				new CustomEvent("hass-notification", {
					detail: { message: (e && e.message) || String(e) },
					bubbles: true,
					composed: true,
				}),
			);
		}
	}
}

if (!customElements.get("ultimate-updater-panel")) {
	customElements.define("ultimate-updater-panel", UltimateUpdaterPanel);
}
