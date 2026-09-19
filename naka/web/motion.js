// motion.js — Lenis smooth scroll, GSAP scroll reveals, anime.js data
// micro-motion, Lottie hero.
//
// Every library here is loaded from a CDN by index.html and is therefore
// allowed to be absent: a venue wifi hiccup must degrade the page to a
// plain, fully working console, never a blank one. That is why nothing
// below assumes a global exists, and why the reveal classes are authored
// "visible by default" in app.css — the `motion-ready` class that hides
// them is only added once GSAP has actually been confirmed present.

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const gsap = window.gsap || null;
const ScrollTrigger = window.ScrollTrigger || null;
const Lenis = window.Lenis || null;
const anime = window.anime || null;
const lottie = window.lottie || null;

if (gsap && ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

export const motionAvailable = Boolean(gsap);

// ---------------------------------------------------------------- scroll

export function initScroll() {
  if (!Lenis || !gsap || reduced) return null;

  const lenis = new Lenis({
    duration: 1.05,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    // Touch devices already have momentum scrolling; layering Lenis on top
    // of it fights the platform and feels laggy, so leave touch alone.
    smoothTouch: false,
  });

  // Drive Lenis from GSAP's ticker rather than its own rAF loop, so scroll
  // position and every ScrollTrigger reading come from the same frame.
  // Two independent rAF loops is how you get one-frame jitter on pinned
  // elements.
  lenis.on("scroll", () => {
    if (ScrollTrigger) ScrollTrigger.update();
  });
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);

  return lenis;
}

// ------------------------------------------------------------------ hero

export function initHero() {
  const title = document.querySelector("[data-split]");
  if (title && gsap && !reduced) {
    // Split into per-character spans for the stagger. Done here rather
    // than in the markup so the HTML keeps a single readable text node
    // for screen readers and for the no-JS case.
    const text = title.textContent.trim();
    title.setAttribute("aria-label", text);
    title.textContent = "";
    for (const ch of text) {
      const span = document.createElement("span");
      span.className = "char";
      span.setAttribute("aria-hidden", "true");
      span.textContent = ch;
      title.appendChild(span);
    }

    gsap
      .timeline({ defaults: { ease: "expo.out" } })
      .from(title.querySelectorAll(".char"), {
        yPercent: 118,
        opacity: 0,
        duration: 1.1,
        stagger: 0.045,
      })
      .from("[data-hero-fade]", { y: 22, opacity: 0, duration: 0.85, stagger: 0.09 }, "-=0.7");
  }

  if (gsap && !reduced) {
    // The two hero washes drift on independent, non-matching periods so
    // they never visibly re-sync into a loop the eye can latch onto.
    gsap.to(".hero-glow", {
      xPercent: 6,
      yPercent: -4,
      scale: 1.08,
      duration: 13,
      ease: "sine.inOut",
      repeat: -1,
      yoyo: true,
    });
  }

  if (lottie) {
    const mount = document.getElementById("lottie-redact");
    if (mount) {
      try {
        lottie.loadAnimation({
          container: mount,
          renderer: "svg",
          loop: true,
          autoplay: !reduced,
          path: "./anim/redact.json",
        });
      } catch {
        /* a missing or malformed animation must not take the page down */
      }
    }
  }
}

// --------------------------------------------------------------- reveals

export function initReveals() {
  if (reduced) return;
  try {
    buildReveals();
  } catch (err) {
    // `motion-ready` is what hides .reveal elements. If anything below it
    // throws, leaving that class on would leave real content at opacity 0
    // with nothing scheduled to bring it back — a blank page caused purely
    // by decoration. Always hand visibility back.
    document.documentElement.classList.remove("motion-ready");
    console.error("naka: reveal setup failed, falling back to static", err);
  }
}

function buildReveals() {
  // Content reveals run on IntersectionObserver + CSS, NOT on ScrollTrigger.
  // That is deliberate and was not the first attempt: driving them through
  // ScrollTrigger while Lenis owns the scroll left every trigger reporting
  // isActive with its tween stuck at progress 0, so all eleven panels stayed
  // at opacity 0 — a completely blank page caused purely by decoration.
  // Whether a user can READ the page must not depend on two animation
  // libraries agreeing about scroll position. IntersectionObserver is native,
  // has no interplay with Lenis, and degrades to "everything visible" when
  // it is missing.
  if (!("IntersectionObserver" in window)) return;

  document.documentElement.classList.add("motion-ready");

  // Polled from requestAnimationFrame, not from a scroll event, an
  // IntersectionObserver or ScrollTrigger. All three were tried here and
  // all three failed for the same underlying reason: **Lenis does not emit
  // native scroll events on window**. Measured on the deployed page —
  // window.scrollY advances to 1600 while a window 'scroll' listener fires
  // exactly 0 times. ScrollTrigger consequently left every tween at
  // progress 0 with all eleven panels stuck at opacity 0 (a blank page),
  // and IntersectionObserver fired once on load and never again.
  //
  // A rAF poll asks the DOM where things are instead of waiting to be told,
  // so it cannot be starved by whatever a scroll library does to events. It
  // costs one getBoundingClientRect per pending element per frame and stops
  // itself the moment the last one is revealed, so the steady-state cost is
  // zero.
  const pending = new Set(document.querySelectorAll(".reveal"));
  let queued = false;

  const sweep = () => {
    queued = false;
    const limit = window.innerHeight * 0.92;
    for (const el of [...pending]) {
      if (el.getBoundingClientRect().top < limit) {
        el.classList.add("revealed");
        pending.delete(el);
        decorate(el);
      }
    }
    if (pending.size && document.visibilityState === "visible") {
      queued = true;
      requestAnimationFrame(sweep);
    }
  };

  const kick = () => {
    if (!queued && pending.size) {
      queued = true;
      requestAnimationFrame(sweep);
    }
  };

  // rAF is suspended entirely while a tab is hidden — measured on this page:
  // zero frames in 1200 ms with visibilityState "hidden". Left on rAF alone,
  // a viewer who switches away mid-scroll and comes back finds the sections
  // they scrolled past still invisible, with nothing scheduled to fix it.
  // These three re-arm the loop on any signal that the viewport may have
  // moved; each is idempotent and they all stop once `pending` empties.
  document.addEventListener("visibilitychange", kick);
  window.addEventListener("scroll", kick, { passive: true });
  window.addEventListener("resize", kick, { passive: true });

  sweep();
}

