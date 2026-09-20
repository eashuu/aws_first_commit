/**
 * Section4 — Architecture topology.
 *
 * Vanilla SVG. Every node position, edge path, and animation delay
 * is calculated by hand for pixel-perfect orthogonal layout.
 *
 * Animation sequence (triggered once when SVG enters viewport):
 *  t=0s        nodes fade in (empty outlines first)
 *  t=0.05–0.8s edges draw on (stroke-dashoffset, staggered)
 *  t=0.5–1.0s  edge labels + node text settle to full opacity
 */
import { useEffect, useRef, useState } from 'react';
import { ScrollEntry } from '../../lib/ScrollEntry';
import './Section4.css';

/* ── Types ─────────────────────────────────────────────────────── */
type NType = 'normal' | 'primary' | 'service' | 'isolated' | 'persist';
type EType = 'flow' | 'cedar' | 'vault' | 'return' | 'bus';

interface ArchNode {
  id: string; label: string; sub?: string;
  x: number; y: number; w: number; h: number;
  t: NType;
}
interface ArchEdge {
  id: string; d: string; t: EType;
  label?: string; lx?: number; ly?: number;
  delay: number; bidir?: boolean;
}

/* ── Node definitions ──────────────────────────────────────────── */
/* viewBox 1060 × 400.  Three zones separated by lane lines.
   Top (y 40–100):  model + policy
   Mid (y 150–260):  interception chain
   Bot (y 280–390):  detection + persistence                       */
const NODES: ArchNode[] = [
  /* top zone */
  { id:'nova',     label:'Nova Lite',       sub:'model loop',     x:170, y:58,  w:82,  h:26, t:'service'  },
  { id:'policy',   label:'Policy Bundle',   sub:'floor_ok gate',  x:818, y:58,  w:110, h:26, t:'normal'   },
  /* mid zone */
  { id:'lambda',   label:'Lambda URL',                            x:32,  y:188, w:86,  h:28, t:'normal'   },
  { id:'agent',    label:'Strands Agent',                         x:162, y:188, w:108, h:28, t:'normal'   },
  { id:'guard',    label:'DisclosureGuard', sub:'before · after', x:330, y:186, w:130, h:32, t:'primary'  },
  { id:'cedar',    label:'Cedar',           sub:'Q1 · Q2',        x:518, y:188, w:70,  h:28, t:'normal'   },
  { id:'rehydr',   label:'Rehydrator',                            x:646, y:188, w:96,  h:28, t:'normal'   },
  { id:'tool',     label:'Tool',                                  x:806, y:188, w:60,  h:28, t:'normal'   },
  /* bot zone */
  { id:'textract', label:'Textract',                              x:228, y:314, w:76,  h:26, t:'service'  },
  { id:'compr',    label:'Comprehend',                            x:322, y:314, w:100, h:26, t:'service'  },
  { id:'nova_pro', label:'Nova Pro',        sub:'tier 3',         x:440, y:314, w:76,  h:26, t:'service'  },
  { id:'vault',    label:'Vault',           sub:'in-process',     x:564, y:314, w:60,  h:26, t:'isolated' },
  { id:'dynamo',   label:'DynamoDB',        sub:'authoritative',  x:712, y:314, w:100, h:26, t:'persist'  },
];

/* ── Edge definitions ──────────────────────────────────────────── */
/* All paths use orthogonal (Manhattan) routing.
   flow   = solid white,  draw-on animation
   bus    = solid dim,    draw-on animation (thinner)
   vault  = solid rose-gold, draw-on animation
   cedar  = dashed white, opacity animation
   return = dashed dim,   opacity animation                        */
