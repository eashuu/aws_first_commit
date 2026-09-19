// render.js — pure functions. Each one writes into the DOM element it is
// given and nothing else: no fetches, no globals, no module-level state.
//
// renderDiff's one hard rule: it must never be handed, and must never try
// to fetch, original plaintext. There is no field anywhere in the API
// contract that could carry it (DynamoDB never stored it — see guard.py's
// _redact, which only ever counts and replaces spans, never persists them).
// The "before" side below is rebuilt purely from entities_found's
// {type: count} map as type-and-shape tokens; the "after" side lists
// entities_masked (as placeholder-shaped tokens, annotated with the Cedar
// policy that masked them) versus entities_revealed (as "released" counts).

// Status hues follow the AWS console convention: red means "this failed",
// not "this was blocked". A denied call or a withheld payload is the
// guardrail working as designed, so both read amber; --fault (the only red
// in the product) is reserved for the states where Naka could not reach a
// decision at all. A demo full of successful blocks must not look like a
// demo full of errors.
const DECISION_COLOR = {
  ALLOW: "var(--allow)",
  DENY: "var(--deny)",
};

const OUTCOME_COLOR = {
  ok: "var(--allow)",
  denied_call: "var(--deny)",
  denied_placeholder: "var(--deny)",
  withheld_detector: "var(--fault)", // the detector never ran — a real fault
  withheld_normalize: "var(--redact)",
  withheld_ledger: "var(--fault)", // ledger unreachable — a real fault
  withheld_internal_error: "var(--fault)",
};

// Canonical shape hints, NOT measured per-instance data (the API never
// gives us a real length, only a count per type — see audit.py's
// entities_found: dict[str, int]). Only entity types whose format is fixed
// by construction in detect.py's tier-1 checksum validators get an exact
// shape: Aadhaar is always a 12-digit Verhoeff-valid run, PAN is always
// 5 letters + 4 digits + 1 letter = 10 chars. Every other type (Comprehend
// or tier-3 output: NAME, EMAIL, PHONE, ADDRESS, ...) has no fixed length,
// so one is never fabricated for it.
const SHAPE_HINTS = {
  IN_AADHAAR: "12 digits",
  IN_PERMANENT_ACCOUNT_NUMBER: "10 chars",
};

function shapeFor(type) {
  return SHAPE_HINTS[type] || "variable shape";
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function fmtTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  // Bare, not esc()'d — every caller escapes the return value itself, and
  // escaping here too renders a literal "&amp;" for an unparseable ts.
  if (Number.isNaN(d.getTime())) return ts;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  const ms = String(d.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

function pill(text, color) {
  // `pill-tag`, not `pill` — `pill` is the hero's rounded status capsule.
  // A status mark in a data table is a squared stamp, and it carries the
  // decision hue on a left rule rather than as a full-saturation fill.
  return `<span class="pill-tag" style="--pill-color:${color}">${esc(text)}</span>`;
}

// ---------------------------------------------------------------------------
// renderFeed
// ---------------------------------------------------------------------------

export function renderFeed(rows, el) {
  if (!el) return;
  if (!rows || rows.length === 0) {
    // An empty screen is an invitation to act, so it says what to click.
    el.innerHTML =
      '<div class="empty"><strong>No decisions yet.</strong> ' +
      "Pick a one-click scenario above — each one runs a real call sequence " +
      "against the deployed stack and fills this feed with what it decided.</div>";
    return;
  }

  const table = document.createElement("table");
  table.className = "feed-table";
  const thead = document.createElement("thead");
  thead.innerHTML =
    "<tr><th>time</th><th>tool</th><th>principal</th><th>subject</th><th>decision</th><th>outcome</th></tr>";
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.tabIndex = 0;
    tr.className = "feed-row";
    // Stable identity across re-renders, so the caller can animate only
    // the rows that are genuinely new rather than the whole table.
    tr.dataset.key = `${row.ts}#${row.seq}#${row.tool}#${row.principal}`;
    const decisionColor = DECISION_COLOR[row.call_decision] || "var(--ink-500)";
    const outcomeColor = OUTCOME_COLOR[row.outcome] || "var(--ink-500)";
    const decisionLabel = row.deny_policy ? `${row.call_decision} · ${row.deny_policy}` : row.call_decision;

    tr.innerHTML = `
      <td class="mono">${esc(fmtTime(row.ts))}</td>
      <td>${esc(row.tool)}</td>
      <td class="mono">${esc(row.principal)}</td>
      <td class="mono">${esc(row.subject)}</td>
      <td>${pill(decisionLabel, decisionColor)}</td>
      <td>${pill(row.outcome, outcomeColor)}</td>
    `;

    const select = () => {
      for (const sib of tbody.querySelectorAll("tr.feed-row-selected")) sib.classList.remove("feed-row-selected");
      tr.classList.add("feed-row-selected");
      el.dispatchEvent(new CustomEvent("naka:selectrow", { detail: row, bubbles: true }));
    };
    tr.addEventListener("click", select);
    tr.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        select();
      }
    });

    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  el.innerHTML = "";
  el.appendChild(table);
}

