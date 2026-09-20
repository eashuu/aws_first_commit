// console.js — the Naka operator console.
//
// Was an inline <script type="module"> in index.html when the console and
// the marketing page were one document. They are separate surfaces now:
// index.html is the product site, console.html is the application, and this
// is the application's controller.
//
// Structure:
//   - a hash router over .d-view sections (no framework, no build step)
//   - each view owns a render function and says what it needs from the API
//   - the store polls /feed and every view re-renders from it
//
// THE RULE THIS FILE ENFORCES, everywhere, without exception:
// nothing on screen is invented. Every figure is derived from a real audit
// row, a real /diag probe or a real /policy read. Where a surface has no
// data — and the endpoint fleet genuinely has none until someone enrols a
// laptop — it renders an empty state that says so and says what to do about
// it. A plausible-looking fake row in an audit console is worse than an
// empty one, because an operator will act on it.

import { api } from "./api.js";
import { store } from "./store.js";
import { renderFeed, renderMeter, renderDiff, renderTiers } from "./render.js";
import {
  animateFeedRows, animateMeterSlots, animateChips, animateCount, playTrip,
} from "./motion.js";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* ============================================================ view router */

const VIEWS = {
  overview:  { title: "Overview",          sub: "Every plane, and the one number that must stay at zero" },
  egress:    { title: "Agent Egress",      sub: "Cedar authorization on the AI agent's tool boundary" },
  endpoint:  { title: "Endpoint DLP",      sub: "Local agents inspecting paste, upload and prompt traffic" },
  files:     { title: "File & Document",   sub: "Attachment and identity-document scanning" },
  ledger:    { title: "Disclosure ledger", sub: "What each principal has learned about each subject" },
  detectors: { title: "Detector coverage", sub: "Which tiers are actually reachable from this account" },
  policy:    { title: "Policy",            sub: "Cedar source, versioned and ETag-guarded" },
};

function route() {
  const id = (location.hash || "#overview").slice(1).split("?")[0];
  const view = VIEWS[id] ? id : "overview";

  for (const el of $$(".d-view")) el.classList.toggle("is-on", el.id === `view-${view}`);
  for (const a of $$(".d-nav a")) {
    const on = a.getAttribute("href") === `#${view}`;
    if (on) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }

  $("#crumb-h").textContent = VIEWS[view].title;
  $("#crumb-sub").textContent = VIEWS[view].sub;
  document.title = `${VIEWS[view].title} · Naka console`;

  // The shell is fixed-height with its own scroller, so a hash change does
  // not reset scroll the way a normal page navigation would. Do it here.
  const scroller = $(".d-scroll");
  if (scroller) scroller.scrollTop = 0;
  $(".d-app").classList.remove("is-open");

  // Views that need a one-off fetch do it the first time they are opened,
  // rather than all of them on boot — so opening the console costs one
  // /feed call, not six.
  if (view === "detectors") loadDetectors();
  if (view === "policy") refreshPolicy();
}

window.addEventListener("hashchange", route);

/* ================================================================== boot */

$(".d-burger")?.addEventListener("click", () => $(".d-app").classList.toggle("is-open"));

// ---- health ---------------------------------------------------------------

async function pingHealth() {
  const control = $("#health-control");
  const agent = $("#health-agent");
  let controlOk = false;
  let agentOk = false;

  try {
    const h = await api.health();
    controlOk = Boolean(h && h.ok);
    if (h && h.agent_url && !agentUrlInput.value) {
      agentUrlInput.value = h.agent_url;
      api.setAgentUrl(h.agent_url);
    }
  } catch { /* controlOk stays false */ }

  const url = api.getAgentUrl();
  if (url) {
    try {
      agentOk = (await fetch(url.replace(/\/$/, "") + "/health")).ok;
    } catch { /* agentOk stays false */ }
  }

  control.classList.toggle("is-live", controlOk);
  control.classList.toggle("is-down", !controlOk);
  agent.classList.toggle("is-live", agentOk);
  agent.classList.toggle("is-down", !agentOk);

  // The overview's plane tiles read their liveness from the same probe.
  setPlaneState("egress", agentOk ? "is-live" : "is-down", agentOk ? "live" : "unreachable");
  return { controlOk, agentOk };
}

function setPlaneState(plane, cls, text) {
  const el = $(`#plane-${plane} .d-plane-state`);
  if (!el) return;
  el.className = `d-plane-state ${cls}`;
  el.textContent = text;
}

