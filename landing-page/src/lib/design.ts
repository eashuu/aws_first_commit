/**
 * design.ts — Typed JS mirror of the CSS token system.
 *
 * Use this for values that CSS variables cannot reach:
 *   - HTML5 Canvas (CursorDots)
 *   - Framer Motion inline styles
 *   - SVG fill/stroke props
 *   - Dynamic style calculations
 *
 * RULE: If a value exists here, it must match tokens.css exactly.
 * Single source of truth: tokens.css. This file derives from it.
 */

/* ── Colors ────────────────────────────────────────────────────── */
export const color = {
  surface: {
    base:    '#020203',
    raised:  '#0A0A0C',
    overlay: '#101012',
  },
  text: {
    primary:   '#F5F5F7',
    secondary: '#A1A1A6',
    tertiary:  '#6E6E73',
  },
  accent: {
    primary: '#DEA193',
    muted:   '#A6766C',
  },
  status: {
    success: '#6B7B65',
    warn:    '#B3997A',
    danger:  '#8E5A5A',
  },
  syntax: {
    string:  '#8CA9C5',
  },
} as const;

/* ── Alpha Stops ───────────────────────────────────────────────── */
/** Pre-computed rgba values matching alpha.css */
export const alpha = {
  rose: {
    a04: 'rgba(222, 161, 147, 0.04)',
    a08: 'rgba(222, 161, 147, 0.08)',
    a10: 'rgba(222, 161, 147, 0.10)',
    a12: 'rgba(222, 161, 147, 0.12)',
    a15: 'rgba(222, 161, 147, 0.15)',
    a18: 'rgba(222, 161, 147, 0.18)',
    a25: 'rgba(222, 161, 147, 0.25)',
    a40: 'rgba(222, 161, 147, 0.40)',
    a55: 'rgba(222, 161, 147, 0.55)',
    a80: 'rgba(222, 161, 147, 0.80)',
  },
  white: {
    a05: 'rgba(255, 255, 255, 0.05)',
    a08: 'rgba(255, 255, 255, 0.08)',
    a10: 'rgba(255, 255, 255, 0.10)',
    a12: 'rgba(255, 255, 255, 0.12)',
  },
  black: {
    a40: 'rgba(0, 0, 0, 0.40)',
    a55: 'rgba(0, 0, 0, 0.55)',
  },
  green: {
    a12: 'rgba(107, 123, 101, 0.12)',
    a25: 'rgba(107, 123, 101, 0.25)',
  },
  red: {
    a12: 'rgba(142, 90, 90, 0.12)',
    a25: 'rgba(142, 90, 90, 0.25)',
    a40: 'rgba(142, 90, 90, 0.40)',
  },
} as const;

/* ── Spacing ───────────────────────────────────────────────────── */
/** Pixel values matching the --space-* CSS scale */
export const space = {
  '0.5': 2,
  1:  4,
  2:  8,
  3: 12,
  4: 16,
  5: 24,
  6: 32,
  7: 48,
  8: 64,
  9: 80,
  10: 120,
} as const;

/* ── Z-Index ───────────────────────────────────────────────────── */
export const z = {
  ground:  0,
  base:    1,
  raised:  2,
  overlay: 10,
  modal:   100,
  cursor:  9999,
} as const;

/* ── Breakpoints ───────────────────────────────────────────────── */
export const bp = {
  sm:  600,
  md:  768,
  lg: 1024,
  xl: 1280,
} as const;

/* ── Duration ──────────────────────────────────────────────────── */
/** In seconds (for Framer Motion) */
export const duration = {
  snap:   0.08,
  fast:   0.15,
  base:   0.20,
  slow:   0.30,
  xslow:  0.50,
} as const;

/** In milliseconds (for setTimeout / CSS transitions) */
export const durationMs = {
  snap:   80,
  fast:  150,
  base:  200,
  slow:  300,
  xslow: 500,
} as const;
