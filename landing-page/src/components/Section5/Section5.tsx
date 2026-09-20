/**
 * Section5 — Per-call nine-step breakdown.
 *
 * Nine numbered steps that track exactly what happens between
 * a tool returning its result and the model receiving the output.
 *
 * Layout: .s5-timeline has padding-left: 25px (clears the 1px spine).
 * Inside each .s5-step: CSS grid with col 1 = step number (48px),
 * col 2 = step content. No negative margins. No position hacks.
 *
 * Spine: uses Section 3's exact pattern — a sticky fill div inside
 * a .s5-spine-track positioned absolutely on the left edge of the
 * timeline. Framer Motion scaleY tracks timelineRef scroll progress.
 */
import { useRef } from 'react';
import { motion, useScroll, useReducedMotion } from 'framer-motion';
import { ScrollEntry } from '../../lib/ScrollEntry';
import './Section5.css';

/* ── Step data ──────────────────────────────────────────────────── */
interface Step {
  n:      string;  // zero-padded "01"–"09"
  name:   string;  // monospace ALL-CAPS heading
  body:   string;  // prose explanation
  code:   string;  // data-shape / pseudocode annotation
  badge?: string;  // service chip label
}

const STEPS: Step[] = [
  {
    n: '01', name: 'NORMALIZE',
    body: 'Every payload becomes markdown before detection. Text and JSON pass through directly. PDFs and images always go to Textract — even text-layer PDFs, because a text-extractor silently misses a scanned Aadhaar embedded inside. Multi-page documents are withheld entirely. Truncation is a detected condition in the audit row, never a silent cut.',
    code: 'input   bytes | { media_type: str, b64: str }\noutput  Normalized(markdown: str, pages: int,\n                   ocr_sourced: bool, truncated: bool)',
    badge: 'Textract',
  },
  {
    n: '02', name: 'DETECT T1 — LOCAL CHECKSUM',
    body: 'Verhoeff algorithm (D₅ dihedral-group tables, written fresh) validates Aadhaar. PAN: shape regex plus holder-type character (P/C/H/F/A/T/B/L/J/G). On OCR-sourced text, a 12-digit run that fails Verhoeff still emits an entity at score 0.45 — checksum as a confidence signal, not a hard gate. Zero API calls. Zero latency cost.',
    code: 'verhoeff_valid(digits: str) → bool\npan_valid(s: str)           → bool  # shape + holder-type\n\nEntity(type="IN_AADHAAR", score=1.0,  tier="checksum")\nEntity(type="IN_AADHAAR", score=0.45, tier="checksum", ocr_derived=True)',
  },
  {
    n: '03', name: 'DETECT T2 — COMPREHEND',
    body: 'One DetectPiiEntities call per tool hop on the full normalized markdown. Chunked at 90,000 bytes with a 200-character overlap so entities straddling a chunk boundary are never missed — the offset shift is the single most likely place to introduce an off-by-N bug. If Comprehend fails the hop is withheld — the system never degrades to tier 1 alone.',
    code: 'detect_pii_entities(Text=markdown, LanguageCode="en")\n→ { Entities: [{ Score, Type, BeginOffset, EndOffset }] }\n\n# chunk k offset shift:\nentity.begin += chunk_start_offset',
    badge: 'Comprehend',
  },
  {
    n: '04', name: 'DETECT T3 — NOVA PRO MULTIMODAL',
    body: 'Devanagari, Tamil, Telugu names are invisible to Textract (Latin-script only) and Comprehend (English/Spanish). Nova Pro receives the raw image as a Bedrock ImageBlock and returns substrings only. str.find() locates the offset in source text. If find() returns -1 the finding is dropped. Tier 3 is additive-only: it cannot clear another tier\'s finding.',
    code: 'prompt → [{type, text}]  # substrings only, no coordinates\nfor item in result:\n    idx = source_text.find(item["text"])\n    if idx == -1: drop(item); continue\n    yield Entity(begin=idx, tier="indic")',
    badge: 'Nova Pro',
  },
  {
    n: '05', name: 'MERGE',
    body: 'All three tiers union — no tier can remove another\'s findings. Specificity ranking resolves contained spans: a NAME span fully inside an IN_AADHAAR span is dropped. Identical spans keep the higher-rank type and max score. Partial overlaps keep both entities, resolved at redaction time right-to-left so earlier span positions are not shifted.',
    code: '# Specificity rank (highest → lowest)\nIN_AADHAAR = IN_PAN\n  > CREDIT_DEBIT_NUMBER\n  > PHONE > EMAIL > NAME > ADDRESS > OTHER',
  },
  {
    n: '06', name: 'ATTRIBUTE',
    body: 'Each entity is assigned to a data subject from the tool\'s input keys, checked in priority order: customer_id → subject_id → ticket_id → account_id. First match wins. Content with no subject hint shares one per-session "unattributed" bucket — it cannot dodge the budget by being anonymous.',
    code: 'SUBJECT_KEYS = ("customer_id", "subject_id",\n                "ticket_id",  "account_id")\n\nattribute(entities, tool_input={"customer_id": "cust_2291"})\n→ all entities → subject "cust_2291"',
  },
  {
    n: '07', name: 'Q2 AUTHORIZE',
    body: 'Cedar is_authorized_batch — one request per detected (subject × entity type), all in a single call. The Cedar resource is the data subject, not the agent — this is what makes subject-scoped policy possible. Context carries the full ledger state: role, seen[], seen_count, budget. Default deny. NoDecision is treated as deny.',
    code: 'action   Action::"reveal_IN_AADHAAR"\nresource Subject::"cust_2291"\ncontext  { role: "analyst", seen: ["NAME","PHONE"],\n           seen_count: 2, budget: 3 }\n\n→  DENY  (determining policy: forbid_aadhaar_analyst)',
    badge: 'cedarpy',
  },
  {
    n: '08', name: 'REDACT',
    body: 'Denied spans become numbered typed tokens. str.replace() — never re.sub() — a field value containing regex metacharacters is a routine bug and a plausible injection vector. The Vault mints each token with a per-invocation 4-hex nonce so a stale token from a previous Lambda container cannot resolve to a different person\'s data. Redacted right-to-left by begin offset so earlier span positions are not shifted.',
    code: 'input   "aadhaar: 3456 7890 1234"\noutput  "aadhaar: [IN_AADHAAR_1_7f3a]"\n\nvault   { "[IN_AADHAAR_1_7f3a]": "3456 7890 1234" }\n        # process-local · never serialized · cleared in finally:',
  },
  {
    n: '09', name: 'SPEND',
    body: 'DynamoDB UpdateItem with ADD on a String Set — atomic set-union, one round trip, no read-modify-write, no lost update. This write completes before Transform releases content to the model. A crash between spend and Transform withholds rather than discloses. Only revealed fields spend. Redacted fields do not consume the budget that protected them.',
    code: 'UpdateItem(\n  Key  = { pk: "SESSION#s-77", sk: "METER#cust_2291" },\n  Expr = "ADD seen :t SET budget=:b, last_ts=:ts",\n  Args = { ":t": {"SS": ["NAME","PHONE"]} },\n  ReturnValues = "ALL_OLD"\n)\n\n# Transform fires ONLY after this write succeeds',
    badge: 'DynamoDB',
  },
];

