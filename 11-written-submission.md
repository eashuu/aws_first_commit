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

## What is running, and what is provisioned but gated

We would rather state this plainly than have it discovered.

**Both Lambdas are deployed and healthy in ap-south-1**, `/health` returns 200 on each, and a real request traverses the entire stack — Cedar policy load from S3, DynamoDB ledger read, agent assembly with all three interventions installed. `selfcheck.py` is green. **`livecheck.py`, which exercises real AWS rather than mocks, is 24 passed, 0 failed, 6 skipped** — and all six skips are the same three services.

**Three AWS AI services are gated on this account pending verification**, which is an account-provisioning state and not a defect in the build:

| | |
|---|---|
| Bedrock Converse (`ap-south-1`) | `AccessDeniedException` — "your account is currently being verified" |
| Comprehend `DetectPiiEntities` | `SubscriptionRequiredException` |
| Textract `DetectDocumentText` | `SubscriptionRequiredException` |
| Lambda concurrency | 10 rather than 1000 |
| DynamoDB · S3 · Lambda · IAM | all working, same credentials |

This is [documented AWS behaviour](https://repost.aws/knowledge-center/bedrock-invokemodel-api-error) for a new account without billing history — AWS states that such restrictions "don't appear in the Amazon Bedrock console and can't be resolved through IAM permissions or model access settings," and that the only route is a support case.

**The configuration is correct and waiting, not wrong.** `aws bedrock list-inference-profiles --region ap-south-1` returns `apac.amazon.nova-lite-v1:0` and `apac.amazon.nova-pro-v1:0` — our `MODEL_ID` and `INDIC_MODEL_ID` — both **ACTIVE**. That call needs no model entitlement, so it succeeds while the account is gated, which is precisely what makes it evidence: the profiles exist, the IDs are right, and the only thing between this and a live model call is account verification.

The console reports this itself rather than claiming it. A `GET /diag` route probes each service server-side and renders a per-tier state, with gated services shown as **not run**, in neutral grey, never as a failure — because a provisioning state is not a defect. What you see on the tier table is a live answer about this account at the moment you load the page, not a claim baked into the HTML.

**What this does and does not cost us.** Tier 1 — the local checksum detectors for Aadhaar, PAN, GSTIN, IFSC and voter ID — is ours and runs regardless. Cedar authorization, the per-subject ledger, placeholder substitution and the rehydration check are all deterministic and none of them calls a model. **The enforcement path is intact.** What is unavailable is tier-2 and tier-3 detection breadth, document OCR, and the agent's own narration.

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

## What we learned

Five things we did not know on Thursday. Each one changed the build.

**1. The service that has Indian identifier types cannot read Hindi, and the service that reads Hindi has no Indian identifier types.** We assumed Amazon Comprehend would carry the detector. Its `DetectPiiEntities` API accepts `LanguageCode="hi"` — the enum lists it — but the developer guide says English and Spanish only, so the call succeeds and does not do what you want. Bedrock Guardrails' sensitive-information filter *does* support Hindi, one of seventeen languages, and has no `IN_AADHAAR` or `IN_PERMANENT_ACCOUNT_NUMBER` at all; Indian identifiers there mean hand-written regex, and lookarounds are unsupported. Neither service covers the case on its own. That is why tier 1 is our own checksum layer and why the tiers union rather than defer to each other — an architecture we arrived at by being wrong first.

**2. A published API enum is not a support matrix, and an exclusion note three paragraphs down is where the real boundary lives.** The Guardrails page states plainly that the filter does not evaluate `toolUse.input`, `toolResult` or `toolSpec` — the three fields that *are* an agent's data surface. We had already built toward that boundary; finding AWS documenting it in its own words was the moment the project stopped being a guess. The general lesson, which cost us hours before it saved us more: read the limitations section before the feature section.

**3. Deployment failures impersonate code failures.** A Lambda Function URL needs both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` granted; the console adds both, the CLI adds neither. The resulting 403 reads exactly like an application bug. Worse, `--function-url-auth-type` is only valid on `InvokeFunctionUrl` — pass it to both in one script and the second call is rejected outright, so you silently add one statement and the URL 403s forever. We lost real time to this before reading the rejection instead of the symptom.

**4. A published layer ARN is not a version guarantee.** The AWS-managed Strands layer is `strands-agents-py3_12-aarch64` — underscore, and `aarch64`, not the `py3.12-arm64` form we first wrote. Version 2 of that layer ships strands-agents 1.40.0, which does **not** contain `strands.vended_interventions`; `CedarAuthorization` needs ≥1.44. So the managed layer cannot supply the one class the design depends on, and the deployment zip has to bundle it. Check what a layer actually contains, not what its name implies.

**5. On a new AWS account, the AI services are gated together and the failure modes are not alike.** With identical credentials, DynamoDB, S3, Lambda and IAM all worked while Bedrock returned `AccessDeniedException` ("your account is currently being verified") in one region and `ValidationException` in another, and Comprehend and Textract both returned `SubscriptionRequiredException`. A Lambda concurrency limit of 10 instead of 1000 is the tell that it is account verification, not IAM and not region. The design lesson we took from it is the one we would keep in production: every model-dependent step needs a deterministic fallback behind a flag, and the enforcement path should never be the part that depends on a model. Ours does not — Cedar and the checksum tier decide; the model only narrates.

**6. A smooth-scroll library can silently starve three unrelated mechanisms at once.** Lenis suppresses native scroll events on `window` entirely — measured on the deployed page, `window.scrollY` advances to 1600 while a `window` `'scroll'` listener fires exactly zero times. That broke GSAP ScrollTrigger, then IntersectionObserver, then a hand-written scroll handler, in that order: three fallbacks that all looked independent and were all waiting on the same signal that never arrives. The fix is a requestAnimationFrame poll re-armed on `visibilitychange`, `scroll` and `resize`. The transferable lesson is about fallbacks, not about Lenis — a fallback chain is only as good as its assumption that each link fails for a *different* reason. A related one from the same afternoon: renaming a CSS custom property broke every status pill in the console with no error anywhere, because custom properties fail silently and a no-build stack has nothing to catch it.

**What we would do differently.** We spent the first pass arguing that the mechanism was novel. A research pass falsified that — the concept is published (CAMP, OCELOT), and AWS shipped the policy substrate weeks before we started. Rewriting the claim to the narrow thing that survived took an afternoon and made every other document easier to write. We should have tried to falsify it on day one instead of day two.

## Links

- **Live demo:** `<LIVE_URL>` (ap-south-1)
- **Repository:** `<REPO_URL>`
- **Video (3 min):** `<VIDEO_URL>`
- **Team:** `<TEAM>`
