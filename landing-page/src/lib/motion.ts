/**
 * motion.ts — Complete motion design language.
 *
 * Three tiers of constants:
 *
 * 1. SPRING PRESETS — Named physics configs for Framer Motion.
 *    Rule (Apple §4): Use the right spring for the right intent.
 *
 * 2. DURATION / EASE — For CSS transitions and timed animations.
 *    Maps to --duration-* and --ease-* CSS tokens.
 *
 * 3. VARIANT FACTORIES — Reusable entrance/exit animation objects.
 *    Use these to build consistent stagger sequences across sections.
 */

import type { Transition, Variants } from 'framer-motion';
import { duration } from './design';

/* ═══════════════════════════════════════════════════════════════
   1. SPRING PRESETS
   ═══════════════════════════════════════════════════════════════ */

/**
 * uiSpring — Critically damped. Zero overshoot.
 * Use for: entrance animations, reveals, panels, drawers.
 * Do NOT use for gesture-driven tracking.
 */
export const uiSpring: Transition = {
  type:      'spring',
  stiffness: 300,
  damping:   35,
  mass:      1,
};

/**
 * parallaxSpring — Under-damped, responsive, interruptible.
 * Use for: cursor tracking, tilt/parallax, gesture-driven elements.
 * Must feel instantaneously responsive at any cursor speed.
 */
export const parallaxSpring = {
  stiffness: 60,
  damping:   20,
};

/**
 * momentumSpring — Slight overshoot bounce.
 * Use ONLY when the element carries an actual flick/throw gesture.
 * The overshoot IS the velocity handoff.
 */
export const momentumSpring: Transition = {
  type:      'spring',
  stiffness: 280,
  damping:   22,
  mass:      1,
};

/**
 * drawSpring — Slow, deliberate settle.
 * Use for: divider line draws, SVG path animations, ink-on-paper.
 */
export const drawSpring: Transition = {
  type:      'spring',
  stiffness: 120,
  damping:   24,
};

/**
 * spotlightSpring — Lightweight cursor follow for internal effects.
 * Use for: mouse spotlight on cards, subtle hover tracking.
 */
export const spotlightSpring = {
  stiffness: 200,
  damping:   20,
  mass:      0.5,
};

/* ═══════════════════════════════════════════════════════════════
   2. DURATION + EASE
   ═══════════════════════════════════════════════════════════════ */

export const DURATION = duration; // re-export from design.ts

export const EASE = {
  apple:    [0.2,  0,    0,    1   ] as const,
  out:      [0.16, 1,    0.3,  1   ] as const,
  inOut:    [0.65, 0,    0.35, 1   ] as const,
} as const;

/* ═══════════════════════════════════════════════════════════════
   3. VARIANT FACTORIES
   ═══════════════════════════════════════════════════════════════ */

/**
 * reveal(delay) — Standard entrance for any text/content element.
 * Combines spring settle with blur-fade for a premium feel.
 */
export const reveal = (delay = 0, fromY = 8): Variants => ({
  hidden: {
    opacity: 0,
    y:       fromY,
    filter:  'blur(4px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    filter:  'blur(0px)',
    transition: { ...uiSpring, delay },
  },
});

/**
 * revealReduced(delay) — Reduced-motion version: cross-fade only.
 * No transform, no blur — Apple §14 compliance.
 */
export const revealReduced = (delay = 0): Variants => ({
  hidden:  { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: duration.slow, delay },
  },
});

/**
 * cardEntrance — Full entrance for floating card elements.
 * More scale + blur than reveal() for elevated components.
 */
export const cardEntrance: Variants = {
  hidden: {
    opacity: 0,
    y:       18,
    scale:   0.97,
    filter:  'blur(6px)',
  },
  visible: {
    opacity: 1,
    y:       0,
    scale:   1,
    filter:  'blur(0px)',
    transition: { ...uiSpring, delay: 0.1 },
  },
  exit: {
    opacity: 0,
    y:       12,
    scale:   0.94,
    filter:  'blur(4px)',
    transition: { ...momentumSpring, duration: duration.slow },
  },
};

/**
 * staggerContainer — Wrapper for staggered child animations.
 */
export const staggerContainer = (stagger = 0.08): Variants => ({
  hidden:  {},
  visible: { transition: { staggerChildren: stagger } },
});