const EDGES: ArchEdge[] = [
  /* ─ main pipeline, left → right ─ */
  { id:'e1',  d:'M 118,202 L 162,202',                                                  t:'flow',   delay:0.06 },
  { id:'e2',  d:'M 213,188 L 213,84',                                                   t:'flow',   delay:0.10, bidir:true },
  { id:'e3',  d:'M 270,202 L 330,202',   label:'tool_use',   lx:295, ly:194,           t:'flow',   delay:0.14 },
  { id:'e4',  d:'M 460,202 L 518,202',   label:'Q1',         lx:483, ly:194,           t:'cedar',  delay:0.22 },
  { id:'e5',  d:'M 588,202 L 646,202',   label:'Allow',      lx:611, ly:194,           t:'flow',   delay:0.30 },
  { id:'e6',  d:'M 742,202 L 806,202',                                                  t:'flow',   delay:0.34 },
  /* ─ tool → guard return loop ─ */
  { id:'e7',  d:'M 836,216 L 836,262 L 395,262 L 395,218',
              label:'result',             lx:618,  ly:256,                              t:'return', delay:0.38 },
  /* ─ guard → detection bus ─ */
  { id:'e8',  d:'M 395,218 L 395,290',                                                  t:'bus',    delay:0.44 },
  { id:'e9',  d:'M 222,290 L 830,290',                                                  t:'bus',    delay:0.48 },
  /* ─ bus → services ─ */
  { id:'e10', d:'M 266,290 L 266,314',                                                  t:'flow',   delay:0.52 },
  { id:'e11', d:'M 372,290 L 372,314',                                                  t:'flow',   delay:0.56 },
  { id:'e12', d:'M 478,290 L 478,314',                                                  t:'flow',   delay:0.60 },
  { id:'e13', d:'M 594,290 L 594,314',                                                  t:'vault',  delay:0.64 },
  { id:'e14', d:'M 762,290 L 762,314',   label:'spend',      lx:769,  ly:300,          t:'flow',   delay:0.68 },
  /* ─ vault → rehydrator (isolated trusted path) ─ */
  { id:'e15', d:'M 624,327 L 880,327 L 880,175 L 694,175 L 694,188',
              label:'resolve',            lx:754,  ly:320,                              t:'vault',  delay:0.74 },
  /* ─ policy → cedar (policy refresh feeds cedar) ─ */
  { id:'e16', d:'M 873,84 L 873,150 L 553,150 L 553,188',
              label:'refresh',            lx:716,  ly:145,                              t:'cedar',  delay:0.18 },
  /* ─ guard → agent (Transform, return path) ─ */
  { id:'e17', d:'M 395,186 L 395,128 L 216,128 L 216,188',
              label:'Transform',          lx:299,  ly:122,                              t:'return', delay:0.80 },
];

/* ── Style maps ─────────────────────────────────────────────────── */
const N_COLOR: Record<NType, { fill:string; stroke:string; text:string; sub:string }> = {
  normal:   { fill:'rgba(255,255,255,0.025)', stroke:'rgba(255,255,255,0.14)',  text:'rgba(255,255,255,0.72)', sub:'rgba(255,255,255,0.30)' },
  primary:  { fill:'rgba(222,161,147,0.09)',  stroke:'rgba(222,161,147,0.55)',  text:'rgba(222,161,147,0.94)', sub:'rgba(222,161,147,0.48)' },
  service:  { fill:'rgba(255,255,255,0.015)', stroke:'rgba(255,255,255,0.08)',  text:'rgba(255,255,255,0.45)', sub:'rgba(255,255,255,0.22)' },
  isolated: { fill:'rgba(222,161,147,0.07)',  stroke:'rgba(222,161,147,0.45)',  text:'rgba(222,161,147,0.82)', sub:'rgba(222,161,147,0.40)' },
  persist:  { fill:'rgba(222,161,147,0.05)',  stroke:'rgba(222,161,147,0.38)',  text:'rgba(222,161,147,0.74)', sub:'rgba(222,161,147,0.34)' },
};

const E_STROKE: Record<EType, string> = {
  flow:   'rgba(255,255,255,0.20)',
  bus:    'rgba(255,255,255,0.10)',
  vault:  'rgba(222,161,147,0.55)',
  cedar:  'rgba(255,255,255,0.10)',
  return: 'rgba(255,255,255,0.10)',
};
const E_DASH: Record<EType, string | undefined> = {
  flow:'', bus:'', vault:'', cedar:'3 5', return:'4 6',
};
const E_MARKER: Record<EType, string> = {
  flow:'arr-w', bus:'arr-b', vault:'arr-v', cedar:'arr-c', return:'arr-r',
};

