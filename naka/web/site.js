// site.js — motion for the marketing surface.
//
// Three libraries, each doing the job it is actually best at:
//
//   Lenis      — owns the scroll position for the whole page.
//   GSAP       — timelines and SVG stroke work: the hero sequence, the
//                draw-on diagrams, the plane-card choreography.
//   motion.dev — the declarative spring/keyframe animator used for reveals,
//                the marquee, counters and the FAQ accordion. Its WAAPI
//                backend runs those off the main thread, which is why the
//                page stays smooth while GSAP is busy with the hero.
//
// EVERY ONE OF THEM IS OPTIONAL AT RUNTIME. They are loaded from CDNs and a
// venue wifi hiccup must degrade this page to a plain, readable site — never
// a blank one. So nothing below assumes a global exists, and the reveal
// classes in site.css are authored *visible*; the `s-motion` class that
// hides them is added only after a working reveal loop has been built.
//
// ---------------------------------------------------------------------------
// One hard-won constraint, restated here because it is invisible and it will
// bite anyone who edits this file:
//
//   LENIS DOES NOT EMIT NATIVE `scroll` EVENTS ON `window`.
//
// Measured on the deployed page: window.scrollY advances to 1600 while a
// window 'scroll' listener fires exactly zero times. Anything that needs to
// know where the page is must therefore either (a) be told by Lenis directly,
// or (b) ask the DOM itself from requestAnimationFrame. Listening for
// 'scroll' is option (c): silently never running.
//
// Content whose *readability* depends on scroll position — the leak scene —
// uses a rAF poll plus native CSS `position: sticky`. Decoration that can
// safely never run uses ScrollTrigger.
// ---------------------------------------------------------------------------

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const gsap = window.gsap || null;
const ScrollTrigger = window.ScrollTrigger || null;
const Lenis = window.Lenis || null;
const M = window.Motion || null; // motion.dev UMD sets globalThis.Motion

if (gsap && ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

const EASE = [0.16, 1, 0.3, 1]; // motion.dev cubic-bezier, matches --ease

let lenis = null;

/* ------------------------------------------------------------------ scroll */

function initLenis() {
  if (!Lenis || reduced) return null;

  lenis = new Lenis({
    duration: 1.05,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    // Touch devices already have momentum scrolling. Layering Lenis on top
    // of it fights the platform and reads as lag, so leave touch native.
    smoothTouch: false,
  });

  if (gsap) {
    // Drive Lenis from GSAP's ticker rather than its own rAF loop, so scroll
    // position and every ScrollTrigger reading come from the same frame.
    // Two independent rAF loops is how you get one-frame jitter on pins.
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);
    if (ScrollTrigger) lenis.on("scroll", ScrollTrigger.update);
  } else {
    const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
  }

  // Anchor links have to go through Lenis or they fight it for one second.
  document.addEventListener("click", (ev) => {
    const a = ev.target.closest('a[href^="#"]');
    if (!a) return;
    const id = a.getAttribute("href");
    if (!id || id === "#") return;
    const target = document.querySelector(id);
    if (!target) return;
    ev.preventDefault();
    lenis.scrollTo(target, { offset: -80 });
  });

  return lenis;
}

/* --------------------------------------------------------------------- nav */

