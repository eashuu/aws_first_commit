# Naka — Diagram Pack

**Document:** 09 of the Naka planning package · **Written:** 18 September 2026
**Draws:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md` (PRD v2) and `08-technical-design.md`

Twelve diagrams. Nothing here is new design — every diagram is a projection of a decision already made in the PRD or in doc 08. Where the two disagree, or where drawing the flow exposed something neither settles, the caption says so and §13 collects them.

**Naming.** The project is **Naka**. The rename is complete across every document, including doc 08's identifiers (`naka/`, `naka_audit`, `X-Naka-Key`, `NAKA_KEY`). Only the folder name `chowki-hackathon/` and the `01`–`12` filenames retain the old spelling; cosmetic, and deliberately left until after submission.

**Question numbering used throughout.** **Q1** = may this tool call happen (PRD §5 step 2, Cedar via Strands). **Q2** = may this principal learn this field about this subject, given the ledger (PRD §5 step 7, `cedarpy.is_authorized_batch`). **Q3** = may this placeholder be rehydrated into *this* destination call (PRD §11.2). Q3 is this pack's label; the PRD calls it "itself a Cedar question".

Every diagram below was rendered through a Mermaid validator and returned valid.

---

## Contents

| # | Diagram | Type |
|---|---|---|
| 1 | [System architecture](#1-system-architecture) | flowchart |
| 2 | [Per-tool-call sequence](#2-per-tool-call-sequence) | sequenceDiagram |
| 3 | [The file path](#3-the-file-path) | flowchart |
| 4 | [Detector tier decision tree](#4-detector-tier-decision-tree) | flowchart |
| 5 | [The two Cedar questions](#5-the-two-cedar-questions) | flowchart |
| 6 | [Disclosure ledger state](#6-disclosure-ledger-state) | stateDiagram-v2 |
| 7 | [Rehydration as a third Cedar question](#7-rehydration-as-a-third-cedar-question) | flowchart |
| 8 | [Data model](#8-data-model) | erDiagram |
| 9 | [Failure modes](#9-failure-modes) | flowchart |
| 10 | [Threat model and trust boundaries](#10-threat-model-and-trust-boundaries) | flowchart |
| 11 | [Deploy pipeline](#11-deploy-pipeline) | flowchart |
| 12 | [The demo timeline](#12-the-demo-timeline) | gantt |
| 13 | [What drawing these revealed](#13-what-drawing-these-revealed) | — |

---

## 1. System architecture

```mermaid
flowchart LR
  UI["Naka dashboard SPA"]

  subgraph CP["CONTROL PLANE - Lambda + Function URL"]
    CTRL["app_control"]
    BUNDLE["policy bundle + ETag"]
  end

  subgraph DP["DATA PLANE - Lambda + Function URL"]
    POLC["policy.py + floor_ok"]
    AGENT["Strands Agent"]
    CHAIN["DisclosureGuard -> CedarAuthorization -> Rehydrator"]
    HOOK["AuditHook"]
    VAULT["Vault - plaintext, in-process"]
    TOOLS["3 demo tools"]
  end

  subgraph AWS["AWS managed - ap-south-1"]
    NOVA["Bedrock Nova"]
    COMP["Comprehend"]
    TEXT["Textract"]
    DDB[("DynamoDB naka_audit")]
    S3[("S3 session cache")]
    CW["CloudWatch Logs"]
  end

  UI -->|"POST / run a turn"| AGENT
  UI -->|"GET /feed /session"| CTRL
  UI -->|"PUT /policy + key"| CTRL
  CTRL --- BUNDLE
  CTRL --> DDB
  POLC -. "TRUST BOUNDARY - bundle is untrusted, floor_ok gates it" .-> CTRL
  POLC --> CHAIN
  AGENT --- CHAIN
  CHAIN --> TOOLS
  CHAIN --- VAULT
  AGENT <--> NOVA
  CHAIN --> COMP
  CHAIN --> TEXT
  CHAIN --> NOVA
  CHAIN --> DDB
  HOOK --> DDB
  AGENT --> S3
  HOOK --> CW
