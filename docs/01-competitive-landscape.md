# Naka — Competitive & Existing-Systems Review

**Document 01 of the planning package** · Written 18 September 2026 · Ships Sunday 20 September, 20:00 IST
**Input:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md` — this document replaces its §2.3 entirely
**Method:** adversarial. The brief was to falsify the novelty claim, not to confirm it.

---

## 0. Verdict, first

**The central claim is false.** "Every existing agent guardrail is stateless per call; none carries disclosure state across calls" does not survive one afternoon of searching. Six independent falsifiers:

1. **AWS shipped the substrate six weeks ago.** [Dogwood](https://aws.amazon.com/blogs/opensource/introducing-dogwood-runtime-verification-for-ai-agents/) (6 August 2026) extends Cedar with temporal conditions that read an agent's event history, bind fields out of tool *responses*, and aggregate over them with `count` and `sum`. It is wired into AgentCore Policy, which is GA in Mumbai. One of AWS's own worked examples is a cumulative budget cap per trajectory.
2. **The exact mechanism is published academia.** [CAMP](https://arxiv.org/abs/2604.16521) (16 April 2026) formalises "Cumulative PII Exposure", keeps a session-level PII registry and a quasi-identifier co-occurrence graph, scores after each turn, and retroactively masks history past a threshold. Its abstract attacks per-turn maskers in almost the project's own words.
3. **So is the budget framing.** [OCELOT](https://arxiv.org/abs/2606.12341) (10 June 2026) is a runtime mediator that "budgets how much an adversary's belief about a secret may improve across a trajectory", with a tamper-evident ledger, explicitly covering tool calls.
4. **Someone has already built a cumulative disclosure ledger in front of MCP.** [Noisegate](https://github.com/yashmahajan10/llm-differential-privacy-gateway) — Apache-2.0, 28★ — keeps "an exact ledger of cumulative disclosure … per identity", persisted to disk, and refuses rather than degrade.
5. **Cumulative state already gates enforcement in a shipping enterprise product.** Microsoft Purview's [cumulative exfiltration detection](https://learn.microsoft.com/en-us/purview/insider-risk-management-settings-policy-indicators) accumulates over 30 days and feeds the result back into DLP through [Adaptive Protection](https://learn.microsoft.com/en-us/purview/dlp-adaptive-protection-learn).
6. **Even Pipelock, cited in the PRD as per-call prior art, is not.** It carries a per-session threat score and taint escalation across task boundaries.

**What survives is narrower and still defensible:** nobody accumulates **per data subject**, and nobody turns that accumulation into a **redaction** decision in the same policy language as the allow/deny. Purview accumulates about the *actor*. Dogwood accumulates *declared event attributes*, and nothing populates those attributes with detected PII. CAMP and OCELOT accumulate correctly but are papers with no policy engine, no authorization model, and no tool-boundary implementation. Noisegate accumulates an ε-budget and answers with noise, not redaction.

Say **"subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision."** Say "cumulative state" and you lose the room.

---

## 1. The central question, tested hard

### 1.1 What was searched

Deliberately outside the LLM-security bubble: statistical-database inference control, k-anonymity and quasi-identifier accumulation, differential-privacy budget enforcement, re-identification risk scoring, session-scoped data-exposure limits, "context budget" controls, information-flow control for agents, and the privacy-engineering vendor set where aggregation control has been settled theory for decades. Roughly 60 sources; every load-bearing citation below was opened and read, and the handful that were not are marked.

### 1.2 The falsifiers, ranked by how much damage they do

#### Rank 1 — Dogwood and AgentCore temporal policies (AWS, 6 August 2026). Fatal to the category claim.

This is the one that ends the argument, and it is the one an AWS audience is most likely to know.

[Dogwood](https://github.com/dogwood-policy/dogwood) (Apache-2.0, 392★, authors Marc Brooker, Joseph Tassarotti, Jean-Baptiste Tristan) is an open-source policy language that embeds Cedar and adds a temporal sublanguage. AWS's [product-side blog](https://aws.amazon.com/blogs/machine-learning/securing-ai-agents-with-temporal-policies-in-amazon-bedrock-agentcore/) defines it verbatim:

> "Temporal policies are authorization controls that answer the question 'given the recent trajectory observed at the AgentCore Gateway, is this specific request authorized?'. They evaluate whether a gateway-routed request should be permitted based on the current request *and* recent trajectory (that is, events within a session)."

The [language guide](https://dogwood-policy.github.io/dogwood/guide/04-temporal-expressions.html) gives three temporal operators — `formerly within <interval>`, `previous within <interval>`, `<left> since within <interval> <right>` — and two aggregations, `count for (vars). where φ` and `sum v for (vars). where φ`. There is no count-distinct operator; deduplication falls out of the `for` domain projection. Critically, a temporal condition can bind fields out of a tool **response**:

```
formerly within 1h Drupe::Action::"Login"::response{
  input.user: context.input.user,
  output.result: true
}
```

And [information providers](https://dogwood-policy.github.io/dogwood/guide/05-information-providers.html) are a near-exact analogue of the `context_enricher` the PRD's whole design rests on: "values computed at authorize time by a small piece of sandboxed code, then folded back into a policy as if they had always been part of the request context", evaluated for every decision, with risk scoring named as an intended use.

**Read honestly:** AWS has shipped a policy language in which a disclosure budget is expressible. If tool response events carried `pii_type` and `subject_id` attributes, `count for (t). where formerly within 24h Action::"X"::response{output.subject: context.subject, output.field: f}` is the budget, in one line, from the vendor.

**What it does not do, verified:** Dogwood performs no content inspection and has no PII detection ([README](https://github.com/dogwood-policy/dogwood); the AWS blog's seven worked policies are all trading/approval flows). It reasons over *declared* event attributes. Nothing in AgentCore populates those attributes with detected entity types attributed to a person. AWS also states the reference interpreter is "NOT intended for production use", that temporal conditions lose Cedar's automated-reasoning analysis, and that evaluation time depends on event-log length.

**The residual gap is precisely: the thing that fills the events.** That is Naka's detect → attribute → spend pipeline. Say that out loud before a judge says it for you.

#### Rank 2 — CAMP (arXiv, 16 April 2026). Fatal to conceptual novelty.

[CAMP: Cumulative Agentic Masking and Pruning for Privacy Protection in Multi-Turn LLM Conversations](https://arxiv.org/abs/2604.16521), Aman Panjwani. The abstract is the project's own pitch, six months early:

> "Current approaches to Personally Identifiable Information (PII) masking operate on a per-turn basis, scanning each user message in isolation and replacing detected entities with typed placeholders before forwarding sanitized text to the model. While effective against direct identifier leakage within a single message, these methods are fundamentally stateless and fail to account for the compounding privacy risk that emerges when PII fragments accumulate across conversation turns. A user who separately discloses their name, employer, location, and medical condition across several messages has revealed a fully re-identifiable profile — yet no individual message would trigger a per-turn masker. We formalize this phenomenon as Cumulative PII Exposure (CPE) … CAMP maintains a session-level PII registry, constructs a co-occurrence graph to model combination risk between entity types, computes a CPE score after each turn, and triggers retroactive masking of conversation history when the score crosses a configurable threshold."

Session-level registry, combination risk, threshold, retroactive masking. Even the denied-now beat — the PRD's 1:10–1:40, "the phone number, which was allowed at call two, is denied now" — is in there. Note the precision the PRD's §12 narration rule insists on: CAMP rewrites the transcript sent to the *next* inference call. Nothing un-reads what a model already read.

**Where it stops:** user messages, not tool results. No authorization model, no principal, no policy language, no tool boundary. Evaluated on four synthetic scenarios. No file handling. No Indian identifiers. No stated code release.

#### Rank 3 — OCELOT (arXiv, 10 June 2026). Fatal to the phrase "disclosure budget".

[OCELOT: Inference-Leakage Budgets for Privacy-Preserving LLM Agents](https://arxiv.org/abs/2606.12341), Jin Xie & Songze Li. Abstract, in part:

> "leakage is cumulative, as individually innocuous releases accumulate across honest-but-curious or colluding sinks into inferences about a protected secret … Per-release contextual-integrity filters, information-flow controls, and posterior-leakage monitors each address part of this but none controls cumulative, inference-based leakage at runtime. We recast agent privacy as posterior-risk control and present OCELOT, a runtime mediator that budgets how much an adversary's belief about a secret may improve across a trajectory, rather than filtering outputs."

It covers tool calls explicitly, charges a certified min-entropy cost per release, authorises "the least-disclosing useful release under a sink-trust-weighted budget recorded on a tamper-evident ledger." This is a stronger, better-grounded version of the same idea. It is also a paper with no implementation disclosed, no policy engine, and a mechanism (a locally fine-tuned defender model plus deterministic verifier) that is unbuildable in a weekend.

#### Rank 4 — Noisegate. Kills "nobody has built this".

[Noisegate](https://github.com/yashmahajan10/llm-differential-privacy-gateway), Apache-2.0, 28★, hobby scale, Yash Mahajan. Runs as an MCP server; the connecting agent is untrusted by design. README: *"An exact ledger of cumulative disclosure is kept per identity and persisted to disk, and the gateway refuses to answer before that ledger can exceed the guarantee."* It is real (ε, δ)-DP with the Laplace mechanism and it refuses rather than quietly degrading.

**Different in kind, usefully:** it accumulates a *privacy budget per querying identity* and answers with calibrated noise. It does not detect PII, does not attribute to a data subject, and does not redact. It is also the reason the PRD's §6.3 instruction — *never say differential privacy* — is correct: someone has done the DP version properly and comparison will not flatter you.

#### Rank 5 — Microsoft Purview. Kills "no product feeds cumulative state into an enforcement decision".

Verbatim from the [policy indicators doc](https://learn.microsoft.com/en-us/purview/insider-risk-management-settings-policy-indicators) (ms.date 2026-06-22), under *Cumulative exfiltration detection indicators*:

> "These indicators detect when a user's exfiltration activities across all exfiltration channels over the last 30 days exceed organization or peer group norms … A risk score is assigned if the user's cumulative exfiltration activity is unusual and exceeds organization or peer group norms."

[Adaptive Protection](https://learn.microsoft.com/en-us/purview/dlp-adaptive-protection-learn) makes insider-risk level a DLP policy condition, so enforcement tightens as accumulated risk rises. Cumulative state → enforcement decision, shipping, at enterprise scale.

**The category difference, which is the whole answer:**

| | Purview IRM + Adaptive Protection | Naka |
|---|---|---|
| Accumulates about | the **acting user** | the **data subject** |
| Unit | volume of egress events vs peer-group baseline | which identifying fields of one person have been revealed |
| Semantics | statistical anomaly | sufficiency for re-identification |
| Latency | 30-day window, risk tiers, policy re-scoping | inline, this call |

"Purview can tell you an employee is exfiltrating more than their peers. Nothing tells you that three innocuous tool calls have jointly re-identified one patient." That sentence is worth memorising.

#### Rank 6 — Pipelock, and the general point that "stateless" was sloppy.

[Pipelock](https://github.com/luckyPipewrench/pipelock) (884★, Apache-2.0 core / Elastic 2.0 enterprise) tracks per-session behavioural profiling, a per-session threat score that escalates warn→block, and taint escalation across task boundaries. It also already emits typed numbered placeholders — `<pl:aws-access-key:1>` — across HTTP, WebSocket and MCP `tools/call` arguments, with numbering restarting per class on every request. **The numbered-placeholder design in PRD §6.2 is prior art.** Pipelock has no rehydration, no Aadhaar/PAN, and its 65 DLP patterns are credential- and secret-oriented.

Likewise [Strands' own Cedar intervention](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/cedar-authorization/) exposes `context.session.call_count`, documented as persisting "with the agent's state and survive[ing] session reloads", where "only successful tool calls increment the counter." The framework Naka is built on already ships a cross-call counter into Cedar. That is a gift for the build and a landmine for the pitch.

### 1.3 The privacy-engineering world: the idea is 47 years old and nobody ported it

Aggregation and inference control in statistical databases is settled theory. Denning, Denning & Schwartz, ["The Tracker: A Threat to Statistical Database Security"](https://dl.acm.org/doi/10.1145/320064.320069), ACM TODS 4(1), March 1979 ([PDF](https://faculty.nps.edu/dedennin/publications/TrackerThreat.pdf)) showed that per-query threshold checking — query-set-size control — fails against composed queries. **Per-call guardrails being insufficient was proven in the 1970s.** History's answer was auditing across a session.

The vendors who own that math have not brought it into the AI path:

- **Immuta** ships genuine quasi-identifier k-anonymisation: "masking with k-anonymization examines pairs of values across columns and hides groups that do not appear at least the specified number of times (k)" ([docs](https://documentation.immuta.com/2024.2/secure-your-data/authoring-policies-in-secure/data-policies/reference-guides/data-policies)). But it is compiled from the source's value distribution into a SQL rewrite ([blog](https://www.immuta.com/blog/sql-based-enforcement-of-k-anonymization/)) — every query is rewritten identically regardless of what that user asked five minutes ago. No odometer. And [Immuta AI](https://www.immuta.com/blog/immuta-ai-announcement/) plus its [MCP server](https://www.immuta.com/resources/immuta-ai-and-model-context-protocol-mcp/) turned out to be a conversational front-end to policy authoring and access requests, not a data-path guardrail.
- **NVIDIA** owns both sides and has not joined them: Gretel's privacy filters and re-id reporting run at synthetic-data *generation* time ([docs](https://docs.gretel.ai/optimize-synthetic-data/evaluate/synthetic-quality-privacy-report)), while [NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/pii-detection) is a separate codebase doing Presidio-based per-interaction scanning.
- **Tonic**, **Skyflow**, **Securiti**, **Protecto**, **Privacera PAIG**, **BigID** — all per-interaction. Where they hold state it is audit retention, deterministic token mappings, or posture graphs, never a per-subject disclosure ledger. **Privacy Dynamics** shut down; its anonymisation tech was [acquired by Xata](https://xata.io/blog/xata-acquires-privacy-dynamics) for Postgres dev databases.
- **DP tooling has real odometers** — [Tumult Analytics](https://docs.tmlt.dev/analytics/latest/topic-guides/privacy-budgets.html): "Each time you evaluate a query through the Session, you must specify how much budget the query should use, which is then subtracted from the Session's total" — but none of it sits in front of an agent tool call.

Worth knowing: in agent infrastructure, **"context budget" already means token budget**, not privacy. The privacy sense of the phrase is simply not in use. Do not introduce it and expect to be understood.

### 1.4 What the field itself says the gap is

The strongest external support is a survey, not a product. [Agents That Know Too Much: A Data-Centric Survey of Privacy in LLM Agents](https://arxiv.org/abs/2606.26627) (Lahjouji & Colaco, 25 June 2026), from the abstract:

> "Two findings recur: among governance mechanisms only information-flow control covers both compositional and cross-session inference leakage, the two least-protected risks; and no benchmark drives an agent across its data surfaces under one privacy policy, the instrument the field most lacks."

A peer-reviewed-adjacent survey naming compositional and cross-session inference leakage as the two least-protected risks is better positioning material than any novelty claim. It says the problem is real and unsolved without requiring you to say nobody thought of it.

**The information-flow control line of work is the serious competition** and none of it is per-subject: CaMeL (Google DeepMind) attaches capability metadata to every value; [FIDES](https://arxiv.org/abs/2505.23643) (Costa, Köpf et al.) tracks confidentiality and integrity labels in the planner; [AgentFlow](https://arxiv.org/html/2608.22868) (Shivakumar, Priya & Gao, Virginia Tech, 24 August 2026) ships a policy language with flow rules, path rules, a taint map, a lineage map and declassification transforms — and tracks PII "through a category system within its label lattice rather than by specific entity identity. It does not track which individual data subjects are affected." AgentFlow's own framing of Cedar is worth stealing:

> "Request-level authorization languages such as Cedar are well suited to deciding whether a principal may perform an action on a resource. Agent systems need that check, but also need to remember where data came from, how it was transformed, and which later actions it may influence."

---

## 2. The landscape matrix

Columns: **Authz** = authorises tool calls; **Redact** = redacts tool *results*; **Files** = handles PDFs/images/binaries in the AI path; **IN** = Indian identifiers; **Cumul.** = does a decision on call N depend on what was disclosed in calls 1..N−1.
`n/s` = public material does not specify. All rows read from vendor documentation unless flagged.

### 2.1 AWS-native

| Product | What it actually does | Deploy | Authz | Redact | Files | IN | Cumul. |
|---|---|---|---|---|---|---|---|
| [AgentCore Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html) | Cedar, default-deny, on MCP tool invocations at the Gateway. GA 3 Mar 2026, 13 regions incl. Mumbai | Managed | **Yes** | No | No | No | No (base Cedar) |
| [Dogwood temporal policies](https://aws.amazon.com/blogs/machine-learning/securing-ai-agents-with-temporal-policies-in-amazon-bedrock-agentcore/) | Cedar + temporal operators + `count`/`sum` over session event history; binds `output.*` from tool responses | Managed + [OSS](https://github.com/dogwood-policy/dogwood) | **Yes** | No | No | No | **Yes — over declared event attributes** |
| [Gateway Lambda interceptors](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/) | REQUEST/RESPONSE Lambdas; can "filter or sanitize the tool response before it returns to the agent" | Managed + your Lambda | Via Policy | **Yes, you write it** | Your code | Your code | No — per-request event, no state |
| [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html) | PII block/mask on prompts and model responses; custom regex | Managed | No | **No — see below** | No | **No** | No |
| Amazon Comprehend [`DetectPiiEntities`](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html) | Entity spans + confidence. EN/ES only, 100 KB | API | n/a | Offsets only | No | **Yes: `IN_AADHAAR`, `IN_NREGA`, `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER`** | No |
| Amazon Macie | S3 object discovery and classification | Managed | No | No | Yes (at rest) | n/s | No — not a runtime path |
| [Strands interventions](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/) | 5 hooks, Proceed/Deny/Guide/Confirm/Transform; vended Cedar authorization | Library | **Yes** | Transform at `after_tool_call`; no PII intervention ships | No | No | **`call_count` persists across session reloads** |

**The single best line in the entire research**, from the Guardrails doc, unedited:

> "This filter evaluates text content only. In tool use (function calling) workloads, it does not evaluate the following, so PII in these fields is neither blocked nor masked: PII the model generates into tool call arguments (`toolUse.input` in Converse, `tool_use` parameters in InvokeModel) … PII in tool results your application returns to the model (`toolResult`) … PII in the tool definitions you supply (`toolSpec.description`, `toolSpec.inputSchema`)."

Two more from the same page worth knowing and not over-claiming: the Guardrails trace `match` field "contains the original PII value, not the masked output", and model invocation logs "always contain the original, unmodified request regardless of guardrail intervention." And the entity taxonomy is General / Finance / IT / **USA specific / Canada specific / UK specific** / Custom regex — no India-specific type exists. PRD §4 claim 3 is verified, not asserted.

Also worth having in your pocket: [AgentCore Policy's limitations page](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-limitations-section.html) — no regex, no floats, 10 KB per policy, 400 KB combined schema, and "Mixing `context.input.` and `context.output.` in a single invocation is rejected."

### 2.2 Open-source agent firewalls and MCP gateways

| Product | What it actually does | Deploy | Authz | Redact | Files | IN | Cumul. |
|---|---|---|---|---|---|---|---|
| [Pipelock](https://github.com/luckyPipewrench/pipelock) 884★ | Agent egress firewall over HTTP/MCP/A2A/WebSocket; 65 DLP patterns (secrets-oriented), 17 tool-policy rules, signed action receipts, typed numbered placeholders | Self-host mediator | **Yes** (17 rules) | Yes, placeholders, **no rehydration** | Image metadata strip only; no PDF | **No** | **Yes — session threat score, taint escalation** |
| [Noisegate](https://github.com/yashmahajan10/llm-differential-privacy-gateway) 28★ | (ε,δ)-DP gateway as an MCP server; per-identity cumulative disclosure ledger on disk; refuses at budget | Self-host MCP server | Budget-gated | No — adds noise | No | No | **Yes — exact cumulative ledger per identity** |
| [hoop.dev](https://hoop.dev/blog/pii-phi-redaction-for-ai-agents-on-postgres) (MIT) | L7 access gateway proxying DB/SSH/K8s/HTTP; streams result sets to Presidio or Google DLP and redacts before rows reach the agent; session recording | Self-host gateway | Connection-level | **Yes, on query results** | No | Via Presidio *(inferred)* | No |
| [mcp-firewall](https://github.com/ressl/mcp-firewall) | 7 inbound stages + optional human approval + 2 outbound scanners per tool call | Self-host | Yes | Yes | n/s | n/s | n/s |
| [Presidio](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md) | The PII engine most of the field actually runs | Library/container | n/a | Detection + anonymise | **[presidio-image-redactor](https://microsoft.github.io/presidio/image-redactor/)** — Tesseract OCR, DICOM | **`IN_AADHAAR` (checksum), `IN_PAN`, `IN_VOTER`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION` (checksum), `IN_GSTIN`** | No |