/* ── Component ──────────────────────────────────────────────────── */
export function Section5() {
  const timelineRef = useRef<HTMLDivElement>(null);
  const reduced     = useReducedMotion();

  /* ── Spine scroll — anchored directly to the timeline container.
     offset ['start center', 'end center']:
     Progress 0 = timeline top reaches viewport center (user starts Step 01).
     Progress 1 = timeline bottom reaches viewport center (user finishes steps).
     1:1 physical scroll tracking with zero drift. */
  const { scrollYProgress: spineP } = useScroll({
    target: timelineRef,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: ['start center', 'end center'] as any,
  });

  return (
    <section className="section s5-section" aria-labelledby="s5-headline">
      <div className="grain-overlay" aria-hidden="true" />
      <div className="section-inner">

        <ScrollEntry>
          <p className="eyebrow">Per Call</p>
          <h2 id="s5-headline" className="section-headline">
            Nine steps between tool response<br />
            and model context.
          </h2>
          <p className="section-subline">
            Every tool result runs the full pipeline on every hop —
            normalize, detect across three tiers, attribute, authorize,
            redact, spend. The model only ever receives the output of step nine.
          </p>
        </ScrollEntry>

        {/* ── Timeline — ref is the spine's scroll target ─────── */}
        <div className="s5-timeline" ref={timelineRef}>

          {/* Spine — fills exactly as user scrolls through steps */}
          <div className="s5-spine-track" aria-hidden="true">
            <motion.div
              className="s5-spine-fill"
              style={reduced ? { height: '100%' } : { scaleY: spineP, height: '100%' }}
            />
          </div>

          {/* Steps list */}
          <div className="s5-steps">
            {STEPS.map(step => (
              <ScrollEntry key={step.n} className="s5-step">

                {/* Column 1: step number */}
                <div className="s5-step-num" aria-hidden="true">
                  {step.n}
                </div>

                {/* Column 2: step content */}
                <div className="s5-step-content">
                  <div className="s5-step-header">
                    <h3 className="s5-step-name">{step.name}</h3>
                    {step.badge && (
                      <span className="s5-badge">{step.badge}</span>
                    )}
                  </div>
                  <p className="s5-step-body">{step.body}</p>
                  <pre className="s5-code"><code>{step.code}</code></pre>
                </div>

              </ScrollEntry>
            ))}
          </div>

          {/* Terminal note — aligned with content column */}
          <ScrollEntry className="s5-terminal">
            <div className="s5-terminal-inner">
              <span className="s5-terminal-label">model receives</span>
              <span className="s5-terminal-sep">·</span>
              <span className="s5-terminal-value">
                redacted markdown only — vault holds the rest
              </span>
            </div>
          </ScrollEntry>

        </div>
      </div>
    </section>
  );
}