// ---------------------------------------------------------------------------
// renderTiers — every detector tier, including the ones that did nothing
// ---------------------------------------------------------------------------
//
// Listing only the tiers that ran would turn this into an error log. Listing
// all of them, with a neutral NOT_RUN for anything gated, is what makes it an
// audit — and it is the same distinction the product itself enforces: "found
// nothing" and "never looked" must never render the same way.

const TIER_STATUS = {
  PASS: { label: "Available", color: "var(--allow)" },
  NOT_RUN: { label: "Not run", color: "var(--ink-500)" },
  FAIL: { label: "Fault", color: "var(--fault)" },
};

export function renderTiers(diag, el) {
  if (!el) return;
  if (!diag || !diag.tiers) {
    el.innerHTML = '<div class="empty">Checking detector coverage…</div>';
    return;
  }

  const rows = diag.tiers
    .map((t) => {
      const s = TIER_STATUS[t.status] || TIER_STATUS.NOT_RUN;
      const note =
        t.status === "NOT_RUN" && t.note
          ? `${t.note} — service not enabled on this account`
          : t.note || "—";
      return `
        <tr>
          <td class="mono">${esc(t.tier)}</td>
          <td>${esc(t.name)}</td>
          <td class="tier-detail">${esc(t.detail)}</td>
          <td><span class="tier-status" style="--pill-color:${s.color}">${esc(s.label)}</span></td>
          <td class="tier-note mono">${esc(note)}</td>
        </tr>`;
    })
    .join("");

  el.innerHTML = `
    <table class="feed-table tier-table">
      <thead><tr><th>tier</th><th>detector</th><th>does</th><th>status</th><th>detail</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="tier-foot">
      Checked ${esc(diag.checked_at || "")} · ${esc(diag.region || "")}.
      A tier reported <em>Not run</em> is one this account cannot reach — its findings are
      absent, not empty, and nothing downstream treats them as a clean result.
    </div>`;
}

// ---------------------------------------------------------------------------
// renderMeter
// ---------------------------------------------------------------------------
//
// meters: { subject: { seen: string[], budget: number, calls?: AuditRow[] } }
// matching api.session()'s wire shape exactly, with one optional
// enrichment: a per-subject `calls` array (the caller may attach the
// session's own call rows, filtered by subject) that lets this function
// tell a "spent" slot apart from a merely "filled" one. Without `calls`,
// every seen type renders as plain filled — the meter still degrades
// correctly, it just can't show hatching.

function computeHatchedTypes(calls) {
  const sorted = [...calls].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
  const revealedSoFar = new Set();
  const hatched = new Set();
  for (const c of sorted) {
    const masked = c.entities_masked || {};
    for (const type of Object.keys(masked)) {
      if (revealedSoFar.has(type)) hatched.add(type);
    }
    const revealed = c.entities_revealed || {};
    for (const type of Object.keys(revealed)) revealedSoFar.add(type);
  }
  return hatched;
}

// A role can be budget-exempt (policy.py's compliance override defaults to
// 9999) — drawing that many empty slots would flood the DOM for no
// informational gain, so past this many the meter switches to a compact
// "unlimited" readout instead of a full grid.
const UNLIMITED_BUDGET_THRESHOLD = 50;

export function renderMeter(meters, el) {
  if (!el) return;
  const subjects = Object.keys(meters || {});
  if (subjects.length === 0) {
    el.innerHTML = '<div class="empty">No subjects touched in this session yet.</div>';
    return;
  }

  el.innerHTML = "";
  for (const subject of subjects.sort()) {
    const m = meters[subject] || {};
    const seen = m.seen || [];
    const budget = m.budget ?? 0;
    const unlimited = budget >= UNLIMITED_BUDGET_THRESHOLD;
    const hatchedTypes = m.calls ? computeHatchedTypes(m.calls) : new Set();

    const wrap = document.createElement("div");
    wrap.className = "meter";

    const title = document.createElement("div");
    title.className = "meter-title";
    const budgetLabel = unlimited ? `∞ (budget ${budget}, exempt)` : String(budget);
    title.innerHTML = `<span class="mono">${esc(subject)}</span><span class="meter-count">${seen.length} / ${budgetLabel}</span>`;
    wrap.appendChild(title);

    const slots = document.createElement("div");
    slots.className = "meter-slots";
    const totalSlots = unlimited ? Math.max(seen.length, 1) : Math.max(budget, seen.length);
    for (let i = 0; i < totalSlots; i++) {
      const slot = document.createElement("span");
      if (i < seen.length) {
        const type = seen[i];
        slot.className = "slot " + (hatchedTypes.has(type) ? "slot-spent" : "slot-filled");
        slot.title = hatchedTypes.has(type) ? `${type} — revealed earlier, denied on a later call` : type;
      } else if (i < budget) {
        slot.className = "slot slot-empty";
        slot.title = "unused budget slot";
      } else {
        slot.className = "slot slot-over";
        slot.title = "over budget (session ceiling or compliance exemption)";
      }
      slots.appendChild(slot);
    }
    wrap.appendChild(slots);

    if (seen.length) {
      const legend = document.createElement("div");
      legend.className = "meter-legend mono";
      legend.textContent = seen.join(", ");
      wrap.appendChild(legend);
    }

    // The exhausted state. The second clause of this sentence is the whole
    // thesis of the project: what is denied now includes fields that were
    // allowed earlier, because the budget is cumulative, not per-call.
    const exhausted = !unlimited && budget > 0 && seen.length >= budget;
    if (exhausted) {
      wrap.dataset.exhausted = "1";
      const banner = document.createElement("div");
      banner.className = "meter-banner";
      banner.textContent =
        `Budget exhausted for ${subject}. Identifying fields are now redacted, ` +
        `including fields that passed earlier.`;
      wrap.appendChild(banner);
    }

    el.appendChild(wrap);
  }
}

