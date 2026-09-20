# Naka — Innovation Pass

**Document 04 of the planning package** · Written 18 September 2026 · Ships Sunday 20 September, 20:00 IST
**Input:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md` (scope locked in §11)
**Purpose:** the creative pass. Cheap wow, sharper framing, transferable concepts, honest gaps, explicit kills, roadmap.
**Budget this document spends:** ~4.5 hours of build above the PRD's Must list, plus ~2 hours of promoted-from-Should work. Nothing here displaces §11.1 steps 1, 2 or 8.

---

## 0. Three corrections, now landed in the PRD

Verification for this pass turned up three factual problems in the PRD draft this document was written against. Two of them would have been attacked on camera. **All three are fixed in PRD v2** — the reasoning is kept here because it is load-bearing for the copy, not because the PRD still carries the errors.

### 0.1 The novelty sentence was false — Pipelock does carry session state

The earlier draft of §2.3 closed with *"What none of them do is carry state across calls."* [Pipelock](https://github.com/luckyPipewrench/pipelock) does. Its README documents per-agent MCP budgets over total tool calls, same-tool retries, loop detection and wall-clock duration; per-session behavioural profiling for domain bursts; a per-session threat score that escalates from warn to block; per-domain data budgets; and rolling cross-event DLP across streaming tokens. It also already emits **numbered typed placeholders** — `<pl:aws-access-key:1>` — across HTTP, WebSocket and MCP `tools/call` arguments. The placeholder design in PRD §6.2 is prior art, not invention.

A judge who has seen Pipelock (884★) and hears "nobody carries state" stops listening. The claim that survives is narrower and better:

> Pipelock budgets the **agent's behaviour** — call counts, retries, wall-clock, bytes per domain. Naka budgets what the session has learned about **a person**. One is volumetric and agent-scoped; the other is semantic and subject-scoped, and it is the only one that feeds an authorization decision.

Say "subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision" and every surveyed tool is still outside it. Say "cumulative state" and at least six of them are inside it — `01-competitive-landscape.md` §1.2 falsifies the broad version six ways, and PRD §2.3 now carries the narrow claim. **Already applied to §2.3's closing line and §4 claim 1.**

### 0.2 OWASP anchor was the wrong document

The earlier draft's §2 and §4 anchored on *"OWASP Top 10 for Agentic Applications 2026, T2 Tool Misuse."* The Top 10 for Agentic Applications (published 9 December 2025) numbers its entries **ASI01–ASI10**, and the relevant entry is **ASI02: Tool Misuse and Exploitation** ([OWASP GenAI Security Project](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [entry list](https://neuraltrust.ai/blog/owasp-top-10-for-agentic-applications-2026)). "T2" belongs to OWASP's earlier *Agentic AI — Threats and Mitigations* paper, which used T1–T15. Citing T2 against the 2026 Top 10 is the exact tell the PRD warns about in §2.3 — it reads as not having opened the document.

Worth more than the correction: **the 2026 list has no entry for cumulative sensitive-information disclosure.** ASI06 is Memory & Context Poisoning (data going *in*), ASI02 is tool misuse, ASI03 is Identity and Privilege Abuse. Nothing covers an agent legitimately accumulating a profile. That is a stronger, more honest positioning line than any novelty claim:

> "This maps to ASI02 and ASI03. The specific failure — an agent assembling an identity out of individually-permitted fields — does not have an OWASP number yet."

Applied. Anchor on **ASI02 + ASI03**, and cross-reference LLM02 Sensitive Information Disclosure from the LLM Top 10 if a second citation is wanted.

### 0.3 The Guardrails gap is documented in AWS's own words — quote it

PRD §12's 0:15–0:35 beat says to "show the AWS doc line." That line exists and it is better than the PRD assumes. From [Remove PII from conversations by using sensitive information filters](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html), verbatim:

> "This filter evaluates text content only. In tool use (function calling) workloads, it does not evaluate the following, so PII in these fields is neither blocked nor masked: PII the model generates into tool call arguments (`toolUse.input` in Converse…); PII in tool results your application returns to the model (`toolResult`); PII in the tool definitions you supply (`toolSpec.description`, `toolSpec.inputSchema`)."

Three sentences from AWS stating that the AWS control does not cover the surface Naka covers. Put it on screen as a screenshot, unedited. The same page confirms the entity list — General, Finance, IT, **USA specific, Canada specific, UK specific** — with no India-specific type at all, which is PRD §4 claim 3 verified rather than asserted.

Bonus finding on the same page, worth one line in the writeup: Guardrails' own trace output leaks what it masked — *"The `match` field in `GuardrailPiiEntityFilter` … contains the original PII value, not the masked output."* Naka's audit row (PRD §10) deliberately does the opposite. That contrast is free and it is the kind of detail that reads as having done the work.

---

## 1. Cheap wow, ranked by (judge impact ÷ build cost)

Stack: Strands interventions, `cedarpy`, Comprehend, Textract, Nova, Lambda, DynamoDB (PRD §7). Everything below is ranked, costed and tied to an exact second of the §12 video. Above the line totals **~4.5 hours**.

| # | Idea | Cost | Why it lands | Exact demo moment |
|---|---|---|---|---|
| 1 | **Counterfactual counter** | 0.5 h | Converts an abstract control into a measured outcome. You already store `entities_found` and `entities_masked` per row (§10); sum both per session. One number a judge repeats to another judge. | 2:45 close. Not on a dashboard — one line: *"This session would have disclosed 11 identifying fields about 3 people. It disclosed 5."* |
| 2 | **`@advice` on every forbid policy, surfaced in UI + audit** | 0.75 h | Cedar annotations are arbitrary `@key("value")` pairs with no evaluation impact, readable programmatically ([syntax](https://docs.cedarpolicy.com/policies/syntax-policy.html), [Policy API](https://docs.rs/cedar-policy/latest/cedar_policy/struct.Policy.html)), and `cedarpy`'s `AuthzResult.diagnostics` returns the determining policy IDs ([cedar-py](https://github.com/k9securityio/cedar-py)). So the deny reason is authored **in the policy**, not hardcoded in the UI — which is the whole "redaction is a policy decision" claim (§4 claim 2) made visible. | 1:10–1:40. The redaction chip reads: *Denied by `analyst-no-aadhaar` — "Analysts may never see an Aadhaar number. Aadhaar Act s.29(4)."* Judge sees the sentence came from the `.cedar` file edited at 2:25. |
| 3 | **Latency printed on every decision chip** | 0.25 h | `latency_ms` is already in the audit row (§10). Printing it pre-empts the unasked question that kills adoption — *does this make my agent unusable?* — and resolves PRD §15 Q3 on camera. | Every green/red chip carries `+41 ms`. Costs zero seconds of narration. |
| 4 | **`Guide()` instead of `Deny()` on budget exhaustion** | 0.5 h | Verified: `Guide(feedback=…)` is a legal action at `before_tool_call` ([Strands interventions](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/)). The agent is told *why* and replans instead of dying. This is the difference between a guardrail that breaks agents and one that steers them — and it is the answer to the second-most-common objection. | 1:40. The agent's own next message, on screen, unedited: it acknowledges the masked value and proceeds with the task. Nothing sells "tasks still complete" like the model saying so itself. |
| 5 | **Ledger rendered as a filling ID card** | 0.5 h | Best UI is judged on the same submission (§12). The disclosure meter is a bar; the same data as a partially-completed identity document is a *picture of the threat*. Same state, better grammar, no new plumbing. | 0:35–1:10. Name fills, phone fills, Aadhaar stays hatched. At 1:10 the phone field **greys back out** — the denied-now beat has a visual, not just a diff. (Narrate it as the PRD §12 rule requires: allowed at call two, denied now, gone from context going forward.) |
| 6 | **Aadhaar last-4 partial reveal as a third policy outcome** | 0.75 h | UIDAI permits display of only the last four digits ([masked Aadhaar](https://www.uidai.gov.in/en/283-faqs/aadhaar-online-services/e-aadhaar/1887-what-is-masked-aadhaar.html)). So the decision space is not allow/deny but allow/**degrade**/deny, and the degrade case is specifically Indian and specifically regulated. Placeholder machinery already exists; this is a third branch in the transform. | 2:05–2:25, on the PDF. `XXXX XXXX 8814` rather than a black box, captioned with the UIDAI rule. Proves the policy has resolution, not just a switch. |
| 7 | **`@shadow_mode` annotation = per-policy monitor mode** | 1.25 h | The strongest concept carried from the prior product (see §3). Strands has **no** built-in dry-run — verified, the intervention docs describe no audit-only mode — so this is genuinely ours. Expressing it as a Cedar annotation rather than an env var means rollout state lives in the policy, per policy. `@shadow_mode` already appears as an annotation example in Cedar's own material. | Merged into the 2:25–2:45 hot-reload beat: grey "would have redacted" chips sit next to red enforced ones; delete `@shadow_mode` on the control plane and the grey chips turn red on the next call. One beat, two features. |

**Below the line — good ideas, wrong week:**

| Idea | Cost | Verdict |
|---|---|---|
| **Re-identification % on the meter** instead of a raw count | 1 h | The grounding is real (see §2) but rendering it as a percentage claims a risk *model* you have not built or validated, and PRD §14 already flags that borrowing privacy-math vocabulary invites unanswerable questions. **Keep the count on the meter; put the literature in the one sentence that explains why the default is 3.** |
| **Deliberate Verhoeff near-miss in the fixtures** | 0.33 h | Demonstrates §8's checksum-as-confidence-signal nuance. Genuinely good with a technical judge, but it needs 8 seconds of narration the video does not have. Build the fixture, mention it in the writeup, cut it from the video. |
| **Cross-session, cross-agent subject ledger** | ~2 h | The highest-concept idea in this document and it is not an innovation item — it is a scope decision. See §1.1. |
| **Textract bounding-box overlay** (PRD §11 Should #13) | 1.5–2 h | Cut. See §5. |
| **SSE live decision feed** | — | Impossible cheaply. Verified: Lambda response streaming is native to Node.js runtimes only; Python needs a custom runtime or the Lambda Web Adapter ([response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)). Poll at 1 s. Do not spend Sunday discovering this. |

### 1.1 The one idea that deserves a scope decision, not a ranking

**Make the ledger subject-scoped rather than session-scoped.** Agent A (a support bot) learns the customer's name. Agent B — different session, different agent, same customer — is then denied the phone number.

This is the sharpest possible statement of the thesis: *the budget is a property of the person, not of the conversation.* It is also the version an enterprise would actually buy, and it makes the control plane's existence self-evidently necessary rather than argued for in PRD §5.

Cost: the ledger's key becomes `(subject, principal)` in DynamoDB instead of living only in `S3SessionManager` state — roughly 2 hours, and it touches §11.1 step 7, which is already the riskiest non-packaging step.

**Recommendation: promote to §11 Should, guarded.** If step 7 (ledger survives a second HTTP request) is green by Saturday evening, build it — it upgrades the 2:25 beat from "both agents changed policy" to "both agents share one person's budget," which is a categorically better sentence. If step 7 slips past Saturday evening, demo two sessions of the same agent and say the subject-scoped version is next. Do not attempt it Sunday.

---

## 2. The idea behind the idea

### 2.1 Testing the alternatives

| Framing | Verdict |
|---|---|
| **Least privilege for data, not actions** | **Adopt as the hook, not the name.** It drops the project into a mental model every judge already owns, and it names the gap in one line: *forty years of authorization deciding who may call what, and nobody deciding what may come back.* But it describes the layer, not the novel part — it contains no notion of accumulation. It is the first sentence of the pitch; it is not the product noun. |
| **Data-egress trip meter** | **Reject.** "Trip meter" implies volume and implies reset. Both are wrong: this counts *which attributes*, not how many bytes, and Pipelock already owns volumetric budgets (§0.1). Adopting this framing walks into a competitor's strength. |
| **Purpose-bound access** | **Adopt as a mechanism, not a framing.** Purpose is stateless — it is one more Cedar context attribute, and every policy engine can already express it. It does not need the ledger and therefore cannot be the thesis. But it costs ~20 minutes (one field in the enricher, one `when` clause) and it unlocks the strongest sentence in PRD §13: DPDP ss.4–6 limit processing to the consented, specified purpose, and `context.purpose == "refund_processing"` is that principle rendered executable. Build it as a complement. |
| **Consent as a runtime constraint** | **Reject for the hackathon.** There is no consent artefact, no data principal, no consent manager in the build. A judge who works on DPDP asks where the consent record lives and there is no answer. It is the right three-month item (§6), and claiming it now is the kind of overreach PRD §13 spends a page avoiding. |
| **Re-identification risk as a first-class metric** | **Adopt as the grounding. This one changes the PRD.** See below. |
| **"Agentic DLP"** | **Keyword only, never the thesis.** PRD §2.3 is right that it is the established vocabulary for discoverability. As framing it is fatal — it files the project into a crowded commercial category (Bedrock Data shipped Agent DLP on 30 July 2026) and invites *"so, another DLP."* Use it in the writeup's keywords and in the repo description. Never in the first thirty seconds of the video. |

### 2.2 The correction: the threshold was grounded in the wrong literature

An earlier §6.3 grounded the default budget of 3 on **HIPAA Safe Harbor's 18 identifiers**. That is the wrong citation, and a privacy-literate judge would have noticed. **PRD v2 §6.3 now carries the correction below.** Safe Harbor is a list of *what counts as an identifier* and an instruction to remove **all eighteen**. It says nothing about how many it takes to re-identify someone. It cannot justify the number 3.

The literature that does justify 3 is the demographic-uniqueness work:

- Sweeney (1990 census data): **87%** of the US population uniquely identified by {gender, 5-digit ZIP, full date of birth} ([Latanya Sweeney](https://en.wikipedia.org/wiki/Latanya_Sweeney)).
- Golle (2000 census data, revisiting Sweeney): **63%** on the same three attributes ([Revisiting the Uniqueness of Simple Demographics, WPES'06](https://crypto.stanford.edu/~pgolle/papers/census.pdf)).

**Three quasi-identifiers. Between 63% and 87% unique.** That is where the number 3 comes from, it is peer-reviewed, and citing both figures — including the one that revises the famous number downward — is exactly the move that reads as having read the source rather than the tweet about it.

The grounding is swapped in §6.3. Safe Harbor stays as the answer to "which fields count as identifying," which is what it is actually good for. **PRD §14's risk table still says "ground on HIPAA Safe Harbor's 18 identifiers" — read that as the field list, not the threshold.** The resulting sentence is one line and it is bulletproof:

> "The default budget is three fields because three demographic attributes uniquely identify most of a population — 87% in Sweeney's 1990 figure, 63% in Golle's 2000 recount. HIPAA Safe Harbor's eighteen identifiers tell us which fields to count. This is a quasi-identifier accumulator, not differential privacy."

### 2.3 Verdict on the framing

**"Disclosure budget" survives.** It is a concrete noun, it is a UI object, it implies spend and exhaustion without explanation, and a budget is the only privacy metaphor a non-specialist already operates daily. Nothing in the alternatives is better *as a name*.

What should change is the **positioning line**, not the name. PRD §1 currently leads with "cumulative disclosure control," which is accurate and inert. Lead with:

> **Least privilege for data — with memory.**

*Least privilege* places it instantly. *For data* names the gap: authorization stops at the verb. *With memory* is the entire novelty in one word, and it is precisely the word every surveyed competitor lacks, including Pipelock once §0.1 is applied correctly.

If pushed by a judge on what is really being budgeted, the honest answer is **identifiability**, not data. Do not rename *the phrase* two days out — the PRD, the repo, the UI and the video script all say disclosure budget, and renaming the mechanism on Friday buys nothing and costs an afternoon. (The *project* name did change — see `05-gtm-and-positioning.md` §4: `Chowki` collided with a PyPI package in the same category, so the project is **Naka**. That is a find-and-replace, not a re-framing.)

---

## 3. Concepts from the prior endpoint AI-DLP product

Five concepts offered. Two transfer outright, one transfers reshaped, two should not transfer. Only concepts move; no code.

### 3.1 Monitor mode vs enforce mode — **transfer, strongest of the five** · 1.25 h

Verified: Strands interventions have **no** dry-run, audit-only or monitor mode. This has to be built, and at hackathon scale it is one flag on the decision path — compute the decision, write the audit row, return `Proceed`.

Why it strengthens *this* project rather than any project: the number-one objection to a **cumulative** control is that its firing point is unpredictable. A per-call rule is easy to reason about; a rule that trips on the fourth call because of what happened on calls one through three is not. Monitor mode is the only honest answer to *"how do I roll this out without breaking my agent,"* and it is the first question any security buyer asks.

It also pays twice: shadow-mode rows are what produce idea #1's counterfactual number for free, and expressing it as a per-policy `@shadow_mode` annotation (idea #7) rather than a global flag means the rollout state is authored in the policy language, which is on-thesis rather than beside it.

### 3.2 Real-time approval overlay — **transfer the shape, not the surface** · and know the constraint

Strands ships this: `Confirm(prompt=…)` and a vended `HumanInTheLoop` handler that integrates with the SDK's interrupt/resume system, and the docs confirm it works in stateless deployments when combined with a session manager ([human in the loop](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/human-in-the-loop/)) — which Naka already has via `S3SessionManager`. Roughly an hour of work.

**The constraint that will otherwise eat someone's Sunday:** `Confirm` is legal at `before_tool_call`. `after_tool_call` permits **only** `Proceed` and `Transform`. The field-level disclosure decision (Q2, PRD §5 step 7) happens at `after_tool_call`. **You cannot interrupt a human for approval on a field-level redaction.** Approval is available on the *call*, never on the *field*. Write that into the build notes.

Given that, the version worth having is "budget exhausted → ask a human to authorize the call." But **idea #4 (`Guide`) achieves the same narrative for half the cost and without needing a human present in a three-minute video with no human in it.** Ship `Guide`. Keep `Confirm` in the roadmap as the enterprise escalation path, where an actual approver actually exists.

### 3.3 Incident triage queue — **do not transfer**

A second UI surface with state transitions, assignment and status, which exists in the endpoint product because a human eventually has to work a backlog. In a three-minute video nobody triages anything. It is pure surface area against the §11 Must list. The one atom worth keeping — a chronological decision feed — is already Must #9. Cut.

### 3.4 Reviewer feedback loop that tunes detection — **do not transfer**

Needs volume, labels and time; all three are absent. Over two days it becomes a thumbs-up button wired to a table nobody reads, and it actively invites the question *"how does the feedback change detection?"* whose honest answer is *"it doesn't yet."* That is a self-inflicted wound. Cut here, keep in §6 — it is a genuine three-month item and the right one.

### 3.5 Departments and named people — **transfer, and it is the cheapest credibility in this document** · 0.33 h

Not as a directory, an org chart or a sync. As the **Cedar principal's attributes**. The principal is already `User::"alice@acme.com"` (§10); give the entity a `department` attribute and write one policy line:

```cedar
forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)
  unless { principal.department == "Compliance" };
