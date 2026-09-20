import { useEffect, useRef } from 'react';
import { sharedCursorX, sharedCursorY } from '../../lib/cursorState';
import { color } from '../../lib/design';
import './CursorDots.css';

/* Decompose the accent primary hex (#DEA193) into its RGB components so the
   canvas can build dynamic rgba() strings that stay in sync with the token. */
const [_ACCENT_R, _ACCENT_G, _ACCENT_B] = ((): [number, number, number] => {
  const hex = color.accent.primary.replace('#', '');
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
})();

interface CursorDotsProps {
  gap?: number;
  radius?: number;
  proximityRadius?: number;
}

export function CursorDots({
  gap = 14,
  radius = 1.2,
  proximityRadius = 240,
}: CursorDotsProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const handleResize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const startTime = performance.now();

    const render = (time: number) => {
      const t = (time - startTime) * 0.001;
      
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;

      // Get exact, spring-smoothed coordinates from CustomCursor
      // Add window.scrollY because canvas is now position: absolute in the document
      const mouseX = sharedCursorX.get();
      const mouseY = sharedCursorY.get() + window.scrollY;

      ctx.clearRect(0, 0, width, height);

      if (mouseX > -1000 && mouseY > -1000) {
        const minCol = Math.max(0, Math.floor((mouseX - proximityRadius) / gap));
        const maxCol = Math.min(
          Math.ceil(width / gap),
          Math.ceil((mouseX + proximityRadius) / gap)
        );
        const minRow = Math.max(0, Math.floor((mouseY - proximityRadius) / gap));
        const maxRow = Math.min(
          Math.ceil(height / gap),
          Math.ceil((mouseY + proximityRadius) / gap)
        );

        for (let col = minCol; col <= maxCol; col++) {
          for (let row = minRow; row <= maxRow; row++) {
            const dotX = col * gap;
            const dotY = row * gap;

            const dx = dotX - mouseX;
            const dy = dotY - mouseY;
            const dist = Math.hypot(dx, dy);

            if (dist < proximityRadius) {
              // Deterministic pseudo-random seed per dot
              const seed = (col * 374761393 + row * 668265263) ^ (col * row);
              
              // Slightly faster speeds (0.4 to 1.2)
              const randSpeed = 0.4 + ((seed & 0xff) / 255) * 0.8;
              const randPhase = (((seed >> 8) & 0xff) / 255) * Math.PI * 2;
              
              // Smooth continuous wave from 0 to 1
              const wave = 0.5 + 0.5 * Math.sin(t * randSpeed + randPhase);
              
              // Gentle curve (power of 2)
              const pulse = Math.pow(wave, 2);

              // Proximity falloff
              const normDist = dist / proximityRadius;
              const proximity = Math.pow(1 - normDist, 2.2);
              
              // Wider brightness gap: drops to 0.05 and peaks at 0.35
              const alpha = proximity * (0.05 + 0.30 * pulse);

              if (alpha > 0.01) {
                // More noticeable but still smooth radius change
                const currentRadius = radius * (0.7 + 0.4 * pulse + 0.1 * proximity);

                ctx.fillStyle = `rgba(${_ACCENT_R}, ${_ACCENT_G}, ${_ACCENT_B}, ${alpha})`;
                ctx.beginPath();
                ctx.arc(dotX, dotY, currentRadius, 0, Math.PI * 2);
                ctx.fill();
              }
            }
          }
        }
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, [gap, radius, proximityRadius]);

  return <canvas ref={canvasRef} className="cursor-dots-canvas" aria-hidden="true" />;
}
