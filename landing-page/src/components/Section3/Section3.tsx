import { useRef } from 'react';
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
} from 'framer-motion';
import { ScrollEntry } from '../../lib/ScrollEntry';
import './Section3.css';


/* ── CollapseToken ──────────────────────────────────────────────
   Self-contained scroll-driven collapse.
   Has its own ref — fires when IT enters the viewport, not when
   some parent counter reaches an arbitrary threshold.

   CSS grid trick: both spans in the same grid cell → container
   sizes to the wider one → no layout shift during crossfade.       */
function CollapseToken({
  plaintext,
  token,
}: {
  plaintext: string;
  token: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start 80%', 'start 20%'] as any,
  });

  // Collapse fires across the middle of this element's viewport journey
  const collapseP = useTransform(scrollYProgress, [0.2, 0.9], [0, 1]);

  // Plaintext exits: fade + compress upward
  const ptOpacity = useTransform(collapseP, [0, 0.5],  [1, 0]);
  const ptScale   = useTransform(collapseP, [0, 0.5],  [1, 0.68]);
  const ptY       = useTransform(collapseP, [0, 0.5],  [0, -8]);

  // Token arrives: expand from below
  const tkOpacity = useTransform(collapseP, [0.45, 1], [0, 1]);
  const tkScale   = useTransform(collapseP, [0.45, 1], [1.08, 1]);
  const tkY       = useTransform(collapseP, [0.45, 1], [10, 0]);

  return (
    // CSS grid: both children share cell 1/1 → container = max(child widths)
    <span
      ref={ref}
      style={{
        display: 'inline-grid',
        position: 'relative',
        alignItems: 'center',
        height: '1.6em',
      }}
    >
      <motion.span
        style={{
          gridArea: '1 / 1',
          fontFamily: 'Menlo, Monaco, Consolas, monospace',
          fontSize: '0.78rem',
          color: 'var(--color-warn)',
          opacity: ptOpacity,
          ...(reduced ? {} : { scale: ptScale, y: ptY }),
          alignSelf: 'center',
        }}
      >
        {plaintext}
      </motion.span>
      <motion.span
        className="token"
        style={{
          gridArea: '1 / 1',
          opacity: tkOpacity,
          ...(reduced ? {} : { scale: tkScale, y: tkY }),
          alignSelf: 'center',
        }}
      >
        {token}
      </motion.span>
    </span>
  );
}

/* ── LedgerMeter ────────────────────────────────────────────────
   Self-contained — fills when IT enters the viewport.              */
function LedgerMeter({
  filled,
  total,
  types,
  unchanged = false,
}: {
  filled: number;
  total: number;
  types: string[];
  unchanged?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start 80%', 'start 20%'] as any,
  });
  const pct   = `${Math.round((filled / total) * 100)}%`;
  const width = useTransform(scrollYProgress, [0.3, 0.85], ['0%', pct]);

  return (
    <div ref={ref} className="s3-ledger">
      <div className="s3-ledger-bar-wrap">
        <div className="s3-ledger-label">cust_2291 · {filled}/{total} fields</div>
        <div className="s3-ledger-track">
          <motion.div
            className={`s3-ledger-fill ${unchanged ? 's3-ledger-fill--unchanged' : 's3-ledger-fill--full'}`}
            style={{ width }}
          />
        </div>
      </div>
      <div className="s3-ledger-types">
        {types.map((t) => <span key={t} className="s3-ledger-type">{t}</span>)}
      </div>
    </div>
  );
}

/* ── RehydrateFlow ──────────────────────────────────────────────
   Self-contained — token fades out, plaintext slides in, as it
   enters the viewport. No external progress values needed.         */
function RehydrateFlow({ token, plaintext }: { token: string; plaintext: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start 80%', 'start 20%'] as any,
  });

  const progress  = useTransform(scrollYProgress, [0.2, 0.9], [0, 1]);
  const tokenOp   = useTransform(progress, [0, 0.5],  [1, 0]);
  const textOp    = useTransform(progress, [0.5, 1],  [0, 1]);
  const textX     = useTransform(progress, [0.5, 1],  [-14, 0]);

  return (
    <div ref={ref} className="s3-rehydrate-flow">
      <motion.span className="token" style={{ opacity: tokenOp, fontSize: '0.72rem' }}>
        {token}
      </motion.span>
      <span className="s3-rehydrate-arrow">→</span>
      <motion.span
        style={{
          opacity: textOp,
          ...(reduced ? {} : { x: textX }),
          fontFamily: 'Menlo, Monaco, Consolas, monospace',
          fontSize: '0.78rem',
          color: 'var(--text-primary)',
        }}
      >
        {plaintext}
      </motion.span>
      <span className="s3-rehydrate-label">trusted side only</span>
    </div>
  );
}