```

**Caption.** Both planes, every AWS service, and the one boundary that matters: the data plane treats the control plane's policy bundle as untrusted input and runs `floor_ok()` on it before loading, so an unauthenticated `PUT /policy` cannot lift the Aadhaar forbid or the budget ceiling. **Deliberately omitted:** intervention ordering (diagram 2), the fact that both Function URLs are `AuthType=NONE` and therefore have no principal boundary at all (diagram 10), and which Nova model runs where — the PRD puts Nova Lite on the agent loop and Nova Pro on tier 3 only, doc 08 puts Nova Pro on both, and that is unresolved (§13.7).

---

## 2. Per-tool-call sequence

```mermaid
sequenceDiagram
    autonumber
    participant M as Nova agent loop
    participant G as DisclosureGuard
    participant C as CedarAuthorization
    participant R as Rehydrator
    participant T as Tool
    participant D as Textract / Comprehend / Nova Pro
    participant Z as cedarpy
    participant DB as DynamoDB
    participant H as AuditHook

    Note over G,DB: per HTTP request - policy.refresh then ledger.load with ConsistentRead. A failed load is 503 LEDGER_UNAVAILABLE and no turn runs.

    M->>G: before_tool_call
    G->>G: 1. canonical subject, stash snapshot, session_ceiling check
    G-->>C: Proceed
    C->>G: context_enricher
    G-->>C: role, subject, seen, seen_count, budget
    C->>Z: 2. Q1 may this call happen
    Z-->>C: Allow or Deny
    alt Q1 Deny
        C-->>M: Deny with reason. Rehydrator and tool both skipped.
    else Q1 Allow
        C-->>R: Proceed
        R->>R: 3. scan args for placeholder tokens
        alt token found
            R->>Z: Q3 rehydrate_TYPE, resource = destination tool
            Z-->>R: Allow or Deny
            R-->>M: Deny if unresolvable or unauthorized
        end
        R-->>T: Proceed
        T-->>G: after_tool_call with result
        G->>G: 4. normalize to markdown
        G->>D: 5. detect - tier 1 local, tier 2 Comprehend, tier 3 Nova Pro
        D-->>G: Entity list, union of tiers
        G->>G: 6. attribute each entity to a subject
        G->>Z: 7. Q2 is_authorized_batch, one request per subject and type
        Z-->>G: results keyed by correlation_id
        G->>G: 8. redact denied spans right-to-left, Vault mints tokens
        G->>DB: 9. spend - UpdateItem ADD seen, ALL_OLD
        DB-->>G: ledger_before
        G-->>M: Transform, result becomes redacted markdown
        H->>DB: PutItem audit row - observes, never gates
    end
```

**Caption.** The full nine-step flow, both interventions and the hook. Two orderings are load-bearing and both are drawn: handlers run in registration order so a Q1 `Deny` skips the Rehydrator entirely (a denied call never gets plaintext substituted into its arguments), and the DynamoDB spend lands **before** the `Transform` releases content, so a crash between the two withholds rather than discloses. **Deliberately omitted:** retries and timeouts (diagram 9), the per-hop `asyncio.Lock` held across `detect → spend` for parallel tool use, and the enricher stash key `(tool_name, canonical_json(tool_input))` that makes parallelism safe. The `AuditHook` row is drawn as always written — see §13.6, which is not settled.

---

## 3. The file path

```mermaid
flowchart TD
  A["Tool returns content"] --> B{"media_type"}
  B -->|"text or json"| P["passthrough, truncate at MAX_NORMALIZED_CHARS"]
  B -->|"csv or xlsx"| TBL["markdown pipe table"]
  B -->|"unsupported"| UM["NormalizeError unsupported_media"]
  B -->|"pdf or image"| SZ{"bytes within MAX_ATTACHMENT_BYTES"}
  SZ -->|"no"| UM2["NormalizeError too_large"]
  SZ -->|"yes"| TX["Textract DetectDocumentText, inline Bytes<br/>always, even on a text-layer PDF"]
  TX --> PG{"DocumentMetadata.Pages"}
  PG -->|"more than 1"| MP["NormalizeError multipage<br/>sync Textract only reads page 1"]
  PG -->|"exactly 1"| MD["markdown from LINE blocks<br/>words with bbox, ocr_sourced = true"]
  MD --> T3{"INDIC_ENABLED and a png or jpeg image block exists"}
  T3 -->|"yes"| NV["Tier 3 Nova Pro multimodal on the image"]
  T3 -->|"no - e.g. the source was a PDF"| MAIN
  NV --> MAIN["back to the main flow<br/>detect, attribute, Q2, redact, spend"]
  P --> MAIN
  TBL --> MAIN
  UM --> WH["WITHHELD marker to the model<br/>ledger not spent, row records the outcome"]
  UM2 --> WH
  MP --> WH