/* ── Component ─────────────────────────────────────────────────── */
export function Section4() {
  const svgRef  = useRef<SVGSVGElement>(null);
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setEntered(true); io.disconnect(); } },
      { threshold: 0.12 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <section className="section s4-section" aria-labelledby="s4-headline">
      <div className="grain-overlay" aria-hidden="true" />
      <div className="section-inner">

        <ScrollEntry>
          <p className="eyebrow">The Architecture</p>
          <h2 id="s4-headline" className="section-headline">
            Two Lambda functions.<br />
            Three interventions. One session of ground truth.
          </h2>
          <p className="section-subline">
            DisclosureGuard intercepts every tool call before and after execution.
            Cedar is asked twice — once about the call, once about each detected field.
            The Vault is process-local and never touches persistence.
            DynamoDB is the only authoritative ledger.
          </p>
        </ScrollEntry>

        {/* ── SVG diagram ────────────────────────────────────── */}
        <ScrollEntry className="s4-diagram" entryEnd="start 60%">
          <svg
            ref={svgRef}
            viewBox="0 0 1060 400"
            width="100%"
            className={`s4-svg${entered ? ' s4-svg--entered' : ''}`}
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Xerath system architecture"
            style={{ overflow: 'visible' }}
          >
            <defs>
              {/* Arrowheads — open chevron style */}
              {[
                { id:'arr-w', stroke:'rgba(255,255,255,0.28)' },
                { id:'arr-b', stroke:'rgba(255,255,255,0.12)' },
                { id:'arr-v', stroke:'rgba(222,161,147,0.70)' },
                { id:'arr-c', stroke:'rgba(255,255,255,0.12)' },
                { id:'arr-r', stroke:'rgba(255,255,255,0.12)' },
              ].map(m => (
                <marker key={m.id} id={m.id}
                  markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M1,1 L7,4 L1,7"
                    fill="none" stroke={m.stroke} strokeWidth="1"
                    strokeLinecap="square" strokeLinejoin="miter" />
                </marker>
              ))}
              {/* Bidirectional start */}
              <marker id="arr-w-s"
                markerWidth="8" markerHeight="8" refX="1" refY="4" orient="auto-start-reverse">
                <path d="M7,1 L1,4 L7,7"
                  fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="1"
                  strokeLinecap="square" strokeLinejoin="miter" />
              </marker>
            </defs>

            {/* ── Lane separator lines ── */}
            {[120, 272].map(y => (
              <line key={y} x1="0" y1={y} x2="1060" y2={y}
                stroke="rgba(255,255,255,0.045)" strokeWidth="0.5" strokeDasharray="4 10" />
            ))}

            {/* ── Zone labels ── */}
            {[
              { y:44,  t:'MODEL' },
              { y:165, t:'INTERCEPTION CHAIN' },
              { y:286, t:'DETECTION  ·  PERSISTENCE' },
            ].map(z => (
              <text key={z.t} x="1052" y={z.y}
                textAnchor="end" className="s4-zone-lbl"
                fill="rgba(255,255,255,0.10)">
                {z.t}
              </text>
            ))}

            {/* ── Entry arrow from Analyst ── */}
            <path
              d="M 2,202 L 32,202"
              className="s4-edge s4-edge--flow"
              stroke={E_STROKE.flow} strokeWidth="1" fill="none"
              markerEnd="url(#arr-w)"
              style={{ '--d': '0s' } as React.CSSProperties}
            />
            <text x="3" y="192" className="s4-elbl"
              style={{ '--d': '0.55s' } as React.CSSProperties}>
              Analyst
            </text>

            {/* ── Edges ── */}
            {EDGES.map(e => (
              <g key={e.id}>
                <path
                  d={e.d}
                  className={`s4-edge s4-edge--${e.t}`}
                  stroke={E_STROKE[e.t]}
                  strokeWidth={e.t === 'bus' ? 0.75 : 1}
                  strokeDasharray={E_DASH[e.t] || undefined}
                  fill="none"
                  markerEnd={`url(#${E_MARKER[e.t]})`}
                  {...(e.bidir ? { markerStart: 'url(#arr-w-s)' } : {})}
                  style={{ '--d': `${e.delay}s` } as React.CSSProperties}
                />
                {e.label != null && e.lx != null && e.ly != null && (
                  <text x={e.lx} y={e.ly} className="s4-elbl"
                    style={{ '--d': `${e.delay + 0.36}s` } as React.CSSProperties}>
                    {e.label}
                  </text>
                )}
              </g>
            ))}

            {/* ── Vault isolation annotation ── */}
            <rect x="557" y="307" width="74" height="40"
              fill="none"
              stroke="rgba(222,161,147,0.16)" strokeWidth="0.5"
              strokeDasharray="3 4" rx="1"
              className="s4-vault-box"
            />

            {/* ── Nodes (drawn on top of edges) ── */}
            {NODES.map((n, i) => {
              const c  = N_COLOR[n.t];
              const hasSub = Boolean(n.sub);
              const isPrimary = n.t === 'primary' || n.t === 'isolated' || n.t === 'persist';
              return (
                <g key={n.id}
                  className={`s4-node s4-node--${n.t}`}
                  style={{ '--nd': `${i * 0.04}s` } as React.CSSProperties}>
                  
                  {/* We expand foreignObject by 100px on all sides to prevent box-shadow clipping, then center the node */}
                  <foreignObject 
                    x={n.x - 100} 
                    y={n.y - 100} 
                    width={n.w + 200} 
                    height={n.h + 200}
                    style={{ overflow: 'visible' }}
                  >
                    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <div 
                        className={`btn ${isPrimary ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ 
                          width: `${n.w}px`, 
                          height: `${n.h}px`, 
                          padding: 0,
                          pointerEvents: 'auto',
                          cursor: 'default',
                          flexDirection: 'column',
                          gap: 0,
                          /* Match standard button border-radius exactly */
                          borderRadius: 'var(--radius-full)',
                          /* Add a subtle internal structure */
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <span className="s4-nlbl" style={{ color: c.text, fill: 'unset', zIndex: 10, lineHeight: 1 }}>{n.label}</span>
                        {hasSub && <span className="s4-nsub" style={{ color: c.sub, fill: 'unset', zIndex: 10, lineHeight: 1, marginTop: '1px' }}>{n.sub}</span>}
                      </div>
                    </div>
                  </foreignObject>
                </g>
              );
            })}
          </svg>
        </ScrollEntry>

        {/* ── Three key callouts ─────────────────────────────── */}
        <div className="s4-callouts">
          {[
            {
              n: '01',
              title: 'Cedar is asked twice per call',
              body:  'Q1 asks "may this tool call happen?" — action is the tool name, resource is the agent. Q2 asks "may this principal learn this field about this subject?" — action is reveal_TYPE, resource is Subject::<id>. Different resources. Same policy file. One audit row.',
            },
            {
              n: '02',
              title: 'Vault is architecturally isolated',
              body:  'The Vault has no edge to DynamoDB, S3, or any persistence layer. Plaintext lives in Lambda process memory for one invocation, cleared in a finally: block. The rose-gold isolation annotation in the diagram is the proof — not a configuration, a structural property.',
            },
            {
              n: '03',
              title: 'Spend lands before Transform',
              body:  'DynamoDB\'s atomic ADD (set-union) completes before the Transform releases content to the model. A crash in the gap withholds rather than discloses. The diagram\'s edge ordering from guard→DynamoDB→model is the atomicity argument.',
            },
          ].map(c => (
            <ScrollEntry key={c.n} className="s4-callout">
              <span className="s4-callout-n">{c.n}</span>
              <div>
                <div className="s4-callout-title">{c.title}</div>
                <div className="s4-callout-body">{c.body}</div>
              </div>
            </ScrollEntry>
          ))}
        </div>

      </div>
    </section>
  );
}