// ---------------------------------------------------------------------------
// renderDiff
// ---------------------------------------------------------------------------

function tokenChips(countsByType, { placeholder = false, shaped = false, policies = null } = {}) {
  const chips = [];
  for (const [type, count] of Object.entries(countsByType || {})) {
    for (let i = 1; i <= count; i++) {
      if (placeholder) {
        chips.push(`<span class="chip chip-masked">[${esc(type)}_${i}]</span>`);
      } else if (shaped) {
        chips.push(`<span class="chip chip-before">‹${esc(type)} · ${esc(shapeFor(type))}›</span>`);
      } else {
        chips.push(`<span class="chip chip-revealed">${esc(type)} #${i} released</span>`);
      }
    }
    if (placeholder && policies && policies[type]) {
      chips.push(`<span class="chip-note">via ${esc(policies[type])}</span>`);
    }
  }
  return chips.join(" ");
}

export function renderDiff(row, el) {
  if (!el) return;
  if (!row) {
    el.innerHTML = '<div class="empty">Click a row in the feed to see what the tool returned vs. what reached the model.</div>';
    return;
  }

  if (row.call_decision === "DENY") {
    el.innerHTML = `
      <div class="diff-denied">
        <div class="diff-head">Call denied at Q1 — the tool never ran</div>
        <div class="diff-meta mono">
          tool: ${esc(row.tool)} &middot; subject: ${esc(row.subject)}
          ${row.deny_policy ? ` &middot; policy: ${esc(row.deny_policy)}` : ""}
        </div>
        <p class="diff-note">Nothing was scanned or masked: the call itself was refused by Cedar before it reached the tool, so there is no "before"/"after" to compare.</p>
      </div>
    `;
    return;
  }

  const foundEmpty = !row.entities_found || Object.keys(row.entities_found).length === 0;
  const beforeHtml = foundEmpty
    ? '<span class="empty-inline">no entities detected</span>'
    : tokenChips(row.entities_found, { shaped: true });

  const maskedEmpty = !row.entities_masked || Object.keys(row.entities_masked).length === 0;
  const maskedHtml = maskedEmpty
    ? '<span class="empty-inline">nothing masked</span>'
    : tokenChips(row.entities_masked, { placeholder: true, policies: row.mask_policies });

  const revealedEmpty = !row.entities_revealed || Object.keys(row.entities_revealed).length === 0;
  const revealedHtml = revealedEmpty
    ? '<span class="empty-inline">nothing released</span>'
    : tokenChips(row.entities_revealed, {});

  const outcomeColor = OUTCOME_COLOR[row.outcome] || "var(--ink-500)";

  el.innerHTML = `
    <div class="diff">
      <div class="diff-meta mono">
        tool: ${esc(row.tool)} &middot; subject: ${esc(row.subject)} &middot; ${pill(row.outcome, outcomeColor)}
        &middot; detector tiers: ${row.detector_tiers && row.detector_tiers.length ? esc(row.detector_tiers.join(", ")) : "none"}
      </div>

      <div class="diff-col">
        <div class="diff-col-title">what the tool returned (shape only — never plaintext)</div>
        <div class="diff-chips">${beforeHtml}</div>
      </div>

      <div class="diff-col">
        <div class="diff-col-title">masked before reaching the model</div>
        <div class="diff-chips">${maskedHtml}</div>
      </div>

      <div class="diff-col">
        <div class="diff-col-title">released to the model</div>
        <div class="diff-chips">${revealedHtml}</div>
      </div>
    </div>
  `;
}