/* ================================================== elements (egress view) */

const feedEl = $("#feed");
const meterEl = $("#meter");
const diffEl = $("#diff");

const agentUrlInput = $("#agent-url");
const sessionIdInput = $("#session-id");
const userEmailInput = $("#user-email");
const roleSelect = $("#role-select");
const promptInput = $("#prompt-input");
const runBtn = $("#run-btn");
const runErrorEl = $("#run-error");
const runOkEl = $("#run-ok");

const cedarTextarea = $("#policy-cedar");
const nakaKeyInput = $("#naka-key");
const policyEtagEl = $("#policy-etag");
const policyErrorEl = $("#policy-error");
const policyOkEl = $("#policy-ok");

let selectedRow = null;
let policyEditorTouched = false;
let currentEtag = null;

agentUrlInput.value = api.getAgentUrl();
agentUrlInput.addEventListener("change", () => api.setAgentUrl(agentUrlInput.value.trim()));
sessionIdInput.value = "demo-session-1";
userEmailInput.value = "analyst@example.com";

function hide(el) { el.hidden = true; el.textContent = ""; }
function showError(el, text) { el.hidden = false; el.textContent = text; }
function showOk(el, text) { el.hidden = false; el.textContent = text; }

/* ================================================================== run */

async function runSession() {
  hide(runErrorEl); hide(runOkEl);
  const prompt = promptInput.value.trim();
  if (!prompt) { showError(runErrorEl, "Enter a prompt for the agent first."); return; }
  runBtn.disabled = true;
  try {
    const resp = await api.run({
      session_id: sessionIdInput.value.trim(),
      prompt,
      user: userEmailInput.value.trim(),
      role: roleSelect.value,
    });
    showOk(runOkEl, `${resp.calls?.length ?? 0} tool calls · policy ${resp.policy_version}`);
    await store.refreshFeed();
    await store.loadSession(sessionIdInput.value.trim());
  } catch (err) {
    showError(runErrorEl, err.body?.error ? `${err.body.error.code}: ${err.body.error.message}` : err.message);
  } finally {
    runBtn.disabled = false;
  }
}
runBtn.addEventListener("click", runSession);

// Scenario buttons: each is a complete payload, so an evaluator reaches a
// real decision in one click rather than filling four fields first.
$("#scenario-row")?.addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".scenario");
  if (!btn) return;
  for (const b of $$(".scenario")) b.classList.remove("scenario-active");
  btn.classList.add("scenario-active");
  promptInput.value = btn.dataset.prompt || "";
  roleSelect.value = btn.dataset.role || "analyst";

  // A fresh session id per scenario, so each starts with an empty ledger
  // instead of inheriting the previous scenario's spend — otherwise
  // "budget bites" is already exhausted before it runs.
  const sid = "demo-" + Math.random().toString(36).slice(2, 8);
  sessionIdInput.value = sid;

  hide(runErrorEl); hide(runOkEl);
  runBtn.disabled = true;
  try {
    const resp = await api.demo({
      scenario: btn.dataset.scenario,
      session_id: sid,
      user: userEmailInput.value.trim(),
      role: btn.dataset.role || "analyst",
    });
    const denied = resp.transcript.filter((t) => String(t.outcome).startsWith("denied")).length;
    const masked = resp.transcript.reduce(
      (n, t) => n + Object.values(t.entities_masked || {}).reduce((a, b) => a + b, 0), 0);
    showOk(runOkEl,
      `${resp.title} — ${resp.transcript.length} tool calls, ${masked} fields withheld, ` +
      `${denied} calls refused. ${resp.proves}`);
    await store.refreshFeed();
    await store.loadSession(sid);
  } catch (err) {
    showError(runErrorEl, err.body?.error ? `${err.body.error.code}: ${err.body.error.message}` : err.message);
  } finally {
    runBtn.disabled = false;
  }
});

$("#load-session-btn")?.addEventListener("click", async () => {
  const id = sessionIdInput.value.trim();
  if (!id) return;
  try { await store.loadSession(id); }
  catch (err) { showError(runErrorEl, err.body?.error ? `${err.body.error.code}: ${err.body.error.message}` : err.message); }
});

const loadOlderBtn = $("#load-older-btn");
loadOlderBtn?.addEventListener("click", async () => {
  loadOlderBtn.disabled = true;
  try { await store.loadOlder(); }
  catch (err) { console.error("naka: load older failed", err); }
  finally { loadOlderBtn.disabled = !store.cursor; }
});