// Per-section GSAP flourishes, fired by the same observer that reveals the
// section. Everything here is decoration: if gsap is absent the section is
// still fully readable, which is why each block guards rather than assumes.
function decorate(el) {
  if (!gsap) return;

  const accent = el.querySelector(".q-card-accent");
  if (accent) gsap.fromTo(accent, { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: "expo.out" });

  const svg = el.querySelector(".q-art svg");
  if (!svg) return;

  svg.querySelectorAll("[data-draw]").forEach((s) => {
    const len = typeof s.getTotalLength === "function" ? s.getTotalLength() : 0;
    if (!len) return;
    gsap.fromTo(
      s,
      { strokeDasharray: len, strokeDashoffset: len },
      { strokeDashoffset: 0, duration: 0.9, ease: "power2.inOut" }
    );
  });

  const dots = svg.querySelectorAll("[data-pop]");
  if (dots.length) {
    gsap.from(dots, {
      scale: 0,
      transformOrigin: "center",
      duration: 0.5,
      ease: "back.out(2)",
      stagger: 0.08,
      delay: 0.3,
    });
  }
}

// ------------------------------------------------------- data micro-motion

// Feed rows: only the genuinely new ones animate. Animating the whole
// table on every poll is what made the old console feel like it was
// thrashing, and it destroys the selected-row highlight mid-read.
export function animateFeedRows(rows) {
  if (!rows || !rows.length) return;
  if (anime && !reduced) {
    anime({
      targets: rows,
      translateY: [-8, 0],
      opacity: [0, 1],
      duration: 420,
      delay: anime.stagger(45),
      easing: "easeOutExpo",
    });
  } else if (gsap && !reduced) {
    gsap.from(rows, { y: -8, opacity: 0, duration: 0.42, stagger: 0.045, ease: "expo.out" });
  }
}

// Meter slots fill from the left, in order, so the sequence reads as
// "this was spent, then this" rather than "all of it, at once".
export function animateMeterSlots(slots) {
  if (!slots || !slots.length) return;
  if (anime && !reduced) {
    anime({
      targets: slots,
      scaleX: [0, 1],
      duration: 520,
      delay: anime.stagger(70),
      easing: "easeOutExpo",
    });
  } else if (gsap && !reduced) {
    gsap.from(slots, { scaleX: 0, duration: 0.52, stagger: 0.07, ease: "expo.out" });
  }
}

export function animateChips(chips) {
  if (!chips || !chips.length) return;
  if (anime && !reduced) {
    anime({
      targets: chips,
      scale: [0.94, 1],
      opacity: [0, 1],
      duration: 360,
      delay: anime.stagger(38),
      easing: "easeOutExpo",
    });
  } else if (gsap && !reduced) {
    gsap.from(chips, { scale: 0.94, opacity: 0, duration: 0.36, stagger: 0.038, ease: "expo.out" });
  }
}

// The counter is the one number allowed to tick, because it is a running
// total whose *movement* is the point. It is rounded every frame so it is
// never mid-fraction on screen.
export function animateCount(el, to) {
  if (!el) return;
  const from = Number(el.dataset.value || 0);
  el.dataset.value = String(to);
  if (from === to || reduced || !anime) {
    el.textContent = String(to);
    return;
  }
  const state = { n: from };
  anime({
    targets: state,
    n: to,
    duration: 600,
    easing: "easeOutExpo",
    update() {
      el.textContent = String(Math.round(state.n));
    },
  });
}

// The budget trip — the one sequenced, once-only moment in the product.
// Four stages, deliberately not simultaneous, so a viewer reads causation
// rather than a simple change of state.
export function playTrip(card) {
  if (!card || reduced || !gsap) {
    if (card) card.classList.add("tripped");
    return;
  }
  if (card.dataset.tripped === "1") return;
  card.dataset.tripped = "1";

  const slots = card.querySelectorAll(".slot-filled, .slot-spent");
  const over = card.querySelector(".slot-over");

  const tl = gsap.timeline();
  if (over) {
    tl.fromTo(
      over,
      { x: 24, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.2, ease: "power4.in" }
    ).to(over, { x: -6, duration: 0.08 }).to(over, { x: 0, duration: 0.1 });
  }
  if (slots.length) {
    tl.fromTo(
      slots,
      { filter: "brightness(1)" },
      { filter: "brightness(0.72)", duration: 0.18, stagger: 0.07 },
      over ? "-=0.1" : 0
    );
  }
  tl.call(() => card.classList.add("tripped"));
  return tl;
}

// ScrollTrigger.refresh() re-measures every trigger on the page, which is
// far too expensive to run on each poll tick. The feed re-renders whenever
// new rows arrive, so this coalesces those bursts into one measurement.
let refreshTimer = null;
export function refreshScroll() {
  if (!ScrollTrigger) return;
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => ScrollTrigger.refresh(), 400);
}
