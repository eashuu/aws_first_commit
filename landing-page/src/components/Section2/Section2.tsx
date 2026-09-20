/**
 * Section2 — The Problem: The Aggregation Attack.
 *
 * Story role: Bridges S1 ("we count the total") to S3 (the mechanism).
 * Shows three individually-permitted calls that together identify a person.
 * The third call hits the budget ceiling — same session, same person as S3.
 *
 * Design: Three plain type columns, hairline dividers, no cards.
 * Each column scrolls in staggered. Column 3 is the moment of truth.
 * Refero: facts > illustration. No cards as default containers.
 */
import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ScrollEntry } from '../../lib/ScrollEntry';
import './Section2.css';

/* ── Per-column budget meter — fills as column enters viewport ─── */
function BudgetBar({ filled, total }: { filled: number; total: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start 95%', 'start 45%'] as any,
  });
  const pct   = `${Math.round((filled / total) * 100)}%`;
  const width = useTransform(scrollYProgress, [0.4, 1], ['0%', pct]);

  return (
    <div ref={ref} className="s2-budget-row">
      <span className="s2-budget-label">{filled} / {total}</span>
      <div className="s2-budget-track" aria-label={`Budget: ${filled} of ${total} fields`}>
        <motion.div
          className={`s2-budget-fill ${filled >= total ? 's2-budget-fill--full' : ''}`}
          style={{ width }}
        />
      </div>
    </div>
  );
}

/* ── Call column data ─────────────────────────────────────────── */
interface CallData {
  index: number;
  badge: string;
  fn: string;
  fields: { label: string; value: string }[];
  budgetBefore: number;
  budgetTotal: number;
  status: 'disclosed' | 'blocked';
  token?: string;
}

const CALLS: CallData[] = [
  {
    index: 1,
    badge: 'Call 1',
    fn: 'fetch_customer',
    fields: [
      { label: 'Name',  value: 'Priya Sharma'    },
      { label: 'Phone', value: '+91 99887 66554'  },
      { label: 'Email', value: 'priya@sharma.in'  },
    ],
    budgetBefore: 0,
    budgetTotal: 3,
    status: 'disclosed',
  },
  {
    index: 2,
    badge: 'Call 2',
    fn: 'read_ticket',
    fields: [
      { label: 'Subject', value: 'Payment failure' },
      { label: 'Card',    value: '···· ···· ···· 4821' },
    ],
    budgetBefore: 0,
    budgetTotal: 3,
    status: 'disclosed',
  },
  {
    index: 3,
    badge: 'Call 3',
    fn: 'read_ticket (desc)',
    fields: [
      { label: 'Aadhaar', value: '' },
    ],
    budgetBefore: 3,
    budgetTotal: 3,
    status: 'blocked',
    token: '[IN_AADHAAR_1_7f3a]',
  },
];

/* ── Individual call column ───────────────────────────────────── */
function CallColumn({ call, entryDelay }: { call: CallData; entryDelay: string }) {
  const isBlocked = call.status === 'blocked';

  return (
    <ScrollEntry
      className={`s2-call ${isBlocked ? 's2-call--blocked' : ''}`}
      entryEnd={entryDelay}
    >
      {/* Badge + function name */}
      <div className="s2-call-header">
        <span className="s2-call-badge">{call.badge}</span>
        <code className="s2-call-fn">{call.fn}</code>
      </div>

      {/* Session chip */}
      <div className="s2-call-session">cust_2291 · s-77</div>

      {/* Fields revealed */}
      <div className="s2-call-fields">
        {call.fields.map(({ label, value }) => (
          <div key={label} className="s2-call-field">
            <span className="s2-call-field-label">{label}</span>
            {isBlocked ? (
              <span className="token">{call.token}</span>
            ) : (
              <span className="s2-call-field-value">{value}</span>
            )}
          </div>
        ))}
      </div>

      {/* Budget meter */}
      <BudgetBar
        filled={isBlocked ? call.budgetTotal : call.index}
        total={call.budgetTotal}
      />

      {/* Status label */}
      <div className={`s2-call-status ${isBlocked ? 's2-call-status--blocked' : 's2-call-status--ok'}`}>
        {isBlocked ? 'Budget exceeded · Withheld' : 'Disclosed'}
      </div>
    </ScrollEntry>
  );
}

/* ── Section2 ─────────────────────────────────────────────────── */
export function Section2() {
  return (
    <section className="section" aria-labelledby="s2-headline">
      <div className="grain-overlay" aria-hidden="true" />

      <div className="section-inner">

        {/* ── Header ──────────────────────────────────────────── */}
        <ScrollEntry>
          <p className="eyebrow">The Problem</p>
          <h2 id="s2-headline" className="section-headline s2-headline-wide">
            Each call was allowed.{' '}
            Together they identify her.{' '}
            <span className="s2-headline__fade">Nobody was counting.</span>
          </h2>
        </ScrollEntry>

        {/* ── Three-column aggregation trace ──────────────────── */}
        {/* Refero: no cards. Three type columns with hairline dividers. */}
        <div className="s2-columns" role="list" aria-label="Three calls that assembled a complete identity">

          {/* Top hairline — full width */}
          <div className="s2-columns-rule" aria-hidden="true" />

          <div className="s2-columns-grid">
            {CALLS.map((call, i) => (
              <CallColumn
                key={call.index}
                call={call}
                /* Stagger: column 1 at 40%, 2 at 35%, 3 at 30% — arriving later */
                entryDelay={i === 0 ? 'start 40%' : i === 1 ? 'start 37%' : 'start 33%'}
              />
            ))}
          </div>

          {/* Bottom hairline */}
          <div className="s2-columns-rule" aria-hidden="true" />
        </div>

        {/* ── Caption — connects back to S1 and forward to S3 ─── */}
        <ScrollEntry className="s2-caption">
          <p className="s2-caption-text">
            Three calls. No single one was suspicious.
            The combination assembled a complete identity profile.
            {' '}<span className="s2-caption-accent">Xerath counted the total. Section 3 shows how.</span>
          </p>
          <div className="s2-caption-stats">
            <span>Session s-77</span>
            <span className="s2-caption-sep" aria-hidden="true">·</span>
            <span>Budget 3 fields / subject</span>
            <span className="s2-caption-sep" aria-hidden="true">·</span>
            <span>2 disclosed · <span style={{ color: 'var(--accent-rose)' }}>1 withheld</span></span>
            <span className="s2-caption-sep" aria-hidden="true">·</span>
            <span>+41 ms overhead</span>
          </div>
        </ScrollEntry>

      </div>
    </section>
  );
}

