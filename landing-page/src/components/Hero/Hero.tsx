import React, { useRef } from 'react';
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
} from 'framer-motion';
import { Button } from '../Button/Button';
import { CursorDots } from '../CursorDots/CursorDots';
import { uiSpring, parallaxSpring, drawSpring } from '../../lib/motion';
import './Hero.css';

/* ─── Entrance Variants ───────────────────────────────────────── */
/* Apple §4: uiSpring (critically damped) for entrance — no overshoot. */

const heroSequence = {
  hidden:  {},
  visible: { transition: { staggerChildren: 0 } },
};

const logoReveal = {
  hidden:  { opacity: 0, scale: 0.88, filter: 'blur(14px)' },
  visible: {
    opacity: 1, scale: 1, filter: 'blur(0px)',
    transition: { ...uiSpring, delay: 0.1 },
  },
};

const reveal = (delay: number, fromY = 0) => ({
  hidden:  { opacity: 0, y: fromY, filter: 'blur(6px)' },
  visible: {
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { ...uiSpring, delay },
  },
});

const dividerDraw = {
  hidden:  { scaleY: 0, opacity: 0 },
  visible: {
    scaleY: 1, opacity: 0.65,
    transition: { ...drawSpring, delay: 0.55 },
  },
};

/* ─── Reduced Motion Variants ─────────────────────────────────── */
/* Apple §14: cross-fade only — no transform, no blur.            */
const reducedReveal = (delay: number) => ({
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.3, delay } },
});

/* ─── Component ───────────────────────────────────────────────── */
export function Hero() {
  const sectionRef    = useRef<HTMLElement>(null);
  const prefersReduced = useReducedMotion();

  /* Cursor parallax — parallaxSpring (interruptible, responsive) */
  const rawX   = useMotionValue(0);
  const rawY   = useMotionValue(0);
  const springX = useSpring(rawX, parallaxSpring);
  const springY = useSpring(rawY, parallaxSpring);

  const rotateX = useTransform(springY, [-0.5, 0.5], ['8deg', '-8deg']);
  const rotateY = useTransform(springX, [-0.5, 0.5], ['-8deg', '8deg']);

  function handleMouseMove(e: React.MouseEvent<HTMLElement>) {
    if (prefersReduced) return; /* Respect reduced motion — no parallax */
    const rect = sectionRef.current?.getBoundingClientRect();
    if (!rect) return;
    rawX.set((e.clientX - rect.left)  / rect.width  - 0.5);
    rawY.set((e.clientY - rect.top)   / rect.height - 0.5);
  }

  function handleMouseLeave() {
    rawX.set(0);
    rawY.set(0);
  }

  /* Select variant set based on reduced-motion preference */
  const r = prefersReduced ? reducedReveal : reveal;

  return (
    <motion.section
      ref={sectionRef}
      className="hero-section"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      initial="hidden"
      animate="visible"
      variants={heroSequence}
    >
      {/* Grain texture — tactile surface, not flat digital black */}
      <div className="grain-overlay" aria-hidden="true" />
      
      {/* Interactive cursor proximity dots, scoped only to the hero */}
      <CursorDots />

      <div className="hero-split">

        {/* ── LEFT: Logo + Logotype ──────────────────────────── */}
        <div className="hero-split__left">
          <div className="hero-logo-stack">

            {/* 3-D parallax wrapper — Apple §3: interruptible at any instant */}
            <motion.div
              style={{
                position: 'relative',
                rotateX: prefersReduced ? 0 : rotateX,
                rotateY: prefersReduced ? 0 : rotateY,
                perspective: 800,
                transformStyle: 'preserve-3d',
                willChange: 'transform',
              }}
            >
              {/* Entrance animation wrapper — separate from filter-bearing <img> */}
              {/* (Framer Motion overwrites the filter property during animation, */}
              {/* so we isolate it here to protect the drop-shadow on the img.)   */}
              <motion.div variants={logoReveal}>
                <img
                  src="/logo.png"
                  alt="Xerath — agentic privacy infrastructure"
                  width={240}
                  height={240}
                  style={{
                    objectFit: 'contain',
                    mixBlendMode: 'screen',
                    display: 'block',
                    filter:
                      'drop-shadow(0 0 16px rgba(255,255,255,0.38))' +
                      ' drop-shadow(0 0 64px rgba(255,255,255,0.12))' +
                      ' drop-shadow(0 0 24px rgba(222,161,147,0.18))',
                  }}
                />
              </motion.div>
            </motion.div>

            {/* Logotype */}
            <motion.h1
              className="hero-mark"
              variants={r(0.38)}
              style={{ overflow: 'hidden' }}
            >
              Xerath
            </motion.h1>

          </div>
        </div>

        {/* ── CENTER: Rose-Gold Divider — draws top → bottom ──── */}
        <motion.div
          variants={prefersReduced ? reducedReveal(0.4) : dividerDraw}
          className="hero-divider"
          style={{ transformOrigin: 'top center' }}
          aria-hidden="true"
        />

        {/* ── RIGHT: Description + CTAs ──────────────────────── */}
        <div className="hero-split__right">
          <div className="hero-content">

            {/* Hook — brighter weight, primary color */}
            <motion.p variants={r(0.72)} className="hero-hook">
              Your AI agent learns one field at a time.<br />
              We count the total.
            </motion.p>

            {/* Explanation — muted, supporting detail */}
            <motion.p variants={r(0.84)} className="hero-desc">
              Xerath provides the infrastructure for agentic privacy,
              enforcing data constraints dynamically across every session.
            </motion.p>

            {/* CTAs */}
            <motion.div variants={r(1.0)} className="hero-actions">
              <Button variant="primary">Deploy Infrastructure</Button>
              <Button variant="secondary">Read the Architecture</Button>
            </motion.div>

          </div>
        </div>

      </div>
    </motion.section>
  );
}
