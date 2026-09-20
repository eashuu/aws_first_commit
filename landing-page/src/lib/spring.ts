/**
 * spring.ts — Named physics constants.
 *
 * Rule (Apple §4): Two categories only.
 *
 * uiSpring      — Critically damped (no overshoot). For elements the user
 *                 did NOT throw/flick: entrance animations, reveals, panels.
 *                 Damping ≥ 1.0 equivalent.
 *
 * parallaxSpring — Under-damped, responsive. For cursor/gesture-driven motion
 *                  that must feel lightweight and interruptible at any instant.
 *
 * momentumSpring — Slight bounce. Only for elements that carry a flick/throw
 *                  gesture — the overshoot IS the velocity handoff (Apple §5).
 */

import type { Transition } from 'framer-motion';

/** Critically damped — graceful settle, zero overshoot. */
export const uiSpring: Transition = {
  type:      'spring',
  stiffness: 300,
  damping:   35,
  mass:      1,
};

/** Responsive & interruptible — cursor/gesture tracking. */
export const parallaxSpring = {
  stiffness: 60,
  damping:   20,
};

/** Momentum-only — use ONLY after a measured flick/throw gesture. */
export const momentumSpring: Transition = {
  type:      'spring',
  stiffness: 280,
  damping:   22,
  mass:      1,
};

/** Divider draw — slower, deliberate ink-on-paper feel. */
export const drawSpring: Transition = {
  type:      'spring',
  stiffness: 120,
  damping:   24,
};
