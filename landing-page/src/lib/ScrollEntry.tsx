/**
 * ScrollEntry — shared scroll-driven entrance component.
 *
 * Every animated landing-page element uses this.
 * Each instance tracks its OWN element via useScroll({ target: ref })
 * so there is zero shared progress state — no lag, no drift.
 *
 * Timing contract:
 *   start  'start 80%'  → element top reaches 80% down the viewport.
 *                          At this point the element is clearly on screen,
 *                          in the lower reading zone. Animation begins here.
 *   end    entryEnd      → defaults to 'start 30%'. Element top is 30% down
 *                          — well into the reading zone. Animation complete.
 *   arc    50% viewport  → ~450px of scroll on a 900px screen. Smooth,
 *                          deliberate, finishes before the eye has left.
 *
 * y + opacity share the same [0, 0.85] input range so they complete
 * together — no two-phase feel where y snaps before opacity settles.
 *
 * Apple §3: animation IS the scroll — interruptible at any frame.
 * Apple §11: only opacity + transform (compositor-friendly).
 */
import { useRef, type ReactNode } from 'react';
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion';

interface ScrollEntryProps {
  children: ReactNode;
  /** CSS class name(s) applied to the motion.div wrapper. */
  className?: string;
  /** Extra inline styles (layout/spacing — animations are owned internally). */
  style?: React.CSSProperties;
  /** aria-label for accessibility — passed through to the motion.div. */
  'aria-label'?: string;
  /** role attribute passed through to the motion.div. */
  role?: string;
  /** id attribute passed through to the motion.div. */
  id?: string;
  /**
   * Where the animation finishes (top of element at X% down viewport).
   * Default 'start 30%' — element fully revealed when well into reading zone.
   * Pass 'start 20%' for larger/taller elements that need to settle earlier.
   */
  entryEnd?: string;
}

export function ScrollEntry({
  children,
  className,
  style,
  entryEnd = 'start 30%',
  'aria-label': ariaLabel,
  role,
  id,
}: ScrollEntryProps) {
  const ref     = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  // Each instance tracks its own element — no section-level progress sharing.
  const { scrollYProgress } = useScroll({
    target: ref,
    // 'start 80%': animation begins when element top is 80% down viewport.
    // Element is clearly on screen, in the lower reading zone.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start 80%', entryEnd] as any,
  });

  // Both opacity and y share the same [0, 0.85] input window
  // so they settle simultaneously — no two-phase mechanical feel.
  const opacity = useTransform(scrollYProgress, [0, 0.85], [0, 1]);
  const y       = useTransform(scrollYProgress, [0, 0.85], [18, 0]);

  return (
    <motion.div
      ref={ref}
      className={className}
      aria-label={ariaLabel}
      role={role}
      id={id}
      style={{ opacity, ...(reduced ? {} : { y }), ...style }}
    >
      {children}
    </motion.div>
  );
}
