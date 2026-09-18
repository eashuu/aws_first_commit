# Pitch Deck

**Project:** Naka — disclosure budgets for AI agent tool calls
**Parent document:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md`. The video script in Part A is aligned to the demo beat sheet in PRD §12. Positioning language comes from `05-gtm-and-positioning.md` §5.
**Written:** 18 September 2026 · **Ships:** Sunday 20 September 2026, 20:00 IST

---

## What is in this document, and which part is judged

There is no pitch session at this hackathon and no live demo. Judging is on a public repo, a written submission, and a **YouTube video of three minutes or less**. So there are two different artifacts here and they should not be confused:

| Part | What it is | Who sees it | Priority |
|---|---|---|---|
| **A — the three-minute video script** | A timed narration and shot list for a screen-recorded demo | The judges. **This is what gets scored.** | **Primary.** Everything else is secondary to this. |
| **B — the eleven-slide deck** | Slides for a room with people in it | Whoever the team presents to afterwards — an Amazon interviewer from the fast-track slots, a recruiter, an investor | Build after Sunday. Do not spend Saturday on it. |
| **C — the written submission** | The text field on the submission form and the repo README | The judges, alongside the video | Half a page of guidance, at the end. |

A hard constraint from PRD §12 that governs Part A: *a feature described in the writeup but absent from the video does not count.* If it is not on camera it does not exist.

---

# PART A — the three-minute video script

## A.0 Production rules

- **Three minutes is a ceiling, not a target.** Cut to 2:50 and leave headroom. A video that runs 3:04 may be disqualified.
- **Screen recording with voiceover.** No face cam, no intro animation, no music under speech. If music is used at all, it goes under the cold open only and drops out when the voice starts.
- **Burn in captions.** Judges watch on phones and often muted. Every on-screen text cue below is doing work whether or not the audio is playing.
- **Record the narration separately from the screen capture** and cut the screen to the audio. Trying to narrate live while driving a demo is how a 3-minute video becomes a 4-minute video.
- **Pace:** the script below is 388 words over 180 seconds — about 129 words per minute. That is deliberately unhurried. Demo videos always run long; being under is the correct error.
- **Never say the product name as a bare word.** Per `05-gtm-and-positioning.md` §4, the on-screen title is `Naka — disclosure budgets for agent tool calls`.

## A.1 The first fifteen seconds, and why this is the strongest opening available

**The open:** a scanned Aadhaar card fills the frame. Cut to three green ALLOW rows in the decision feed. Two sentences of narration.

**Why this one:**

1. **It is a real object, not a diagram.** Every Indian judge recognises an Aadhaar card instantly and needs no setup to know what is at stake. An architecture diagram at 0:03 asks the viewer to do work before they care.
2. **It puts the viewer next to the person whose data it is,** not next to the developer's stack.
3. **It states a mechanism, not a category.** "Each call was allowed. Together they identify her. Nothing was counting the total." A judge can repeat that to another judge after hearing it once. That is the only real test of a hook — not whether it is exciting, but whether it survives being relayed.
4. **It needs no vocabulary.** A viewer who has never heard of Cedar, Strands or MCP understands it completely.
5. **It contains the punchline in compressed form.** Someone who stops watching at 0:20 still leaves with the idea. Given how many submissions a judge works through, assume many viewers are that person.
6. **It puts the hardest thing first.** The aggregation problem is the one thing here that is genuinely difficult to explain. Spending the freshest fifteen seconds on it, rather than on a logo, is the whole strategy.

**What was rejected, and why:**

- *"Hi, we're team X from Y college."* Zero seconds of this. The team name goes on screen as a lower-third at 0:45 while something is happening. Every second of introduction is a second not spent on the mechanism.
- *A statistics slide about data breaches.* `05-gtm-and-positioning.md` §8 explains why there is no defensible number for this failure mode. Opening on a number we cannot defend invites the first question to be an attack.
- *Opening on the architecture diagram.* It is the second-most-impressive thing in the project and the least legible in fifteen seconds. It belongs at 2:25, when the viewer already knows what it is for.
- *Opening on the competitor gap.* Stronger than a logo, weaker than the card — it requires the viewer to already care about agent guardrails. Establish the harm first, then the gap. That is why the gap is beat 2 and not beat 1.

## A.2 The script

Timings are cumulative and to the second. Word counts are given so the recording can be checked against the clock rather than guessed at.

---

### Beat 1 — 0:00–0:14 · Cold open (32 words)

**Headline (on screen):** `Each call was allowed. Together they identify her.`

**On screen:** A scanned Aadhaar card, filling the frame, held for three seconds with no narration. Then a hard cut to the decision feed showing three rows, all green, all `ALLOW`. No UI chrome yet — just the three rows.

**Narration:**
> This scanned Aadhaar card is sitting in your support queue. Your agent is about to read it.
>
> Three tool calls. Each one approved. Together they identify her. Nothing was counting the total.

**Speaker notes:** Three full seconds of silence on the card before the first word. Silence is the cheapest way to make an opening feel deliberate. Deliver the second paragraph flat — the content is doing the work and emphasis will make it sound like a sales pitch. Use a plainly synthetic card: seeded fixture data only, never a real Aadhaar number, and say so in the README.

---

### Beat 2 — 0:14–0:30 · The gap, precisely (38 words)

**Headline (on screen):** `The controls that exist decide one call at a time.`

**On screen:** Split frame. Left, the AgentCore Policy GA announcement with the date visible. Right, the AWS documentation page for Guardrails sensitive-information filters, with the relevant line highlighted in the live browser — not a screenshot, and not a re-typed quote.

**Narration:**
> AgentCore Policy went GA in March. It decides whether a tool call may happen. It doesn't decide what the result may reveal. And Bedrock Guardrails' PII filter doesn't evaluate tool fields — it has no Indian entity types either.

**Speaker notes:** This beat is insurance. PRD §14 names "judge knows AgentCore Policy shipped" as the risk that collapses the novelty claim. Naming it in the first thirty seconds converts that risk into a credibility signal. Show the AWS page in a real browser so it is visibly the documentation and not our characterisation of it. Do not say "nobody does this", and do not say "nobody carries state across calls" — several do (Dogwood, Pipelock, Purview). The claim is *subject-scoped* accumulation feeding a redaction decision, and it comes later, once the demo has shown what that means.

---

### Beat 3 — 0:30–0:44 · Why Nova, not Claude (36 words)

**Headline (on screen):** `A project about where Indian data goes can't ship on a globally routed model.`

