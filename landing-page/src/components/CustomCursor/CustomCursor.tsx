import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { sharedCursorX, sharedCursorY } from '../../lib/cursorState';
import './CustomCursor.css';

export function CustomCursor() {
  const [isHovering, setIsHovering] = useState(false);
  const [isClicking, setIsClicking] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // Exact coordinates
  const cursorX = useMotionValue(-100);
  const cursorY = useMotionValue(-100);

  // Spring physical physics for the smooth trailing effect
  const springConfig = { damping: 25, stiffness: 300, mass: 0.5 };
  const smoothX = useSpring(cursorX, springConfig);
  const smoothY = useSpring(cursorY, springConfig);

  useEffect(() => {
    // Sync the smoothed spring position to the global store for CursorDots to follow
    const unsubX = smoothX.on('change', (v) => sharedCursorX.set(v));
    const unsubY = smoothY.on('change', (v) => sharedCursorY.set(v));
    return () => {
      unsubX();
      unsubY();
    };
  }, [smoothX, smoothY]);

  useEffect(() => {
    // Hide the native cursor globally when this component mounts
    document.body.style.cursor = 'none';

    const moveCursor = (e: MouseEvent) => {
      // Offset slightly to align the smaller SVG arrow tip exactly with the physical mouse location
      cursorX.set(e.clientX - 1);
      cursorY.set(e.clientY - 1);
      if (!isVisible) setIsVisible(true);
    };

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Check if hovering over clickable elements
      const isClickable = target.closest('a, button, [role="button"]');
      if (isClickable) {
        setIsHovering(true);
        // Ensure native cursor remains hidden over interactive elements
        document.body.style.cursor = 'none';
      } else {
        setIsHovering(false);
      }
    };

    const handleMouseDown = () => setIsClicking(true);
    const handleMouseUp = () => setIsClicking(false);
    const handleMouseLeave = () => setIsVisible(false);

    window.addEventListener('mousemove', moveCursor);
    window.addEventListener('mouseover', handleMouseOver);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    document.body.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      document.body.style.cursor = 'auto';
      window.removeEventListener('mousemove', moveCursor);
      window.removeEventListener('mouseover', handleMouseOver);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [cursorX, cursorY, isVisible]);

  // Don't render on mobile touch devices
  const isTouchDevice = typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches;
  if (isTouchDevice) return null;

  return (
    <motion.div
      className="custom-cursor"
      style={{
        x: smoothX,
        y: smoothY,
        opacity: isVisible ? 1 : 0,
        transformOrigin: '1px 1px',
      }}
      animate={{
        scale: isClicking ? 0.9 : isHovering ? 1.15 : 1,
        rotate: isClicking ? -5 : 0
      }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
    >
      <svg width="18" height="20" viewBox="0 0 28 30" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ filter: 'drop-shadow(0px 2px 6px rgba(0,0,0,0.4))' }}>
        <path 
          d="M3.75389 2.19504C3.21046 1.70599 2.375 2.09118 2.375 2.8256V21.1744C2.375 21.9088 3.21046 22.294 3.75389 21.805L10.021 16.1643C10.1558 16.043 10.3344 15.9754 10.5193 15.9754H18.7997C19.5694 15.9754 19.9231 15.0163 19.3444 14.4954L3.75389 2.19504Z" 
          fill="url(#cursor-gradient)" 
          stroke="rgba(255,255,255,0.8)" 
          strokeWidth="1.25" 
          strokeLinejoin="round"
        />
        <defs>
          <linearGradient id="cursor-gradient" x1="2.375" y1="2" x2="19.5" y2="22" gradientUnits="userSpaceOnUse">
            <stop stopColor="#F5F5F7" />
            <stop offset="1" stopColor="#A6766C" />
          </linearGradient>
        </defs>
      </svg>
    </motion.div>
  );
}
