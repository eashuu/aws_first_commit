/**
 * spring.ts — Legacy re-export. Import from motion.ts for new code.
 *
 * All spring presets have moved to src/lib/motion.ts as part of the
 * design system standardisation. This file remains so existing imports
 * continue to resolve without breaking changes.
 */
export {
  uiSpring,
  parallaxSpring,
  momentumSpring,
  drawSpring,
  spotlightSpring,
} from './motion';