**On screen:** The AWS documentation line stating that the `global.` inference profile can route requests outside the source Region, highlighted live. Hard cut to one line of the team's own code: `model = "apac.amazon.nova-lite-v1:0"`.

**Narration:**
> We're in Mumbai. Claude on Bedrock here is global-profile only — AWS says that can route outside the region. A project about where Indian data goes can't ship on that. So: Nova, on the APAC profile — which stays in APAC.

**Speaker notes:** PRD §4 says this is worth its own line in the video, and it is the most quotable fourteen seconds in the whole submission. **Say "stays in APAC", never "stays in India"** — the destination regions inside an APAC geo profile are not published, and a judge who runs `get-inference-profile` and sees Tokyo punctures the over-claim in one sentence. The accurate version is already strong enough. It is not a criticism of any model — it is a routing fact that changed a build decision, which is what makes it interesting. The tell that a team read the documentation rather than the marketing page is a decision that *cost them something*: the more capable model was ruled out by its own routing profile. Say it without editorialising and let the doc line on screen carry it.

---

### Beat 4 — 0:44–1:12 · Three calls, and the meter fills (51 words, leaving room to slow down)

**Headline (on screen):** `1 of 3 … 2 of 3`

**On screen:** The agent running for real. Live decision feed on the left, disclosure meter per data subject on the right. The meter is the hero object: it must be large, it must animate on each call, and the subject identifier (`cust_8814`) must be legible. Lower-third with the team and project name appears here and holds for four seconds.

**Narration:**
> Here's an analyst asking about a customer. First call returns a name. Cedar allows it. The meter for this customer moves to one of three. Second call, a phone number. Allowed — two of three. Each decision is fine on its own. That's the point. Every guardrail we surveyed would allow both.