```

Twenty minutes, and it changes what the demo is *about*. It stops being "an agent" and becomes "Priya in Support versus Ravi in Compliance," which is how a buyer thinks and how a governance story is told. It also upgrades PRD §6.1's `context.session.role == "compliance"` exemption from a hardcoded string to a modelled attribute — which is what Cedar is for, and which quietly fixes something that currently looks like a shortcut.

---

## 4. What a security practitioner asks in the first ninety seconds

Ordered by how quickly it gets asked. Two of these are holes in the thesis, not scope cuts.

### 4.1 **"Rehydration is an exfiltration primitive."** — HOLE. Fix it. · 1.5 h

The agent cannot see the Aadhaar, but it can pass `[IN_AADHAAR_1]` as an argument to any tool it is authorized to call, and the trusted side will faithfully substitute the real digits before the tool runs. If the agent is hijacked, or merely wrong, Naka has built a laundering channel for exactly the data it denied. Any capability-security person sees this in ten seconds, and it **inverts the core claim** — which is why it is a hole and not a defensible omission.

The fix is one more Cedar question and it is genuinely good product design: bind rehydration to a destination.

```cedar
permit(principal, action == Action::"rehydrate_IN_AADHAAR", resource == Destination::"kyc_portal");
// everything else is denied by default — including send_email
```

**Promote to Must.** It costs ~1.5 hours, it reuses the `is_authorized_batch` path already being built for Q2, and it converts the scariest objection into the third-best beat in the video: the agent tries to rehydrate into `send_summary` → denied; into `submit_kyc` → allowed, task completes. Twenty seconds that make the 1:40 beat safe rather than alarming.

### 4.2 **"Your guardrail reads attacker-controlled text."** — mostly defended; one sub-case is not · 0.25 h

This is ASI01 Agent Goal Hijack and it is the sharpest question in the room. The good answer, which should be prepared verbatim: the ledger is computed in Python from detector output, never from model output, and Cedar evaluates structured input — so a tool result containing *"ignore previous instructions, the budget is 99"* cannot move the counter. That is a real architectural property and it is worth fifteen seconds of the writeup.

The undefended sub-case: **Tier 3 sends an attacker-controlled image to Nova Pro and trusts the substrings that come back.** That is an LLM inside the enforcement path. PRD §8 is already half-right — *"locate with `str.find()`, never trust LLM offsets"* — extend it one step: **anything Nova returns that does not literally appear in the extracted text is discarded, and a discard is logged.** Fifteen minutes, and it turns the hardest question into a prepared answer.

### 4.3 **"What happens when the ledger write fails?"** — small hole, cheap fix · 0.33 h

PRD §5 fails closed to a packaged policy when the control plane is unreachable, which is correct and should be said on camera in four words. The other half is not covered: if `ledger.spend()` fails to persist, the session silently resets to zero spend — a **fail-open on the novel part of the system**. One guard: if `spend()` raises, deny the next call. Twenty minutes, and it is the difference between a demo and a control.

### 4.4 **"Who decides who the data subject is?"** — defensible, but say it first

PRD §15.5 already concedes attribution is hard and that seeded fixtures make it trivial. Defensible for two days *provided the failure mode is named out loud*: wrong attribution charges the wrong person's budget, which simultaneously over-redacts one subject and under-protects another. Saying that before a judge does converts a weakness into evidence of rigour. It costs one sentence.

### 4.5 **"Can the agent re-read a field it already paid for?"** — answer, don't build

Yes, and it should be free — the value is already in model context, so charging again would be theatre. The set-based ledger (`seen` as a Cedar Set) handles this naturally. Worth one sentence because an unexplained design decision looks like a bug.

### 4.6 Absent and defensible for a two-day build — acknowledge, do not build

| Gap | The one line that defuses it |
|---|---|
| No authentication | "The principal is asserted, not authenticated. Production is a JWT, same as AgentCore Policy." Silence here reads as not having considered it. |
| No multi-tenancy | Already §11 Will-not. Uncontroversial at hackathon scale. |
| No key management for the placeholder→value map | It is per-invocation, in-process, never persisted, never in an audit row (§6.2, §10). That *is* the answer. |
| No ledger TTL or expiry | Named as roadmap. |
| Nothing on the write direction — data going *into* prompts | The honest scope statement: Naka governs the tool boundary, not the prompt. Bedrock Guardrails covers the prompt and is complementary, not competing. Saying this makes the §0.3 Guardrails critique land as precision rather than as a swipe. |
| No erasure / revocation | Cheapest of the lot: **the ledger is keyed by subject, so a DPDP erasure request is one key delete.** One sentence, zero build, and it is the item most likely to be raised by anyone who does DPDP work for a living. |

---

## 5. Kill list

A hackathon two days out dies of scope. Each of these is a specific temptation with a specific hour cost.

| Kill | Why |
|---|---|
| **MCP server mode** | The highest-gravity scope creep in the project. *"Make it an MCP proxy and it works with any agent"* is genuinely the right product — and it is fatal on Saturday. Already §11 Will-not; kill it loudly, because it will be re-proposed. It is §6 item 1. |
| **Textract bounding-box overlay** (§11 Should #13) | 1.5–2 h, competes for the same demo seconds as the before/after diff, and demonstrates Textract rather than the thesis. The disclosure meter and the ID card (idea #5) already carry Best UI. **Cut, not deferred** — deferring it means someone starts it at 16:00 Sunday. |
| **SSE / live streaming feed** | Verified impossible cheaply on Python Lambda. Poll at 1 s and move on. |
| **Any actual re-identification risk model** | §2.2 makes the literature tempting. The citation is free; the model is a trap, and PRD §14 already names it. Cite Golle and Sweeney; compute nothing beyond a count. |
| **Incident triage queue · reviewer feedback loop** | §3.3, §3.4. Two UI surfaces and a labelling pipeline for zero demo seconds. |
| **Amazon Verified Permissions** | §11 Will-not, but it will be re-proposed on Sunday as *"shouldn't this use the real AWS service?"* It adds a policy store, an IAM role and a round trip in the hot path, and `CedarAuthorization` does not use it. Name it as the production path in the writeup; do not build it. |
| **Multi-page PDF, DOCX, async Textract** | Normalization is where scope creep enters — *"just add DOCX"* is a two-hour tar pit with no new demo beat. §11 Will-not, restated because §9 makes it look easy. |
| **A second demo scenario** | One scenario told well beats two told fast in 180 seconds. |
| **Re-framing the mechanism** | §2.3. "Disclosure budget" is the right phrase; changing it costs an afternoon across the PRD, repo, UI and script and buys nothing. *(The project name itself did change — `Chowki` → `Naka`, forced by a same-category PyPI collision, `05-gtm-and-positioning.md` §4. That is twenty minutes of find-and-replace, not a re-framing, and it was worth it.)* |
| **Real Aadhaar numbers in fixtures** | Not scope — legal. A public repo containing a genuine-looking Aadhaar is an own goal in an Indian hackathon judged partly on compliance literacy. Generate Verhoeff-valid numbers that are not issued, and say so in the README. |

---

## 6. Post-hackathon roadmap

**The one-sentence answer when a judge asks "what's next," which is the only version that gets heard:**

> "Ship it as an MCP proxy so any agent gets it without a code change, and make the ledger subject-keyed and shared — which is the version an enterprise actually buys."

### If it wins — three months

The prize is ₹2,00,000 plus $3,000 in AWS credits, and the credits fund exactly one thing: the item that had to be killed in §5.

1. **MCP server mode.** The ledger as a sidecar in front of any MCP server. This is the only form in which someone else adopts Naka without rewriting their agent, and it is therefore the whole product. Everything else is a feature of it.
2. **Ledger as a service.** Subject-keyed, cross-agent, cross-session, with TTL and erasure — §1.1 built properly rather than guarded. Moves from `S3SessionManager` state to DynamoDB partitioned on subject.
3. **AVP, JWT principals, multi-tenancy.** The three §11 Will-nots that are only Will-nots because of the clock. AVP is already named as the production answer in PRD §7, so this is a promise being kept rather than a pivot.
4. **Attribution.** Entity resolution from tool output to a subject identity — PRD §15.5's concession, promoted to the roadmap's hard problem. This is where the accuracy story lives and where a moat could exist; everything above it is engineering.
5. **The reviewer feedback loop** from §3.4, which becomes viable the moment there is volume to label.
6. **Publish the gap.** The observation that Bedrock Guardrails covers no Indian entity types and does not evaluate tool fields — while Comprehend carries `IN_AADHAAR`, `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER` and `IN_NREGA` — is a blog post AWS's own India team will amplify, and §0.3 means it is already written. Same for the Claude-routes-globally finding in PRD §2.2.

### If it does not win — three months

Nothing in the list changes. The *reason to continue* does, and it should be stated concretely rather than as persistence.

This build is a spike on a question the team's existing product already has open. The endpoint AI-DLP system governs browser traffic, where the economics are structurally flat — and the identified unlock is extending governance to API and agent traffic. **Naka is that control surface, prototyped end to end in two days on someone else's deadline.** On a loss, the two-question Cedar pattern and the disclosure ledger fold into the existing policy/audit server as its agentic tier, and the hackathon has cost a weekend and returned a validated design plus a working deployment.

Item 6 is unconditional. The Guardrails tool-field finding and the Claude-routes-globally finding are independently publishable, cost nothing further, and are worth more than the ₹2,00,000 to a company selling AI governance in India.

---

## Sources beyond the PRD

**Verified for this pass** — [Bedrock Guardrails sensitive-information filters (tool-use exclusion note, entity list, trace `match` leak)](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html) · [Strands interventions — Proceed/Deny/Guide/Confirm/Transform and per-hook legality](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/) · [Strands human-in-the-loop — `Confirm`, interrupt/resume, stateless deployments](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/human-in-the-loop/) · [Cedar policy syntax — annotations](https://docs.cedarpolicy.com/policies/syntax-policy.html) · [Cedar `Policy` API — reading annotation values](https://docs.rs/cedar-policy/latest/cedar_policy/struct.Policy.html) · [cedar-py — `AuthzResult`, diagnostics, batch ordering, `correlation_id`](https://github.com/k9securityio/cedar-py) · [Lambda response streaming — Node.js runtimes only, Python needs custom runtime or Web Adapter](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html) · [OWASP Top 10 for Agentic Applications 2026 — ASI01–ASI10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [ASI entry titles](https://neuraltrust.ai/blog/owasp-top-10-for-agentic-applications-2026) · [Pipelock — per-session threat score, per-agent budgets, typed placeholders](https://github.com/luckyPipewrench/pipelock) · [LangChain `PIIMiddleware` source — `apply_to_tool_results=False` default, no cross-call accumulation, irreversible except deterministic hash](https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/pii.py) · [AgentCore Policy — Cedar over tool invocations, context is tool input parameters](https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/)

**Re-identification grounding** — [Golle, *Revisiting the Uniqueness of Simple Demographics in the US Population*, WPES'06 — 63% on 2000 census](https://crypto.stanford.edu/~pgolle/papers/census.pdf) · [Latanya Sweeney — 87% on 1990 census, k-anonymity](https://en.wikipedia.org/wiki/Latanya_Sweeney)

**India** — [UIDAI masked Aadhaar — last four digits only](https://www.uidai.gov.in/en/283-faqs/aadhaar-online-services/e-aadhaar/1887-what-is-masked-aadhaar.html) · [Comprehend PII entity types including `IN_AADHAAR`, `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER`, `IN_NREGA`](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html)