// Top-bar shortcut: jump to the egress view and fire the first scenario.
$("#top-demo")?.addEventListener("click", () => {
  location.hash = "#egress";
  $(".scenario")?.click();
});

/* ============================================== feed selection -> diff pane */

feedEl.addEventListener("naka:selectrow", (ev) => {
  selectedRow = ev.detail;
  renderDiff(selectedRow, diffEl);
  animateChips(diffEl.querySelectorAll(".chip"));
  // Follow the row into its own session, so the meter shows the subject the
  // row is about rather than staying pinned to the typed session id.
  const rowSession = ev.detail.session_id;
  if (rowSession && rowSession !== sessionIdInput.value.trim()) {
    sessionIdInput.value = rowSession;
    store.loadSession(rowSession).catch((err) => console.error("naka: session load failed", err));
  }
});

/* ================================================================== views */

function currentSessionMeters() {
  const id = sessionIdInput.value.trim();
  const session = store.sessions[id];
  if (!session) return {};
  const meters = {};
  for (const [subject, m] of Object.entries(session.meters || {})) {
    meters[subject] = { ...m, calls: session.calls.filter((c) => c.subject === subject) };
  }
  return meters;
}

const countOf = (map) => Object.values(map || {}).reduce((a, b) => a + b, 0);
const isDenied = (row) => String(row.outcome || "").startsWith("denied");

// A row came from a file/document path if the guard recorded a non-text
// content type, or if the tool that produced it was an attachment reader.
// Both are real fields on the audit row; neither is inferred from a guess.
const isFileRow = (row) =>
  (row.content_type && !row.content_type.startsWith("text/")) ||
  /attachment|document|file|scan/i.test(row.tool || "");

// ---- overview -------------------------------------------------------------

function renderOverview(rows) {
  const withheld = rows.reduce((n, r) => n + countOf(r.entities_masked), 0);
  const denied = rows.filter(isDenied).length;
  const unscanned = rows.filter(
    (r) => r.outcome === "ok" && (!r.detector_tiers || !r.detector_tiers.length)).length;

  animateCount($("#kpi-calls"), rows.length);
  animateCount($("#kpi-withheld"), withheld);
  animateCount($("#kpi-denied"), denied);
  animateCount($("#kpi-unscanned"), unscanned);

  const inv = $("#kpi-invariant");
  inv.classList.toggle("is-broken", unscanned > 0);
  $("#kpi-unscanned").className = "d-kpi-v " + (unscanned === 0 ? "is-good" : "is-fault");
  $("#kpi-invariant-note").textContent = unscanned === 0
    ? "Holding. Every egress event today passed at least one detector tier."
    : `${unscanned} event(s) reached a model without a detector tier running. Investigate before trusting today's trail.`;

  // Subjects touched today, and how many are at or over budget. Both come
  // straight from the rows' own ledger_after and budget fields.
  const subjects = new Map();
  for (const r of rows) {
    if (!r.subject) continue;
    const prev = subjects.get(r.subject) || { seen: 0, budget: 0 };
    subjects.set(r.subject, {
      seen: Math.max(prev.seen, (r.ledger_after || []).length),
      budget: r.budget || prev.budget,
    });
  }
  const exhausted = [...subjects.values()].filter((s) => s.budget && s.seen >= s.budget).length;
  $("#kpi-subjects").textContent = String(subjects.size);
  $("#kpi-exhausted").textContent = String(exhausted);

  // Plane tiles. Counts are real; a plane with no traffic says "no traffic",
  // which is a fact, not a failure.
  const fileRows = rows.filter(isFileRow);
  const agentRows = rows.filter((r) => !isFileRow(r));

  $("#plane-egress-calls").textContent = String(agentRows.length);
  $("#plane-egress-masked").textContent = String(agentRows.reduce((n, r) => n + countOf(r.entities_masked), 0));

  $("#plane-files-scans").textContent = String(fileRows.length);
  $("#plane-files-masked").textContent = String(fileRows.reduce((n, r) => n + countOf(r.entities_masked), 0));
  setPlaneState("files", fileRows.length ? "is-live" : "is-idle",
    fileRows.length ? "scanning" : "no scans today");

  // Recent activity: the ten newest rows, rendered with the same row
  // vocabulary as the full feed.
  const tbody = $("#overview-recent");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty">No calls recorded today. Run a scenario on the <a href="#egress">Agent Egress</a> view to produce some.</td></tr>`;
  } else {
    tbody.innerHTML = rows.slice(0, 10).map((r) => {
      const masked = countOf(r.entities_masked);
      const tone = isDenied(r) ? "var(--deny)" : masked ? "var(--redact)" : "var(--allow)";
      const label = isDenied(r) ? "denied" : masked ? `${masked} withheld` : "released";
      return `<tr>
        <td class="mono">${esc(r.ts || "").slice(11, 19)}</td>
        <td class="mono">${esc(r.tool)}</td>
        <td class="mono">${esc(r.subject || "—")}</td>
        <td>${esc(r.principal)}</td>
        <td><span class="pill-tag" style="--pill-color:${tone}">${label}</span></td>
      </tr>`;
    }).join("");
  }
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// ---- files ----------------------------------------------------------------

