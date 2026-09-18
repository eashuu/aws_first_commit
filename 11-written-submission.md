# Naka — written submission

**For:** WeMakeDevs × AWS "First Commit" (Bharat Builds Tour), submissions close Sunday 20 September 2026, 20:00 IST
**Covers the three things the form asks for:** the problem, the build, and where AWS fits.

---

### Before you paste this

Everything below the horizontal rule is the submission text. Five things to fill or cut first:

1. `<REPO_URL>`, `<LIVE_URL>`, `<VIDEO_URL>`, `<TEAM>` — replace throughout.
2. **Comprehend latency** in *Where AWS fits*: insert the measured number, or delete the sentence. Do not estimate it (PRD §15.3).
3. **Indic tier** sentence in *What we built* — marked `[SHOULD]`. Keep only if it is in the video. A feature described here but absent from the video does not count (PRD §12).
4. **Policy hot-reload** sentence — same rule, same marker.
5. **Bounding boxes** are not mentioned at all. If they shipped and are on camera, add one clause; otherwise leave as is.

**Length as written: ~2,100 words.** If the form caps it, cut in this order and stop when you fit — *Compliance framing* (whole section), then the Denning paragraph in *The problem*, then the last three rows of the prior-art table (keep AgentCore Policy, Dogwood and CAMP — those are the ones a judge might already know), then the *Where AWS fits* bullets down to one line each. Do **not** cut *What this does not do* or the AI disclosure. Prior art stays where it is: a judge who knows AgentCore Policy shipped will look for it, and finding it in position two rather than position eight changes how the rest is read.

---

Each call was allowed. Together they identify her. Nobody was counting.

## The problem

Most guardrails in front of an AI agent's tool calls decide one call at a time. A tool returns a name — allowed. The next returns a phone number — allowed. The next returns the last four digits of an Aadhaar — allowed, because none of them *is* an Aadhaar number. Together they identify a real person, and no control in the path noticed, because each was built to answer a question about a single payload.