function initNav() {
  const nav = document.querySelector(".s-nav");
  if (!nav) return;

  // Read scroll from the document, not from a scroll event — see the header.
  let stuck = false;
  const poll = () => {
    const y = window.scrollY || document.documentElement.scrollTop || 0;
    const next = y > 12;
    if (next !== stuck) {
      stuck = next;
      nav.classList.toggle("s-nav-stuck", stuck);
    }
    requestAnimationFrame(poll);
  };
  requestAnimationFrame(poll);

  // Product mega-menu. Opens on hover for pointer users and on click for
  // everyone, because hover-only is unusable on touch and with a keyboard.
  for (const wrap of nav.querySelectorAll(".s-menu-wrap")) {
    const trigger = wrap.querySelector(".s-nav-link");
    if (!trigger) continue;
    const open = (on) => {
      wrap.classList.toggle("s-menu-open", on);
      trigger.setAttribute("aria-expanded", on ? "true" : "false");
      const menu = wrap.querySelector(".s-menu");
      if (menu && M && !reduced && on) {
        M.animate(
          menu.querySelectorAll(".s-menu-item"),
          { opacity: [0, 1], transform: ["translateY(6px)", "translateY(0px)"] },
          { duration: 0.32, delay: M.stagger(0.04), ease: EASE }
        );
      }
    };
    trigger.addEventListener("click", (ev) => {
      ev.preventDefault();
      open(!wrap.classList.contains("s-menu-open"));
    });
    wrap.addEventListener("mouseenter", () => { if (window.innerWidth > 1080) open(true); });
    wrap.addEventListener("mouseleave", () => { if (window.innerWidth > 1080) open(false); });
    wrap.addEventListener("focusout", (ev) => {
      if (!wrap.contains(ev.relatedTarget)) open(false);
    });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") open(false); });
  }

  const burger = nav.querySelector(".s-nav-burger");
  if (burger) {
    burger.addEventListener("click", () => {
      const on = nav.classList.toggle("s-nav-open");
      burger.setAttribute("aria-expanded", on ? "true" : "false");
    });
  }

  // Mark the current page in the nav from the URL, so every page does not
  // have to hand-maintain an aria-current attribute that will drift.
  const here = location.pathname.replace(/\/$/, "").split("/").pop() || "index.html";
  for (const a of nav.querySelectorAll(".s-nav-link[href]")) {
    const target = a.getAttribute("href").split("/").pop();
    if (target && target === here) a.setAttribute("aria-current", "page");
  }
}

/* ----------------------------------------------------------------- reveals */

// The rAF sweep. This exact shape is load-bearing: IntersectionObserver was
// tried on this codebase and fired once on load and never again under Lenis,
// leaving every panel stranded at opacity 0. Polling asks the DOM where
// things are instead of waiting to be told, so it cannot be starved. It
// costs one getBoundingClientRect per pending element per frame, and stops
// itself the moment the last element has been revealed — steady-state zero.
function initReveals() {
  const items = [...document.querySelectorAll(".s-rise")];
  if (!items.length || reduced) return;

  document.documentElement.classList.add("s-motion");

  const pending = new Set(items);
  let queued = false;

  const show = (el) => {
    const group = el.dataset.riseGroup
      ? el.querySelectorAll(el.dataset.riseGroup)
      : null;

    if (M) {
      M.animate(
        el,
        { opacity: [0, 1], transform: ["translateY(26px)", "translateY(0px)"] },
        { duration: 0.75, ease: EASE, delay: Number(el.dataset.riseDelay || 0) }
      );
      // A container can stagger its own children by naming them. Used for
      // card grids, where one block fade reads as a slab and a stagger
      // reads as a list.
      if (group && group.length) {
        M.animate(
          group,
          { opacity: [0, 1], transform: ["translateY(18px)", "translateY(0px)"] },
          { duration: 0.6, ease: EASE, delay: M.stagger(0.07, { startDelay: 0.08 }) }
        );
      }
    }
    // The class is what actually persists the end state. The animation above
    // is a nicety on top of it; if motion.dev is missing the class alone
    // still brings the element in via the CSS transition.
    el.classList.add("s-in");
    decorate(el);
  };

  const sweep = () => {
    queued = false;
    const limit = window.innerHeight * 0.9;
    for (const el of [...pending]) {
      if (el.getBoundingClientRect().top < limit) {
        pending.delete(el);
        show(el);
      }
    }
    if (pending.size && document.visibilityState === "visible") {
      queued = true;
      requestAnimationFrame(sweep);
    }
  };

  const kick = () => {
    if (!queued && pending.size) { queued = true; requestAnimationFrame(sweep); }
  };

  // rAF is suspended entirely while a tab is hidden — measured here as zero
  // frames in 1200ms. Without these, a visitor who switches away mid-scroll
  // and comes back finds everything they scrolled past still invisible with
  // nothing scheduled to fix it. Each is idempotent; all stop when empty.
  document.addEventListener("visibilitychange", kick);
  window.addEventListener("scroll", kick, { passive: true });
  window.addEventListener("resize", kick, { passive: true });
  if (lenis) lenis.on("scroll", kick);

  sweep();
}