function renderFiles(rows) {
  const fileRows = rows.filter(isFileRow);
  const host = $("#files-body");

  $("#files-count").textContent = String(fileRows.length);
  $("#files-masked").textContent = String(fileRows.reduce((n, r) => n + countOf(r.entities_masked), 0));

  if (!fileRows.length) {
    host.innerHTML = `
      <div class="d-empty">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 3h6l5 5v12a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M14 3v5h5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>
        <h3>No documents scanned today</h3>
        <p>File rows appear here when a tool returns a non-text content type —
           an attachment, a scan or a photograph of an identity document. The
           <strong>Exfiltration attempt</strong> scenario on the Agent Egress view
           reads a ticket attachment and will populate this table.</p>
        <a class="btn" href="#egress" style="text-decoration:none;display:inline-flex;align-items:center">Go to Agent Egress</a>
      </div>`;
    return;
  }

  host.innerHTML = `
    <table class="d-table">
      <thead><tr><th>time</th><th>tool</th><th>content type</th><th>tiers run</th><th>found</th><th class="num">withheld</th></tr></thead>
      <tbody>${fileRows.map((r) => `
        <tr>
          <td class="mono">${esc(r.ts || "").slice(11, 19)}</td>
          <td class="mono">${esc(r.tool)}</td>
          <td class="mono">${esc(r.content_type || "—")}</td>
          <td>${(r.detector_tiers || []).map((t) => `<span class="pill-tag" style="--pill-color:var(--brand)">${esc(t)}</span>`).join(" ") || '<span class="pill-tag" style="--pill-color:var(--fault)">none</span>'}</td>
          <td class="mono">${Object.keys(r.entities_found || {}).map(esc).join(", ") || "—"}</td>
          <td class="num mono">${countOf(r.entities_masked)}</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}

// ---- endpoint -------------------------------------------------------------

// The endpoint agent runs on a laptop — it cannot run on AWS and is not
// meant to. What runs on AWS is its control plane, and this renders it.
// When no device has enrolled the empty state still says so plainly; it is
// a real zero, not a loading spinner that never resolves.
let fleetTimer = null;