The idea is old. Denning, Denning and Schwartz showed in 1979 that per-query threshold checking fails against composed queries, and the answer then was auditing across a session ([*The Tracker*](https://dl.acm.org/doi/10.1145/320064.320069), ACM TODS 4(1)). What is new is volume without a person in the loop: a human analyst runs three queries, an agent runs three hundred. Per-call redaction is necessary and insufficient.

There is a second version of the same failure. A tool returns a PDF. Comprehend takes text, so a base64 attachment passes straight through and the audit row reads "0 entities found" — while that one page carried a name, an address, an Aadhaar number and a photograph.

What a small team cannot do today is state *"an analyst may query customers, but may never accumulate enough about any one customer to identify them"* and hold a log proving it held.

## Prior art, before anything about us

We put this second on purpose. An earlier draft of this project claimed nobody governs agent tool traffic and that no guardrail carries state across calls. Both claims are false, and an adversarial research pass found six separate falsifiers.

| What exists | What it does | Where it beats us |
|---|---|---|
| [**AgentCore Policy**](https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/) (AWS, GA 3 Mar 2026, in Mumbai) | Cedar, default-deny, principal from JWT, action from the MCP tool call, decisions logged | Managed, supported, in-region, and AWS's own roadmap |
| [**Dogwood**](https://github.com/dogwood-policy/dogwood) (AWS, 6 Aug 2026) | Embeds Cedar, adds temporal operators plus `count`/`sum` over an agent's session event history, binding fields out of tool *responses*. [Wired into AgentCore Policy](https://aws.amazon.com/blogs/machine-learning/securing-ai-agents-with-temporal-policies-in-amazon-bedrock-agentcore/); one worked example is a cumulative budget per trajectory | **AWS shipped the policy substrate for this six weeks ago.** Its "information providers" are a near-exact analogue of the mechanism we build on |
| [**CAMP**](https://arxiv.org/abs/2604.16521) (arXiv, 16 Apr 2026) | Formalises Cumulative PII Exposure: session PII registry, quasi-identifier co-occurrence graph, threshold, retroactive masking | It is our pitch, five months early, and better formalised |
| [**OCELOT**](https://arxiv.org/abs/2606.12341) (arXiv, 10 Jun 2026) | Budgets how much an adversary's belief about a secret may improve across a trajectory, covering tool calls, on a tamper-evident ledger | Stronger grounding than ours |
| [**Noisegate**](https://github.com/yashmahajan10/llm-differential-privacy-gateway), [**Pipelock**](https://github.com/luckyPipewrench/pipelock), [**Purview**](https://learn.microsoft.com/en-us/purview/insider-risk-management-settings-policy-indicators) | An exact cumulative disclosure ledger per identity in front of MCP; a per-session threat score with taint escalation and numbered placeholders; 30-day cumulative exfiltration feeding DLP enforcement | All three ship. Pipelock's numbered placeholders predate ours |
| [**MaskFlow**](https://github.com/maskflow/maskflow) | Indian identifiers with Verhoeff, reversible `unmask()`, an MCP proxy masking tool arguments and unmasking results | The closest single project to this design, and it is Indian |

A separate sweep of sixteen commercial vendors found none *publicly documenting* a cumulative disclosure budget or a re-identification score that rises through a session. Six carry cross-call state, but it is **attack-sequence** state — "did A then B happen in this order" — not disclosure accumulation. We cannot prove a negative; we name what we surveyed and invite correction.

**So what is left, and it is narrow.** Nobody accumulates **per data subject**, and nobody turns that accumulation into a **redaction** decision expressed in the same policy language as the allow/deny. Purview accumulates about the actor. Dogwood accumulates *declared* event attributes — and nothing in AgentCore fills those attributes with detected entity types attributed to a person. CAMP and OCELOT accumulate correctly but are papers: no policy engine, no authorization model, no tool-boundary implementation.

The concept is published, the policy language exists, the detection exists. Nobody has connected them. That is the contribution, and the honest production path is that our ledger becomes a Dogwood information provider rather than a competitor to it.

Vocabulary note: the 2026 OWASP Top 10 for Agentic Applications numbers ASI01–ASI10, and the nearest anchors are ASI02 Tool Misuse and Exploitation, and ASI03. The list has no entry for cumulative sensitive-information disclosure.

## What we built

A Strands agent on Lambda that asks Cedar **two** questions per tool call instead of one.

**Q1, before the tool runs — may this call happen?** The vended `CedarAuthorization` intervention. A deny short-circuits.

**Q2, after the tool returns — may this principal learn this field about this subject, given what it already knows?** The tool result is normalised to markdown (text, JSON, single-page PDF), detected in tiers, and each detected entity is attributed to a data subject. One `cedarpy.is_authorized_batch` call per hop then asks one question per `(subject, field)` pair, carrying the session ledger as Cedar context. Denied fields become numbered placeholders — `[IN_AADHAAR_1]` — and the ledger spends.

Detection runs cheapest-first: a local Verhoeff check-digit test for Aadhaar and a format test for PAN at zero cost, then Comprehend `DetectPiiEntities` for everything else at a deliberately low confidence threshold of 0.5. `[SHOULD]` A third tier sends the page image to a multimodal model for regional-script text, because Comprehend does English and Spanish and Textract's OCR is Latin-script only — so the Devanagari or Tamil name printed beside the English on an Indian identity document is invisible to the rest of the stack. Any substring that model returns which is not literally present in the source is discarded, and tiers may only add findings, never clear another tier's.

**Rehydration, so the control does not break the task.** When a later call carries a placeholder in its arguments, the real value is substituted on the trusted side before the tool runs — but only if that substitution is itself authorized by Cedar against the destination tool. Without that check the guardrail is an exfiltration primitive: an injected agent emits the placeholder at an attacker-controlled destination and gets the plaintext back. An unknown placeholder fails closed and stays a placeholder.

**The default threshold is 3, and it is not arbitrary.** Sweeney found 87% of the US population uniquely identified by {gender, ZIP, date of birth} on 1990 census data; [Golle's replication](https://dl.acm.org/doi/10.1145/1179601.1179615) on 2000 data revised that to 63%. Both are three quasi-identifiers. It is configurable in policy. This is a quasi-identifier accumulator, not differential privacy, and we do not borrow that vocabulary.

**Everything lands in one audit row per tool call** in DynamoDB: principal, role, subject, tool, call decision, the deciding policy id, content type, detector tiers, entities found, masked and revealed, ledger before and after, budget, what was rehydrated, per-stage latency. No raw values and no placeholder map — the log does not become the leak it prevents.

Policy is authored on a separate control-plane Lambda and fetched with an ETag, with a copy baked into the agent's package so an unreachable control plane fails closed to a known policy rather than to no policy. `[SHOULD]` One edit there changes two running agents on their next call, with no redeploy.

## Where AWS fits

Everything runs in **ap-south-1 (Mumbai)**.

- **Lambda, arm64, Python 3.12, behind a Function URL** for both planes. Not API Gateway: the HTTP API caps at 30 seconds and an agent loop with three tool calls plus document extraction will exceed it. Function URLs give a 15-minute ceiling and HTTPS with no extra infrastructure.
- **Bedrock, Nova on the `apac.*` inference profile.** Claude on Bedrock in Mumbai is available only through a `global.*` profile, which AWS documents as able to route requests outside the source Region. A project about Indian personal data cannot ship on that, so the more capable model was ruled out by its routing profile. We say "stays in APAC", never "stays in India" — the destination Regions inside a geo profile are not published.
- **Comprehend `DetectPiiEntities`** for tier-2 detection, batched one request per hop. It carries `IN_AADHAAR`, `IN_NREGA`, `IN_PERMANENT_ACCOUNT_NUMBER` and `IN_VOTER_NUMBER`.
- **Textract `DetectDocumentText`**, synchronous with inline bytes, for single-page documents.
- **S3** via `S3SessionManager` for session state; **DynamoDB** for audit rows and the dashboard. DynamoDB holds the authoritative counter, because Strands' built-in session managers take no distributed lock and are last-writer-wins, while a DynamoDB `UpdateItem … ADD` on a string set is a server-side atomic union that cannot drop an update.
- **Cedar evaluation is `cedarpy`**, embedded in the package. It is a community binding, not an AWS library, and its own page says it is not officially supported by AWS or the Cedar team. Verified Permissions is the production answer; it adds a policy store, an IAM role and a round trip in the hot path, which is the wrong trade here.

Deployment is a plain zip and the AWS CLI, not CDK. Cost at demo scale — 500 invocations, three tool calls each, 50 document pages, at full ap-south-1 rates with no free tier assumed — is roughly **$2.25/month** on Nova Lite, and effectively zero idle. Measured Comprehend latency from ap-south-1: `<INSERT MEASURED ms — or delete this sentence>`; AWS publishes none.

Two AWS paths we rejected: **AgentCore Runtime**, because `InvokeAgentRuntime` is SigV4 or JWT only with no public URL and this submission needs a link a judge can open; and **Bedrock Data Automation**, which returns markdown and bounding boxes in one call but bills $0.010/page with no free tier and a cross-region hop.

## What this does not do

- **The principal is asserted, not authenticated.** `AuthType=NONE` on the Function URL is what makes the demo openable, and the entire policy model is principal-based. The production answer is JWT or AgentCore Identity.
- **The budget is a budget over *detected* disclosure.** A missed entity is never counted, so the ceiling never binds on it. There is no eval set. Comprehend's [AI Service Card](https://docs.aws.amazon.com/ai/responsible-ai/comprehend-detectpii/overview.html) is dated November 2023, publishes name F1 ≥0.87 / phone ≥0.88 / address ≥0.91 on internal datasets, publishes **nothing** for Aadhaar or PAN, and names degraded performance on OCR text. We make no accuracy claim for Indian identifiers.
- **Embedded images inside text-layer PDFs.** If extraction does not recurse into them, the highest-risk content passes while the audit row reads clean. This is the hole in the file story.
- **Three bypasses.** A caller can start a fresh session for a fresh budget. The subject id comes from the tool's own arguments, so a fresh id per call means a fresh budget — we canonicalise to kill the trivial variants, but real value-level identity resolution is out of scope. Both are backstopped only by a session ceiling across all subjects.
- **Entity-to-subject attribution is trivial here and hard in general.** The demo uses seeded structured fixtures; we do not claim general-purpose attribution.
- **Cross-session accumulation** by the same principal is not tracked, and **audit rows are unsigned** — this is an audit trail, not tamper-proof evidence.
- **Volume.** A spreadsheet column of 5,000 Aadhaar numbers is still text, but it exceeds Comprehend's 100 KB limit and turns one hop into a chunking loop.

## Compliance framing

India's DPDP Act 2023 and the DPDP Rules 2025 (notified November 2025) set a phased timeline, with substantive obligations for organisations commencing around May 2027 — they are not in force today. Sections 4–6 limit processing to the consented, specified purpose and to the data necessary for it, which is the principle a disclosure budget makes executable, and Rule 6 requires safeguards expressly including "encryption, obfuscation or masking or the use of virtual tokens" with logs retained for one year. Cross-border transfer is permissive — s.16 uses a negative list and no country has been notified — so redaction here is data minimisation and defence in depth, not a transfer block. Separately and already in force, Aadhaar Act s.29(4) bars public display of Aadhaar numbers, with UIDAI guidance permitting display of only the last four digits.

## Fixtures, and AI-tool disclosure

**No real personal data appears anywhere.** Every Aadhaar number, PAN, name, phone number and document in the repository, the video and the deployed demo is synthetic fixture data generated for this project.

**AI assistance.** We would rather over-disclose than under-disclose. An AI assistant (Claude) was used for three things: the research passes behind the prior-art section and the AWS findings in our blog post; drafting and editing the planning documents and this submission; and code generation and review during the build. What to build, the architecture, and every judgement about what could honestly be claimed are the team's. Every external claim here was checked against the primary source linked beside it — including the pass that falsified our own original novelty claim, which is why the prior-art section reads the way it does. The repository was created for this event, and the Verhoeff check-digit implementation was written from the published D₅ dihedral-group tables rather than copied from an existing one.

## Links

- **Live demo:** `<LIVE_URL>` (ap-south-1)
- **Repository:** `<REPO_URL>`
- **Video (3 min):** `<VIDEO_URL>`
- **Team:** `<TEAM>`
