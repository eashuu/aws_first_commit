import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence, useSpring, useTransform, useMotionValue } from 'framer-motion';
import { uiSpring, momentumSpring } from '../../lib/spring';
import { spotlightSpring } from '../../lib/motion';
import { alpha, durationMs } from '../../lib/design';
import './AdviceCard.css';

/* ─── Animation Variants ──────────────────────────────────────── */

const cardEntrance = {
  hidden: {
    opacity: 0,
    y: 18,
    scale: 0.97,
    filter: 'blur(6px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: 'blur(0px)',
    transition: { ...uiSpring, delay: 0.1 },
  },
  exit: {
    opacity: 0,
    y: 12,
    scale: 0.94,
    filter: 'blur(4px)',
    transition: { ...momentumSpring, duration: 0.28 },
  },
};

const childReveal = (delay: number) => ({
  hidden: { opacity: 0, y: 8, filter: 'blur(4px)' },
  visible: {
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { ...uiSpring, delay },
  },
});

const expandVariants = {
  collapsed: { height: 0, opacity: 0 },
  expanded: {
    height: 'auto',
    opacity: 1,
    transition: { ...uiSpring, opacity: { duration: 0.22 } },
  },
};

/* ─── Sparkle Icon ────────────────────────────────────────────── */
function SparkleIcon({ isHovered }: { isHovered: boolean }) {
  return (
    <motion.svg
      className="advice-icon"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      animate={isHovered ? { rotate: 18, scale: 1.15 } : { rotate: 0, scale: 1 }}
      transition={{ ...uiSpring }}
      aria-hidden="true"
    >
      {/* Central 4-point star */}
      <motion.path
        d="M10 2 L10.8 8.5 L17 10 L10.8 11.5 L10 18 L9.2 11.5 L3 10 L9.2 8.5 Z"
        fill="currentColor"
        animate={isHovered ? { opacity: 1 } : { opacity: 0.85 }}
        transition={{ duration: 0.22 }}
      />
      {/* Small accent stars */}
      <motion.circle
        cx="16" cy="4" r="1"
        fill="currentColor"
        animate={isHovered ? { r: 1.4, opacity: 1 } : { r: 1, opacity: 0.6 }}
        transition={{ ...uiSpring }}
      />
      <motion.circle
        cx="4" cy="16" r="0.8"
        fill="currentColor"
        animate={isHovered ? { r: 1.1, opacity: 1 } : { r: 0.8, opacity: 0.5 }}
        transition={{ ...uiSpring }}
      />
    </motion.svg>
  );
}

/* ─── Props ───────────────────────────────────────────────────── */
interface AdviceCardProps {
  label?: string;
  title: string;
  body: string;
  detail?: string;
  onDismiss?: () => void;
  className?: string;
}

/* ─── Component ───────────────────────────────────────────────── */
export function AdviceCard({
  label = 'Pro Tip',
  title,
  body,
  detail,
  onDismiss,
  className = '',
}: AdviceCardProps) {
  const [isVisible, setIsVisible]   = useState(true);
  const [isHovered, setIsHovered]   = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);

  /* Mouse-spotlight motion values */
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);

  const smoothX = useSpring(mouseX, spotlightSpring);
  const smoothY = useSpring(mouseY, spotlightSpring);

  /* Convert to CSS-ready percentage strings */
  const gradientX = useTransform(smoothX, [0, 1], ['0%', '100%']);
  const gradientY = useTransform(smoothY, [0, 1], ['0%', '100%']);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    mouseX.set((e.clientX - rect.left) / rect.width);
    mouseY.set((e.clientY - rect.top)  / rect.height);
  }, [mouseX, mouseY]);

  const handleMouseLeave = useCallback(() => {
    mouseX.set(0.5);
    mouseY.set(0.5);
    setIsHovered(false);
  }, [mouseX, mouseY]);

  const handleDismiss = useCallback(() => {
    setIsVisible(false);
    setTimeout(() => onDismiss?.(), durationMs.slow + durationMs.snap);
  }, [onDismiss]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          ref={cardRef}
          className={`advice-card ${className}`}
          variants={cardEntrance}
          initial="hidden"
          animate="visible"
          exit="exit"
          onMouseMove={handleMouseMove}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={handleMouseLeave}
          whileTap={{ scale: 0.985 }}
          style={{ position: 'relative' }}
          role="note"
          aria-label={`Advice: ${title}`}
        >
          {/* ── Mouse spotlight layer ────────────────────────── */}
          <motion.div
            className="advice-card__spotlight"
            style={{
              background: `radial-gradient(var(--card-spotlight-radius) circle at ${gradientX} ${gradientY},
                ${alpha.rose.a10} 0%,
                ${alpha.rose.a04} 40%,
                transparent 70%)`,
            }}
            aria-hidden="true"
          />

          {/* ── Header row ──────────────────────────────────── */}
          <motion.div className="advice-card__header" variants={childReveal(0.15)}>
            <div className="advice-card__label-row">
              <SparkleIcon isHovered={isHovered} />
              <span className="advice-card__label">{label}</span>
            </div>

            {/* Dismiss button */}
            <motion.button
              className="advice-card__dismiss"
              onClick={handleDismiss}
              whileHover={{ scale: 1.12, opacity: 1 }}
              whileTap={{ scale: 0.9 }}
              transition={{ ...uiSpring }}
              aria-label="Dismiss advice"
            >
              <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </motion.button>
          </motion.div>

          {/* ── Title ───────────────────────────────────────── */}
          <motion.h4 className="advice-card__title" variants={childReveal(0.22)}>
            {title}
          </motion.h4>

          {/* ── Body ────────────────────────────────────────── */}
          <motion.p className="advice-card__body" variants={childReveal(0.28)}>
            {body}
          </motion.p>

          {/* ── Expandable detail ────────────────────────────── */}
          {detail && (
            <>
              <motion.div
                className="advice-card__detail"
                variants={expandVariants}
                initial="collapsed"
                animate={isExpanded ? 'expanded' : 'collapsed'}
              >
                <p className="advice-card__detail-text">{detail}</p>
              </motion.div>

              <motion.button
                className="advice-card__expand-btn"
                onClick={() => setIsExpanded((p) => !p)}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.97 }}
                transition={{ ...uiSpring }}
                variants={childReveal(0.32)}
                aria-expanded={isExpanded}
              >
                <motion.span
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  transition={{ ...uiSpring }}
                  className="advice-card__expand-chevron"
                >
                  ↓
                </motion.span>
                {isExpanded ? 'Show less' : 'Learn more'}
              </motion.button>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
