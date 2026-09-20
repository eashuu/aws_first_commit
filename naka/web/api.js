// The only module that knows a URL exists. CONTROL_URL is "this page's
// origin" (the control plane serves the UI). AGENT_URL is the data-plane
// Function URL, which is a separate Lambda — the viewer sets it once and it
// is remembered in localStorage, a per-viewer convenience, never sent
// anywhere but into these fetch calls.
//
// localStorage is per-viewer by definition, so a first-time visitor has
// none and would hit "Set the agent Function URL first" with nothing to
// tell them what that URL is. `health()` carries the deploy's own
// AGENT_URL as a fallback for exactly that case.

const CONTROL_URL = window.location.origin;

function getAgentUrl() {
  try {
    return localStorage.getItem("naka_agent_url") || "";
  } catch {
    return "";
  }
}

function setAgentUrl(url) {
  try {
    localStorage.setItem("naka_agent_url", url);
  } catch {
    /* private window / blocked storage — the session still works, just unremembered */
  }
}

async function asJson(resp) {
  const text = await resp.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!resp.ok) {
    const message = body && body.error ? body.error.message : `HTTP ${resp.status}`;
    const err = new Error(message);
    err.status = resp.status;
    err.body = body;
    throw err;
  }
  return body;
}

export const api = {
  getAgentUrl,
  setAgentUrl,

  async health() {
    const resp = await fetch(`${CONTROL_URL}/health`);
    return asJson(resp);
  },

  async diag() {
    const resp = await fetch(`${CONTROL_URL}/diag`);
    return asJson(resp);
  },

  async feed({ after, limit = 50, date } = {}) {
    const qs = new URLSearchParams();
    if (after) qs.set("after", after);
    if (limit) qs.set("limit", String(limit));
    if (date) qs.set("date", date);
    const resp = await fetch(`${CONTROL_URL}/feed?${qs.toString()}`);
    return asJson(resp);
  },

  // Endpoint plane. Devices enrol with the operator key and then report
  // their own decisions; this read is what turns the console's Endpoint
  // view from an honest empty state into a live fleet.
  async fleet() {
    const resp = await fetch(`${CONTROL_URL}/endpoint/fleet`);
    return asJson(resp);
  },

  async enrollDevice({ hostname, os, user, agent_version }, key) {
    const resp = await fetch(`${CONTROL_URL}/endpoint/enroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(key ? { "X-Naka-Key": key } : {}) },
      body: JSON.stringify({ hostname, os, user, agent_version }),
    });
    return asJson(resp);
  },

  async session(id) {
    const resp = await fetch(`${CONTROL_URL}/session/${encodeURIComponent(id)}`);
    return asJson(resp);
  },

  async policy() {
    const resp = await fetch(`${CONTROL_URL}/policy`);
    const etag = resp.headers.get("ETag");
    const bundle = await asJson(resp);
    return { bundle, etag };
  },

  async savePolicy(bundle, etag, key) {
    const resp = await fetch(`${CONTROL_URL}/policy`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...(etag ? { "If-Match": etag } : {}),
        ...(key ? { "X-Naka-Key": key } : {}),
      },
      body: JSON.stringify(bundle),
    });
    return asJson(resp);
  },

  async run({ session_id, prompt, user, role }) {
    const agentUrl = getAgentUrl();
    if (!agentUrl) throw new Error("Set the agent Function URL first");
    const resp = await fetch(agentUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, prompt, user, role }),
    });
    return asJson(resp);
  },

  // Scripted scenario: the same guardrail, driven by a fixed call sequence
  // instead of by the model. Used while Bedrock is gated on this account —
  // every decision it returns is real, only the choice of which tool to
  // call next is scripted. See demo.py.
  async demo({ scenario, session_id, user, role }) {
    const agentUrl = getAgentUrl();
    if (!agentUrl) throw new Error("Set the agent Function URL first");
    const resp = await fetch(agentUrl.replace(/\/$/, "") + "/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario, session_id, user, role }),
    });
    return asJson(resp);
  },
};