**Speaker notes:** Resist speeding up here. The viewer has to feel the meter filling or beat 5 does not land. "Every guardrail we surveyed" is the exact hedge to use — it is a claim about what was examined, which PRD §2.3 documents, rather than a claim about everything that exists.

---

### Beat 5 — 1:12–1:42 · The budget is spent, and a field that passed is denied now (57 words)

**Headline (on screen):** `Allowed at call two. Denied now.`

**On screen:** The fourth call returns an Aadhaar number. The meter hits 3 of 3 and changes state. The before/after diff shows `[IN_AADHAAR_1]` — and, in the same frame, the previously-allowed phone number becoming `[PHONE_2]`. **Both redactions must be visible simultaneously in one uncut shot.** If necessary, slow the playback rather than cutting between them.

**Narration:**
> Fourth call. An Aadhaar number comes back. The budget is spent, so Cedar denies it — and watch the phone number. It was allowed at call two. It's denied now, and it's gone from the context going forward, because the decision isn't about this payload. It's about what this analyst has already learned about this one person. That's a second question, and answering it needs memory.

**Speaker notes:** PRD §12 calls this "the beat that wins it." Everything before exists to set it up and everything after exists to show it is real rather than staged. Land on "needs memory" and hold the frame for a beat before cutting. If only one thing in this video is watched twice, it is this shot — so it must be one continuous take with no edit that could be read as a splice.

---

### Beat 6 — 1:42–2:05 · Rehydration, so the task still completes (55 words)

**Headline (on screen):** `The task completes. The model never held the digits.`

**On screen:** The agent calls `send_summary` with `[IN_AADHAAR_1]` in its arguments. The `before_tool_call` step substitutes the real value on the trusted side. Two panels side by side: the outbound message containing the real value, and the model context containing only the placeholder. The contrast between those two panels is the shot.

**Narration:**
> Now the agent needs that number to finish the task. It calls `send_summary` with the placeholder. That call is authorized, so the real value is substituted in before the tool runs — on the trusted side. The task completes. The model never held the digits. Redaction that breaks the task isn't a control, it's an outage.

**Speaker notes:** This is the beat that answers "so your product just breaks agents." Answering the objection inside the demo is better than answering it in a Q&A that will never happen. The last sentence is the one to keep if time has to be cut from this beat.

---

### Beat 7 — 2:05–2:25 · One file, the whole budget (46 words)

**Headline (on screen):** `One attachment. Zero entities found — until you convert it first.`

**On screen:** A single-page scanned PDF arrives as a tool result. Normalisation to markdown, then the detector tiers lighting up in sequence: checksum, then Comprehend. The meter goes from empty to full in one call. If Textract bounding boxes were built, draw them on the rendered page here.

**Narration:**
> Files are the other half. A tool returns a scanned PDF. Text-only scanners see a base64 blob and log "zero entities found." This one turns it into markdown first — name, address, Aadhaar, all on one page. One attachment spends the whole budget in a single call.

**Speaker notes:** Single-page fixtures only — PRD §14 lists a multi-page PDF appearing in demo data as a named risk, because sync Textract handles one page and fails at page two. If the Indic tier works, this is where two extra seconds show the Devanagari name being caught, with a caption noting that Textract's OCR is Latin-script only. If it does not work, cut it entirely and say nothing; PRD §11 has it as a *Should*, not a *Must*.

---

### Beat 8 — 2:25–2:45 · One policy, two agents, one audit view (43 words)

**Headline (on screen):** `Edit one line. Both agents change on their next call.`

**On screen:** The control plane's `agent.cedar` open in an editor. One line changes — budget `3` to `1`. Save. Two agent sessions side by side, both continuing, both behaving differently on the next call. Cut to the audit view holding rows from both.

**Narration:**
> The policy lives on a control plane, fetched with an ETag. I'll change one line here — drop the budget to one. Two separate agents, different sessions. Both change behaviour on their next call. No redeploy. Both decisions land in the same audit view.