### 2.3 Agent-framework built-ins

| Product | What it actually does | Authz | Redact | Files | IN | Cumul. |
|---|---|---|---|---|---|---|
| [LangChain 1.0 `PIIMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/pii/PIIMiddleware) | `pii_type` ∈ {`email`,`credit_card`,`ip`,`mac_address`,`url`} or custom; strategies `block`/`redact`/`mask`/`hash` | HITL approval only | **`apply_to_tool_results` exists but defaults to `False`** | No | **No** | No — `ToolCallLimitMiddleware` `thread_limit` counts calls only |
| [LlamaIndex PII postprocessors](https://developers.llamaindex.ai/python/examples/node_postprocessor/pii/) | `NERPIINodePostprocessor`, `PIINodePostprocessor`, `PresidioPIINodePostprocessor` over retrieved RAG nodes | No | RAG nodes only | No | Via Presidio variant *(inferred)* | Per-node map only |
| [CrewAI tool hooks](https://docs.crewai.com/en/learn/tool-hooks) | `PRE_TOOL_CALL` / `POST_TOOL_CALL`; post-hook can replace `ctx.tool_result` | **Yes** | **Yes** | No | **No PII detection at all** | No |
| [Strands](https://strandsagents.com/docs/user-guide/safety-security/pii-redaction/) | See 2.1. PII page states the SDK "does not natively perform PII redaction within its core telemetry generation" | **Yes** | Transform hook | No | No | `call_count` |
| [Semantic Kernel filters](https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/filters) | Function/prompt/auto-function-invocation filters; block by not calling `next` | Mechanically yes | Mechanically yes | No | PII is a [sample](https://github.com/microsoft/semantic-kernel/blob/main/dotnet/samples/Concepts/Filtering/PIIDetection.cs) wiring Presidio, not a feature | Per-invocation |
| [Purview middleware for Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/middleware/purview) | `PurviewPolicyMiddleware`; inline DLP blocking on prompt + history + response. M365 E5 | Blocks | Yes | **The only one documenting binaries — see below** | Purview classifiers | Per-call inline; Purview aggregates post-hoc |
| [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/ref/tool_guardrails/) | `ToolInputGuardrail` / `ToolOutputGuardrail` with tripwires | **Yes** | **Suppression, not redaction** — "Output withheld by an output guardrail" | No | **No PII detection at all** | No |

The Purview middleware line is the only documented attachment story in the whole survey: *"The middleware evaluates every non-empty message content item, not only plain text … Base64 data URI payloads are evaluated as binary content. Non-base64 data, URI content, function calls, function results, and other structured content are serialized as text so they aren't skipped."*

### 2.4 LLM gateways

| Product | What it actually does | Deploy | Authz | Redact | Files | IN | Cumul. |
|---|---|---|---|---|---|---|---|
| [Bifrost](https://docs.getbifrost.ai/enterprise/guardrails) (Maxim AI) | Guardrails with an explicit `mcp` target: inspect/redact arguments "before the MCP tool executes" and results "after the tool returns". Redaction modes `runtime`, `logs_only`, `runtime_reversible` (numbered placeholders, e.g. `[EMAIL-1]`) | Self-host Go, Apache-2.0 | **Yes** | **Yes, both boundaries** | n/s | Via Presidio integration *(inferred)* | Budgets are cumulative; **guardrails are not** |
| [LiteLLM](https://docs.litellm.ai/docs/proxy/guardrails/tool_permission) | `pre_mcp_call` guardrail hook + a Tool Permission Guardrail over `tool_calls`/`tool_use`/MCP with `allowed_param_patterns` | Self-host proxy | **Yes** | Strip/rewrite; PII on results n/s | No | [All Presidio entity types](https://docs.litellm.ai/docs/proxy/guardrails/pii_masking_v2) *(inferred)* | No (spend budgets only) |
| [Portkey](https://portkey.ai/docs/product/guardrails) | 20+ checks; each validates "ONLY ONE OF the Input or the Output". MCP Gateway blocks unapproved tool invocations. "Redaction is irreversible by design" | OSS + SaaS + self-host | **Yes** (allowlist) | Model output yes; tool results n/s | No | **No** | No |
| [TrueFoundry](https://www.truefoundry.com/blog/ai-agent-guardrails) | Four hook points incl. MCP pre-tool and post-tool | SaaS + self-host | **Yes** | **Yes** | n/s | Via Presidio template *(inferred)* | **Explicitly stateless, by design** |
| [Kong AI Gateway](https://developer.konghq.com/plugins/ai-sanitizer/) | `ai-prompt-guard` regex + `ai-sanitizer` PII service container; `recover_redacted` restores originals in the response | Self-host + sidecar | Not by these plugins | LLM responses yes | No (body text, 1 MB cap) | **`nationalid` "for example, Aadhaar … or voter IDs"** — bucketed, no PAN entity | No |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/features/dlp/) | Guardrails (Llama Guard 3) + DLP using Cloudflare One profiles | SaaS edge | No | Responses yes | **Explicit no** | No | No — and **cache hits skip DLP** |
| [Helicone](https://docs.helicone.ai/features/advanced-usage/llm-security) | Prompt Guard / Llama Guard security only; OpenAI models only | SaaS proxy | No | No | No | **No PII at all** | No |

Cloudflare's is the bluntest published statement of the attachment blind spot anywhere: *"DLP does not decode base64-encoded content or follow external URLs. Only the raw text of the request and response body is inspected."* Their WAF AI detection adds *"the detection only handles requests with a JSON content type."*

### 2.5 Commercial AI-DLP and AI-security

| Product | What it actually does | Deploy | Authz | Redact | Files | IN | Cumul. |
|---|---|---|---|---|---|---|---|
| [Bedrock Data Agent DLP](https://bedrockdata.ai/news/bedrock-data-launches-agent-dlp-runtime-data-loss-prevention-built-for-ai-agents) (30 Jul 2026) | "inspects every tool call in both directions"; allow/modify/block "at the time of action"; **hooks natively into AWS AgentCore and LiteLLM** | Inline hooks | **Yes** | **Yes** (mask/redact/block) | n/s | Not mentioned | **Per-call** |
| [Lasso Security MCP Gateway](https://www.lasso.security/use-cases/mcp) | Plugin-based MCP gateway inspecting traffic in real time; masks and redacts PII in **both requests and responses**, validates tool-call parameters, filters network destinations. [Embedded into Portkey's MCP Gateway](https://portkey.ai/blog/securing-mcp-to-deliver-enterprise-grade-agentic-ai-protection/) | Self-host gateway | **Yes** | **Yes** | n/s | n/s | n/s — "risky tool combinations" is about tool pairs, not data accumulation |
| [Securiti](https://securiti.ai/gencore/llm-firewalls/) | Prompt Firewall / Retrieval Firewall / Response Firewall, all inline per-interaction; Data Command Graph is posture, not a ledger | SaaS | Partial | Yes | n/s | n/s | No — closest *marketing* adjacency ("context-aware") |
| [Skyflow](https://www.skyflow.com/product/skyflow-for-agents) | Deterministic tokenisation + per-request detokenisation under vault ACLs; "field-level privacy across MCP connections" | Vault + proxy | Per-request ACL | Tokenise/detokenise | n/s | n/s | Token identity mapping is stable across calls — **not disclosure accounting** |
| [Protecto](https://www.protecto.ai/ai-guardrails/) | "detects, masks, and controls sensitive data before it reaches any LLM, agent, or MCP tool"; Context-Based Access Control decides allow/mask/block/minimize | SaaS/SDK | Yes | Yes | n/s | n/s | Logging is cumulative; **the decision is not** |
| [WitnessAI](https://witness.ai/protect/) | Intent-based classification claims patterns "that evolve across sessions"; own writeup says enforcement is "at the moment of interaction" | Inline | Yes | Yes | n/s | n/s | Behavioural, about the **user** |
| [Privacera PAIG](https://github.com/privacera/paig) | Real-time gateway scanning prompts/responses, tag-based RAG filtering | OSS + SaaS | Partial | Yes | n/s | n/s | Conversation recorded for **audit**, not fed back |
| [Cyberhaven](https://www.cyberhaven.com/blog/ai-inference-risk-dlp) (25 Jun 2026) | Data lineage + AI entry-point detection. **Blog describes cumulative inference risk precisely and does not claim to enforce on it** | Endpoint/browser | No | Entry-point blocking | n/s | n/s | Lineage, not a per-subject ledger |
| [Purview DSPM for AI](https://learn.microsoft.com/en-us/purview/data-security-posture-management-learn-about) | Posture + observability + per-interaction DLP; aggregate reporting | SaaS | No | Per-interaction | Via classifiers | Purview classifiers | Aggregation is **post-hoc analytics**; see §1.2 rank 5 for the exception |

### 2.6 India

**No Indian vendor was found doing agent-level AI guardrails with Aadhaar/PAN enforcement.** Indian identifier coverage in this market comes from exactly two places, neither of them a differentiator:

- **Presidio**, free and open source, with `IN_AADHAAR` **including checksum validation**, plus `IN_PAN`, `IN_VOTER`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION` and `IN_GSTIN`. Anything that embeds Presidio — LiteLLM, TrueFoundry's template, LlamaIndex's Presidio postprocessor, hoop.dev, NeMo Guardrails — inherits all of it for nothing.
- **Amazon Comprehend**, with `IN_AADHAAR`, `IN_NREGA`, `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER`.

Two things that *are* genuinely thin and worth saying carefully: `IN_NREGA` exists in Comprehend and **not** in Presidio; and Comprehend is English/Spanish only, so **every mainstream detector is blind to the Devanagari or Tamil half of an Aadhaar card**. The Indic-script gap is real and defensible. "We detect Aadhaar" is not — Presidio has done it with a Verhoeff checksum for years.

### 2.7 The four most threatening entries, in prose

**1. AgentCore Policy + Dogwood + a Gateway response interceptor.** This is the composition an AWS SA will assemble in their head while watching the video, and it is close. Policy gives allow/deny with a real principal. Dogwood gives session-scoped counting over tool responses with an information-provider escape hatch. A RESPONSE interceptor gives read/write on the tool payload and can call Guardrails or Comprehend. Everything is managed, GA, and in Mumbai. The honest differences: nothing joins them, Dogwood's reference interpreter is explicitly not production-ready and loses formal analysis, AgentCore Policy rejects mixing `context.input.` and `context.output.` in one invocation, the interceptor is stateless per request so the ledger has nowhere to live, and no AWS component attributes detected entities to a data subject. **The gap is integration and the detect→attribute→spend pipeline, not the policy substrate. Concede the substrate immediately.**

**2. CAMP.** The closest thing to a direct hit on the idea, and the one that makes any conceptual-novelty claim unsurvivable. Do not fight it — cite it. "CAMP formalised cumulative PII exposure for conversation turns in April. We put the same idea at the tool boundary, behind an authorization model, in a policy language an admin can edit." That is a better sentence than anything a novelty claim buys you, and it signals the literature was read.

**3. Bedrock Data Agent DLP.** The most direct commercial competitor by position: it hooks natively into AgentCore and LiteLLM, inspects every tool call in both directions, and masks/redacts/blocks with a logged verdict per decision. It shipped 30 July 2026. Its published material shows no cumulative state, no attachment handling, no Indian identifiers, and no policy language exposed to the customer — but it occupies the same shelf and it got there first. Note also the name collision: "Bedrock Data" is an unrelated company, not an AWS service. Do not let that confusion into the writeup.

**4. Bifrost and TrueFoundry.** Both already do the boring 80% — guardrails at the MCP tool boundary, arguments inspected before execution and results after, with redaction. Bifrost's `runtime_reversible` mode even produces numbered placeholders the way PRD §6.2 does. TrueFoundry is the more useful of the two rhetorically, because it markets per-hop independence as correct engineering: *"Because every hop is checked independently, a compromised tool result on hop three is caught on hop three, not after it has already fanned out into three more calls."* That sentence is the thesis statement of the status quo, from a competitor, and it is exactly the assumption Naka inverts. Use it.

---

## 3. What a judge has personally used

At a WeMakeDevs × AWS event in India, the realistic profile is an AWS Solutions Architect or a senior engineer building agents on Bedrock. Ranked by likelihood of first-hand knowledge:

| Likelihood | What they've touched | Why |
|---|---|---|
| Near certain | **Bedrock Guardrails** | Default answer to "how do I stop PII leaking", on every AWS GenAI slide for two years |
| Near certain | **Strands** or LangChain | Strands is AWS's own agent SDK; the hackathon is on AWS |
| High | **AgentCore Policy / Gateway** | GA since March 2026, in Mumbai, heavily blogged |
| **High, and rising fast** | **Dogwood** | Six weeks old, AWS Open Source Blog, InfoQ, The New Stack, 392★. Fresh enough to be the thing an SA read last month and wants to talk about |
| Moderate | **Comprehend PII** | The standard AWS PII answer; Indian entities are a known talking point locally |
| Moderate | **Presidio** | The default for anyone who found Guardrails or Comprehend too expensive |
| Low | CAMP, OCELOT, AgentFlow, Noisegate | Nobody has read these. They are risk in the writeup, not in the room |

### The sentence that stings most

> **"Isn't this just Dogwood with a PII detector in front of it? AWS shipped temporal policies in August — I can already write `count for` over my tool-response history in AgentCore Policy. What are you adding?"**

It stings because it is substantially correct about the policy layer, it comes from someone who read the blog, and any answer that starts by disputing it loses.

**The answer, in order:**

> "Yes — and that's the right comparison. Dogwood is the best thing that happened to this idea; it proves AWS thinks session-scoped policy is the direction. But Dogwood reasons over event attributes that something else has to put there. `count for` counts what the event declares. Nothing in AgentCore declares `this response contained an Aadhaar number belonging to customer 8814`. That's the part we built: normalize any content type to markdown, detect with a checksum-plus-Comprehend tier stack including the Indic tier Comprehend can't do, attribute entities to a data subject, and *then* spend from a ledger. And the outcome isn't allow/deny — it's field-level redaction with a reversible placeholder, decided by the same policy, with the same principal, in one audit row. Dogwood has no redaction outcome. Our ledger would drop straight into a Dogwood information provider — that's the production path, and it's on the roadmap slide."

Three things that answer does: concedes fully and instantly, names the specific missing layer rather than waving, and ends by positioning Naka as *composable with* the thing being compared rather than competing with it. An SA who hears "our ledger is an information provider for your policy language" leaves thinking about integration, not novelty.

### Three more you should have a one-liner for

- **"Comprehend already has `IN_AADHAAR`. Why the Verhoeff code?"** — "Cost and OCR. Comprehend bills a 300-character minimum per request so field-by-field scanning is ~10× the naive estimate, and AWS's own service card names degraded performance on OCR'd text. The checksum is a free pre-filter and a confidence signal; we deliberately keep 12-digit sequences that *fail* Verhoeff at lower confidence, tagged OCR-derived, because a checksum is robust against false positives and fragile against a misread digit."
- **"Bedrock Guardrails does PII. Why not just use it?"** — Put the doc quote on screen. It does not evaluate `toolUse.input`, `toolResult`, or `toolSpec`. Three sentences from AWS saying the AWS control does not cover this surface.
- **"Isn't this differential privacy?"** — "No, and deliberately not. It's a quasi-identifier accumulator: HIPAA Safe Harbor's 18 identifiers say which fields count, and the threshold of three comes from the demographic-uniqueness work — Sweeney's 87%, revised to 63% by Golle. If you want the DP version, Noisegate does it properly with a real ε-ledger — and it answers with noise, which breaks the task. We redact reversibly so the task still completes."

---

## 4. Novelty verdict

Scored separately, because they score very differently.

### Category novelty: **2 / 10**

"Guardrails on an agent's tool boundary" is a crowded, commoditised 2026 category. Verified entrants doing tool-call authorization *and* result redaction: AgentCore Policy + interceptors, Bedrock Data Agent DLP, Bifrost, TrueFoundry, LiteLLM, CrewAI hooks, OpenAI Agents SDK, Pipelock, mcp-firewall, Portkey, Securiti, Protecto, Skyflow. This is table stakes and should be presented as such.

### Cumulative-state novelty: **3 / 10**

Falsified six ways in §1.2. AWS ships the substrate; academia has published the mechanism twice in five months; a working open-source ledger exists; Purview does cumulative→enforcement in production. **This is the claim the PRD currently leads with and it must be rewritten.**

### Subject-scoped semantic accumulation fed into an authorizer as a *redaction* decision: **7 / 10**

Here the field is genuinely empty, and every near-miss misses on a different axis:

| System | Accumulates | Over | Outcome | Misses on |
|---|---|---|---|---|
| Dogwood | declared event attributes | session | allow/deny | no detection, no subject, no redaction |
| Purview IRM | egress volume | the **actor**, 30 days | policy tier change | wrong entity, wrong latency |
| CAMP | detected PII entities | conversation turns | masking | no authorizer, no tool boundary, no subject key |
| OCELOT | posterior belief | trajectory | least-disclosing release | no policy language, no implementation |
| Noisegate | ε | querying identity | refusal + noise | no detection, no subject, no redaction |
| AgentFlow | taint labels by category | flow graph | declassification | explicitly not per data subject |
| Pipelock | threat score, taint | session | warn→block | behavioural, not semantic |

Nothing in that table both keys on the **data subject** and produces a **field-level redaction decision from an authorization policy**. That is the unclaimed square.

### File-to-markdown normalisation before detection: **6 / 10**

Not a new technique — [presidio-image-redactor](https://microsoft.github.io/presidio/image-redactor/) has done OCR-then-detect with Tesseract for years, and docling/markitdown-style normalisation is routine. What is genuinely unusual is that **almost nobody does it in the guardrail path**. Cloudflare says outright it does not decode base64 or follow URLs. Portkey, LangChain, CrewAI, OpenAI Agents SDK, LiteLLM and Pipelock have no PDF path. The only documented exception found is Purview's Agent Framework middleware, which needs M365 E5. So: the *capability* is table stakes, the *placement* is not.

### Indian identifiers: **2 / 10**

Presidio has had `IN_AADHAAR` with checksum validation, `IN_PAN`, `IN_VOTER`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION` and `IN_GSTIN` for free, for years. Comprehend adds `IN_NREGA`. Kong buckets Aadhaar into `nationalid`. This is not a differentiator. **The Indic-script gap is** — Comprehend is English/Spanish only and Textract OCR is Latin-script only, so every mainstream detector is blind to half of a real Aadhaar card. Claim that specific thing, not "Indian identifier support".

### Residency framing (Nova on `apac.*` because Claude in Mumbai is `global.*` only): **5 / 10**

Not novel, but rare, checkable, and it demonstrates the docs were read. Worth its line in the video exactly as the PRD says.

### Composite: **6.5 / 10**

Genuinely unclaimed: the subject-keyed ledger feeding a redaction decision through the same policy engine as the allow/deny, plus the Indic detection tier, plus normalisation inside the guardrail path. Table stakes in 2026: tool-boundary interception, tool-result redaction, numbered placeholders, Cedar-based tool authorization, Aadhaar/PAN pattern detection, audit logging.

---

## 5. Positioning recommendation

### 5.1 The framing that holds

Lead with the mechanism, not the novelty. The strongest available opening is a demonstration, not a claim:

> **"Three tool calls. A name. A phone number. A date of birth. Every one of them allowed — correctly. Together they are a person. Nothing on the market is counting, because every guardrail in the field decides one payload at a time. This counts, per person, and feeds the count back into the same Cedar decision that allowed the call."**

Then, unprompted, concede:

> **"AWS shipped the policy substrate for this in August — Dogwood, temporal conditions over session history, with `count` and `sum`. It's the right direction and we're building toward it. What Dogwood counts is what the event declares, and nothing declares that a tool response contained an Aadhaar belonging to customer 8814. That's the layer we built."**

Conceding Dogwood before a judge raises it converts the single most dangerous question into evidence of homework. Volunteering the strongest counter-argument is the highest-leverage thirty seconds in the video.

Three claims, all survivable:

1. **Subject-scoped, not actor-scoped, not call-scoped.** Purview accumulates about the employee. Pipelock accumulates about the agent. Dogwood accumulates events. Naka accumulates about **the person in the data**.
2. **Redaction is a policy outcome, in the same language, for the same principal, in one audit row.** AWS gives Cedar for allow/deny and leaves redaction to a Lambda you write. Dogwood has no redaction outcome. Pipelock redacts from YAML patterns with no identity. LangChain redacts with no authorization and with tool results off by default. Two questions, one policy, one record — that is the composition.
3. **Any content type, and the Indic tier.** Files are a documented blind spot across the field — Cloudflare says so in writing. And Comprehend's English/Spanish limit plus Textract's Latin-script limit means the regional-script half of an Aadhaar card is invisible to every mainstream detector.

Vocabulary: *agent firewall*, *agentic DLP*, *MCP guardrails*, *tool-level policy enforcement*, *quasi-identifier accumulation*, *aggregation control*. Anchor on **OWASP Top 10 for Agentic Applications 2026, ASI02 Tool Misuse & Exploitation** (with ASI03 Identity & Privilege Abuse as the second) — **not "T2"**, which belongs to OWASP's earlier threats-and-mitigations paper and reads as not having opened the document.

Two free rhetorical assets:
- **Denning 1979.** Per-query threshold checking was proven insufficient against composed queries 47 years ago, and the answer then was auditing across a session. "The industry rebuilt query-set-size control for agents and stopped there" is a strong, true, checkable line.
- **The survey.** "Compositional and cross-session inference leakage — the two least-protected risks" is [someone else's](https://arxiv.org/abs/2606.26627) conclusion, which is worth more than your own.

### 5.2 Sentences the team must not say

Each is falsifiable in one link by someone in the room.

| Do not say | Falsified by |
|---|---|
| "Every agent guardrail is stateless per call" | [Dogwood](https://aws.amazon.com/blogs/opensource/introducing-dogwood-runtime-verification-for-ai-agents/), [Pipelock](https://github.com/luckyPipewrench/pipelock), Strands' own `call_count` |
| "Nobody carries state across calls" | Same, plus [Purview](https://learn.microsoft.com/en-us/purview/insider-risk-management-settings-policy-indicators) |
| "No one has thought of a cumulative disclosure budget" | [CAMP](https://arxiv.org/abs/2604.16521), [OCELOT](https://arxiv.org/abs/2606.12341) |
| "Nobody has built a cumulative disclosure ledger" | [Noisegate](https://github.com/yashmahajan10/llm-differential-privacy-gateway) |
| "First of its kind" / "novel" / "nobody governs agent tool traffic" | AgentCore Policy, Bedrock Data Agent DLP, Bifrost, TrueFoundry, LiteLLM |
| "Numbered placeholders are our design" | Pipelock's `<pl:CLASS:N>`, Bifrost's `runtime_reversible` `[EMAIL-1]` |
| "We're the only ones detecting Aadhaar and PAN" | [Presidio](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md) does both, free, with a checksum; Comprehend does four |
| "Bedrock Guardrails can't do PII" | It does — on prompts and model responses. The gap is the tool-use fields, and only those |
| "This is differential privacy" / any ε vocabulary | Noisegate does real DP; the comparison will not flatter you |
| "OWASP T2 Tool Misuse" | The 2026 Agentic list numbers ASI01–ASI10; it is **ASI02** |
| "General-purpose entity-to-subject attribution" | Seeded structured fixtures make it trivial for a demo and nothing more. PRD §15.5 is right |
| "Existing DLP only watches browsers" | hoop.dev, Bifrost, LiteLLM, TrueFoundry and Bedrock Data all sit at the tool boundary |
| "AWS has no session-aware agent policy" | AWS shipped exactly that six weeks ago |

One framing risk that is not a sentence: **do not present the control plane, the ledger and the file pipeline as three separate novelties.** Judges discount a list. One mechanism — the subject-keyed ledger — with two supporting capabilities reads as a thesis; three parallel claims read as a feature tour.

---

## Appendix — verification status

**Read directly and quoted verbatim:** Bedrock Guardrails sensitive-information filters (tool-use exclusion note, full entity taxonomy, trace/logging caveats); Comprehend `DetectPiiEntities` country-specific entities; AgentCore Policy limitations; Dogwood temporal-expressions and information-providers guides; Dogwood GitHub README; AWS temporal-policies blog (all seven example policies); AWS Dogwood open-source blog; AgentCore Gateway Lambda interceptors blog; Presidio supported entities; CAMP abstract; OCELOT abstract; "Agents That Know Too Much" abstract; SurrogateShield (HTML); AgentFlow; Purview insider-risk policy indicators (cumulative exfiltration paragraph, verbatim); Pipelock README; Noisegate README; Bifrost guardrails docs; Strands PII-redaction page; LangChain built-in middleware and `PIIMiddleware` reference; Bedrock Data Agent DLP announcement; Cyberhaven AI-inference blog; hoop.dev; **TrueFoundry's four-hooks blog** (the "every hop is checked independently" sentence confirmed word-for-word); **Cloudflare AI Gateway DLP** (both the base64/URL sentence and "Cache hits skip DLP scanning" confirmed word-for-word).

**Reported by delegated research, sourced with URLs, not personally re-opened:** the Portkey / Kong / Helicone / LlamaIndex / CrewAI / Semantic Kernel / OpenAI Agents SDK row detail; Immuta, Gretel, Tonic, Skyflow, Securiti, Protecto, Privacera, BigID, WitnessAI, Lakera, Tumult; Denning 1979; RootGuard (arXiv 2605.03188); SessionBound (arXiv 2607.00751); Privacy Dynamics shutdown. Treat the specific wordings as reliable and the *absences* as "public material does not specify" rather than "does not exist."

**Not covered, and worth an hour if anyone has it:** Prompt Security (SentinelOne), Zenity, Noma, Aim (Cato), Palo Alto Prisma AIRS, Cisco AI Defense, HiddenLayer, F5/CalypsoAI, Nightfall, Strac, Pangea, Snyk/Invariant `mcp-scan`. Nothing found so far suggests any of them does subject-scoped accumulation — several appear in Portkey's guardrail-partner catalogue as per-request scanners — but they were not individually verified for this pass. Lasso's own pages are marketing-grade: the request/response redaction and tool-parameter validation claims are attributable, the deeper behaviour is not.

**Known unknowns, stated rather than guessed:**
- Whether AgentCore temporal policies are GA or preview, and their region list, is not stated on either AWS blog. AgentCore Policy itself is GA since 3 March 2026 in 13 regions including Mumbai.
- Whether Dogwood's event log stores full tool response bodies or only declared schema attributes is not documented. This matters — if it stores full payloads, the "nothing declares the PII" gap narrows.
- Whether the Purview service performs OCR on the base64 binary content its middleware forwards is not stated.
- Bedrock Data Agent DLP publishes no technical documentation; everything above comes from the launch announcement.
- No Indian vendor doing agent-level AI guardrails with Aadhaar/PAN enforcement was found. That is a negative search result, not proof of absence.