```

**Caption.** Everything becomes markdown before detection, which is what lets §8 have no per-format branching; the two decisions worth defending are that *every* PDF goes to Textract (a text-layer extractor silently misses a scanned Aadhaar embedded in a text-layer page — PRD §9.1) and that `Pages > 1` withholds the whole document rather than releasing page 1. **This diagram deliberately draws a hole rather than hiding it:** the `png or jpeg image block exists` branch. Bedrock's `ImageBlock.format` is `png|jpeg|gif|webp`, a PDF is none of those, and doc 08 §11 keeps a rasteriser out of the package — yet doc 08 §2.2 runs tier 3 on the PDF fixture and records `detector_tiers: [..., "indic"]`. See §13.4. **Omitted:** chunking of oversized markdown, and the EXIF/`docProps` metadata that markdown conversion discards rather than scans.

---

## 4. Detector tier decision tree

```mermaid
flowchart TD
  S["normalized markdown, plus the raw image when there is one"] --> T1["TIER 1 local checksum<br/>Verhoeff for Aadhaar, PAN shape plus holder-type char"]
  T1 --> T1B{"ocr_sourced"}
  T1B -->|"yes, and a 12-digit run fails Verhoeff"| T1C["emit anyway at score 0.45, ocr_derived = true<br/>checksum is a confidence signal, not a gate"]
  T1B -->|"no"| T1D["checksum gates the finding"]
  T1C --> T2
  T1D --> T2["TIER 2 Comprehend DetectPiiEntities<br/>one call per hop, 90k chunks, 200-char overlap"]
  T2 --> T2E{"Comprehend returned a usable response"}
  T2E -->|"no"| FC["FAIL CLOSED, withhold the whole hop<br/>never degrade to tier 1 only"]
  T2E -->|"yes"| T3{"INDIC_ENABLED and an image block exists"}
  T3 -->|"no"| MG
  T3 -->|"yes"| NV["TIER 3 Nova Pro multimodal<br/>substrings only - no offsets, no control fields"]
  NV --> FIND{"str.find of the substring in the source text"}
  FIND -->|"returns -1"| DROP["drop the finding, count indic_find_miss"]
  FIND -->|"returns an index"| KEEP["accept, with the located offset"]
  DROP --> MG
  KEEP --> MG["merge - UNION ONLY<br/>a tier may add findings, never clear another tier's"]
  MG --> R1["1. drop a span fully contained in a more specific span"]
  R1 --> R2["2. identical spans - higher rank wins, checksum type wins, max score"]
  R2 --> R3["3. partial overlaps - keep both, redact right-to-left"]
  R3 --> OUT["Entity list, sorted by begin"]
```

**Caption.** Cheapest tier first, but **not** short-circuiting — every available tier runs and the results union, because tier 3 reads attacker-supplied pixels with an instruction-following model and must never be able to clear another tier's finding. The `str.find` gate is the other half of that containment: a model-returned substring not literally present in the source is dropped, so a crafted document can cause a spurious redaction but never a silent pass. **Omitted:** Comprehend's per-chunk offset shift (the single most likely off-by-N in the build) and the `score >= COMPREHEND_MIN_SCORE` filter at 0.5. **Flagged, not settled:** the PRD's own §8 opening sentence calls the tiers "short-circuiting", which contradicts its closing composition rule; this diagram follows doc 08's run-all-then-merge (§13.8). Tier 1's `verhoeff_valid` is drawn without a provenance claim on purpose — see §13.1.

---

## 5. The two Cedar questions

```mermaid
flowchart TD
  START["model emits a tool use"] --> SNAP["DisclosureGuard.snapshot fills context.session<br/>role, subject, seen, seen_count, budget"]
  SNAP --> Q1{"Q1 - may this call happen<br/>action = the tool name, resource = the agent"}
  Q1 -->|"Deny"| DD["tool never runs. outcome denied_call.<br/>nothing detected, nothing spent, no placeholder"]
  Q1 -->|"Allow"| RUN["tool runs, result normalized and detected"]
  RUN --> ATTR["attribute every entity to a data subject"]
  ATTR --> Q2{"Q2 - may this principal learn this field about this subject<br/>action = reveal_TYPE, resource = the subject, context = the ledger"}
  Q2 -->|"Allow"| REV["field released in the clear<br/>this is what SPENDS from the budget"]
  Q2 -->|"Deny, NoDecision, or a missing correlation_id"| RED["field becomes a numbered placeholder<br/>redaction does NOT spend"]
  REV --> SPEND["ledger.spend - atomic ADD seen"]
  RED --> SPEND
  SPEND --> XF["Transform - the model only ever sees the redacted result"]
  WARN["OPEN ISSUE - the ceiling forbid is written un-scoped by action,<br/>so once seen_count reaches budget it denies Q1 too<br/>and the tool stops running at all. See the caption."]
  Q1 -.- WARN
