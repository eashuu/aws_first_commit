// motion.js — data micro-motion for the operator console.
//
// SCOPE NOTE. This file used to carry the marketing motion layer too —
// Lenis smooth scroll, the hero split, scroll reveals, a Lottie mount —
// back when index.html was both the landing page and the console. It is
// not any more: index.html is the product site and site.js owns its
// motion, while console.html is the application and imports only what is
// below. Everything that moved has been deleted rather than left in place,
// because a reveal helper reachable from the console is a live trap: the
// `motion-ready` class it sets hides every `.reveal` element, and on a
// surface with no reveal loop running they would simply never come back.
//
// What is left is the four things an audit console legitimately animates,
// plus one sequenced moment:
//
//   feed rows      - only genuinely new ones, so the table does not thrash
//   meter slots    - fill left to right, so spend reads as a sequence
//   chips          - the decision detail pane
//   counters       - the one number whose movement is the point
//   playTrip()     - the budget trip, once per subject
//
// anime.js is loaded from a CDN by console.html and is therefore allowed to
// be absent: a venue wifi hiccup must degrade the console to a plain,
// fully working one, never a broken one. GSAP is the fallback where it is
// present; where neither is, the DOM has already been updated correctly by
// the render functions and the animation was only ever a nicety.

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const gsap = window.gsap || null;
const anime = window.anime || null;

// Feed rows: only the genuinely new ones animate. Animating the whole table
// on every poll is what made the old console feel like it was thrashing, and
// it destroys the selected-row highlight mid-read.
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
    tl.fromTo(over, { x: 24, opacity: 0 }, { x: 0, opacity: 1, duration: 0.2, ease: "power4.in" })
      .to(over, { x: -6, duration: 0.08 })
      .to(over, { x: 0, duration: 0.1 });
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