/* ── Chips ──────────────────────────────────────────────────── */
function AllowChip({ label = 'ALLOW' }) {
  return <span className="s3-chip s3-chip--allow">✓ {label}</span>;
}
function DenyChip() {
  return <span className="s3-chip s3-chip--deny">✗ DENY</span>;
}

/* ═══════════════════════════════════════════════════════════════════
   Section3
   ═══════════════════════════════════════════════════════════════════ */
export function Section3() {
  const sectionRef  = useRef<HTMLElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);  // spine tracks THIS, not the section
  const reduced     = useReducedMotion();

  /* ── Spine scroll — anchored to the TIMELINE DIV, not the section.
     Root cause of both bugs when using sectionRef:
     - Section includes header + prompt above the timeline → spine is
       already 20-25% filled before the first chapter node is visible.
     - Section bottom exits viewport AFTER the last chapter is gone →
       spine never reaches 100% while timeline content is still on screen.

     Fix: offset ['start center', 'end center'] on the timeline div.
     Progress 0 → timeline TOP at viewport CENTER (user just reached chapters).
     Progress 1 → timeline BOTTOM at viewport CENTER (user scrolled through all).
     This is exact 1:1: spine fill = how far through the timeline you've read. */
  const { scrollYProgress: spineP } = useScroll({
    target: timelineRef,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start center', 'end center'] as any,
  });

  return (
    <section ref={sectionRef} className="section s3-section" aria-labelledby="s3-headline">
      <div className="grain-overlay" aria-hidden="true" />

      <div className="section-inner">

        {/* ── Section Header ──────────────────────────────────── */}
        <ScrollEntry>
          <p className="eyebrow">The Mechanism</p>
          <h2 id="s3-headline" className="section-headline">
            One prompt. Three tool calls.<br />
            Every field inspected, every decision recorded.
          </h2>
          <p className="section-subline">
            Watch the disclosure budget enforce in real time — from raw tool response,
            through Cedar authorization, to a redacted result the model never sees past.
          </p>
        </ScrollEntry>

        {/* ── Prompt ──────────────────────────────────────────── */}
        <ScrollEntry className="s3-prompt" style={{ marginBottom: 'var(--space-7)' }}>
          <div className="s3-prompt-label">
            Analyst · alice@acme.com · session s-77 · budget 3 fields / subject
          </div>
          <div className="s3-prompt-text">
            "Summarise the open ticket for Priya Sharma and include her contact details."
          </div>
        </ScrollEntry>

        {/* ── Timeline — ref is the spine's scroll target ─────── */}
        <div className="s3-timeline" ref={timelineRef}>

          {/* Spine — fills exactly as user scrolls through timeline chapters */}
          <div className="s3-spine-track" aria-hidden="true">
            <motion.div
              className="s3-spine-fill"
              style={reduced ? { height: '100%' } : { scaleY: spineP, height: '100%' }}
            />
          </div>


          {/* ══════════════════════════════════════════
              CHAPTER 1 — fetch_customer
              ══════════════════════════════════════════ */}
          <div className="s3-chapter" aria-label="Tool call 1: fetch_customer">
            <ScrollEntry className="s3-chapter-node-wrap">
              <div className="s3-chapter-node" />
              <div className="s3-chapter-header">
                <span className="s3-chapter-badge">Tool Call 1</span>
                <code className="s3-chapter-call">
                  <span className="s3-chapter-call-fn">fetch_customer</span>
                  {'('}
                  <span className="s3-chapter-call-arg">customer_id: "cust_2291"</span>
                  {')'}
                </code>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--auth">Q1 Auth</span>
              <div className="s3-step-content">
                <AllowChip /> analyst may call fetch_customer
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type">Response</span>
              <div className="s3-step-content">
                <div className="s3-code">
                  <span className="s3-code-key">name  </span><span className="s3-code-val">"Priya Sharma"</span>{'  '}
                  <span className="s3-code-key">phone </span><span className="s3-code-val">"+91 99887 66554"</span>{'  '}
                  <span className="s3-code-key">email </span><span className="s3-code-val">"priya@sharma.in"</span>
                </div>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type">Inspect</span>
              <div className="s3-step-content">
                <span style={{ color: 'var(--text-tertiary)', fontSize: '0.78rem' }}>
                  3 entities · attr → cust_2291
                </span>
                <div className="s3-entities">
                  <span className="s3-entity-tag">NAME · 0.97</span>
                  <span className="s3-entity-tag">PHONE · 0.99</span>
                  <span className="s3-entity-tag">EMAIL · 0.99</span>
                </div>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--auth">Q2 Auth</span>
              <div className="s3-step-content">
                <div className="s3-field-auths">
                  {([
                    ['reveal_NAME',  'budget 0 → 1'],
                    ['reveal_PHONE', 'budget 1 → 2'],
                    ['reveal_EMAIL', 'budget 2 → 3'],
                  ] as [string, string][]).map(([action, note]) => (
                    <div key={action} className="s3-field-auth-row">
                      <span>{action}</span>
                      <AllowChip />
                      <span style={{ color: 'var(--text-tertiary)', fontSize: '0.68rem' }}>{note}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--ledger">Ledger</span>
              <div className="s3-step-content">
                <LedgerMeter filled={3} total={3} types={['NAME', 'PHONE', 'EMAIL']} />
              </div>
            </ScrollEntry>
          </div>

          {/* ══════════════════════════════════════════
              CHAPTER 2 — read_ticket
              ══════════════════════════════════════════ */}
          <div className="s3-chapter" aria-label="Tool call 2: read_ticket">
            <ScrollEntry className="s3-chapter-node-wrap">
              <div className="s3-chapter-node" />
              <div className="s3-chapter-header">
                <span className="s3-chapter-badge">Tool Call 2</span>
                <code className="s3-chapter-call">
                  <span className="s3-chapter-call-fn">read_ticket</span>
                  {'('}
                  <span className="s3-chapter-call-arg">ticket_id: "tkt_1042"</span>
                  {')'}
                </code>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--auth">Q1 Auth</span>
              <div className="s3-step-content">
                <AllowChip /> analyst may call read_ticket
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type">Response</span>
              <div className="s3-step-content">
                <div className="s3-code">
                  <span className="s3-code-key">subject </span>
                  <span className="s3-code-str">"Payment failure — order #8811"</span>{'\n'}
                  <span className="s3-code-key">desc    </span>
                  <span className="s3-code-val">"Card ending </span>
                  <span className="s3-code-marked">4821</span>
                  <span className="s3-code-val"> charged ₹4,200. Aadhaar: </span>
                  <span className="s3-code-marked">3456 7890 1234</span>
                  <span className="s3-code-val">."</span>
                </div>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type">Inspect</span>
              <div className="s3-step-content">
                <span style={{ color: 'var(--text-tertiary)', fontSize: '0.78rem' }}>
                  2 entities · attr → cust_2291
                </span>
                <div className="s3-entities">
                  <span className="s3-entity-tag">IN_AADHAAR · 1.0 (Verhoeff ✓)</span>
                  <span className="s3-entity-tag">CREDIT_DEBIT_NUMBER · 0.91</span>
                </div>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--deny">Q2 Auth</span>
              <div className="s3-step-content">
                <div className="s3-field-auths">
                  {([
                    ['reveal_IN_AADHAAR',          'budget full + analyst forbid'],
                    ['reveal_CREDIT_DEBIT_NUMBER',  'budget full (3/3)'],
                  ] as [string, string][]).map(([action, note]) => (
                    <div key={action} className="s3-field-auth-row">
                      <span>{action}</span>
                      <DenyChip />
                      <span style={{ color: 'var(--text-tertiary)', fontSize: '0.68rem' }}>{note}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollEntry>

            {/* ── THE MOMENT — self-contained scroll-driven collapse ── */}
            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--redact">Redact</span>
              <div className="s3-step-content">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <CollapseToken plaintext="3456 7890 1234" token="[IN_AADHAAR_1_7f3a]" />
                    <span style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>→ sealed to Vault</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <CollapseToken plaintext="4821" token="[CREDIT_DEBIT_NUMBER_1_3a2f]" />
                    <span style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>→ sealed to Vault</span>
                  </div>
                </div>
                <p className="s3-vault-note" style={{ marginTop: '10px' }}>
                  Vault lives in process memory only — never serialized, never logged, never in agent state.
                </p>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--ledger">Ledger</span>
              <div className="s3-step-content">
                <div style={{ fontSize: '0.72rem', color: 'var(--color-danger)', marginBottom: '6px' }}>
                  Unchanged — redacted fields do not spend the budget
                </div>
                <LedgerMeter filled={3} total={3} types={['NAME', 'PHONE', 'EMAIL']} unchanged />
              </div>
            </ScrollEntry>
          </div>

          {/* ══════════════════════════════════════════
              CHAPTER 3 — send_summary
              ══════════════════════════════════════════ */}
          <div className="s3-chapter" aria-label="Tool call 3: send_summary">
            <ScrollEntry className="s3-chapter-node-wrap">
              <div className="s3-chapter-node" />
              <div className="s3-chapter-header">
                <span className="s3-chapter-badge">Tool Call 3</span>
                <code className="s3-chapter-call">
                  <span className="s3-chapter-call-fn">send_summary</span>
                  {'('}
                  <span className="s3-chapter-call-arg">to: "billing@company.in"</span>
                  {')'}
                </code>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--auth">Q1 Auth</span>
              <div className="s3-step-content">
                <AllowChip /> analyst may call send_summary
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type">Body</span>
              <div className="s3-step-content">
                <div className="s3-code">
                  <span className="s3-code-key">body </span>
                  <span className="s3-code-val">"Aadhaar: </span>
                  <span className="token" style={{ fontSize: '0.72rem' }}>[IN_AADHAAR_1_7f3a]</span>
                  <span className="s3-code-val">. Please verify with billing."</span>
                </div>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: '6px' }}>
                  The model constructed this body. It only ever held the placeholder.
                </p>
              </div>
            </ScrollEntry>

            {/* ── THE REVERSAL — self-contained rehydration reveal ── */}
            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--rehydrate">Rehydrate</span>
              <div className="s3-step-content">
                <RehydrateFlow token="[IN_AADHAAR_1_7f3a]" plaintext="3456 7890 1234" />
                <p className="s3-vault-note" style={{ marginTop: '8px' }}>
                  Vault resolves the placeholder within this Lambda invocation.
                  Tool receives plaintext. Model context never did.
                  Vault clears in{' '}
                  <code style={{ fontSize: '0.68rem' }}>finally:</code> at invocation end.
                </p>
              </div>
            </ScrollEntry>

            <ScrollEntry className="s3-step">
              <span className="s3-step-type s3-step-type--auth">Execute</span>
              <div className="s3-step-content">
                <AllowChip label="DONE" /> Billing system received the real value.
                {' '}Model history only ever contained{' '}
                <span className="token" style={{ fontSize: '0.72rem' }}>[IN_AADHAAR_1_7f3a]</span>.
              </div>
            </ScrollEntry>
          </div>

        </div>

        {/* ── Footer stats ─────────────────────────────────────── */}
        <ScrollEntry>
          <div className="s3-footer">
            {([
              ['Tool Calls',       '3',      false],
              ['Fields Inspected', '5',      false],
              ['Fields Disclosed', '3',      false],
              ['Fields Withheld',  '2',      true],
              ['Rehydrations',     '1',      false],
              ['Overhead',         '+41 ms', false],
            ] as [string, string, boolean][]).map(([label, val, accent]) => (
              <div key={label} className="s3-footer-stat">
                <span className="s3-footer-stat-label">{label}</span>
                <span
                  className="s3-footer-stat-val"
                  style={accent ? { color: 'var(--accent-rose)' } : undefined}
                >
                  {val}
                </span>
              </div>
            ))}
            <span className="s3-footer-note">
              One audit row per tool call. One Cedar policy. Zero plaintext in logs.
            </span>
          </div>
        </ScrollEntry>

      </div>
    </section>
  );
}