**Speaker notes:** PRD §5 calls this the best fifteen seconds in the demo, and it is what separates a library from something an organisation can operate. It is also the beat most likely to break on camera, because it depends on cache behaviour and timing. Rehearse it, and if it will not cooperate, cut it and give the time to beats 5 and 6 rather than shipping a take where the second agent does not change.

---

### Beat 9 — 2:45–3:00 · Close (30 words, ending on silence)

**Headline (on screen):** `Deployed · ap-south-1 · <function URL> · <repo URL>`

**On screen:** The audit table scrolling: `entities_found`, `entities_masked`, `ledger_before`, `ledger_after`. Then the live Function URL typed into a browser and loading — actually loading, on camera. End card: project name, one-line description, repo URL, live URL. Hold two seconds in silence.

**Narration:**
> Every row records what was withheld. No raw values — the log doesn't become the leak it prevents. Each call was allowed. Together they identify her. This time, something was counting.

**Speaker notes:** The Ship It prize requires a deployed URL a judge can open, so showing the browser actually load it is not decoration — it is evidence for the prize criterion. End on the held frame, not on a word. The last line closes the loop with the cold open, which is why both use the same three sentences.

## A.3 Capture checklist

Everything below has to be recorded. Assume two takes each and roughly ninety minutes total. Schedule it, do not leave it to the last hour.

- [ ] Scanned Aadhaar fixture, high resolution, obviously synthetic data
- [ ] Decision feed with three green rows, clean of dev chrome
- [ ] AgentCore Policy GA page, live browser, date visible
- [ ] Guardrails sensitive-information-filter doc page, relevant line highlighted
- [ ] AWS doc line on `global.` inference profile routing outside the source Region
- [ ] The `model = "apac.amazon.nova-lite-v1:0"` line in the team's own code (Pro appears only on the Tier-3 image call)
- [ ] Meter filling 1/3 → 2/3, legible subject id, in one take
- [ ] **Beat 5 in one uncut take** — Aadhaar denied *and* the previously-allowed phone number denied, in the same frame. Never narrate this as the model unlearning something; see PRD §12's narration rule
- [ ] Rehydration: outbound message and model context side by side
- [ ] Single-page PDF ingest, tiers firing, meter 0 → full
- [ ] Bounding boxes *(only if built)*
- [ ] Indic detection *(only if it works — otherwise omit silently)*
- [ ] Policy edit, two agents diverging, shared audit view
- [ ] Audit table scroll showing ledger_before / ledger_after
- [ ] Live Function URL loading in a browser
- [ ] End card with both URLs

## A.4 Sentences that must not be said on camera

From `05-gtm-and-positioning.md` §9 and PRD §4 and §13. Reread this list before recording, because these are the sentences that come out naturally under narration pressure:

"First of its kind." · "Nobody else is doing this." · "Nobody carries state across calls." · "Existing DLP only watches browsers." · "We're the only ones detecting Aadhaar" (Presidio does, free, with a checksum). · "Stays in India" — say "stays in APAC." · "OWASP T2" — it is ASI02. · "The model no longer knows it" — it read it; say denied now, gone from context going forward (PRD §12). · "This makes you DPDP compliant." · "DPDP requires you to mask Aadhaar." · "You'll be fined ₹250 crore." · "Differential privacy." · "AWS's Cedar library" (`cedarpy` is a community binding). · Any accuracy claim about Aadhaar or PAN detection — AWS publishes none (PRD §8).

---

# PART B — the eleven-slide deck

**Not for the hackathon.** This is for afterwards: a fast-track Amazon interview, a recruiter conversation, or anyone who asks to see more. It is written to be presented by someone who has to defend every line in a Q&A immediately afterwards, which is why the prior-art slide sits in the middle rather than being buried at the back.

**For an interview specifically:** slides 7, 10 and 11 matter more than the rest. An interviewer is testing whether the candidate can say what they decided, what they rejected, and what they measured. The rejected-options table in PRD §7 — AgentCore Runtime, App Runner, Fargate, Bedrock Data Automation, CDK, each with a stated reason — is the single most useful artifact in the project for that conversation. Bring it as a backup slide and hope for the question.