```

**Caption.** The two denies produce genuinely different outcomes and that is the point of the diagram: a Q1 deny means the tool never ran and nothing was learned, while a Q2 deny means the tool ran, the content was inspected, and one field came back as a reversible placeholder — so the task still completes. Note also that **only a revealed field spends**; redaction protecting a field must not also consume the budget that protected it. **The dashed node is a live defect, not decoration.** The ceiling rule is written `forbid(principal, action, resource) when { seen_count >= budget }` with no action scope, and the same enricher feeds `context.session` to both questions — so when the budget fills it denies the *call*, not just the *field*, and the demo's 1:10 beat has no result left to redact. Full argument in §13.2. **Omitted:** the Cedar text itself (doc 08 §3.4), and the `compliance` exemption, which interacts badly with the same rule (§13.3).

---

## 6. Disclosure ledger state

```mermaid
stateDiagram-v2
    [*] --> Loading
    Loading --> Unavailable: ledger.load raised
    Unavailable --> [*]: 503 LEDGER_UNAVAILABLE, no turn runs, no tool executes
    Loading --> Empty: query returned no METER items - a new session
    Loading --> Accumulating: METER items restored, ConsistentRead
    Empty --> Accumulating: first field released in the clear
    Accumulating --> Accumulating: new type revealed - ADD seen, count rises
    Accumulating --> Accumulating: type already in seen - union, count unchanged
    Accumulating --> Accumulating: field redacted - nothing spent
    Accumulating --> Tripped: seen_count reaches budget for this subject
    Tripped --> Tripped: every further identifying field is redacted
    Accumulating --> Ceiling: session_total reaches session_ceiling
    Tripped --> Ceiling: session_total reaches session_ceiling
    Ceiling --> [*]: every subject capped for the rest of the session

    note right of Accumulating
      Grow-only set per session and subject.
      Merge is union - commutative, idempotent.
      The only reachable error is over-counting,
      which fails in the safe direction.
    end note

    note right of Tripped
      A fresh session_id or a fresh subject_id
      resets this. Both bypasses are stated,
      not fixed - only session_ceiling backstops them.
    end note
```

**Caption.** One meter per `(session_id, subject_id)`, filling by set union, tripping at `budget`, with `session_ceiling` as the cross-subject backstop against subject-id churn. `Loading → Unavailable` is drawn as a terminal state on purpose: an unreadable ledger that defaults to empty *is* the bypass, so the whole product is unavailable rather than degraded, and "new session" must be distinguishable from "store unavailable". **Deliberately omitted:** the `agent.state` cache copy in S3, which can lose an update and does not matter (union with the authoritative DynamoDB value repairs it), and the distributed race across concurrent Lambda invocations — the budget can be exceeded by one hop per concurrent invocation, which is accepted for the hackathon and closed in production by a `ConditionExpression` using DynamoDB's `size()` on the set.

---

## 7. Rehydration as a third Cedar question

```mermaid
flowchart TD
  A["a later tool call whose args carry a placeholder token"] --> B{"token found in this invocation's Vault, by exact map lookup"}
  B -->|"no - stale token, cold container, or a forged look-alike"| DN["Deny, with a reason the model can act on<br/>outcome denied_placeholder - never a silent passthrough"]
  B -->|"yes"| Q3{"Q3 - Cedar asks again<br/>action = rehydrate_TYPE, resource = the DESTINATION TOOL"}
  Q3 -->|"Deny"| KEEP["the placeholder stays a placeholder<br/>the tool runs with the token, not the value"]
  Q3 -->|"Allow"| SUB["str.replace the token with the real value on the trusted side<br/>never re.sub - a value with regex metacharacters is a routine bug"]
  SUB --> RUN["tool executes with the real value<br/>the model never held the digits"]
  HOLE["THE HOLE THIS CLOSES - PRD 11.2<br/>blanket substitution made the guardrail the exfiltration channel:<br/>an injected agent emits the placeholder into a call to an attacker-chosen<br/>destination and the guardrail helpfully restores the plaintext"]
  Q3 -.- HOLE
