// store.js — a plain object module, no reactivity library. Every mutating
// method reassigns/mutates the fields below in place and then calls
// `_notify()`; subscribers just re-render from `store` directly.
//
// api.feed() rows and api.session(id)'s `calls` come from the same server
// function (_item_to_row in app_control.py), which DOES emit `session_id`
// (derived from the item's `pk`). DynamoDB projects the base table's key
// attributes into every GSI automatically, so /feed rows carry it too —
// which is what lets clicking a feed row drill straight into that row's
// own session. `sessions` is still filled on demand via `loadSession(id)`,
// because the meters it holds are only returned by the /session route.

import { api } from "./api.js";

function rowKey(row) {
  // (ts, seq) is unique per session; tool is just belt-and-braces against
  // any future ts-collision across sessions sharing one feed day.
  return `${row.ts}#${row.seq}#${row.tool}#${row.principal}`;
}

function makeStore() {
  const listeners = new Set();

  const store = {
    sessions: {}, // session_id -> { calls: AuditRow[], meters: {subject: {seen, budget}} }
    feedRows: [], // global live feed, newest first
    cursor: null, // api.feed()'s pagination cursor (oldest-ward, for "load older")
    policy: null, // { bundle, etag }

    _timer: null,
    _feedKeys: new Set(),

    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },

    _notify() {
      for (const fn of listeners) {
        try {
          fn(store);
        } catch (err) {
          console.error("naka: store subscriber threw", err);
        }
      }
    },

    // Pulls the newest page of today's feed and merges anything not seen
    // yet in at the front (feed rows already arrive newest-first).
    async refreshFeed() {
      const resp = await api.feed({ limit: 50 });
      const rows = resp.rows || [];
      const fresh = [];
      for (const row of rows) {
        const key = rowKey(row);
        if (!store._feedKeys.has(key)) {
          store._feedKeys.add(key);
          fresh.push(row);
        }
      }
      if (fresh.length) {
        store.feedRows = [...fresh, ...store.feedRows].slice(0, 1000);
      }
      // Only seed the cursor, never reset it. This runs every 1.5s against
      // page 1, so reassigning unconditionally would drag the paging
      // position back to the top of the feed on every tick and make
      // loadOlder() re-fetch the same page forever.
      if (store.cursor === null && resp.cursor) store.cursor = resp.cursor;
      // Re-rendering the feed replaces the whole <table>, which drops the
      // selected-row highlight, keyboard focus and scroll position. Doing
      // that twice a second when nothing arrived is both pointless and
      // visible — during a demo the selected row un-highlights mid-sentence.
      if (fresh.length) store._notify();
      return resp;
    },

    // Older rows than the current page, via the server's cursor. Appended
    // at the end (they're older) rather than merged at the front.
    async loadOlder() {
      if (!store.cursor) return null;
      const resp = await api.feed({ after: store.cursor, limit: 50 });
      const rows = resp.rows || [];
      for (const row of rows) {
        const key = rowKey(row);
        if (!store._feedKeys.has(key)) {
          store._feedKeys.add(key);
          store.feedRows.push(row);
        }
      }
      store.cursor = resp.cursor ?? null;
      store._notify();
      return resp;
    },

    // Session drill-down: calls + per-subject disclosure meters. Not part
    // of poll() — called on demand (e.g. after a Run, or when the session
    // id field changes) since api.session() is scoped to one session id
    // the caller already has, not something the feed can discover.
    async loadSession(sessionId) {
      if (!sessionId) return null;
      const resp = await api.session(sessionId);
      store.sessions[sessionId] = {
        calls: resp.calls || [],
        meters: resp.meters || {},
      };
      store._notify();
      return store.sessions[sessionId];
    },

    async refreshPolicy() {
      const { bundle, etag } = await api.policy();
      store.policy = { bundle, etag };
      store._notify();
      return store.policy;
    },

    poll(ms = 1500) {
      store.stop();
      const tick = () => {
        store.refreshFeed().catch((err) => console.error("naka: feed poll failed", err));
      };
      tick();
      store._timer = setInterval(tick, ms);
    },

    stop() {
      if (store._timer) {
        clearInterval(store._timer);
        store._timer = null;
      }
    },
  };

  return store;
}

export const store = makeStore();