---

### Slide 1 — Title

**Headline:** `Naka — disclosure budgets for agent tool calls`
**Body:** One line: *An AI agent gets a budget for how much it may learn about any one person, enforced across every tool call in the session.* Below it: deployed URL, repo URL, built for the WeMakeDevs × AWS First Commit hackathon, September 2026.
**Visual:** The disclosure meter at 3 of 3, large, and nothing else.
**Speaker notes:** Ten seconds. Read the one-liner and move. Do not explain the name.

---

### Slide 2 — The mechanism of harm

**Headline:** `Each call was allowed. Together they identify her.`
**Body:** Call 1 returns a name. Call 2 a phone number. Call 3 the last four digits of an Aadhaar. Each passes policy — none of them *is* an Aadhaar. Together they re-identify a person. No control in the path noticed, because each was designed to answer a question about one payload.
**Visual:** Three green `ALLOW` rows, then a fourth row showing the composed identity. No diagram.
**Speaker notes:** This is the whole talk. If the room only remembers one slide, it is this one. Do not advance until it has landed — ask "does that shape make sense?" and wait for a nod.

---

### Slide 3 — Why this is new with agents

**Headline:** `A human analyst runs three queries. An agent runs three hundred.`
**Body:** Aggregation risk scales with call volume. Agents are the first system where call volume is unbounded and nobody is watching. Per-call redaction is necessary and insufficient. Anchor: OWASP Top 10 for Agentic Applications 2026, **ASI02 Tool Misuse and Exploitation** (ASI03 second) — and the list has no entry for cumulative sensitive-information disclosure at all.
**Visual:** Two bars — one human session, one agent session — on the same axis.
**Speaker notes:** Pre-empts "isn't this just an old problem?" The honest answer is that aggregation risk is an old idea; what is new is the volume and the absence of a human in the loop. Say that, rather than claiming the idea is new.

---

### Slide 4 — What we built

**Headline:** `Two questions to Cedar, not one.`
**Body:**
`Q1 — may this call happen?` — `CedarAuthorization`, before the tool runs. Deny short-circuits.
`Q2 — may this principal learn this field about this subject, given what it already knows?` — one `is_authorized_batch` request per `(subject, field)` pair, carrying the ledger, after the tool returns.
Denied fields become numbered placeholders. Both answers land in one audit row.
**Visual:** The ten-step per-call sequence from PRD §5, unedited.
**Speaker notes:** The second question is the contribution. Everything else is plumbing that makes it possible.

---

### Slide 5 — The demo, in one frame

**Headline:** `Allowed at call two. Denied now.`
**Body:** Three-line caption under a still from beat 5 — the fourth call denies the phone number that call two allowed, and removes it from context going forward. Never "the model no longer knows it."
**Visual:** The before/after diff with `[IN_AADHAAR_1]` and `[PHONE_2]` both visible.
**Speaker notes:** If there is a screen, play the fifteen seconds instead of showing the still. If not, this still does the job. Follow immediately with rehydration in one sentence — "and the task still completes, because a placeholder can be substituted back on the trusted side" — because "doesn't this break the agent?" is the first question every time.

---

### Slide 6 — Architecture

**Headline:** `Control plane, data plane, three stores — each one justified.`
**Body:** Lambda + Function URL for both planes. Strands agent with three interventions in registration order — `DisclosureGuard`, then `CedarAuthorization`, then `Rehydrator` — because handlers run in order and a `Deny` skips the rest, so a denied call never gets plaintext substituted into its arguments. **DynamoDB is the ledger authority** (an atomic `ADD` on a String Set); `S3SessionManager` is the cache; DynamoDB also carries audit rows and the dashboard; the Cedar policy is baked into the Lambda package as a fail-closed fallback when the control plane is unreachable.
**Visual:** The PRD §5 diagram.
**Speaker notes:** The store table in PRD §5 is the interesting part, not the boxes. Strands session managers take no distributed lock — that applies to `S3SessionManager` too, not just the file one — which is exactly why the authoritative counter is a DynamoDB atomic set-union; there is no DynamoDB session manager; and the control plane must fail closed to a known policy rather than to no policy. Three choices, three reasons.