// Per-section GSAP flourishes, fired by the same sweep that reveals the
// section. All decoration: if GSAP is absent the section is fully readable.
function decorate(el) {
  if (!gsap || reduced) return;

  const svgs = el.querySelectorAll("svg");
  for (const svg of svgs) {
    const strokes = svg.querySelectorAll("[data-draw]");
    for (const s of strokes) {
      const len = typeof s.getTotalLength === "function" ? s.getTotalLength() : 0;
      if (!len) continue;
      gsap.fromTo(
        s,
        { strokeDasharray: len, strokeDashoffset: len },
        { strokeDashoffset: 0, duration: 1, ease: "power2.inOut" }
      );
    }
    const pops = svg.querySelectorAll("[data-pop]");
    if (pops.length) {
      gsap.from(pops, {
        scale: 0, transformOrigin: "center",
        duration: 0.5, ease: "back.out(2)", stagger: 0.07, delay: 0.25,
      });
    }
  }

  const bars = el.querySelectorAll("[data-bar]");
  if (bars.length) {
    gsap.fromTo(bars, { scaleX: 0 }, { scaleX: 1, transformOrigin: "left", duration: 0.8, ease: "expo.out", stagger: 0.06 });
  }
}

/* -------------------------------------------------------------------- hero */

function initHero() {
  const h1 = document.querySelector("[data-split]");
  if (h1 && gsap && !reduced) {
    // Split into word spans, each wrapped in an overflow-hidden mask so the
    // words rise out of nothing rather than fading in place. Done in JS so
    // the markup keeps one readable text node for screen readers and for
    // the no-JS case; aria-label preserves it either way.
    const text = h1.textContent.replace(/\s+/g, " ").trim();
    h1.setAttribute("aria-label", text);
    const html = h1.innerHTML;
    // Preserve inline <em> emphasis by splitting on the rendered nodes
    // rather than on the flat string.
    h1.innerHTML = "";
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    for (const node of [...tmp.childNodes]) {
      const isEm = node.nodeType === 1 && node.tagName === "EM";
      const words = (node.textContent || "").split(/(\s+)/);
      for (const w of words) {
        if (!w.trim()) { h1.appendChild(document.createTextNode(" ")); continue; }
        const mask = document.createElement("span");
        mask.className = "s-word";
        mask.setAttribute("aria-hidden", "true");
        const inner = document.createElement(isEm ? "em" : "span");
        inner.textContent = w;
        mask.appendChild(inner);
        h1.appendChild(mask);
      }
    }

    gsap
      .timeline({ defaults: { ease: "expo.out" } })
      .from(h1.querySelectorAll(".s-word > *"), {
        yPercent: 112, duration: 1.1, stagger: 0.055,
      })
      .from("[data-hero]", { y: 20, opacity: 0, duration: 0.8, stagger: 0.08 }, "-=0.72");
  } else if (h1) {
    h1.classList.add("s-split-off");
  }

  // The hero scope tilts very slightly toward the pointer. Small enough to
  // read as depth rather than as a toy — 4 degrees maximum, springed so it
  // settles instead of snapping.
  const scope = document.querySelector("[data-tilt]");
  if (scope && M && !reduced && window.matchMedia("(pointer: fine)").matches) {
    const wrap = scope.parentElement;
    wrap.addEventListener("pointermove", (ev) => {
      const r = wrap.getBoundingClientRect();
      const px = (ev.clientX - r.left) / r.width - 0.5;
      const py = (ev.clientY - r.top) / r.height - 0.5;
      M.animate(
        scope,
        { transform: `perspective(1200px) rotateY(${px * 5}deg) rotateX(${-py * 5}deg)` },
        { type: "spring", stiffness: 180, damping: 22 }
      );
    });
    wrap.addEventListener("pointerleave", () => {
      M.animate(
        scope,
        { transform: "perspective(1200px) rotateY(0deg) rotateX(0deg)" },
        { type: "spring", stiffness: 140, damping: 20 }
      );
    });
  }

  // The ledger strip fills left to right once, on load, so the first thing
  // a visitor sees is a budget being spent.
  const slots = document.querySelectorAll(".s-slots i");
  if (slots.length && M && !reduced) {
    M.animate(
      slots,
      { transform: ["scaleX(0)", "scaleX(1)"] },
      { duration: 0.5, delay: M.stagger(0.09, { startDelay: 0.7 }), ease: EASE }
    );
  }
}

// The marquee used to live here as a motion.dev animation. It now runs as a
// CSS keyframe in site.css and needs no JavaScript at all — see the comment
// on .s-marquee-track for why. Nothing to initialise.

/* -------------------------------------------------------------- leak scene */

