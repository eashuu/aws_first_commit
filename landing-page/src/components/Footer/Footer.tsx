/**
 * Footer — Final section of the Xerath landing page.
 *
 * Three zones, separated by hairline rules:
 *   1. Identity + Hackathon context  (two-column)
 *   2. Team credits                  (editorial, full-width names)
 *   3. Stack + Copyright             (bottom bar)
 *
 * No cards. No borders-as-containers. Just typography.
 */
import { ScrollEntry } from '../../lib/ScrollEntry';
import './Footer.css';

const TEAM  = ['Dhanush', 'Eashwar', 'Sabharish', 'Shreyas'] as const;

const STACK = [
  'AWS Lambda', 'Bedrock Nova', 'Cedar',
  'Comprehend', 'Textract', 'DynamoDB', 'React',
] as const;

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer" aria-label="Site footer">

      {/* Rose-gold gradient separator — different from section border-top */}
      <div className="footer-iris" aria-hidden="true" />

      <div className="section-inner footer-inner">

        {/* ── Zone 1: Identity + Hackathon ─────────────────────── */}
        <ScrollEntry className="footer-top">

          {/* Left: product identity */}
          <div className="footer-identity">
            <p className="footer-mark">Xerath</p>
            <p className="footer-tag">
              Least privilege for data, with memory.
            </p>
            <p className="footer-desc">
              Subject-scoped semantic accumulation, enforced at the tool
              boundary, over any content type, with a running ledger that
              proves it held.
            </p>
          </div>

          {/* Right: hackathon context */}
          <div className="footer-context">
            <p className="footer-context-label">Submitted to</p>
            <p className="footer-context-event">First Commit</p>
            <p className="footer-context-org">WeMakeDevs × AWS</p>
            <p className="footer-context-track">
              Bharat Builds Tour · Ship It Track
            </p>
            <p className="footer-context-date">September 2026</p>
          </div>

        </ScrollEntry>

        {/* ── Divider ──────────────────────────────────────────── */}
        <div className="footer-rule" aria-hidden="true" />

        {/* ── Zone 2: Team ─────────────────────────────────────── */}
        <ScrollEntry className="footer-team">
          <p className="footer-team-label">Designed and developed by</p>
          <div className="footer-names" aria-label="Team members">
            {TEAM.map((name, i) => (
              <span key={name} className="footer-name-wrap">
                <span className="footer-name" data-text={name}>{name}</span>
                {i < TEAM.length - 1 && (
                  <span className="footer-name-sep" aria-hidden="true">·</span>
                )}
              </span>
            ))}
          </div>
        </ScrollEntry>

        {/* ── Divider ──────────────────────────────────────────── */}
        <div className="footer-rule footer-rule--dim" aria-hidden="true" />

        {/* ── Zone 3: Stack + Copyright ─────────────────────────── */}
        <ScrollEntry className="footer-bottom">
          <p className="footer-copy">© {year} Xerath</p>

          <div className="footer-stack" aria-label="Technology stack">
            {STACK.map(s => (
              <span key={s} className="footer-chip">{s}</span>
            ))}
          </div>
        </ScrollEntry>

      </div>
    </footer>
  );
}