---

### Slide 7 — Prior art, honestly

**Headline:** `The per-call guardrail is a solved, crowded category.`
**Body:** The table from `05-gtm-and-positioning.md` §3.1: AgentCore Policy (GA 3 March 2026, Cedar, default-deny, in Mumbai) · AgentCore Gateway RESPONSE interceptors · Pipelock (884★) · Bedrock Data Agent DLP (30 July 2026) · LangChain 1.0 `PIIMiddleware` · the AI-DLP vendors. Each row states what it does better than us. Bottom line, and it is deliberately narrow: *cross-call state is not rare — AWS's own Dogwood counts over tool-response history, Pipelock carries a session threat score, Purview accumulates into DLP enforcement. None of them accumulates per data subject, and none turns that accumulation into a redaction decision in the same policy language as the allow/deny.*
**Visual:** The table, with the "what it does better" column left visible, not cropped out.
**Speaker notes:** Putting this in the middle of the deck is the point. The claim is about a composition, not a category, and a room that has already seen us name our competitors accurately will believe the rest. An earlier draft of this project claimed nobody governs agent tool traffic; that was false, and correcting it is a better story than never having been wrong.

---

### Slide 8 — Why India, specifically

**Headline:** `Every mainstream detector is blind to half of an Aadhaar card.`
**Body:** Indian *identifiers* are table stakes — Presidio ships `IN_AADHAAR` with a Verhoeff checksum, free, and Comprehend carries four Indian types (Bedrock Guardrails carries none, which is the AWS-audience comparison). The gap is **script**: Comprehend does English and Spanish, Textract's OCR is Latin-script only, so nothing in the standard stack reads the Devanagari or Tamil half of an Aadhaar card — that tier runs on a multimodal model against the image. And the model is Nova on `apac.*`, because Claude on Bedrock in Mumbai is `global.*` only, which AWS states can route requests outside the source Region; the claim is "stays in APAC".
**Visual:** An Aadhaar card with the English half and the regional-script half boxed separately, one labelled "Textract", the other labelled "not Textract".
**Speaker notes:** The split-card visual is the most memorable image in the deck. The point that every Latin-script-only PII tool is blind to half of every Indian identity document is both true and not widely noticed.

---

### Slide 9 — Evidence it runs

**Headline:** `Deployed, in Mumbai, for single-digit dollars a month.`
**Body:** Both Lambdas behind Function URLs in `ap-south-1`. About **$2.25/month** at demo scale — 500 invocations, three tool calls each, fifty document pages — priced at full `ap-south-1` rates with no free tier assumed, on Nova **Lite** for the agent loop (it would be ~$9.20 on Pro throughout); Textract about $0.08 for fifty pages. The same shape on Claude would be ~$30–35/month and would break the residency premise. Measured Comprehend latency from `ap-south-1`: *insert the real number* — AWS publishes none, so this is a measurement the project contributes.
**Visual:** A real audit row and a real latency breakdown, not a mock.
**Speaker notes:** PRD §15.3 makes measuring Comprehend latency from Mumbai an open question. Measuring it turns it into a small original contribution. If the number was not measured, delete the line — do not estimate it.

---

### Slide 10 — What this does not do

**Headline:** `Where it breaks.`
**Body:**
- **Embedded images inside text-layer PDFs.** If extraction does not recurse into them, high-risk content passes while the audit row says clean. Named in PRD §9 as the hole a judge could puncture.
- **Entity-to-subject attribution.** Trivial on the seeded structured fixtures used in the demo; hard in general. Not claimed as solved.
- **Detection accuracy.** AWS's Comprehend service card is dated November 2023, publishes no per-entity table, and publishes nothing at all for Aadhaar or PAN. It also names degraded performance on OCR text.
- **Cross-session accumulation.** The ledger is per session. The same principal across two sessions is not tracked.
- **Volume.** A spreadsheet column of five thousand Aadhaar numbers is still text, but it exceeds Comprehend's 100 KB limit and turns one hop into a chunking loop.
- **It is a quasi-identifier accumulator, not differential privacy.** We do not borrow that vocabulary.
**Visual:** Plain text. No graphics on this slide.
**Speaker notes:** This is the slide that gets the job. Every candidate has a demo; few can say precisely where their own work fails. Deliver it at the same pace as slide 4 — not apologetically, and not as a joke.