// The argument the whole product rests on: six individually-innocuous calls
// that together rebuild a person. Driven by a rAF poll over a sticky stage
// rather than by ScrollTrigger's pin, because this sequence carries CONTENT
// and must not be able to fail silently. (ScrollTrigger pinning under Lenis
// is exactly what left eleven panels at opacity 0 on the console page.)
function initLeakScene() {
  const rail = document.querySelector("[data-leak]");
  if (!rail) return;

  const steps = [...rail.querySelectorAll(".s-leak-step")];
  const rows = [...rail.querySelectorAll(".s-dossier-row")];
  const verdict = rail.querySelector(".s-dossier-verdict");
  const counter = rail.querySelector("[data-leak-count]");
  if (!steps.length) return;

  // Below the pin breakpoint the CSS lays the steps out as a static list and
  // the dossier shows complete. Nothing to drive.
  const stacked = () => window.innerWidth <= 1080 || reduced;

  let last = -1;
  const frame = () => {
    if (stacked()) {
      for (const s of steps) s.classList.add("is-on");
      for (const r of rows) r.classList.add(r.dataset.blocked ? "is-blocked" : "is-known");
      requestAnimationFrame(frame);
      return;
    }

    const r = rail.getBoundingClientRect();
    const travel = r.height - window.innerHeight;
    const p = travel > 0 ? Math.min(1, Math.max(0, -r.top / travel)) : 0;

    // Map progress onto steps with a small dead zone at each end, so the
    // first and last states are readable rather than flashing past.
    const i = Math.min(steps.length - 1, Math.floor(p * steps.length * 0.999));
    if (i !== last) {
      last = i;
      steps.forEach((s, n) => s.classList.toggle("is-on", n === i));
      rows.forEach((row, n) => {
        const on = n <= i;
        row.classList.toggle("is-known", on && !row.dataset.blocked);
        row.classList.toggle("is-blocked", on && Boolean(row.dataset.blocked));
      });
      if (counter) counter.textContent = String(Math.min(i + 1, rows.length));
      if (verdict) {
        const done = i >= steps.length - 1;
        verdict.textContent = done
          ? "Naka refuses call 6 — the budget is already spent"
          : "every call above was individually authorized";
        verdict.classList.toggle("is-good", done);
        verdict.classList.toggle("is-bad", !done && i >= 3);
      }
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/* ---------------------------------------------------------------- counters */

// Counts up once, when the number first scrolls into view. Rounded every
// frame so it is never caught mid-fraction.
function initCounters() {
  const els = [...document.querySelectorAll("[data-count]")];
  if (!els.length) return;
  const pending = new Set(els);

  const run = (el) => {
    const to = Number(el.dataset.count);
    if (!Number.isFinite(to)) return;
    if (reduced || !M) { el.textContent = el.dataset.countPrefix ? el.dataset.countPrefix + to : String(to); return; }
    M.animate(0, to, {
      duration: 1.3,
      ease: EASE,
      onUpdate: (v) => {
        const n = to % 1 === 0 ? Math.round(v) : v.toFixed(1);
        el.textContent = (el.dataset.countPrefix || "") + n + (el.dataset.countSuffix || "");
      },
    });
  };

  const sweep = () => {
    for (const el of [...pending]) {
      if (el.getBoundingClientRect().top < window.innerHeight * 0.92) {
        pending.delete(el);
        run(el);
      }
    }
    if (pending.size) requestAnimationFrame(sweep);
  };
  requestAnimationFrame(sweep);
}

/* --------------------------------------------------------------------- faq */

function initFaq() {
  for (const item of document.querySelectorAll(".s-faq-item")) {
    const q = item.querySelector(".s-faq-q");
    const a = item.querySelector(".s-faq-a");
    if (!q || !a) continue;
    // Authored height:0 in CSS so the page never flashes every answer open
    // before JS runs; the button carries the real state.
    q.addEventListener("click", () => {
      const open = q.getAttribute("aria-expanded") === "true";
      q.setAttribute("aria-expanded", open ? "false" : "true");
      const target = open ? 0 : a.scrollHeight;
      if (M && !reduced) {
        M.animate(a, { height: `${target}px` }, { duration: 0.42, ease: EASE })
          .finished.then(() => { if (!open) a.style.height = "auto"; })
          .catch(() => {});
      } else {
        a.style.height = open ? "0px" : "auto";
      }
    });
  }
}

/* ----------------------------------------------------------------- pricing */

function initPricing() {
  const buttons = [...document.querySelectorAll("[data-bill]")];
  if (!buttons.length) return;
  const figures = [...document.querySelectorAll("[data-price]")];

  const apply = (period) => {
    for (const b of buttons) b.setAttribute("aria-pressed", b.dataset.bill === period ? "true" : "false");
    for (const f of figures) {
      const next = f.dataset[period];
      if (!next || next === f.textContent) continue;
      f.textContent = next;
      if (M && !reduced) {
        M.animate(f, { opacity: [0, 1], transform: ["translateY(-6px)", "translateY(0px)"] },
          { duration: 0.3, ease: EASE });
      }
    }
  };

  for (const b of buttons) b.addEventListener("click", () => apply(b.dataset.bill));
}

/* ---------------------------------------------------------------- parallax */

// Pure decoration, so this one may use ScrollTrigger: if it silently never
// runs, nothing is lost but a few pixels of drift.
function initParallax() {
  if (!gsap || !ScrollTrigger || reduced) return;
  for (const el of document.querySelectorAll("[data-parallax]")) {
    const amount = Number(el.dataset.parallax) || 40;
    gsap.to(el, {
      y: -amount,
      ease: "none",
      scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: 0.6 },
    });
  }
}

/* ------------------------------------------------------------ live status */

// Real numbers from the deployed control plane, or an honest "unreachable".
// Nothing on these pages fabricates a metric: if the API does not answer,
// the element says so rather than showing a plausible number.
async function initLiveStatus() {
  const nodes = document.querySelectorAll("[data-live]");
  if (!nodes.length) return;
  const origin = window.location.origin;

  const set = (key, value, ok = true) => {
    for (const el of document.querySelectorAll(`[data-live="${key}"]`)) {
      el.textContent = value;
      el.classList.toggle("is-live", ok);
      el.classList.toggle("is-down", !ok);
      const chip = el.closest(".s-chip");
      if (chip) { chip.classList.toggle("is-live", ok); chip.classList.toggle("is-down", !ok); }
    }
  };

  try {
    const h = await fetch(`${origin}/health`).then((r) => r.json());
    set("control", h.ok ? "control plane live" : "control plane degraded", Boolean(h.ok));
    if (h.agent_url) {
      try {
        const ok = (await fetch(h.agent_url.replace(/\/$/, "") + "/health")).ok;
        set("agent", ok ? "data plane live" : "data plane degraded", ok);
      } catch { set("agent", "data plane unreachable", false); }
    }
  } catch {
    set("control", "control plane unreachable", false);
    set("agent", "data plane unreachable", false);
  }

  try {
    const p = await fetch(`${origin}/policy`).then((r) => r.json());
    set("policy", p.version || "unversioned");
  } catch { set("policy", "unreachable", false); }

  // Today's real traffic through the guard. A zero here is a true zero, and
  // is shown as one.
  try {
    const f = await fetch(`${origin}/feed?limit=200`).then((r) => r.json());
    const rows = f.rows || [];
    const withheld = rows.reduce(
      (n, r) => n + Object.values(r.entities_masked || {}).reduce((a, b) => a + b, 0), 0);
    const denied = rows.filter((r) => String(r.outcome || "").startsWith("denied")).length;
    const unscanned = rows.filter(
      (r) => r.outcome === "ok" && (!r.detector_tiers || !r.detector_tiers.length)).length;
    set("calls", String(rows.length));
    set("withheld", String(withheld));
    set("denied", String(denied));
    set("unscanned", String(unscanned), unscanned === 0);
  } catch {
    for (const k of ["calls", "withheld", "denied", "unscanned"]) set(k, "—", false);
  }
}

/* -------------------------------------------------------------------- boot */

function boot() {
  initLenis();
  initNav();
  initHero();
  initReveals();
  initLeakScene();
  initCounters();
  initFaq();
  initPricing();
  initParallax();
  initLiveStatus();

  // ScrollTrigger measures on construction; webfonts land after that and
  // change every element's height. One refresh once they are in keeps the
  // parallax honest.
  if (ScrollTrigger && document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => ScrollTrigger.refresh()).catch(() => {});
  }
}

// The CDN scripts are `defer`red, so they have executed by DOMContentLoaded
// and the globals read at the top of this module are already populated.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