async function refreshFleet() {
  const host = $("#endpoint-fleet");
  if (!host) return;
  let data;
  try {
    data = await api.fleet();
  } catch (err) {
    host.innerHTML = `<div class="d-empty">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="M12 7v6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="12" cy="16.5" r=".9" fill="currentColor"/></svg>
        <h3>Fleet unavailable</h3>
        <p>The control plane did not answer <code>/endpoint/fleet</code>. This is a
           fault, not an empty fleet — the two are different and the console will
           not conflate them.</p>
      </div>`;
    return;
  }

  const devices = data.devices || [];
  const events = data.events || [];
  const live = devices.filter((d) => d.status === "live").length;

  $("#endpoint-count").textContent = devices.length ? String(devices.length) : "";
  $("#plane-endpoint-devices").textContent = String(devices.length);
  $("#plane-endpoint-events").textContent = String(events.length);
  setPlaneState("endpoint",
    devices.length === 0 ? "is-idle" : live ? "is-live" : "is-down",
    devices.length === 0 ? "no agents enrolled" : live ? `${live} live` : "all stale");

  if (!devices.length) {
    host.innerHTML = `<div class="d-empty">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="5" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M9 20h6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
        <h3>No endpoints enrolled yet</h3>
        <p>The control plane is live and accepting enrolments — this is a real zero,
           not a broken view. Enrol a machine with the steps below and its decisions
           appear here within seconds.</p>
      </div>`;
    return;
  }

  host.innerHTML = `
    <div class="d-kpis" style="grid-template-columns:repeat(3,1fr);margin-bottom:var(--s4)">
      <div class="d-kpi"><div class="d-kpi-label">Devices enrolled</div><div class="d-kpi-v">${devices.length}</div></div>
      <div class="d-kpi"><div class="d-kpi-label">Reporting now</div><div class="d-kpi-v ${live ? "is-good" : ""}">${live}</div></div>
      <div class="d-kpi"><div class="d-kpi-label">Recent events</div><div class="d-kpi-v is-warn">${events.length}</div></div>
    </div>

    <div class="d-section-h">Devices</div>
    <div class="panel" style="margin:0 0 var(--s4)">
      <table class="d-table">
        <thead><tr><th>device</th><th>host</th><th>user</th><th>agent</th><th>last seen</th><th class="num">events</th></tr></thead>
        <tbody>${devices.map((d) => `
          <tr>
            <td class="mono">${esc(d.device_id)}</td>
            <td>${esc(d.hostname || "—")}</td>
            <td>${esc(d.principal || "—")}</td>
            <td class="mono">${esc(d.agent_version || "—")}</td>
            <td><span class="pill-tag" style="--pill-color:${d.status === "live" ? "var(--allow)" : "var(--mud)"}">${esc(d.status)} · ${esc((d.last_seen || "").slice(11, 19))}</span></td>
            <td class="num mono">${d.events}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>

    <div class="d-section-h">Decisions</div>
    <div class="panel" style="margin:0">
      ${events.length ? `<table class="d-table">
        <thead><tr><th>time</th><th>host</th><th>action</th><th>destination</th><th>found</th><th>decision</th></tr></thead>
        <tbody>${events.map((e) => {
          const blocked = e.decision === "block";
          const tone = blocked ? "var(--deny)" : e.decision === "warn" ? "var(--redact)" : "var(--allow)";
          const found = Object.entries(e.entities_found || {}).map(([k, v]) => `${k}×${v}`).join(", ");
          return `<tr>
            <td class="mono">${esc((e.ts || "").slice(11, 19))}</td>
            <td>${esc(e.hostname || "—")}</td>
            <td class="mono">${esc(e.action)}</td>
            <td class="mono">${esc(e.destination || "—")}</td>
            <td class="mono">${esc(found || "—")}</td>
            <td><span class="pill-tag" style="--pill-color:${tone}">${esc(e.decision)}</span></td>
          </tr>`;
        }).join("")}</tbody>
      </table>` : `<div class="empty">Devices are enrolled but none has reported a decision yet.</div>`}
    </div>`;
}

function startFleetPolling() {
  if (fleetTimer) return;
  refreshFleet();
  // Slower than the audit feed: an endpoint reports on user action, not
  // continuously, so a 4s cadence is live enough without a request per
  // second against a scan.
  fleetTimer = setInterval(refreshFleet, 4000);
}

// ---- detectors ------------------------------------------------------------

let detectorsLoaded = false;
function loadDetectors() {
  if (detectorsLoaded) return;
  detectorsLoaded = true;
  const host = $("#tiers");
  renderTiers(null, host);
  api.diag()
    .then((d) => {
      renderTiers(d, host);
      // Mirror the tier states onto the overview's detector strip.
      const strip = $("#overview-tiers");
      if (strip && d && d.tiers) {
        strip.innerHTML = d.tiers.map((t) => {
          const tone = t.status === "OK" ? "var(--allow)"
            : t.status === "NOT_RUN" ? "var(--mud)" : "var(--fault)";
          return `<span class="pill-tag" style="--pill-color:${tone}">${esc(t.tier)} · ${esc(t.status)}</span>`;
        }).join(" ");
      }
    })
    .catch(() => {
      host.innerHTML = '<div class="empty">Detector coverage unavailable — the control plane did not answer.</div>';
      detectorsLoaded = false; // let a later visit retry
    });
}

/* ============================================================ store wiring */

let seenRowKeys = new Set();

function rerender() {
  const rows = store.feedRows;

  renderFeed(rows, feedEl);
  const meters = currentSessionMeters();
  renderMeter(meters, meterEl);
  // The ledger view shows the same meters as the egress view's side panel.
  // Rendered twice rather than moved, because an operator working a session
  // on the egress view should not have to change view to see the budget
  // they are spending.
  const ledgerEl = $("#meter-ledger");
  if (ledgerEl && Object.keys(meters).length) renderMeter(meters, ledgerEl);

  // Animate only genuinely new rows. Animating the whole table on every
  // poll is visual thrash and destroys the selected-row highlight mid-read.
  const fresh = [];
  for (const tr of feedEl.querySelectorAll("tr.feed-row")) {
    const key = tr.dataset.key;
    if (key && !seenRowKeys.has(key)) { seenRowKeys.add(key); fresh.push(tr); }
  }
  if (seenRowKeys.size > 400) seenRowKeys = new Set([...seenRowKeys].slice(-200));
  animateFeedRows(fresh);
  animateMeterSlots(meterEl.querySelectorAll(".slot"));

  // The trip runs once per subject, the first time its budget is seen spent.
  for (const card of meterEl.querySelectorAll('.meter[data-exhausted="1"]')) playTrip(card);

  renderOverview(rows);
  renderFiles(rows);

  const badge = $("#nav-count-egress");
  if (badge) { badge.textContent = rows.length ? String(rows.length) : ""; }

  if (loadOlderBtn) loadOlderBtn.disabled = !store.cursor;
}

store.subscribe(rerender);
renderDiff(null, diffEl);

/* ================================================================== policy */

cedarTextarea?.addEventListener("input", () => { policyEditorTouched = true; });

function applyPolicyToUI(policyState) {
  if (!policyState) return;
  const version = policyState.bundle.version || "(unversioned)";
  for (const el of $$("[data-policy-version]")) el.textContent = version;
  currentEtag = policyState.etag;
  if (policyEtagEl) policyEtagEl.textContent = currentEtag ? `etag ${currentEtag}` : "";
  if (!policyEditorTouched && cedarTextarea) cedarTextarea.value = policyState.bundle.cedar || "";
}

async function refreshPolicy() {
  try { applyPolicyToUI(await store.refreshPolicy()); }
  catch { for (const el of $$("[data-policy-version]")) el.textContent = "(unreachable)"; }
}

$("#policy-reload-btn")?.addEventListener("click", () => {
  policyEditorTouched = false;
  refreshPolicy();
});

$("#policy-save-btn")?.addEventListener("click", async () => {
  hide(policyErrorEl); hide(policyOkEl);
  const currentBundle = store.policy ? store.policy.bundle : {};
  // Drop `version` deliberately: app_control.py does
  // `payload.get("version") or _now_iso()`, so echoing the old version back
  // pins the stored bundle to its original version string forever.
  const { version: _oldVersion, ...carriedOver } = currentBundle;
  const bundle = { ...carriedOver, cedar: cedarTextarea.value };
  try {
    const resp = await api.savePolicy(bundle, currentEtag, nakaKeyInput.value);
    showOk(policyOkEl, `saved — version ${resp.version}`);
    policyEditorTouched = false;
    await refreshPolicy();
  } catch (err) {
    const body = err.body && err.body.error;
    showError(policyErrorEl, body ? `${body.code}: ${body.message}` : err.message);
  }
});

/* ========================================================== enrol command */

// Filled with this deployment's own origin, so an operator copies a command
// that works rather than one with a <url> placeholder they have to resolve.
const enrollCmdEl = $("#enroll-cmd");
if (enrollCmdEl) {
  const cmd = `node scripts/naka-enroll.js --control ${window.location.origin} --key <X-Naka-Key>`;
  enrollCmdEl.textContent = cmd;
  $("#enroll-copy")?.addEventListener("click", async (ev) => {
    try {
      await navigator.clipboard.writeText(cmd);
      const b = ev.currentTarget;
      b.textContent = "copied";
      setTimeout(() => { b.textContent = "copy"; }, 1400);
    } catch { /* falls back to manual selection, same as the other commands */ }
  });
}

/* ============================================================ copy buttons */

for (const btn of $$("[data-copy]")) {
  btn.addEventListener("click", async () => {
    const text = btn.dataset.copy;
    try {
      await navigator.clipboard.writeText(text);
      const was = btn.textContent;
      btn.textContent = "copied";
      setTimeout(() => { btn.textContent = was; }, 1400);
    } catch {
      // Clipboard is blocked in some embedded/insecure contexts. Select the
      // command instead so the operator can copy it by hand rather than
      // being told nothing happened.
      const pre = btn.closest(".d-cmd")?.querySelector("span:not(.p)");
      if (pre) {
        const range = document.createRange();
        range.selectNodeContents(pre);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    }
  });
}

/* ==================================================================== boot */

route();
startFleetPolling();
pingHealth();
setInterval(pingHealth, 15000);
refreshPolicy();
setInterval(refreshPolicy, 10000);
store.poll(1500);