---

### Slide 11 — Where it goes, and the ask

**Headline:** `The production shape of this is an AgentCore Gateway interceptor with Verified Permissions behind it.`
**Body:** `cedarpy` is an embedded community binding, chosen because Amazon Verified Permissions adds a policy store, an IAM role and a round trip in the hot path, and is not what `CedarAuthorization` uses — AVP is the production story, not the hackathon one. Next: recursion into embedded images, cross-session ledgers per principal, signed audit receipts, MCP server mode. Ask: *design partners running agents over customer data who will spend an hour trying to break it* (see `05-gtm-and-positioning.md` §7).
**Visual:** The current architecture beside the production architecture, with the two changed boxes highlighted.
**Speaker notes:** For an interview, replace the ask with "what I would do differently with another week", and have the PRD §7 rejected-options table ready as a backup slide.

---

### Backup slides, to have but not to present

- **PRD §7 rejected options** — AgentCore Runtime (no public URL, SigV4/JWT only), App Runner (bills provisioned memory 24/7; each deploy is a 5–10 minute ECR build), Fargate (hours of VPC/ALB setup), Bedrock Data Automation (no free tier, cross-region APAC hop), CDK (30–60 minutes of TypeScript that gets thrown away). **The most valuable slide in the deck for a technical interview.**
- **Grounding the threshold** — the default budget is 3 because three quasi-identifiers uniquely identify most of a population: Sweeney's 87% on 1990 census data, revised to 63% by Golle on 2000 data. HIPAA Safe Harbor's 18 identifiers say *which fields count*, not how many are too many.
- **The Verhoeff checksum finding** — a checksum is robust against false positives but fragile against OCR errors, so on OCR-sourced text a failing 12-digit sequence is flagged at lower confidence rather than dropped. Checksum as a confidence signal, not a gate.
- **The Cedar cardinality constraint** — Cedar has no `.size()` and sets are not comparable, so counts are computed in Python and injected as longs.
- **Compliance framing** — PRD §13 verbatim, including the do-not-claim list.

---

# PART C — the written submission

The submission form and the README are read alongside the video. Keep them consistent with it and short.

**First line, identical in both** — the sentence from `05-gtm-and-positioning.md` §5.4:
> Each call was allowed. Together they identify her. Nobody was counting.

**Then, in order, and nothing else:**

1. **One paragraph on the mechanism** — the §2.2 paragraph from the GTM document.
2. **Prior art, before anything about us.** The §3.1 table, with the "what it does better" column intact. A judge who already knows AgentCore Policy shipped will look for this, and finding it in position 2 rather than position 9 changes how the rest is read.
3. **What runs** — the deployed URL, the region, the three tool calls, the two Cedar questions, the detector tiers, the audit record shape.
4. **What does not work** — slide 10, in full. Including the embedded-image hole.
5. **What we found in the documentation** — the corrections in PRD §2.2 that changed the build: sync Textract is one page for PDF; Textract OCR is Latin-script only; Cedar has no set cardinality operator; Comprehend bills a 300-character minimum per request; `InvokeAgentRuntime` has no public URL; API Gateway HTTP API caps at 30 seconds; Claude in Mumbai is `global.*` only. This section is the one a blogger prize is judged on and it is useful to other people independent of this project.
6. **Compliance framing** — PRD §13 verbatim, no stronger.
7. **Fixtures are synthetic.** State plainly that no real Aadhaar, PAN or personal data appears anywhere in the repo, the video or the deployed demo.

**Length:** if the form has no limit, aim for 800–1,200 words. Longer reads as padding.

**What not to include:** a roadmap, a business model, a market size, or a team-strengths section. None of them is being scored and each one costs a judge attention that should go to section 5.
