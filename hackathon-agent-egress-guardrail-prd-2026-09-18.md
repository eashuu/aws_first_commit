# Disclosure Budget for AI Agents — PRD v2

**For:** First Commit hackathon (WeMakeDevs × AWS, Bharat Builds Tour), submissions close Sunday 20 September 2026, 20:00 IST
**Written:** 18 September 2026 · **Revision:** v2, rebuilt around cumulative disclosure control
**Track:** Ship It (₹2,00,000 + $3,000 AWS credits). Same submission is judged for Best UI.
**Name:** **Naka** — a checkpoint. Locked. ("Chowki" was dropped: a PyPI package of that name exists in the same category, and it has four romanisations, which is disqualifying when the only distribution channel is a spoken video. Document 05 §4.4 has the full reasoning.)

---

## 1. The idea

Every AI-agent guardrail on the market is **stateless per call**. Each tool result is scanned in isolation, each decision made with no memory of the last. So: call 1 returns a name, call 2 returns a phone number, call 3 returns the last four digits of an Aadhaar. Each passes policy — none of them *is* an Aadhaar. Together they re-identify a person. Nobody catches it, because nobody is counting across calls.

This builds the thing that counts.

Every session carries a **disclosure budget** — what it may cumulatively learn about any one data subject. Each tool call spends from it. Cedar is asked two questions per call: *may this call happen*, and *may this principal learn this field about this subject given what it already knows*. When the budget is spent, further identifying fields are redacted even though each would individually pass. Redaction is reversible, so the task still completes.

Three layers, one sentence: **one policy, enforced at the tool boundary, over any content type, with cumulative disclosure tracked across the whole session.**

**Why this is new with agents rather than inherited from older systems:** a human analyst runs three queries. An agent runs three hundred, autonomously, unsupervised. Aggregation risk scales with call volume, and agents are the first system where call volume is unbounded and nobody is watching. Per-call redaction is necessary and insufficient.

---

## 2. What the research changed

Two research passes ran before this revision. Both returned corrections that alter the build. They are recorded here rather than quietly absorbed.

### 2.1 The core design is supported — verified, not assumed

The whole idea depends on Cedar being able to read accumulated state. It can.

- `CedarAuthorization(context_enricher=...)` receives one dict `{'tool_name', 'tool_input', 'invocation_state'}` and returns a dict **merged into `context.session`**. Arbitrary computed state reaches policy. This was the make-or-break question.
- Cedar `when` clauses support `.contains()`, `.containsAll()`, `.containsAny()`, `.isEmpty()`, `has`, `in`. Return a Python **list** and it becomes a Cedar Set.
- **Cedar has no set cardinality operator** — no `.size()`, no `.count()`, and sets are not comparable with `<`/`>`. Counts must be computed in Python and passed as a long. This is a real constraint on how the budget is expressed.
- `agent.state` is JSON-serializable key-value storage. `call_count` already lives there under the key `"cedar-authorization"`, so the ledger sits alongside it legitimately.
- Handlers run in **registration order**, and a `Deny` skips the rest. List the ledger handler first, `CedarAuthorization` second.
- `CedarAuthorization` implements **only** `before_tool_call`. The after-tool path is entirely ours.
- For the second question, Strands exposes no public "authorize now" method — call `cedarpy.is_authorized_batch` directly. It takes a list of requests against shared policies, returns results in order with optional `correlation_id`, and is roughly 10× faster than looping. Purpose-built for asking one question per detected entity type.
- **Omit the `schema` argument.** With a schema present, custom `context.session` attributes may fail validation.
- Gotcha the docs do not resolve: the enricher's `ctx["invocation_state"]` is not documented as the same object the handler mutated. Do not rely on it — have the enricher read the handler instance directly (`context_enricher=lambda ctx: ledger.snapshot()`).
- **`Confirm` is legal only at `before_tool_call`.** `after_tool_call` permits only `Proceed` and `Transform`. There is therefore **no way to interrupt for human approval on a field-level redaction decision** — the approval-overlay pattern does not transfer to the after path. `Guide(feedback=...)` at `before_tool_call` is the substitute.
- **Python Lambda has no native response streaming** (managed streaming is Node.js only). Any SSE live-feed design is dead on this stack — poll at 1s.
- Cedar **annotations** (`@advice("...")`, `@shadow_mode`) are arbitrary, evaluation-neutral and readable programmatically, and `cedarpy` returns determining policy IDs in its diagnostics. Self-explaining denials and per-policy monitor mode are both cheap as a result — this is what makes `deny_policy` in §10 populable.

### 2.2 Infrastructure corrections that change the stack

| Assumption | Reality | Consequence |
|---|---|---|
| Textract sync handles PDFs | **Sync is 1 page for PDF/TIFF.** ≥2 pages forces async, S3-only, with polling | Demo on single-page documents — an Aadhaar card, a PAN card, a payslip *are* one page |
| Textract reads Indian documents | **Textract OCR is Latin-script only.** It will not OCR Devanagari or Tamil | The Indic tier cannot go through Textract. Use a multimodal Bedrock model on the image directly |
| Claude on Bedrock in Mumbai | **No in-region and no APAC geo profile — `global.*` only**, which AWS states explicitly "can route requests outside the source Region" | Using Claude would contradict the project's own premise. **Use Nova via `apac.amazon.nova-*-v1:0`**, which stays in APAC |
| AgentCore Runtime could host this | `InvokeAgentRuntime` is **SigV4 or JWT only — no public URL**, and no CloudFormation/CDK support | Ruled out. Ship It requires a URL a judge can open |
| API Gateway is the normal front door | **HTTP API caps at 30 seconds.** An agent with three tool calls plus document extraction will exceed it | Lambda **Function URL** — 15-minute ceiling, built-in HTTPS, `AuthType=NONE` |
| CDK is the deployment path | The official Strands guide uses CDK, but it costs 30–60 minutes of TypeScript that gets thrown away | Plain zip + AWS CLI. Under 10 minutes, no `cdk bootstrap` IAM fight |

Two more worth carrying into the build:

- **Comprehend bills a 3-unit (300-character) minimum per request.** Scanning many small strings costs roughly 10× what a naive model predicts. Batch tool output into one call per hop, never one call per field.
- **`cedarpy` is not AWS-supported** ("not officially supported by AWS or the Cedar Policy team"). v4.12.0 ships manylinux2014 wheels for x86_64 and aarch64, Python 3.10–3.14, so the zip layer works — but say "community binding" in the writeup, not "AWS library."

### 2.3 The novelty claim, corrected

An earlier draft claimed nobody governs agent tool traffic. That is false and would fail in front of an AWS audience.

[Amazon Bedrock AgentCore Policy](https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/) went GA on 3 March 2026 — Cedar, default-deny, principal from JWT, action from the MCP tool call, every decision logged to CloudWatch. It is available in Mumbai. [AgentCore Gateway RESPONSE interceptors](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/) give a Lambda read/write on tool payloads. [Pipelock](https://github.com/luckyPipewrench/pipelock) (884★) does placeholder redaction with signed receipts. [Bedrock Data's Agent DLP](https://bedrockdata.ai/news/bedrock-data-launches-agent-dlp-runtime-data-loss-prevention-built-for-ai-agents) shipped commercially on 30 July 2026. [LangChain 1.0 `PIIMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/pii) exists — but an earlier draft overstated it. Verified: it detects only email, credit card, IP, MAC address and URL; `apply_to_tool_results` **defaults to `False`**; there is no restore; and it does not touch tool *arguments* at all. Do not cite it as equivalent prior art.

The per-call guardrail is a solved, crowded category.

**This section is superseded by `chowki-hackathon/01-competitive-landscape.md`. Read that before writing any copy.** Summarised here because the correction is load-bearing:

**An earlier draft claimed "none of them carry state across calls." That is false six different ways**, and one of them is an AWS release from six weeks ago that this audience is likely to know:

1. **Dogwood** (AWS, 6 August 2026) — an open-source policy language that embeds Cedar and adds temporal operators (`formerly within`, `previous within`, `since within`) plus `count` and `sum` aggregations over an agent's event history, including fields bound out of tool *responses*. Wired into AgentCore Policy, GA in Mumbai. One of AWS's own worked examples is a cumulative budget cap per trajectory. Its "information providers" are a near-exact analogue of the `context_enricher` this design rests on.
2. **CAMP** (arXiv, 16 April 2026) formalises "Cumulative PII Exposure" — session-level PII registry, quasi-identifier co-occurrence graph, threshold, retroactive masking of history. The abstract is this pitch, six months early.
3. **OCELOT** (arXiv, 10 June 2026) budgets how much an adversary's belief about a secret may improve across a trajectory, explicitly covering tool calls, on a tamper-evident ledger.
4. **Noisegate** (Apache-2.0) keeps "an exact ledger of cumulative disclosure per identity" in front of MCP.
5. **Microsoft Purview** accumulates exfiltration signal over 30 days and feeds it into DLP enforcement through Adaptive Protection — shipping, at enterprise scale.
6. **Pipelock** carries a per-session threat score and taint escalation across task boundaries, and already emits numbered typed placeholders — so §6.2's placeholder design is prior art too.

**What survives, and it is narrow:** nobody accumulates **per data subject**, and nobody turns that accumulation into a **redaction** decision expressed in the same policy language as the allow/deny. Purview accumulates about the *actor*. Dogwood accumulates *declared* event attributes — and **nothing in AgentCore populates those attributes with detected entity types attributed to a person**. CAMP and OCELOT accumulate correctly but are papers: no policy engine, no authorization model, no tool-boundary implementation. Noisegate budgets ε per querying identity and answers with noise, not redaction.

> **The line to say:** "subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision."
> Say "cumulative state" and you lose the room.

**The commercial field was then swept separately — 16 vendors plus an India scan — and the gap holds there.** Prompt Security, Zenity, WitnessAI, Lasso, Noma, Aim/Cato, Palo Alto Prisma AIRS, Cisco AI Defense, HiddenLayer, F5/CalypsoAI, Nightfall, Strac, Bedrock Data, Netskope, Zscaler, Pangea/CrowdStrike, Snyk/Invariant. **None publicly documents a cumulative disclosure budget, a running total of what has been disclosed, or a re-identification score that rises through a session.** Six carry cross-call state, but it is *attack-sequence* state — Zenity's "stateful threat engine" (multi-step injection, gradual exfiltration), Snyk/Invariant's flow `->` operator and Toxic Flows. Those answer "did A then B happen in this order?", not "how much has been disclosed, and does this next field cross the line?" Four state per-call statelessness outright.

Also worth knowing: **nobody in that set both redacts tool output and can restore it.** Strac, Pangea, Protecto and Seclore have reversible redaction but not on tool outputs; Palo Alto, Lasso, Noma, Nightfall and Bedrock Data redact tool output with no documented restore.

**The one genuine near-hit is [MaskFlow](https://github.com/maskflow/maskflow)** — MIT, "Made in India", zero stars, ~109 commits. It combines Indian identifiers (Aadhaar with Verhoeff, PAN, GSTIN, IFSC, UPI, ABHA, Voter ID), reversible `unmask()`, an MCP proxy that masks outbound tool arguments and unmasks results on return, and session-consistent placeholders in Redis. That is close to this design. Cite it — an unproven solo project is validation of the idea, and pretending not to have found it is the version that costs credibility.

**The strongest honest framing, and it is better than the false claim was.** Academia has formalised the concept and shipped no implementation. AWS shipped a policy language in which a disclosure budget is already expressible — but the events are empty, because nothing fills them with detected PII attributed to a person. Sixteen commercial vendors do attack-sequence state, not disclosure accumulation. **The concept is published, the language exists, the detection exists — nobody has connected them.** That is the contribution, and it is defensible. Volunteer Dogwood before a judge raises it; positioning the ledger as a Dogwood *information provider* — composable, not competing — is the highest-leverage thirty seconds available.

Vocabulary: *agent firewall*, *agentic DLP*, *MCP guardrails*, *tool-level policy enforcement*. On OWASP, cite correctly — "T2 Tool Misuse" belongs to the older *Agentic AI: Threats and Mitigations* (T1–T15), not the 2026 list. The 2026 OWASP Top 10 for Agentic Applications numbers ASI01–ASI10, and the right anchors are **ASI02 Tool Misuse and Exploitation** and ASI03. Stronger still, and true: **the 2026 list has no entry for cumulative sensitive-information disclosure.** "This failure mode doesn't have an OWASP number yet" is a better line than any number.

---

## 3. Problem

**User:** a small Indian team shipping an agent over a customer database, support desk or document store. No security engineer, no compliance budget.

**The mechanism of harm.** You approve a toolset, not individual calls. The agent decides what to call and when. Each result is scanned, each looks clean, and after two hundred calls the model context holds a complete profile of a real person that no single decision would ever have permitted. The controls that exist cannot see this, because each was designed to answer a question about one payload.

**Second mechanism, same root:** files. A tool returns a PDF. Comprehend takes text, so a base64 attachment passes straight through and the audit row reads "0 entities found." The guardrail is blind to binaries, and one scanned document can carry name, address, Aadhaar and photograph in a single call — the largest possible budget spend, entirely invisible.

**What the user cannot do today:** state "an analyst may query customers, but may never accumulate enough about any one customer to identify them" and hold a log that proves it held.

---

## 4. Positioning

Three claims, each survivable:

1. **Subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision.** Cross-call budgets exist and AWS ships one — but they accumulate the *actor's behaviour* or *declared event attributes*, never *what has been learned about one person*, and none of them turns the accumulation into a redaction expressed in the same policy language as the allow/deny. One counts actions; this counts knowledge about an individual. **Positioning line: least privilege for data, with memory.**
2. **Redaction is a policy decision, in the same language.** AWS gives Cedar for allow/deny and leaves redaction to a hand-written Lambda. Pipelock redacts from YAML patterns, not identity-aware policy. LangChain redacts with no authorization at all. Here both questions are Cedar, same principal, one audit record.
3. **The Indic-script gap — not "Indian identifiers", which is not a differentiator.** Presidio ships `IN_AADHAAR` *with checksum validation*, plus `IN_PAN`, `IN_VOTER`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION` and `IN_GSTIN`, free, and it is inherited by LiteLLM, TrueFoundry, LlamaIndex and NeMo. Claiming Indian identifiers as novel is falsifiable in one link. **The real gap is script:** Comprehend does English and Spanish, Textract OCRs Latin script only — so the regional-script name printed beside the English on every Indian identity document is invisible to the whole stack. That is the claim.

   Residency belongs here too: the model is Nova on the APAC inference profile specifically because Claude in Mumbai is available only through a `global.*` profile that AWS documents as able to route outside the source region.

**Say "stays in APAC", never "stays in India."** The destination regions inside an APAC geo profile are not published, so "in India" is a claim that cannot be supported. Run `get-inference-profile` to enumerate the actual regions — the same output also determines the IAM `Resource` list, since AWS requires the foundation model to be specified in each region associated with the profile.

That third point is worth its own line in the video. It shows the docs were read.

**Do not write:** "first of its kind", "nobody governs agent traffic", "existing DLP only watches browsers."

---

## 5. Architecture

```
CONTROL PLANE                              DATA PLANE
Lambda + Function URL                      Lambda + Function URL
  GET  /policy   → agent.cedar (ETag)        Strands Agent
  GET  /ledger   → dashboard reads             interventions = [ DisclosureGuard,    ← ours, first
  GET  /         → single-page UI                              CedarAuthorization,  ← vended
                                                               Rehydrator ]         ← ours, last
                                               hooks          = [ AuditHook ]
         ▲                     ▲               tools          = [ fetch_customer,
         │ fetch + cache       │ direct write                     read_attachment,
         │                     │                                  send_summary ]
         └─────────────────────┴───────────    model          = apac.amazon.nova-lite-v1:0
                                               session        = S3SessionManager (cache)
                                               ledger         = DynamoDB (authority)
```

No `POST /decisions`. Both Lambdas can already write DynamoDB; an HTTP hop to insert a row adds ~40 ms and a failure mode for nothing.

Per tool call, in order:

```
before_tool_call
  1. DisclosureGuard      → snapshot ledger, expose via context_enricher
  2. CedarAuthorization   → Q1: may this call happen?          Deny short-circuits
  3. Rehydrator           → substitute placeholders in args, itself a Cedar question (§11.2)

  <tool executes>

after_tool_call
  4. normalize()          → bytes/PDF/image → markdown
  5. detect()             → checksum tier → Comprehend tier → Indic tier
  6. attribute()          → map entities to data subjects
  7. is_authorized_batch  → Q2: one request per (subject, field), carrying the ledger
  8. Transform            → redact denied fields to numbered placeholders
  9. ledger.spend()       → update agent.state; AuditHook writes the row
```

**Why the control plane is load-bearing, not decoration.** The ledger must outlive one Lambda invocation and span multiple agents. Policy authored centrally and fetched with an ETag is what turns a library into something an organisation can operate — and it produces the best fifteen seconds in the demo: edit one line on the server, two separate agents change behaviour on their next call, both decisions land in one audit view.

**Three storage roles, each justified:**

| Store | Holds | Why this one |
|---|---|---|
| `S3SessionManager` | Agent session state, including the ledger | Built in, zero code, restores on `session_id`, and durable. **Correction: Strands session managers are not thread-safe and take no distributed lock — that applies to the S3 one too, not just `FileSessionManager`.** Chosen for durability, not atomicity. Last write wins; say so, and put the authoritative counter in DynamoDB (§11.2) |
| DynamoDB | Audit rows, cross-session dashboard view | Queryable for the UI; the session manager is not |
| Lambda package | `agent.cedar` fallback | Control plane unreachable must fail closed to a known policy, not to no policy |

`AgentCoreMemorySessionManager` was considered and rejected: it needs a provisioned Memory resource and is built for conversational recall, not a precise structured ledger. Not worth it for a one-day build.

---

## 6. The disclosure budget

### 6.1 Cedar, with the cardinality constraint handled

Cedar cannot count a set, so counts are computed in Python and injected as longs. Sets go in as lists.

```python
context_enricher=lambda ctx: ledger.snapshot()
# → {"role": "analyst",
#    "subject": "cust_8814",
#    "seen": ["NAME", "PHONE"],        # Cedar Set
#    "seen_count": 2,                  # Cedar Long — Cedar cannot compute this
#    "budget": 3}
```

**Q1 — may the call happen:**

```cedar
permit(principal, action == Action::"fetch_customer", resource)
  when { context.session has role && context.session.role == "analyst" };
```

**Q2 — may this principal learn this field about this subject, given what it already knows:**

```cedar
// an analyst may see a phone number, but not once it already holds
// BOTH a name and an address — two quasi-identifiers plus a phone is a profile.
// containsAll, not containsAny: with containsAny(["NAME", ...]) this fires as soon
// as a name is seen, which denies the phone at call 2 and contradicts the §12 beat
// sheet, where the phone is ALLOWED at call 2 and denied at call 4. The whole demo
// turns on that ordering — validate any policy edit against the beat sheet.
forbid(principal, action == Action::"reveal_PHONE", resource)
  when { context.session.role == "analyst"
      && context.session.seen.containsAll(["NAME", "ADDRESS"]) };

// Aadhaar never, for analysts — regardless of the ledger
forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)
  when { context.session.role == "analyst" };

// hard ceiling: three identifying fields about one subject per session.
// MUST be scoped to the reveal actions. An unbound `action` also matches Q1's
// tool-call actions, so a full budget would deny the CALL — the tool never runs,
// no payload comes back, and there is nothing left to redact. That kills the
// demo's central beat and inverts the design from a redaction control into a
// kill switch. Found by drawing the flow; it reads as correct until you do.
forbid(principal,
       action in [Action::"reveal_NAME",
                  Action::"reveal_PHONE",
                  Action::"reveal_ADDRESS",
                  Action::"reveal_IN_AADHAAR",
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER"],
       resource)
  when { context.session has seen_count && context.session.seen_count >= context.session.budget };

// compliance role is exempt
permit(principal, action, resource)
  when { context.session.role == "compliance" };
```

**Cedar `forbid` always wins over `permit`**, so the compliance exemption above does *not* override the Aadhaar `forbid` or the ceiling — it only grants where nothing forbids. If compliance must genuinely see everything, the role check belongs inside each `forbid`'s condition (`&& context.session.role != "compliance"`), not in a separate `permit`. Decide which you mean before recording; the demo's role-switch beat depends on it.

One `is_authorized_batch` call per hop, one request per `(subject, field)` pair, `correlation_id` carrying the pair so results map back.

### 6.2 Redaction and rehydration

Denied fields become numbered placeholders — `[IN_AADHAAR_1]`, `[PHONE_2]` — with the placeholder-to-value map held per invocation on the trusted side, never in `agent.state` and never in an audit row. When a later tool call carries a placeholder in its arguments and that call is itself authorized, the real value is substituted back at `before_tool_call`, before the tool runs.

The agent completes a task that genuinely needs the value without the value ever entering model context. That is the demo.

**Lifetime mismatch, and it must fail closed.** The ledger persists across HTTP requests through `S3SessionManager`; the plaintext map does not — it is per-invocation. So a placeholder can survive into a later request whose map no longer holds it. An unknown placeholder must **fail closed**: leave it as a placeholder, log the miss, never guess. Decide explicitly whether numbering is stable per value across a session or per invocation, and say which in the writeup — stable numbering is friendlier to the agent and leaks slightly more.

**Never put the map at module scope.** A warm Lambda container persists module-level state into the next invocation, which may belong to a different caller. Keep it function-local. And wrap the rehydration path's exception handling deliberately — an unhandled traceback renders local variables into CloudWatch Logs, which would write the plaintext straight into the log the design exists to keep clean.

### 6.3 Grounding the threshold

An arbitrary number looks like a gimmick, and the obvious citation is the wrong one. **HIPAA Safe Harbor cannot justify a budget of 3** — it says remove all 18 identifiers, which is a rule about completeness, not a threshold. Use it only for *which fields count as identifying*.

The number comes from the re-identification literature: Sweeney found 87% of the US population uniquely identified by {gender, ZIP, date of birth} on 1990 census data; Golle's replication on 2000 census data revised it down to 63%. Both are **three quasi-identifiers**. Citing the downward revision rather than the famous number reads as rigour rather than cherry-picking.

Default budget: 3 identifying fields per subject per session, configurable in policy.

State plainly in the writeup that this is a **quasi-identifier accumulator, not differential privacy.** Do not borrow the DP vocabulary — it invites a question that cannot be answered.

---

## 7. AWS setup

All of it in **ap-south-1 (Mumbai)**, which is both the right latency and the right story.

| Role | Service | Decision notes |
|---|---|---|
| Compute | **Lambda, arm64, Python 3.12** | Prebuilt layer `arn:aws:lambda:ap-south-1:856699698935:layer:strands-agents-py3.12-arm64:<v>` |
| Public URL | **Function URL, `AuthType=NONE`** | 15-min ceiling. API Gateway HTTP API caps at 30s and the agent loop will exceed it |
| Model | **`apac.amazon.nova-lite-v1:0`** for the agent loop, **`apac.amazon.nova-pro-v1:0`** only for the Tier 3 image call | Lite is ~13× cheaper ($0.071/M in vs $0.94/M) and the loop does not need Pro. Both stay in APAC; Claude in Mumbai is `global.*` only. Nova Pro has **no in-region option** in ap-south-1 either — `apac.` is the only path, not a preference |
| Text PII | **Comprehend `DetectPiiEntities`** | Offsets + confidence. 100 KB limit. Batch per hop — 300-char minimum per request |
| Document text | **Textract `DetectDocumentText`** | Sync, inline `Bytes`, 10 MB, **1 page for PDF**. Per-word `Geometry.BoundingBox` for drawing redaction boxes |
| Indic script | **Nova Pro, multimodal, on the image** | Textract is Latin-script only. Return matched substrings, locate with `str.find()` — never trust LLM offsets |
| Ledger/session | **S3** via `S3SessionManager` | Built in. No DynamoDB session manager exists |
| Audit + dashboard | **DynamoDB**, on-demand | One item per tool call |
| Policy eval | **`cedarpy`** embedded | Not Amazon Verified Permissions — AVP adds a policy store, an IAM role and a round trip in the hot path, and is not what `CedarAuthorization` uses. Name AVP as the production story |

**Deploy — plain zip, not CDK:**

```bash
pip install -r requirements.txt \
  --platform manylinux2014_aarch64 --only-binary=:all: --target ./pkg
cd pkg && zip -r ../fn.zip . && cd .. && zip -g fn.zip *.py
aws lambda create-function --architectures arm64 --runtime python3.12 --region ap-south-1 ...
aws lambda create-function-url-config --auth-type NONE --region ap-south-1 ...

# BOTH of these, or the URL returns 403. The console and SAM add them; the CLI does not.
aws lambda add-permission --action lambda:InvokeFunctionUrl \
  --principal '*' --function-url-auth-type NONE --statement-id url-invoke ...
aws lambda add-permission --action lambda:InvokeFunction \
  --principal '*' --function-url-auth-type NONE --statement-id fn-invoke ...
```

**The two `add-permission` calls are not optional.** Since October 2025 a new function URL requires both `lambda:InvokeFunctionUrl` *and* `lambda:InvokeFunction`. Creating the URL without them yields a 403 that looks like a code problem and is not. This is §11.1 step 1 — the highest-risk step in the build, failing for a reason that has nothing to do with the project.

`cedarpy` 4.12.0 ships the `manylinux2014_aarch64` wheel, so `--only-binary=:all:` resolves. No abi3 — pin Python 3.12.

**Cost at demo scale** (500 invocations × 3 tool calls, 50 document pages), priced at full ap-south-1 rates with no free tier assumed: **~$2.25/month** on Nova Lite, **~$9.20/month** if Nova Pro is used throughout. Idle after the event is effectively **$0.00**. The $200 in signup credits covers roughly seven years at the low figure.

Traps, all verified: **Bedrock has no free tier at all**; **DynamoDB on-demand request units have no free allowance** (the 25 RCU/WCU free tier is provisioned-mode only — the 25 GB of storage is free in both); CloudWatch Logs is **$0.67/GB** in Mumbai, ~34% above us-east-1, and **retention defaults to never expire**; Textract sync is **5 TPS in Mumbai** versus 25 in us-east-1; new accounts get **reduced Lambda concurrency and memory quotas**; Bedrock Data Automation has no free tier. Comprehend's 300-character minimum per request is confirmed verbatim — batching per hop rather than per field is a 5× difference on identical bytes.

### 7.1 Account setup — decide before creating anything

**Choose the Paid plan, not the Free plan.** Since 15 July 2025 both plans grant the same $100 on signup plus up to $100 earned, expiring twelve months from account creation. The Free plan differs in three ways that each break this project:

1. Free-plan accounts are **not eligible for promotional credits** — which means the **$3,000 prize credits could not be redeemed**, nor any credits the organisers grant.
2. Free plan gets Always-Free offers **only, no short-term trials** — and Comprehend's 12-month and Textract's 3-month allowances are trials.
3. Free plan **auto-closes the account at six months**, taking the deployed demo URL with it.

**AWS Builder Center grants nothing runnable.** An AWS Builder ID explicitly "can't obtain AWS IAM credentials to access the AWS Management Console, AWS CLI, AWS SDKs, or AWS Toolkit." It is identity, learning, SheerID verification and a credit *redemption* page. Student Rewards pays $10 at seven badges and $20 more at fourteen — not a build budget. The hackathon requires the profile for eligibility, not for compute.

**Ask the organisers for credits tonight.** The hackathon rules say verbatim that additional credits can be requested from them. Nothing else arrives inside 48 hours — AWS Educate advertises no credits currently and AWS Academy is institution-gated.

**Rejected, with reasons:** AgentCore Runtime (no public URL); App Runner (bills provisioned memory 24/7, and each deploy is a 5–10 minute ECR build — one bad Dockerfile eats a quarter of the remaining time); Fargate (hours of VPC/ALB setup); Bedrock Data Automation (simpler single call and it returns markdown plus bounding boxes, but $0.010/page with no free tier and a cross-region APAC hop — revisit only if multi-page PDFs become a Must).

---

## 8. Detection

Three tiers, cheapest first. **Run all of them and merge — never short-circuit.** An earlier draft said "short-circuiting" two paragraphs above "tiers union, they never subtract", which is self-contradictory: short-circuiting means a cheap tier's hit suppresses a later tier's, and the containment argument for tier 3 depends on every tier's findings surviving. Run-all-then-merge is the only version that holds.

**Tier 1 — local checksum.** Aadhaar is 12 digits with a **Verhoeff** check digit. PAN is `[A-Z]{5}[0-9]{4}[A-Z]` with the fourth character encoding holder type. Both verify in-process: zero latency, zero cost, and the checksum removes the false positives Comprehend cannot avoid on a bare 12-digit string.

Write Verhoeff fresh from the published D₅ dihedral-group tables. **Do not copy the implementation that exists elsewhere on this machine** — the hackathon requires new work created during the event, and copied code with mismatched provenance disqualifies the whole team. It is twenty lines. The assertion that distinguishes a correct Verhoeff from a plausible wrong one is **adjacent-pair transposition**: a mislabelled Luhn passes a single-digit-change test but fails `09`↔`90`.

One correction worth carrying: a checksum is robust against false positives but **fragile against OCR errors** — a real Aadhaar with one misread digit fails validation and would be silently missed. On OCR-sourced text, flag 12-digit sequences that *fail* Verhoeff too, at lower confidence, tagged as OCR-derived. Checksum as a confidence signal, not a gate.

**Tier 2 — Comprehend.** Everything else. `LanguageCode="en"` (there is no `en-IN` parameter value, though the AI Service Card lists en-IN among trained locales). Ship the confidence threshold at **0.5** and expose it — the Service Card explicitly advises lowering it for redaction, since a false negative costs far more than a false positive.

**Tier 3 — Indic script, multimodal.** Comprehend does English and Spanish only. An Aadhaar card prints the holder's name in a regional script beside the English, so every PII tool on the market is blind to half of every Indian identity document. Send the image to Nova Pro, ask for matched substrings, locate them with `str.find()`. No offsets from the model, ever.

**Composition rule — tiers UNION, they never subtract.** Tier 3 reads attacker-supplied content with an instruction-following model, so a document can contain text telling the detector to report nothing. A tier may only ever *add* findings; no tier can clear another tier's. Combined with the `str.find()` check in §11.2, this bounds what a malicious document can do to the detector: it can cause a spurious redaction, never a silent pass. Confirm the code composes this way before claiming detection coverage.

Honest accuracy note for the writeup: the Comprehend AI Service Card is dated November 2023 and publishes no per-entity accuracy table. The only stated figures are name F1 ≥0.87, phone ≥0.88, address ≥0.91 on internal datasets — **nothing for Aadhaar or PAN**. AWS also names degraded performance on OCR and transcribed text. Say so rather than implying precision that was never published.

---

## 9. File normalization

Everything becomes markdown before detection. Not a compromise — it is what makes the detector uniform: text, PDF, scan and spreadsheet all arrive as one type, and §8 needs no per-format branching.

```
normalize(payload) → markdown
  text/json      → passthrough
  PDF, 1 page    → Textract DetectDocumentText (inline Bytes)
  image          → Textract (Latin) or Nova Pro multimodal (Indic)
  xlsx/csv       → markdown table
```

Three things that bite, all real engineering rather than objections:

1. **Embedded objects are the hole.** A text-layer PDF whose Aadhaar is a scanned image inside it. Text-layer-only extraction passes the highest-risk content through invisibly while the audit row says "clean." Extraction must recurse into embedded images or the guarantee is false. This is the one a judge could puncture.
2. **Volume, not format.** A spreadsheet column of 5,000 Aadhaar numbers is still text, but it blows the 100 KB Comprehend limit and turns one hop into a chunking loop.
3. **Multi-page needs async.** Sync Textract is one page. Demo on single-page documents — an Aadhaar card, a PAN card, a payslip are one page each. Do not build S3 polling.

Freebie worth claiming: PDF author, DOCX `docProps` and image EXIF GPS are **discarded** by markdown conversion rather than scanned. That is a genuine safety property — just do not phrase it as "we scanned it."

---

## 10. Audit record

One DynamoDB item per tool call, written from a Strands **hook** rather than an intervention so it never blocks the decision path.

**Bind `BeforeToolCallEvent` as well as `AfterToolCallEvent`.** A call denied at Q1 short-circuits and never reaches the after path, so an after-only hook silently omits every denial — precisely the evidence the audit trail exists to produce. Bind both and record which path wrote the row, so a denied call and a completed one are distinguishable.

Keys revised — a session spans several Lambda invocations, so keying on `invocation_id` makes the dashboard's primary view ("one session, all its calls and meters") unqueryable without a scan.

```
pk                SESSION#<session_id>
sk                CALL#<ts>#<seq>   |   METER#<subject>
principal         "User::alice@acme.com"
role              "analyst"
subject           "cust_8814"
tool              "fetch_customer"
call_decision     ALLOW | DENY
deny_policy       <cedar policy id or null>        // Q1 only
field_decisions   [ { field, decision, policy_id } ]  // Q2, one per detected field
content_type      "application/pdf"
detector_tiers    ["checksum", "comprehend"]
entities_found    { IN_AADHAAR: 1, NAME: 1, PHONE: 1 }
entities_masked   { IN_AADHAAR: 1 }
entities_revealed { NAME: 1, PHONE: 1 }
ledger_before     ["NAME"]
ledger_after      ["NAME", "PHONE"]
budget            3
rehydrated        ["IN_AADHAAR_1"]
latency_ms        { normalize: n, detect: n, cedar: n, total: n }
ts                ISO8601
```

No raw values. No placeholder-to-value map. The row proves what was withheld without becoming the leak it prevents.

Two gaps worth closing cheaply, both cited in §13's compliance framing: Rule 6 asks for logs **retained one year**, which is a DynamoDB TTL attribute set to `ts + 365d` and one line of table config; and the rows are **unsigned**, so the audit trail is tamper-evident only to the extent DynamoDB itself is. Claiming "audit trail" is fine. Claiming "tamper-proof evidence" is not, unless a hash chain gets built — and it should not, for a two-day build.

---

## 11. Scope

Roughly two working days: this evening, Saturday (reduced if attending the Bangalore venue day), Sunday until 20:00 IST.

**Must**

1. Both Lambdas deployed with working Function URLs — **before any logic exists**
2. Strands agent, three tools, one returning a single-page PDF with a seeded Aadhaar
3. `CedarAuthorization` for Q1 with a visible deny path
4. `DisclosureGuard`: snapshot via `context_enricher`, `is_authorized_batch` for Q2, numbered placeholders
5. **Rehydration bound to an authorized destination** — see §11.2. Not optional; without it the guardrail is an exfiltration primitive
6. Ledger authoritative in DynamoDB (atomic `ADD` on a String Set), cached via `S3SessionManager`, surviving across HTTP requests
7. Detection tiers 1 and 2 (checksum, Comprehend)
8. `normalize()` for text and single-page PDF
9. `AuditHook` on **both** `BeforeToolCallEvent` and `AfterToolCallEvent` → DynamoDB
10. Single-page UI: live decision feed, before/after diff, **disclosure meter per subject**
11. Public repo, ≤3-minute YouTube video, writeup

**Should**

11. Tier 3 Indic detection on an image
12. Policy hot-reload demonstrated live from the control plane. **The edit must ADD a `forbid`, never narrow a `permit`** — a narrowed permit yields a default-deny with no determining policy id, so the UI has nothing to render and the beat lands as an unexplained blank
13. Textract bounding boxes drawn on the rendered page

**Will not** — Amazon Verified Permissions · AgentCore Runtime · OpenSearch · streaming · authentication · multi-tenancy · MCP server mode · signed receipts · async multi-page Textract · custom detection models

### 11.2 Two holes in the design, not scope cuts

Both were found reviewing §6.2 and §8 adversarially. Neither is a feature to defer; each is a defect in the thesis if left.

**Rehydration is an exfiltration primitive.** As specced, any authorized tool call carrying `[IN_AADHAAR_1]` in its arguments gets the real value substituted before execution. So a compromised or injected agent emits the placeholder into a call to an attacker-controlled destination and the guardrail *helpfully* restores the plaintext. The guardrail becomes the exfiltration channel. **Fix:** rehydration is itself a Cedar question — `Action::"rehydrate_IN_AADHAAR"` against the destination tool as resource, not a blanket substitution. Roughly 1.5 hours. Promoted to Must (§11 item 5). It also makes a good demo beat: the agent tries to send the Aadhaar somewhere it should not, and the placeholder stays a placeholder.

**Tier 3 puts a model in the enforcement path.** The Indic detector asks Nova to return matched substrings. A model that hallucinates a substring causes a redaction of text that was never there; worse, one that omits a match causes a silent miss. **Fix:** discard any returned substring not literally present in the source via `str.find()`. 15 minutes. Never trust a generative model's output as an authority inside a security control — only as a candidate to verify.

**The ledger can lose updates. Move its authority to DynamoDB.** The Strands session docs state that the built-in session managers take no distributed lock and the single-instance guard is in-process — so `S3SessionManager` is last-writer-wins, exactly like the file one, and can silently drop a ledger update. **Fix:** DynamoDB `UpdateItem … ADD seen :types` on a String Set is a server-side atomic set-union that cannot lose one, and `ReturnValues=ALL_OLD` hands back `ledger_before` in the same round trip, race-free. `agent.state` via S3 stays as the cache — Must #5 is still satisfied and still demoable, the state copy is real. ~1 hour.

**Three bypasses to name rather than let a judge find.** (a) Nothing stops a caller starting a fresh session for a fresh budget. (b) The subject id comes from the tool's own arguments, so a fresh subject id per call means a fresh budget every call — canonicalise (NFKC, strip, casefold) to kill the trivial variants; the genuine version needs value-level identity resolution and is out of scope. (c) Both are backstopped by a `session_ceiling` (default 25) across all subjects. State the limitation openly; it is a fine concession for a two-day build, and a terrible discovery.

**The obvious diff implementation turns the dashboard into the leak.** Showing "what the tool returned" beside "what reached the model" naturally means shipping the original text to the browser. Do not. Reconstruct the left side from `entities_found` as type-and-shape tokens — `‹IN_AADHAAR · 12 digits›` — and give the API no field that could carry plaintext. Same principle as the audit row, applied to the UI.

### 11.3 Two things the writeup must concede rather than defend

**The principal is asserted, not authenticated.** `AuthType=NONE` on the Function URL is what makes the demo openable by a judge, and the entire policy model is principal-based. Say so and name the production answer (JWT, or AgentCore Identity) rather than letting someone find it.

**The budget is a budget over *detected* disclosure.** If a detector misses an entity, the ledger never counts it and the ceiling never binds. There is no eval set and Comprehend's own Service Card publishes no figure for Aadhaar or PAN. This is strictly weaker than "a budget over disclosure", and a judge will derive it unaided — so state it first.

### 11.1 Build order — fail fastest first

1. **Hello-world Strands agent on Lambda behind a Function URL, arm64, deps zipped.** This is the single highest-risk step and it is a packaging problem, not a logic problem. Discovering it on Sunday afternoon loses Ship It.
2. Second Lambda for the control plane. Both URLs live. Nothing else yet.
3. Cedar Q1 locally, deny path working.
4. Detection tiers 1 and 2, with an assertion-based check on Verhoeff.
5. `normalize()` for text and PDF.
6. Ledger, Q2 batch, placeholders, rehydration.
7. `S3SessionManager` — confirm the ledger survives a second HTTP request.
8. Audit hook, redeploy, confirm both URLs still serve.
9. UI.
10. Video, writeup, blog post.

Steps 1, 2 and 8 must not slip. Everything from 9 onward is recoverable; a broken deploy is not.

---

## 12. Demo — three minutes, judged on the video alone

Judges see only submitted materials. No live demo, no calls. A feature described in the writeup but absent from the video does not count.

**Narration rule, and it matters more than it looks.** Retroactive masking of conversation history is real and CAMP does exactly it — but it means *rewriting the transcript sent to the next inference call*, not undoing what the model already read. Be precise, because the imprecise version dies in one sentence.

- ✅ "Removed from context going forward — the model saw it once; it will not see it again, and nothing downstream can use it."
- ✅ "The field that was allowed at call two is denied now, because the ledger has moved."
- ❌ "The model no longer knows it." False. It read it.

If `Transform` at `before_model_call` can mutate the message list — §15 flags that the docs do not specify which fields are mutable — the history rewrite is genuinely available and worth the hour. If it cannot, the present-tense version carries the same visual with no exposure.

| Time | Beat |
|---|---|
| 0:00–0:15 | A scanned Aadhaar card. "This is in your support ticket queue. Your agent is about to read it." |
| 0:15–0:35 | The gap, precisely: AgentCore Policy decides *whether* a call happens; Bedrock Guardrails' PII filter does not evaluate tool fields and has no Indian entity types. Show the AWS doc line. |
| 0:35–1:10 | Three tool calls. Name — green. Phone — green. Each individually fine. The **disclosure meter fills.** |
| 1:10–1:40 | Fourth call returns an Aadhaar. Budget is spent. It redacts — **and the phone number, which was allowed at call two, is denied now.** This is the beat that wins it. |
| 1:40–2:05 | Rehydration: the agent calls `send_summary` with the placeholder, the call is authorized, the real value is substituted on the trusted side. Task completes. The model never held the digits. |
| 2:05–2:25 | Feed the PDF. One attachment exhausts the budget in a single call. Show the bounding boxes if built. |
| 2:25–2:45 | Edit one line of `agent.cedar` on the control plane. Both agents change behaviour on their next call. One audit view. |
| 2:45–3:00 | Close on the ledger and the live URL. |

**Prize mapping.** Ship It needs a deployed URL — hence §11.1 step 1. Best UI is judged on the same submission, and the disclosure meter is a genuinely good UI object that costs a bar chart and a threshold. The blogger prize is most of §2 written up — the Guardrails tool-field gap and the Claude-routes-globally finding are useful independent of this project.

---

## 13. Compliance framing

Use this and nothing stronger.

> India's Digital Personal Data Protection Act 2023 and the DPDP Rules 2025 (notified November 2025) set a phased compliance timeline, with substantive obligations for organisations commencing in May 2027. Under s.8(2) a Data Fiduciary may engage a Data Processor — which is what a hosted LLM provider is — only under a valid contract, and under s.8(1) the Fiduciary remains liable regardless of any agreement to the contrary. Sections 4–6 limit processing to the consented, specified purpose and to the data necessary for it, which is the principle a disclosure budget makes executable. Rule 6 requires reasonable security safeguards expressly including "encryption, obfuscation or masking or the use of virtual tokens", together with logs and monitoring retained for one year. Cross-border transfer is permissive — s.16 uses a negative list and no restricted country has been notified — so redaction here is data minimisation and defence in depth, not a transfer block, though sector rules already in force including RBI's 2018 payment-data localisation directive and the CERT-In 2022 directions are stricter. Separately and already in force, Aadhaar Act s.29(4) bars public display of Aadhaar numbers and UIDAI guidance permits display of only the last four digits, with penalties under s.37 and a civil penalty of up to ₹1 crore per contravention under s.33A.

**Do not claim:** that DPDP is in force today (obligations commence ~May 2027); that DPDP restricts sending data to US LLMs (negative list, empty); that DPDP mandates masking Aadhaar (Rule 6 lists it as one option); a right to explanation for automated decisions (no Article 22 equivalent exists); that ₹250 crore penalties apply (a discretionary ceiling for security-safeguard failures, not yet live); that Aadhaar Data Vault tokenisation is required of you (binds AUA/KUA ecosystem entities only); any "PAN privacy law" (none exists). Say "November 2025" and "May 2027", not precise days — sources disagree.

Fair to cite as context: MeitY's **India AI Governance Guidelines** (5 November 2025), explicitly **voluntary and non-binding**.

---

## 14. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| arm64 packaging fails late | Loses Ship It | Deploy hello-world first, step 1 of 10 |
| `context_enricher` return shape differs from docs | Core design breaks | API ref renders `-> None` while every example returns a dict — almost certainly a doc artifact, but **verify in the first hour**, before building on it |
| Enricher cannot see handler mutations | Ledger never reaches Cedar | Do not rely on `invocation_state`; read the handler instance directly |
| Judge knows AgentCore Policy shipped | Novelty collapses | §2.3 is in the writeup. Position on cumulative state, never on category novelty |
| Budget threshold reads as arbitrary | Looks like a gimmick | Ground on Sweeney and Golle — three quasi-identifiers, per §6.3. **Not** HIPAA Safe Harbor, which says remove all 18 and cannot justify a threshold; use it only for *which fields count*. Never say "differential privacy" |
| Comprehend misses an entity on camera | Undermines the core claim | Seed fixtures deliberately, threshold 0.5, disclose accuracy limits rather than implying perfection |
| Multi-page PDF appears in demo data | Sync Textract fails at page 2 | Single-page fixtures only |

---

## 15. Open questions

1. `ContextEnricher` return type — docs render `-> None`, examples return a dict. Resolve at runtime in the first hour.
1b. **Does Comprehend accept `LanguageCode="hi"`?** The API enum lists `hi` among valid values while the developer guide says PII detection is English and Spanish only. One call settles it, and the payoff is large: if `hi` works, Tier 3 gets real offsets and confidence scores instead of LLM substring matching, and a generative model leaves the enforcement path entirely. Ten minutes, highest information-per-minute test available.
2. Whether `agent.state` survives `S3SessionManager` restore with custom keys intact alongside `"cedar-authorization"`.
3. Measured Comprehend latency from ap-south-1 — AWS publishes none; the ~100 ms community figure is unverified. Measure it and put the real number in the demo.
4. Whether Nova Pro multimodal returns usable Devanagari substrings at demo quality, or whether the Indic tier should be demoted to Should.
5. Entity-to-subject attribution is hard in general. Seeded structured fixtures make it trivial for the demo — do not claim general-purpose attribution.

---

## Sources

**Strands and Cedar** — [Interventions](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/) · [Cedar Authorization](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/cedar-authorization/) · [State Management](https://strandsagents.com/docs/user-guide/concepts/agents/state/) · [Session Management](https://strandsagents.com/docs/user-guide/concepts/agents/session-management/) · [Cedar operators](https://docs.cedarpolicy.com/policies/syntax-operators.html) · [cedarpy](https://pypi.org/project/cedarpy/) · [Lambda deploy guide](https://strandsagents.com/docs/user-guide/deploy/deploy_to_aws_lambda/)

**AWS services** — [Textract quotas](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html) · [DetectDocumentText](https://docs.aws.amazon.com/textract/latest/dg/API_DetectDocumentText.html) · [Comprehend PII entities](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html) · [Comprehend AI Service Card](https://docs.aws.amazon.com/ai/responsible-ai/comprehend-detectpii/overview.html) · [Claude Sonnet 5 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5.html) · [Claude in India via global CRIS](https://aws.amazon.com/blogs/machine-learning/access-anthropic-claude-models-in-india-on-amazon-bedrock-with-global-cross-region-inference) · [Nova Lite model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-lite.html) · [Guardrails sensitive-information filters](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html) · [AgentCore FAQs](https://aws.amazon.com/bedrock/agentcore/faqs/)

**Prior art** — [AgentCore Policy GA](https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/) · [Why Policy chose Cedar](https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/) · [Lambda interceptors in AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/) · [Pipelock](https://github.com/luckyPipewrench/pipelock) · [Bedrock Data Agent DLP](https://bedrockdata.ai/news/bedrock-data-launches-agent-dlp-runtime-data-loss-prevention-built-for-ai-agents) · [LangChain PIIMiddleware](https://reference.langchain.com/python/langchain/agents/middleware/pii) · [OWASP Agentic AI Top 10](https://www.paloaltonetworks.com/blog/cloud-security/owasp-agentic-ai-security/)

**Legal** — [DPDP phased rollout](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/) · [Rules notification](https://www.amsshardul.com/insight/enforcement-of-the-dpdp-act-and-notification-of-the-dpdp-rules/) · [s.8](https://indiankanoon.org/doc/186118625/) · [Rule 6](https://www.dpdpa.com/dpdparules/rule6.html) · [Schedule of penalties](https://www.dpdpa.com/theschedule.html) · [Cross-border negative list](https://www.mondaq.com/india/data-protection/1764976/from-localisation-debates-to-a-negative-list-making-cross-border-data-transfers-work-under-indias-dpdp-act) · [Aadhaar Act](https://uidai.gov.in/images/Aadhaar_Act_2016_as_amended.pdf) · [Masked Aadhaar](https://www.uidai.gov.in/en/283-faqs/aadhaar-online-services/e-aadhaar/1887-what-is-masked-aadhaar.html) · [India AI Governance Guidelines](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc2025115685601.pdf)