```

**Caption.** Without Q3 the guardrail is an exfiltration primitive — any authorized call carrying `[IN_AADHAAR_1]` gets the plaintext substituted, so a compromised agent just names an attacker-controlled destination and the guardrail helpfully restores the value. Making the **destination tool** the Cedar resource is the fix, and it is a Must (PRD §11 item 5), not a nice-to-have. The unknown-token branch is a `Deny` rather than a passthrough or a `Guide` for three separate reasons: a literal token reaching a downstream system gets stored as if it were an identifier, and a `Guide` invites the model to retry with the same unresolvable token. **Omitted:** the 4-hex per-invocation nonce inside every token (which is what stops a stale token rehydrating to a *different* person's Aadhaar), and the `finally: vault.clear()`.

---

## 8. Data model

```mermaid
erDiagram
    SESSION ||--o{ CALL_ITEM : "one per tool call"
    SESSION ||--o{ METER_ITEM : "one per data subject"
    CALL_ITEM ||--|| GSI1_FEED : "projects into"

    SESSION {
        string partition_key PK "SESSION-session_id"
    }

    CALL_ITEM {
        string partition_key PK "SESSION-session_id"
        string sort_key "range key - CALL-iso8601-seq"
        string principal
        string role
        string subject
        string tool
        string call_decision "ALLOW or DENY"
        string deny_policy "cedar policy id or null"
        string content_type
        number pages
        boolean truncated
        list detector_tiers
        map entities_found "type to COUNT, never to value"
        map entities_masked "type to count"
        map entities_revealed "type to count"
        list ledger_before
        list ledger_after
        number budget
        number session_total
        list rehydrated "token strings only"
        string outcome "ok, withheld_detector, withheld_normalize, withheld_ledger, denied_call, denied_placeholder"
        map latency_ms
        string policy_version
        string invocation_id
        number expires_at "TTL"
    }

    METER_ITEM {
        string partition_key PK "SESSION-session_id"
        string sort_key "range key - METER-subject_id"
        stringset seen "entity TYPE names only - what makes the ledger safe to persist"
        number budget
        string first_ts
        string last_ts
        number expires_at "TTL"
    }

    GSI1_FEED {
        string gsi1_partition PK "FEED-yyyy-mm-dd"
        string gsi1_sort "range key - iso8601-seq"
        string projection "INCLUDE, the feed row only. Meters carry no gsi1 keys, so the index is sparse."
    }
```

**Access patterns — every one maps to a query the dashboard actually issues**

| # | Dashboard need | Query | Index |
|---|---|---|---|
| 1 | Live decision feed, newest first, across sessions | `Query(gsi1pk="FEED#<date>", ScanIndexForward=False, Limit=50, ExclusiveStartKey=cursor)` | GSI1 |
| 2 | One session: all calls **and** all meters, one round trip | `Query(pk="SESSION#<id>")` | base |
| 3 | Disclosure meter for a session's subjects | #2's page, filtered on the `METER#` prefix client-side | base |
| 4 | Ledger load at agent init | `Query(pk="SESSION#<id>", sk begins_with "METER#", ConsistentRead=True)` | base |
| 5 | Drill into one call | already in #2's page — no extra query | base |
| 6 | Atomic spend | `UpdateItem(sk="METER#<subject>", "ADD seen :t", ReturnValues=ALL_OLD)` | base |

**Caption.** One on-demand table, two item shapes, one sparse GSI that exists for exactly one query (#1, which a base-table query cannot order and a scan cannot do cheaply). The structural safety property is visible in the attribute types: `entities_*` are type→**count** maps and `seen` is a set of type **names**, so there is no field in the schema capable of carrying a value — which is what makes the leak check in doc 08 §9.6 a two-line assertion. **Omitted:** Mermaid's ER notation has no vocabulary for a single-table design, so `SESSION` is drawn as a parent entity when it is really just a partition-key prefix, and `PK` markers stand in for DynamoDB's partition/sort split. TTL is 30 days as shipped; DPDP Rule 6's one year is the production setting, not this one.

---

## 9. Failure modes

```mermaid
flowchart TD
  RULE["THE RULE - anything that would let content reach the model<br/>without a completed detector verdict fails CLOSED"] --> DEP{"which dependency failed"}
  DEP -->|"Comprehend"| C1["CLOSED - withhold the hop<br/>tier-1-only would pass NAME and PHONE while the row claimed a clean scan"]
  DEP -->|"Textract, or Pages over 1, or an unreadable format"| C2["CLOSED - withhold the attachment<br/>one card is the largest single budget spend in the system"]
  DEP -->|"Nova Pro, tier 3"| C3{"did Textract return meaningful LINE text"}
  C3 -->|"no - an Indic-only document"| C3A["CLOSED - withhold"]
  C3 -->|"yes"| C3B["OPEN - mark tier3 unavailable and proceed"]
  DEP -->|"DynamoDB ledger.load"| C4["CLOSED - 503, no turn runs<br/>a ledger that defaults to empty IS the bypass"]
  DEP -->|"DynamoDB ledger.spend"| C5["CLOSED - withhold this hop<br/>the spend must be durable before the model sees the data"]
  DEP -->|"DynamoDB audit write"| C6["OPEN - log, alarm, continue<br/>THE ONLY FAIL-OPEN IN THE SYSTEM"]
  DEP -->|"S3 session read or write"| C7["OPEN - it is the cache, not the authority"]
  DEP -->|"control plane GET /policy"| C8["CLOSED TO A KNOWN POLICY<br/>keep the current bundle, else the packaged agent.cedar"]
  DEP -->|"cedarpy Q1"| C9["CLOSED - on_error deny. A null principal also denies."]
  DEP -->|"cedarpy Q2"| C10["CLOSED - NoDecision, exception or a missing correlation_id means redact<br/>redaction is reversible, disclosure is not"]
  DEP -->|"Bedrock, the agent's own model"| C11["503 to the caller - no data risk<br/>the agent not running is not a disclosure"]
  WARN["OPEN ISSUE - every real Aadhaar card prints Latin text beside the Devanagari,<br/>so this test almost always takes the OPEN branch and the Indic name goes unscanned<br/>while the row still reads ok. See the caption."]
  C3B -.- WARN
```

**Caption.** Doc 08 §5.1 as a tree, with the one intentional fail-open marked in caps: a failed audit write cannot cause a disclosure, only an unproven one, and withholding on a logging failure converts a telemetry outage into a product outage. **The dashed node is a second live defect.** The tier-3 direction is decided by "did Textract return meaningful `LINE` text" — but the demo artifact is an Aadhaar card, which by the project's own §8 argument prints the holder's name in Latin *beside* the regional script. Textract therefore always returns meaningful LINE text, the branch is always OPEN, and the Devanagari name is released unscanned while `outcome` still reads `ok`. See §13.5. **Omitted:** exact timeouts and retry counts (doc 08 §8), and the `WITHHELD` marker text handed back to the model.

---

## 10. Threat model and trust boundaries

```mermaid
flowchart TB
  ATK["ATTACKER - can send prompts, influence what tools return,<br/>and reach both Function URLs. Out of scope - AWS credentials<br/>or code execution inside the Lambda."]

  subgraph B1["Boundary 1 - the public Function URLs, AuthType NONE"]
    T7["T7 session-id forgery<br/>ACCEPTED - authentication is Will-Not"]
    T3["T3 rewrite the policy via PUT<br/>PARTIAL, the largest accepted hole<br/>shared key, cedar parse, and the policy floor"]
    T8["T8 cost and DoS<br/>MITIGATED - size caps, chunk caps, reserved concurrency"]
  end

  subgraph B2["Boundary 2 - attacker-influenced content reaching the detector"]
    T5["T5 prompt injection aimed at the guardrail<br/>tiers 1-2 immune, tier 3 additive-only and str.find verified"]
    T6["T6 subject-id churn<br/>PARTIAL - canonicalise kills the trivial variants,<br/>session_ceiling backstops the genuine one"]
    T10["T10 placeholder-shaped tool output<br/>MITIGATED - exact map lookup, never pattern matching"]
  end

  subgraph B3["Boundary 3 - the trusted side, the only place plaintext lives"]
    T1["T1 read the Vault<br/>MITIGATED for the realistic attacker, ACCEPTED structurally<br/>production needs KMS or a separate process"]
    T4["T4 forge or replay a placeholder<br/>MITIGATED - per-invocation nonce, unknown token denies"]
  end

  subgraph B4["Boundary 4 - everything the system writes outward"]
    T2["T2 the audit row or the UI becomes the leak<br/>MITIGATED structurally - counts by type, no free-form string field"]
    T9["T9 log injection<br/>MITIGATED - json.dumps, and values never reach a log at all"]
  end

  ATK --> B1
  ATK --> B2
  B1 -.-> B3
  B2 -.-> B3
  B3 --> B4
```

**Caption.** Doc 08 §7's ten threats grouped by the boundary each one attacks, with status kept on the node so the accepted holes are as visible as the mitigated ones — T3 (an unauthenticated `PUT /policy` behind a shared secret and a substring-matched policy floor) and T7 (a caller-chosen `session_id`) are the two a judge is most likely to reach for, and both are named in the writeup before anyone else names them. **Deliberately omitted:** an attacker with AWS credentials or code execution inside the Lambda — that is a total compromise of a system with no isolation boundary inside it, and pretending otherwise would be dishonest. The dashed edges into Boundary 3 mean "can influence, cannot read".

---

## 11. Deploy pipeline

```mermaid
flowchart TD
  A["pip install -r requirements.txt<br/>--platform manylinux2014_aarch64 --only-binary all --target ./pkg"] --> B["zip -r fn.zip from pkg, then zip -g fn.zip the .py files"]
  B --> C["aws lambda create-function<br/>--architectures arm64 --runtime python3.12 --region ap-south-1<br/>plus the prebuilt strands-agents arm64 layer"]
  C --> D["aws lambda create-function-url-config --auth-type NONE"]
  D --> E["aws lambda add-permission --action lambda:InvokeFunctionUrl"]
  E --> F["aws lambda add-permission --action lambda:InvokeFunction"]
  F --> G{"curl the Function URL"}
  G -->|"200"| H["live - now repeat the whole path for the control-plane Lambda"]
  G -->|"403"| I["BOTH add-permission calls are required since Oct 2025.<br/>The console and SAM add them. The CLI does not.<br/>This 403 looks like a code bug and is not one."]
  I --> E
  H --> J["build order - deploy both hello-world URLs BEFORE any logic exists<br/>this is the highest-risk step and it is a packaging problem, not a logic one"]
```

**Caption.** Plain zip and CLI, no CDK, with the failure loop drawn explicitly because it is the one the PRD flags as costing the Ship It prize: since October 2025 a new Function URL needs **both** `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`, the console and SAM add them silently, the CLI does not, and the resulting 403 reads exactly like a code bug. `cedarpy` 4.12.0 ships the `manylinux2014_aarch64` wheel with no abi3, which is why Python is pinned to 3.12. **Omitted:** IAM role and policy creation, DynamoDB table and S3 bucket creation, CORS configuration (set on the Function URL, never emitted from the handler, or the browser sees duplicate `Access-Control-Allow-Origin` headers), and environment variables.

---

## 12. The demo timeline

```mermaid
gantt
    title Naka demo video - three minutes, judged on the video alone
    dateFormat mm:ss
    axisFormat %M:%S
    todayMarker off

    section Hook
    A scanned Aadhaar is in your ticket queue :h1, 00:00, 15s

    section The gap
    AgentCore Policy decides whether a call happens - not what comes back :g1, after h1, 20s

    section Accumulation
    Three tool calls. Name green. Phone green. The meter fills. :a1, after g1, 35s

    section The beat that wins it
    Fourth result carries an Aadhaar. Budget spent. Phone denied now. :b1, after a1, 30s

    section Rehydration
    send_summary carries the placeholder. Value substituted on the trusted side. :r1, after b1, 25s

    section Files
    One PDF exhausts the budget in a single hop. Bounding boxes if built. :f1, after r1, 20s

    section Control plane
    Edit one line of policy. Both agents change on their next hop. :c1, after f1, 20s

    section Close
    The ledger and the live URL :z1, after c1, 15s
```

**Caption.** PRD §12's beats at true scale, so the team can see that accumulation plus the reversal is 65 of the 180 seconds and everything else is 15–25. Judges see only the submitted video, so a feature described in the writeup and absent here does not count. **Omitted:** narration wording, which matters more than the pacing — say "removed from context going forward", never "the model no longer knows it", because the model read it and the imprecise version dies in one sentence. **Note the dependency:** the 1:10 beat requires the fourth tool call to *run* and be redacted; §13.2 says that as the policy is currently written it will be denied at Q1 instead, and the shot will not exist.

---

## 13. What drawing these revealed

Ten findings, ordered by how much they cost if nobody looks. The first two are the ones to fix tonight.

**13.1 — Verhoeff provenance is a direct contradiction, and one side of it says "disqualification".** PRD §8: *"Write Verhoeff fresh from the published D₅ dihedral-group tables. Do not copy the implementation that exists elsewhere on this machine — the hackathon requires new work created during the event, and copied code with mismatched provenance disqualifies the whole team."* Doc 08 §1.3: *"`verhoeff_valid` is not new code — `detection-engine/recognizers/checksums.py` in this repo already has a correct, table-driven, unit-tested Verhoeff. Copy that function and its two tables verbatim."* Doc 08 §9.1 repeats it. These cannot both be followed. Diagram 4 draws the tier without a provenance claim because there is no correct answer to draw. **Decide before writing a line of `detect.py`** — it is twenty lines either way, and only one of the two options carries a team-wide disqualification risk.

**13.2 — The ceiling `forbid` is un-scoped by action, so it denies Q1, and the money shot of the demo cannot happen.** The rule is `forbid(principal, action, resource) when { context.session has seen_count && context.session.seen_count >= context.session.budget }`. `CedarAuthorization` evaluates Q1 against the *same* `context.session` the enricher builds, which carries `seen_count` and `budget`. So the instant a subject's meter fills, the next `fetch_customer` on that subject is denied outright — the tool never runs, nothing is detected, and there is no result to redact. PRD §12's 1:10 beat ("it redacts — **and the phone number, which was allowed at call two, is denied now**") requires exactly the opposite. Three things make this worse than a typo: doc 08 §9.5 encodes the behaviour as a *passing* assertion (`seen_count = 3, budget = 3 → Deny on any action`), the rule's text is one of the two strings in `FLOOR_RULES` so it cannot be removed or edited at runtime, and the policy floor is a substring check so the fix has to change the floor too. **Fix:** scope the ceiling to the reveal actions — `forbid(principal, action in [Action::"reveal_NAME", ...], resource) when {...}` — and update `FLOOR_RULES` to match.

**13.3 — The same rule breaks the compliance exemption, and doc 08 says it doesn't.** Cedar `forbid` always beats `permit`. Doc 08 §9.5 asserts `role="compliance"` allows everything and explains that this works because "the policy must scope the forbids on `role == "analyst"`, which is exactly how §3.4 writes them". It is not: the ceiling forbid in §3.4 is scoped on `seen_count`/`budget` only, with no role condition. The compliance permit cannot override it. What actually saves the case is `budget_per_role: {"compliance": 9999}` making the condition unreachable — a configuration accident doing a policy's job. Scoping the ceiling on `role == "analyst"` fixes 13.2 and 13.3 in one edit.

**13.4 — Tier 3 cannot run on the demo's own fixture.** The headline artifact is a single-page scanned Aadhaar **PDF** (`read_attachment` → `aadhaar.pdf`). Tier 3 sends a Bedrock `ImageBlock`, whose `format` is `png | jpeg | gif | webp` — doc 08 §1.3 says so explicitly and adds "convert anything else before sending". Nothing in the package converts: §11 keeps `pypdf` and every other PDF library out ("Textract does the PDF work"), and Textract returns text and bounding boxes, not a raster. Yet doc 08 §2.2 step 16 runs tier 3 on that PDF and step 20 records `detector_tiers: ["checksum","comprehend","indic"]`. Either the demo fixture becomes a PNG or something has to rasterise. A PNG fixture is the lazy fix and costs nothing.

**13.5 — The tier-3 fail-closed test never fires on a real Aadhaar card.** Doc 08 §5.1 routes a tier-3 failure as *"CLOSED if the document is Indic-only; OPEN (degrade) if tiers 1–2 already covered it"*, distinguished by "whether Textract returned meaningful `LINE` text". But the entire §8 differentiator is that an Aadhaar card prints the holder's name in regional script **beside the English** — so Textract always returns meaningful LINE text, the test always takes the OPEN branch, and the Devanagari name is released unscanned while the audit row reads `outcome: ok`. §7 threat 5's `tier3_unverified` marker exists but does not change `outcome`, so §10.4's "unscanned egress events must be exactly zero" counter will not see it either. **Fix:** make `tier3_unverified` a non-`ok` outcome, or redact the tier-3 region when the tier was expected and unavailable.

**13.6 — The two deny outcomes may never produce an audit row.** `AuditRow.outcome` includes `denied_call` and `denied_placeholder`, and doc 08 §5.3 says a denied placeholder has "the audit row written". But `AuditHook` registers on **`AfterToolCallEvent` only**, and both denies happen at `before_tool_call`, where the tool does not run. Doc 08 §12 lists `AfterToolCallEvent`'s behaviour in this case among the things *not established by the docs reviewed*. If the event does not fire on a denied call, the visible deny path (Must #3) writes nothing to the live feed and the two outcome values are unreachable.

**Now addressed in the PRD:** §10 requires `AuditHook` to bind **both** `BeforeToolCallEvent` and `AfterToolCallEvent`, and Must #9 says so. A denial is exactly the evidence the audit trail exists to produce, so an after-only hook was omitting the most important rows. Still worth the five-minute confirmation on Saturday: deny one call, check a row lands, and check it is distinguishable from a completed one.

**13.7 — RESOLVED.** Doc 08's `build_agent` and `MODEL_ID` default now match the PRD: `apac.amazon.nova-lite-v1:0` on the loop, Nova Pro reserved for tier 3. The demo prices at ~$2.25/month on that basis. Diagram 1 still says "Bedrock Nova" generically, which remains correct since both models are in play.

**13.8 — "Short-circuiting" and "union" are the same paragraph contradicting itself.** PRD §8 opens *"Three tiers, cheapest first, short-circuiting"* and closes *"tiers UNION, they never subtract. A tier may only ever add findings."* Doc 08 implements run-all-then-merge, which is the only version compatible with the tier-3 containment argument. Strike "short-circuiting" from the PRD before it reaches the writeup — a judge who notices will read it as the detector being described by someone who did not build it.

**13.9 — RESOLVED.** PRD §11's Must list has been renumbered (it had two consecutive items numbered "6"); the ledger item is now **Must #6** and states DynamoDB authority rather than S3. The Chowki→Naka rename has reached all identifiers — `naka/`, `naka_audit`, `X-Naka-Key`, `NAKA_KEY`. Only the folder and filenames retain the old spelling, deliberately.

**13.10 — One thing drawing confirmed rather than broke.** The ordering in diagram 2 — spend durable in DynamoDB *before* `Transform` releases content, and `Rehydrator` registered third so a Q1 `Deny` skips it — is the only arrangement in which no single-step failure discloses. Every other permutation leaks on some crash. It is worth saying out loud in the writeup, because it looks arbitrary and is not.
