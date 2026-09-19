# Field Recon — what else is in this hackathon, and what the rules actually say

**Written:** 19 September 2026 · **For:** First Commit (WeMakeDevs × AWS), submissions close Sun 20 Sep 2026, 20:00 IST.
**Method:** five parallel research agents over GitHub, the organiser's own pages, the judges' public writing, past WeMakeDevs winners, and recent AWS agent hackathons.

**This document contains only what is *not* already in 01–13.** Everything the sweep surfaced that doc 01 already covers — CAMP, OCELOT, Dogwood, hoop.dev, AgentFlow, the Guardrails `toolUse.input` / `toolResult` / `toolSpec` exclusion, the ASI02/ASI03 anchor, the `ContainsPiiEntities` pre-filter, the SSE-on-Python-Lambda dead end — has been stripped. If it is below, it is new or it is a correction.

---

## 1. Corrections to documents already written

Four. The first three are cheap. The fourth is load-bearing and unresolved.

### 1.1 Three scored or required items are missing from the package · ~1 h total

| Missing | Where it belongs | Source |
|---|---|---|
| ~~A "what I learned" section~~ | `11-written-submission.md` | ✅ **Added 19 Sep.** Judging criterion **#03 of five**, verbatim: *"Tell us what you learned, and it counts towards your score."* Five findings that each changed the build — Comprehend/Guardrails Hindi inversion, the Guardrails exclusion note, the Function URL permission asymmetry, the Strands layer version gap, and the account-gating failure modes — plus a "what we would do differently". |
| ~~A literal list of AI coding tools used~~ | — | ✅ **Already present and stronger than the rule requires** — doc 11 §"Fixtures, and AI-tool disclosure" names the assistant, the three uses, and what remained the team's judgement. My earlier reading of this was wrong. No action. |
| ~~A publication venue for the blog~~ | `12-blog-post.md` | ✅ **Added 19 Sep** as an editorial header to be deleted before publishing, plus a "The problem" and "The stack" section so the post hits the prize's three beats **in its order**. Post at `builder.aws.com/create/content` in the WeMakeDevs Space, on the **same Builder Center profile the entry is checked against**, live *before* submitting. |

The blog prize is **five keyboards to five *people*, not five teams** — more than one team member writing is not wasted effort. Its content spec is literally three beats, in this order: **the problem, the stack, what fought back.** Doc 12's research is the asset; it needs a venue and that ordering.

**Post it into the WeMakeDevs Space specifically**, not just anywhere on Builder Center: `builder.aws.com/connect/space/29f78273-9a25-34b1-818f-eec9b0bacb31/wemakedevs` — 2,870 members, ~570 posts. That space is the actual centre of gravity for this hackathon, far more than X.

**The prize is winnable on current volume.** Of ~570 posts in the space, maybe **25–30 are genuine build posts**, and most of those are "Day 1, I brainstormed for two hours" filler. Four or five (HaqCheck, AgentShield, VeriAI, RecallIndia, Manifest) are dramatically better than everything else. **One well-structured problem → architecture → what-broke → what-I-learned post is very likely top-five material right now.** Doc 12 is already far past that bar.

Tags in use: `#BharatBuilds #FirstCommit #AWS #WeMakeDevs #Hackathon #BuildInPublic #StudentDeveloper`. Organisers explicitly asked people to post progress on social under **#BharatBuilds**, tagging WeMakeDevs and AWS Developers. Cross-posting to dev.to is being done but the prize is not there — `dev.to/t/firstcommit` and `/t/bharatbuilds` do not exist.

⚠️ **Brand discrepancy:** the official site and the WeMakeDevs prize tweet say **Logitech**; Kunal Kushwaha's own launch post says **Keychron**. Same count. Don't quote either brand confidently.

### 1.2 ~~"GA in Mumbai" is too strong~~ — **RETRACTED. The README was right.**

**This section was wrong and is retracted in full.** Verified against primary sources 19 Sep:

**Policy in Amazon Bedrock AgentCore is formally GA, and Mumbai is named explicitly.** The what's-new is titled *"Policy in Amazon Bedrock AgentCore is now generally available"* (March 2026) and lists **thirteen regions including Asia Pacific (Mumbai)**. The AWS News Blog post carries an editor's note — *"Updated on March 3, 2026 - Policy in Amazon Bedrock AgentCore is now generally available"* — and its original body says "Policy in AgentCore (Preview)", dating the preview to December 2025. The preview-to-GA transition is documented at both ends.

**Say GA.** Cite the thirteen-region GA list rather than the docs region table, because Mumbai is named explicitly there. (The two disagree on breadth - 13 vs 22, the docs table having since added more regions - but they agree on Mumbai.)

**Why the first sweep got this wrong, worth keeping as a research lesson:** the devguide itself contains **zero** instances of "preview", "generally available" or "GA" on any of its 30 policy pages. The lifecycle designation lives only in the announcements. Absence of the label in the documentation is not absence of the designation.

**Dogwood is different and must be described differently.** It has no GA or preview designation anywhere, because it is an open-source language specification and not an AWS service. **Call it open source. Never "GA", never "preview".**

### 1.3 The Dogwood information-provider socket does not exist in `ap-south-1`

**Guardrails-as-an-information-provider inside Cedar policy is available in seven regions, and Mumbai is not one of them:** us-east-1, us-east-2, us-west-2, ap-southeast-2, ap-northeast-1, eu-west-2, eu-north-1.

The README's plan is to position the ledger as a Dogwood *information provider* — composable, not competing. That framing survives, and arguably strengthens: the socket is specified, nothing fills it with per-subject disclosure state, and the composition surface is not in the region this is built in. But it must be said accurately. Do not imply the composition was available and declined.

### 1.4 The AWS quote is **NOT REAL**. Do not use it. Use this table row instead.

**The sentence I previously recommended putting at the top of the README - *"A policy engine permits or denies a call. It doesn't modify one"*, with redaction "requiring a separate control, not a policy" - could not be found in any AWS material.** A verification pass pulled and full-text-searched the complete bodies of the Cedar security blog, both Policy machine-learning blogs and the graduated-autonomy architecture blog: zero hits for "permits or denies", "doesn't modify", "does not modify" or "separate control". An exact-phrase web search returned nothing either. **It is a paraphrase that reached this document as a citation.**

Attributing a fabricated quote to AWS, in front of AWS solutions architects, is the worst error available to this submission. It never reached the README or `naka/` - it existed only here.

**The real citation, verbatim, and it makes the point better.** From the "When to use Policy compared to Lambda interceptors" decision table:

> | Payload transformation | Use Policy: **Not supported** | Use Lambda interceptor: Full read/write access to headers and body |
> | Response modification | Use Policy: **Not supported** | Use Lambda interceptor: RESPONSE interceptor |

- [AWS ML Blog, Policy and Lambda interceptors in AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/)

That is AWS's own table placing response modification outside Policy's scope. **Screenshot the row; do not quote a sentence.**

#### `suppressOutput` - real, and it strengthens the position

| Question | Answer |
|---|---|
| Does it exist? | **Yes.** *"a new effect that operates on the data an action returns. After an authorized action is completed, it evaluates the outputs against the guardrail and suppresses the output when the guardrail is violated."* |
| Whole response or specific fields? | **Whole response.** The effects table reads *"Block the model's response (output phase) when it exceeds the threshold."* `context.output.<path>` selects what the guardrail **reads**, not what is removed. Across all 30 `policy-*` pages, a grep for redact / mask / sanitiz / transform returns **zero hits**. |
| Can the task continue after suppression? | **Undocumented.** No error code, no payload shape, no worked example. **Do not assert either way on camera** - say "AWS doesn't document the post-suppression response shape." |
| Available in `ap-south-1`? | **No.** `suppressOutput` is usable only inside guardrail policies, and guardrails-in-policy excludes Mumbai in both the docs table and its own June 2026 GA announcement (5 regions there, 7 in the docs table). |

**The likeliest on-camera error in this whole document: Policy is GA in Mumbai; guardrails-in-policy - and therefore `suppressOutput` - is not.** They are different availability surfaces. Do not conflate them.

Two more constraints: `suppressOutput` supports **only** guardrail checks - no standard Cedar conditions, no `temporal` blocks - and mixing `context.input.` with `context.output.` in a single invocation is rejected.

#### The novelty sentence must be sharpened - "authorizing responses" is occupied ground

**This is the most important correction in this document.** Do not claim that authorizing the tool *response* is unoccupied. It is falsifiable in one search:

- **`cedar-policy/cedar-for-agents`** (Apache-2.0, real) ships an `Authorize` subcommand documented as *"Convert MCP tool **Input & Output** to a Cedar Authorization Request and check authorization against a set of policies"*, taking `--mcp-tool-input` **and** `--mcp-tool-output`, with an `--include-outputs` flag that encodes tool outputs into the action-specific Cedar context.
- **Dogwood** exposes `context.output.<field>` in conditions.
- **`suppressOutput`** acts on returned data by definition.

**What none of them do is return a transformed payload.** cedar-for-agents' authorize path terminates in exactly two outcomes in `src/cli/exec.rs`: `Decision::Allow => "ALLOW"` / `Decision::Deny => "DENY"`. A grep of the unpacked repo for redact / suppress / mask / sanitiz finds only an unrelated rate-limit key helper. Dogwood's verdict is `Decision::Allow` / `Decision::Deny`; its effects "must be exactly `permit` or `forbid`".

**So the defensible claim is:**

> **Authorization returns a decision, not a document. No policy language returns a redacted payload.**

Not *"we're the only ones who authorize responses."* The first held up against AgentCore Policy, Dogwood, Cedar and cedar-for-agents; the second gets corrected by anyone with a search box.

**Volunteer the qualifier before a judge finds it.** AWS *does* ship response redaction - via Lambda RESPONSE interceptors, whose docs describe transformation and filtering after the target responds, and whose blog describes an interceptor that *"redacts sensitive information dynamically based on user permissions"* and integrates Guardrails for PII redaction. That is **imperative code, not policy.** The real differentiator is redaction as an authorization *outcome expressed in the policy language*, versus redaction as handwritten code downstream of a boolean. That distinction survives every source checked.

**One counter-string to be ready for:** `policy-test-a-policy.html` contains an enforcement-mode cell reading *"Evaluated and enforced. May block or modify requests."* It is the only place AWS uses "modify" about the policy engine, and it concerns **requests**, not responses. Probably loose drafting - but know it exists.

---

## 2. The field — who else is in this hackathon

~90–110 repos are identifiable as entries; ~40 are empty starters. There is **no public submission gallery** — GitHub repo descriptions and AWS Builder Center posts are the only enumerable surfaces, so a submission with a generic description is invisible to this method.

**The governance/guardrails-on-AI-agents cluster is the single largest and most sophisticated theme in the hackathon**, not a niche. A phrase recurs almost verbatim across unrelated authors: *deterministic code decides, the LLM only explains.* Cedar and Amazon Verified Permissions are its signature tools. Naka is not an outlier here — it is in the most crowded high-quality field in the event.

### 2.0 🚨 AgentShield — the collision that matters most

**https://github.com/arnavgupta2004/AgentShield** · live at `main.d1g50p52p40rhx.amplifyapp.com` · Builder Center post: *"When allowed actions become unsafe"*

> "Runtime **composition-aware** authorization for AI agents — catches attacks where every individual action is authorized but the combination isn't (**aggregation-inference**)."

**That is our thesis, stated in our own words, by someone else, deployed, with a benchmark.** Deterministic engine, no LLM in the auth path. Measured: 30 sessions, **12/12 attacks caught, 0 false positives, versus 6/12 for a strong baseline.** Python/FastAPI/React/TypeScript on Lambda, API Gateway, DynamoDB, SAM, Amplify.

**What it is not:** no PII detection, no per-field decision on a tool *return*, no placeholders, and — critically — **no per-data-subject keying.** "Composition-aware" here means the combination of *actions*, not the accumulation of *fields about one person*. The delta survives, but it is now a delta against a deployed, benchmarked project in the same room rather than against papers.

**Two consequences:**

1. **The phrase "individually permitted, jointly dangerous" is taken.** Doc 04 §0.2's line — *"an agent assembling an identity out of individually-permitted fields"* — now sounds like AgentShield unless the *subject* is in the sentence. Lead with the person, not the combination: **"four fields about one person"**, never "a dangerous combination of actions."
2. **Its benchmark format is the bar.** 12/12 vs 6/12 over 30 sessions is exactly the "one hard number" pattern from §5.2, and it is already published. Doc 04 idea #1's counterfactual counter must be at least this concrete.

**Mitigating:** AgentShield's UI is *"a bare Live demo / Benchmark toggle over a long dropdown of raw session IDs."* It will win on substance and lose Best UI outright. That is the gap to take.

### 2.1 Cedar is not ours alone this weekend

**Four other teams are building on Cedar.** Two of them use Amazon Verified Permissions — the managed service doc 04's kill list declines.

| Project | What it is | Collision |
|---|---|---|
| **`leash`** (4-person team, Ship It) | CloudWatch alarm → EventBridge → SQS → Strands agent. **Every mutating tool call authorized by Cedar (`cedarpy` in Lambda, or AVP) before it executes.** Audit row written *before* the answer. Hot-reloading versioned policy bucket. English → validated Cedar → human approves. Red-team panel: 20 attacks, leash off vs on. | **Same stack, same primitive, opposite side of the boundary.** Cedar + Strands + Lambda + `cedarpy` + DynamoDB. Reported as the most polished submission in the event: CI badges, cfn-lint, offline demo, measured numbers, teardown script, honest cost table. **A judge will likely see this before ours.** |
| **`gurdy`** | Go MCP proxy, **embedded Cedar**, hash-chained batch-signed ledger verifiable offline by a third party. Monitor-mode only. Ships **27 replayable attack traces including 7 it fails**. | Cedar on the tool boundary. Its classify stage is documented as pulling metadata *"Never payload content."* |
| **`relay`** | Rust local-first MCP gateway. Cedar default-deny per canonicalized tool call, JIT credential leasing, netns sandbox, DSSE/in-toto signed receipts, SQLite hash chain. 380 tests. | Request-side Cedar. No payload inspection. |
| **`Cedar-Sentinel`** · **`healops`** | Strands + Cedar check before sensitive operations; immutable audit. `healops` is "Cedar-*style*" — likely not a real engine. | Thinner leashes. Same one-sentence pitch as `leash`. |
| **`haqcheck`** | Cedar/AVP computes gig-worker welfare eligibility with `@source` clause citations. Nova Lite via Strands only translates the verdict. `ap-south-1`. | **No tool boundary, no PII, no agent autonomy. Zero mechanism collision.** But see §2.2 — they have taken a phrase. |
| **`support-coach`** | India-focused support agent. **PII replaced with placeholders before anything reaches the model, restored in the reply.** Mock order system. | No policy engine, no per-field decision, no accumulation. But a judge who saw it will say *"that already redacts tool data and rehydrates."* |
| **`hallmark`** | "Provenance-aware firewall for AI agents. Every value an agent handles carries a record of where it came from; before a consequential action executes, a Cedar policy checks not only *what* the agent is doing but **where each argument came from**." `cedarpy`, append-only ledger. | **Structurally the nearest project in the event: per-field authorization of data flowing through an agent.** Taint/provenance, not PII, and no per-person ledger. |
| **`sovereign-guard`** | "Zero-Trust Policy Gateway for Autonomous AI Agents" (Build It). `cedarpy` v4.8 intercepts **every tool call in <0.2 ms** and aborts before it touches disk or socket. OpenSearch audit, Monaco-based live Cedar policy studio. README names the threat as agents "snooping on confidential payroll spreadsheets, medical data, or **PII**". | The closest analogue of our interceptor. PII named as a protected resource class; no detector. |
| **`Between_Sessions`** | OCD clinical companion. **Cedar WASM authorizes clinician access per data category** (`checkins`, `journal_structured`, `practice_logs`, `ai_summary`); revoking consent for a category makes the summary endpoint return `403 CONSENT_REQUIRED`. | **Closest thing in the event to a running per-person permission state** — but per-category and static, not accumulating. |
| **`kagazready`** | Scholarship document readiness: Textract → deterministic rules → **mask** → Bedrock rephrase-only. Every "mark" carries status, which document, **the masked value that was read**, and the rule that decided it. Bank accounts masked to last 4 before storage; Textract output lives only in Lambda memory; explicit PRIVACY.md. | **The strongest real PII masking in the hackathon** — our concept's other half, without Cedar. |
| **`Aegis`** | "The Authorization & Accountability Layer for Autonomous AI." Local Cedar PEP + optional AVP comparison that **fails closed on divergence**; event ledger in **S3 Object Lock Compliance Mode**; Bedrock proposes refined Cedar policies for human sign-off. Ship It. | Third AVP project. Its fail-closed-on-divergence design is a better answer to "embedded or managed?" than picking one. |

**The `leash` rebuttal, which needs to be ready:**

> *"Leash authorizes the request — an action the agent proposed, with arguments the agent itself wrote, where every policy input exists before the call. Naka authorizes the return — data the agent did not choose and has not yet seen, where the inputs do not exist until the tool answers, and the decision depends on what earlier answers already revealed about the same person. Leash's denial stops an action. Ours rewrites a payload and the task continues."*

Note also: `leash` and two AVP-based projects in the same room means **"why not Amazon Verified Permissions?" now gets asked with live counterexamples.** Doc 04 kills AVP on a round-trip-in-the-hot-path argument. Sharpen that — AVP is `$0.000005` per `IsAuthorized` call and is available in `ap-south-1`, so **the cost argument is not available.** The rebuttal has to be latency and the embedded-in-the-intervention-path design, or it does not hold.

### 2.0a Two more head-on competitors, both strong

**`Daksha1611/FirstCommit` — "Pocket Change".** *"Bounded, auditable spending authority for AI agents. You hand an agent pocket change, not your wallet."* The agent is assumed compromised. **Biscuit capability tokens** (attenuable — a child token can only narrow) implement the delegation chain from the Agent Identity Protocol, then supply the two things that protocol puts out of scope: **cumulative spend enforcement** and replay inside the token TTL. The budget check and decrement are **one DynamoDB conditional write**, so 148 agents across 5 layers cannot collectively exceed one ceiling. Cedar is used *only* for rules that are chosen, never ones cryptography already settles — a deliberate anti-decoration argument. Scored against the SoK agentic-commerce threat taxonomy (10/12 vectors) and AgentDojo. **535 tests, 0.18 ms enforcement.**

**This is a cumulative ceiling used as an authorization decision, shipped.** The subject is money, not a person, and there is no detection or redaction — but *"a running total, checked atomically, that no sequence of individually-permitted calls can exceed"* is now built by someone else in this event. **The budget half of the thesis is no longer unclaimed; only the per-subject, per-field, post-return half is.** Weakness: **not deployed, and they say so** — the root signing key is per-instance, so a serverless cold start would revoke every mandate.

**`CSNEHA20/first_commit` — "PolicyLab".** *"Prove your authorization changes before they reach production."* A Cedar policy-engineering platform: write → validate → simulate → **diff** → analyze → **counterexamples** → explain → regression tests → verify → deploy, computing **bounded authorization blast radius** for a policy edit and gating deployment to AVP behind cryptographic human approval. Explicit principle: **"AI never decides authorization"** — Bedrock only explains deterministic evidence. Cedar WASM, Step Functions, CloudWatch EMF, **119 passing tests**. Its UI is a **dark glassmorphic workspace with Monaco, a diff analyzer, an Access Matrix and a What-If simulator** — so it is a Best-UI threat as well as a technical one.

**Correction to `leash`'s numbers:** its deployed run of 19 Sep 2026 is **20 attacks, the model persuaded 18/20, destructive action executed 18/20 without the leash and 0/20 with it**, with per-tactic and per-goal breakdowns read live from the audit table rather than typed in. (An earlier figure of 13/14 was from a previous run.) It also plants a prompt injection in an EC2 instance's `Name` tag.

### 2.0b 🟢 The strategic read: our lane is saturated, but our *product* is not

Of 55 substantive projects, the inventory counts **13 using Cedar** and **6 squarely in agent-security/authorization**. The verdict is blunt:

> **"Cedar gates the agent + immutable audit trail" is now a saturated pitch at this event** — at least six teams built it and three built it very well.

But the same sweep counts service usage across 53 READMEs, and the numbers are decisive:

| | Count |
|---|---|
| DynamoDB 38 · Bedrock 35 · Lambda 33 · S3 32 · API Gateway 29 · SAM 22 · Amplify 21 | the default stack |
| **Cedar** | **13** |
| Strands Agents SDK | 12 |
| Bedrock Guardrails | 6 |
| Amazon Verified Permissions | 4 |
| **Bedrock AgentCore** | **1** |
| Textract | 2 |
| **Amazon Comprehend** | **0** |
| **Amazon Macie** | **0** |
| Rekognition · Kendra | **0** |

**The unoccupied ground is precisely ours: PII, redaction and data-leak prevention *as the product*.** Only `kagazready` and `ShikshaMesh` touch it at all, both as a side-feature. **Nobody used Comprehend. Nobody used Macie.** The detection layer that doc 01 correctly refuses to claim as novel is, in *this room*, the thing nobody else has.

That flips the positioning problem. The risk is no longer "is this novel?" — it is **"will a judge who has seen six Cedar-gates-the-agent projects notice that this one is about the data rather than the action?"** The demo must establish *in the first fifteen seconds* that the payload is the subject, not the tool call. Doc 13's re-ordering already pushes in this direction; this sharpens why it matters.

Other open ground named by the sweep, for completeness: AgentCore-native security (1 project), an adversarial measurement story stronger than leash's, and an **externally verifiable** audit trail (only Aegis attempts a hash chain, and only process-locally).

### 2.1a The field splits cleanly, and the gap is still ours

Verified against every entry found, the hackathon divides into two **non-overlapping** halves:

- **The policy half** — `leash`, `sovereign-guard`, `Cedar-Sentinel`, `Aegis`, `haqcheck`, `hallmark`, `AgentShield`, PRAAPTI, ShiftFair, errandloop, payproof, warrant, Cedar-Merge-Gatekeeper. Cedar or AVP authorizes **an action before it runs**. Every one of them treats authorization as a pre-condition on the tool call and stops there. **Not one authorizes what comes back.**
- **The PII half** — `kagazready`, `thaam`, `Vouchmark`, SCADS, RahatSetu. Regex/rules masking applied uniformly. No policy engine, no per-person state.

**Two pieces remain unclaimed in this event:** post-return per-field authorization (only `hallmark` reasons about returned values at all, as provenance taint), and **a running per-person disclosure ledger that drives the decision** (nearest are `Between_Sessions` — per-category, static — and `hiveos` — per-person, but a ledger of *spend*).

One more differentiator, free: **a search for `comprehend + pii` across the hackathon window returned zero repos.** Nobody in this event used Amazon Comprehend PII detection. Nobody's thesis mentions DPDP, Aadhaar-number redaction, or data minimisation. **AgentCore was essentially unused** — participants used raw Bedrock + Strands + Lambda.

### 2.2 Names and phrases now taken

- **"Leash", "flight recorder", "tamper-evident ledger", "zero-trust gateway"** — taken inside this hackathon.
- **"Cedar Decides. The LLM Just Talks."** — `haqcheck` published this as an AWS Builder Center article. Judges will have read it. **Do not use any variant.**
- **"Guardrail"** — 322 repos in nine days. It is noise now.

---

## 3. The rules, as actually written

Verbatim from `wemakedevs.org/aws/first-commit`, `/rules`, `/schedule`, `/judges`.

### 3.1 The single most important line on the site

> **"Judges score what you submit and nothing else. There is no live demo and no call. If the video does not show it, it does not count, and a feature that exists only in the writeup does not count either."**

Doc 07 called this format correctly in its preamble. It is now confirmed verbatim.

### 3.2 Five criteria, no published weights

**No percentages and no per-track rubric are published.** Anyone quoting weights for this event invented them. Assume roughly equal — that is the house style across every past WeMakeDevs event.

| # | Criterion | The line that matters |
|---|---|---|
| 01 | Idea and Impact | *"A small problem solved well beats a big one solved vaguely."* |
| 02 | Built on AWS | *"Ship It runs on AWS services, which is where the grand prize is decided."* · *"Using an AWS open-source project or AWS services is mandatory to win a prize."* |
| 03 | **Learning** | *"Tell us what you learned, and it counts towards your score."* |
| 04 | The execution | *"Does it work? Not perfect, not polished. Working. One feature that runs beats five that almost do."* |
| 05 | The demo video | *"There is no live demo, so the video is what the judges see."* |

Closing paragraph, verbatim: *"Cloud usage counts only in Ship It, **where architecture and cost decisions are part of the work**. Best UI is judged on design and usability."*

Best UI, verbatim: *"the best-designed thing at the event, **the one that is a pleasure to use and not only a pleasure to describe**."* That is a direct instruction to show the interface **being driven**, continuously, not narrated over static screenshots. Doc 03's hero component has to be operated on camera by a person.

**One submission, no track checkbox.** *"Ship It, Build It and Best UI are decided by what your project turns out to be, and one submission is considered for all three."* With three tracks + four runners-up + top-five blogs, there are **eleven-plus ways to place from one submission**, and a project with one outstanding dimension is well-positioned.

### 3.3 Hard requirements, and where we are exposed

- **AWS must be visible in the video.** *"Your project has to use AWS, and your demo video has to show it. Naming AWS in the writeup alone is not enough."* Console, CLI output, CloudWatch, the actual resource — something a judge can *see*. This is the most likely way a good project scores zero on criterion 02.
- **Video ≤ 2:55.** The rules say both *"up to three minutes"* and *"run under three minutes."* Do not test the boundary.
- **YouTube, public or unlisted, and verified in a signed-out browser.** The rules explicitly require this check.
- **Repo public at judging time.**
- **AI coding tools listed** — §1.1 above.
- **Eligibility: university student in India, 18+**, with a WeMakeDevs account **and** an AWS Builder Center profile with enrollment verified. An open SheerID case does **not** block submission, judging or prizes — but it does block the Amazon interview fast-track.
- **Team roster locks on submit.**

### 3.4 The deadline is less sourced than assumed

**No wemakedevs.org page states a time.** The schedule page says only *"Sun / Sept 20 — Submissions"* and, separately, *"the deadline the clock stops on … lands on this page first."*

The **only** sourced time anywhere is the Luma page for the Bangalore day: *"Online submissions are open until Sunday 8:00 PM IST."*

So 20:00 IST is corroborated, but by a secondary page. **Treat it as hard, finish by 18:00, and re-check the schedule page and Discord on Sunday morning** in case the finalised hour lands there. Rules §04: *"Once the deadline on your hackathon's page passes, the form closes and no project can be entered after it."*

### 3.5 Submission logistics

The form at `wemakedevs.org/aws/first-commit/submit` is **auth-gated** — its field definitions load only after sign-in. **Log in and screenshot every field now**, rather than discovering the form at 19:50.

Certain to be asked for: public repo URL · YouTube URL · writeup (problem / the build / where AWS fits) · **a blog link field** · deployed URL · project name.

**There is no Devpost, Devfolio or Unstop page for this event.** `firstcommit.devpost.com` is an unrelated hackathon.

### 3.6 One DQ-adjacent risk, fixable in seconds

Rules §05: *"a repository whose history does not match the event dates disqualifies the whole team."*

Dates are clean — all three commits fall inside 17–20 Sep. But all three are `Add files via upload` from the GitHub web UI, which **reads like a pre-built project being pasted in**. Commit incrementally from here. It costs nothing and removes the only plausible ground for suspicion.

---

## 3A. 🚨 Operational hazards other teams hit this weekend

Nothing is built yet and the AWS account does not exist. These are being reported *now*, by participants, and at least two are existential for a Ship It entry.

### 3A.1 🚨 CONFIRMED ON OUR OWN ACCOUNT — all three AI services are gated

This started as four independent participant reports. **It is now verified on our account by the build session**, and it is worse than Bedrock alone.

| Service | Result |
|---|---|
| `bedrock-runtime` Converse, `ap-south-1` | `AccessDeniedException` — *"Your account is currently being verified"* |
| `bedrock-runtime` Converse, `us-east-1` | `ValidationException` — *"Operation not allowed"* |
| `comprehend:DetectPiiEntities` | `SubscriptionRequiredException` |
| `textract:DetectDocumentText` | `SubscriptionRequiredException` |
| Lambda concurrency limit | **10**, not 1000 — the unverified-account signature |
| DynamoDB · S3 · Lambda · IAM | ✅ all working, same credentials |

**So it is not IAM and not region — the AI services are gated together while the account is verified, and they announce it three different ways.** Every model-dependent and OCR-dependent tier is currently unavailable.

**This needs the account owner's action, not an engineering fix.** Activation typically stalls on payment method or phone verification in the Billing console. Nothing needs redeploying once it clears.

**What is verified working end to end regardless:** both Lambdas are deployed and healthy, `/health` returns 200 on each, and a real POST traverses the entire stack — Cedar policy load, DynamoDB ledger read, agent assembly with all three interventions — failing *only* at the Bedrock call, with a clean `503 MODEL_UNAVAILABLE`. `selfcheck.py` is all green; `livecheck.py` against real AWS is 24 passed / 0 failed / 6 skipped, where all six skips are exactly the gated services.

#### What the research closed, 19 Sep — and the part that decides the demo

**This is documented AWS behaviour with an official Knowledge Center article describing the exact symptom pairing.** [Resolve InvokeModel API error in Amazon Bedrock](https://repost.aws/knowledge-center/bedrock-invokemodel-api-error), marked AWS OFFICIAL, reviewed and updated **2026-09-16 — three days ago**:

> "If your account has a security restriction, then you receive the following error: *'An error occurred (ValidationException) when calling the InvokeModel operation: Operation not allowed'*. To resolve this issue, contact AWS Support."
>
> "You might also receive an AccessDeniedException that indicates the model isn't available for your account because of an account-level restriction. **These restrictions don't appear in the Amazon Bedrock console and can't be resolved through IAM permissions or model access settings.**"
>
> "**Amazon Bedrock runtime quotas for the affected model can show values of 0 in the Service Quotas console, even when the AWS default quotas are non-zero. This is another indicator of an account-level restriction.**"

**The unblock path is an AWS Support case under "Account and billing" — free on Basic support — and nothing else.** There is no console self-service fix. Service Quotas increase requests are routinely auto-denied with wording like *"we recommend building more account history … at least one billing cycle."* Observed timings in community threads: cases unassigned 16+ days, several closed without a fix, one user on Business Support still waiting days.

> 🚨 **Plan on the assumption that this does not clear before the deadline.** No AWS SLA exists for it, the reported trigger is "new account without established billing history", and support cannot state a threshold. A fix arriving in time would be luck, not a plan.

**Two things that are *not* the problem, so do not waste hours on them:**

- **Model access was retired on 15 October 2025.** Serverless foundation models are enabled by default in all commercial regions; there is nothing to request. Only Anthropic models still need a one-time use-case form.
- **Nova is Amazon-owned, so there is no AWS Marketplace subscription, no product key, no `aws-marketplace:Subscribe`, and no payment-method Marketplace gate.** Every "did you enable model access?" answer on the internet is inapplicable to Nova.

**One genuine technical constraint, and the PRD already has it right:** Nova Lite and Nova Pro are **not available In-Region in Mumbai** — both are Geo (cross-Region) only. Calling the bare `amazon.nova-lite-v1:0` in `ap-south-1` fails; the `apac.` inference profile is mandatory, not a preference.

✅ **RESOLVED 19 Sep — the PRD's literals are correct and both profiles are ACTIVE.** `aws bedrock list-inference-profiles --region ap-south-1` returns `apac.amazon.nova-micro-v1:0`, **`apac.amazon.nova-lite-v1:0`**, **`apac.amazon.nova-pro-v1:0`** and `global.amazon.nova-2-lite-v1:0`, all ACTIVE. The Nova Lite card's missing APAC subsection is purely a documentation gap. The call succeeds while the account is gated — which makes it evidence worth putting in the writeup: **the configuration is correct and waiting, not wrong.** Nothing in the code or config stands between this build and a working model loop except account verification.

The original caveat, retained because the reasoning still applies to any undocumented profile ID:

⚠️ ~~**Verify the Lite profile ID live rather than trusting the PRD string.**~~ AWS's Nova **Pro** card documents `apac.amazon.nova-pro-v1:0`, but the Nova **Lite** card lists only `us.` and `eu.` IDs and has no APAC subsection — while the same page's own regional table marks Geo = YES for `ap-south-1`. That is an internal documentation inconsistency. Confirm with:

```bash
aws bedrock list-inference-profiles --region ap-south-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId,'nova-lite')].inferenceProfileId"
```

**And check the IAM shape:** a geo profile needs permission on the profile, on the foundation model in the **source** region, and on the foundation model in **all destination regions** in the profile. Destination regions do **not** need to be manually enabled on the account, but an SCP blocking any one of them fails the whole request.

**Two claims to avoid on camera**, because they could not be sourced: that any Nova quota has an AWS default of **30** (no such default was found in the quota tables — ask Service Quotas for the `L-` code before quoting a number), and that Bedrock specifically is excluded from the **Free plan** (AWS documents that the Free plan blocks *some* services but names Savings Plans, Reserved Instances and certain Marketplace offers, never Bedrock). The honest trigger is "new account without billing history", not the plan flag — one reported case was a three-year-old paid account.

**Design consequence, and it is the right one anyway:** every model-dependent step needs a deterministic fallback behind a flag, and the enforcement path must never be the part that depends on a model. Ours does not — Cedar and the checksum tier decide; the model only narrates. That is also the honest framing for the UI (§5.4: `NOT_RUN`, not a red error and not a silent skip) and it is the single best entry in doc 11's "what we learned".

**What other teams did, and it is the right hedge:** keep AWS as the infrastructure spine and put a non-AWS model behind a flag, or give every LLM step a deterministic fallback. One participant's framing is worth copying outright: *"Every LLM step has a deterministic fallback behind a flag, so it ships either way."* For Naka this is cheaper than most — the enforcement path is already meant to be deterministic (checksum → Comprehend → Cedar), and only the agent loop and the multimodal Indic tier need the model. **A Bedrock outage should degrade the demo, not end it.**

### 3A.2 Account and billing friction

- **AWS signup requires a debit or credit card. UPI is not accepted.** This pushed at least one participant off Ship It entirely.
- **Textract is not in the Free plan at all** — one team had to upgrade to Paid. Doc 02's Job 1 already recommends the Paid plan for credit-redemption reasons; this is a second, independent reason.
- **Amazon Connect and some services are heavily constrained on Free Tier**; one participant was blocked from deploying until autopay was activated.
- **The $100 participation credits are broken for a meaningful number of people** — "Claim your credits" greyed out despite verified student status, "We Can't Redeem", student verification "limit exceeded". Do not plan around them arriving.
- **Builder Center verification and an AWS account are separate systems.** Having one does not give the other.

### 3A.3 Nobody is sure where to submit

The submission form is auth-gated and **the deadline hour was sent by email, not published** — the schedule page still says the hours are being finalised. A participant post from 17 Sep titled *"Doubt Regarding the Submission"* asks plainly *"where do we need to submit. I don't find any space for submission"* — and has **zero replies**.

**Treat locating the form as an active task, not an assumption.** Check the registration email, the hackathon page, and the Discord `hackathon` category. The public Discord is `discord.com/invite/wemakedevs` (~73k members) and is functioning as the real Q&A surface.

One community claim worth knowing but **not** relying on: a team asked how to showcase an Android frontend without a deploy URL and was told *"there is no need of actual deployment… no real deployment link was asked."* That is community opinion, not an organiser ruling, and it contradicts the Ship It track definition (*"hand us a URL"*). **Deploy anyway.**

### 3A.4 Winners announced the week of 21 September

From Kunal Kushwaha's launch post, not the website: top 10 get fast-track Amazon interviews, *"announced next week, judges by AWS experts."* Also from that post, and not on the rules page: **you may enter both Ship It and Build It** — *"You can take part in both if you like."*

---

## 4. The judges

Eight AWS people: solutions architects, two TAMs, a senior database engineer, a big-data consultant, a DevOps architect, one DevRel. **Kunal Kushwaha and Hitesh Choudhary are speakers, not judges** — both appeared at Saturday's in-person day only. Do not optimise for either's taste.

**Sourcing caveat:** LinkedIn was auth-walled, so headlines come from search-engine snippets. Blog, GitHub and AWS-blog evidence is first-hand. **Two of the eight have no verifiable technical trail at all** (Manisha Choudhary; "BD Brijesh Dubey", whose linked profile returns nothing anywhere). Attribute no specialism to them.

| Judge | Role | What they publicly care about |
|---|---|---|
| **Arkodyuti Saha** | Community Manager, AWS Developer Experience (ex-GitHub, ex-Microsoft) | **Highest-signal judge.** Gave Saturday's "Why Builders Win" talk. His current public thesis is literally *"shipping without understanding"* — a DevRelCon talk framed as *"the demo worked. the understanding didn't."* **Expect him to probe *why* it was built this way.** Writes dev.to posts on winning hackathons and **"Writing a technical blog 101"** — almost certainly the reader of the blog prize. |
| **Jatin Mehrotra** | Listed as DevOps Consultant; his own bio says **Developer Advocate @ AWS** | Richest technical trail. **Writes exclusively in quantified outcomes** — *"Cut CI/CD Costs by 77% & 2x Deployment Speed."* Also publishes critiques like *"CloudWatch Observability: Game-Changer or Just a Glossy Wrapper?"* — **do not present a thin layer as a platform.** |
| **Veeramani A** | Sr Cloud Support DBE II; DMS and RDS-PostgreSQL SME, 15+ years | **The DynamoDB choice will be read by someone who does this for a living.** One sentence on engine choice and access pattern. |
| **Makendran Gunasekaran** | TAM, Financial Services India | Amazon Connect and AI/ML for **regulated enterprises**; "well-architected" is his register. Compliance framing lands with him — which is our natural register anyway. |
| **Jitesh Udwani** | Solutions Architect (ex-Google), SA-Pro Nov 2025 | Thin public trail. Read as classic SA-Pro architecture instincts. |
| **Aman Raj** | "Big Data Consultant" / "Data and AI Cloud Consultant" | Low confidence, very common name. Assume little. |

### 4.1 What this panel converges on

Three of the four best-documented people point at the same thing, and **it is not scope**:

1. Arkodyuti: *"the demo worked. the understanding didn't."*
2. Jatin: quantified results; calls out glossy wrappers.
3. Hitesh Choudhary (speaker, not judge, but sets house culture): reportedly runs a pipeline that clones the repo, reads the source, checks the deployment, and **compares README claims against what is actually implemented**. *(Reported second-hand, not a first-person post — weight accordingly.)*

**In priority order:**

1. **Do not overclaim.** Every feature in README and video must exist in the repo and work at the URL. Already the rule; now also a documented personal habit of people in the room. Doc 07's "Do not claim" lines and doc 04's §4 holes are the defence — keep them.
2. **Add one "why this, not that" beat** — why Lambda not EC2, why DynamoDB not RDS, why embedded Cedar not AVP. Thirty seconds. Doc 02 has the reasoning; it is not in the video.
3. **One real number, said aloud.** Doc 04 idea #3 already puts `latency_ms` on every chip — that is the beat. Adjectives are invisible to this panel.
4. **One defensible sentence on the data layer.**
5. **Write the blog for Arkodyuti Saha**, following the prize's own three beats, with "what fought back" honest and specific. Doc 12's material is exactly this if reordered.

⚠️ **No quotable statement from Kunal Kushwaha on demo technique exists.** Anything citing one is fabricated.

---

## 5. What wins here — evidence from past events and adjacent AWS hackathons

### 5.1 WeMakeDevs' own history

**Narrow, concrete, often India-specific problems beat ambitious platforms.** The Best UI/UX winner at HackFrost 2024 was **an Android app for finding vacant Indian Railway seats after chart preparation** — a mundane transport utility, not a flashy dashboard. Other winners: observability for a *hydroponic farm*; agents that query any API or file as SQL. This is the site's own *"a small problem solved well beats a big one solved vaguely,"* demonstrated.

**Presentation is scored as hard as code.** The house rubric lists *"clarity of the README, the quality of the demo video"* as a **co-equal** criterion. A past event stated it plainly: *"Six criteria, weighted equally. The demo is scored as hard as the code."* First Commit goes further — the video is *all* the judges see.

**"Real software, not a hackathon demo."** WeMakeDevs' own guidance asks for a repo *"another developer could clone, understand, and extend."*

### 5.2 The pattern across recent AWS agent hackathons

The strongest single correlate among winners: **one hard, specific number in the first paragraph.** 60% false-positive reduction. 21/21 form fields correct. 99.5% action accuracy. ~50× cheaper. 200ms cold start.

**It does not need to be rigorous — one category winner's was n=15. It needs to exist and be specific.**

Doc 04's idea #1 is exactly this: *"This session would have disclosed 11 identifying fields about 3 people. It disclosed 5."* **The finding is that it belongs in the README's first paragraph too, not only at 2:45 in the video.**

Other repeated traits: narrow unglamorous named vertical (zero generic chatbots won); deployed and clickable, not a localhost recording; 5–8 AWS services each with a reason; a human-readable output artifact; and meeting the checklist literally — architecture diagram, real setup instructions, end-to-end video.

**Anti-pattern worth knowing:** essentially nobody built a rigorous eval harness, and self-reported domain metrics sufficed. Doc 07's concession that there is no eval set is normal for this category, not a standout weakness.

### 5.3 Best UI — the actual bar, from live demos

Three entries are already deployed and genuinely good. This is not a soft category.

**GrievEase AI** — *the one to beat on judge experience.* Dark near-black canvas, teal/mint accent, monospace label system. A sticky top bar carries **live architecture chips** — `Step Functions · Bedrock RAG · DynamoDB Guard · ● ap-south-1 LIVE` with a green pulse dot — so the AWS story is on screen before you scroll. The standout move is a row labelled **"1-CLICK LIVE TEST SCENARIOS (INSTANT JUDGE WALKTHROUGH)"**: four category-tagged cards that each populate a real, fully-written payload on click — *including a deliberate failure case* ("Guard Guardrail Test: Expired Statutory Limitation"). Someone worked out that the judge has three minutes and zero context, and removed every click between arrival and a working demo.

**HaqCheck** — *the best pure craft.* Warm charcoal, peach accent, an elegant serif display face with a hand-drawn underline stroke, small-caps sans micro-labels. An actual typographic point of view, not a Tailwind default. Preset scenario chips labelled in human terms ("Bengaluru, 73d — the dispute", "90-day boundary"). Verdict cards render **per-condition rows with real progress bars** — "Days worked in the last 12 months: **73 / 90**" with a partially-filled orange bar — plus a "Next Step" line. A **rulebook version hash** pinned in the corner. It renders *why*, not just *what*.

**VeriAI** — *the best light-mode work.* Warm off-white, floating pill navbar with a "☁ LIVE AWS DEMO" badge, enormous tight-tracked display type, generous whitespace, a dark inverted stats panel. Product-grade rather than hackathon-grade.

**And the counter-example:** `AgentShield` — the most technically rigorous project in the space — ships *"a bare Live demo / Benchmark toggle over a long dropdown of raw session IDs."* **It will win on substance and lose Best UI outright.** That is the exact gap available to us, against the one project whose thesis is closest to ours.

**What the bar actually consists of** — nothing exotic, no 3D, no heavy animation:

1. A committed theme (dark or warm-light) with **one** accent colour and a real type pairing.
2. **Live AWS-service status chips in the header** — this is also how you satisfy "the video must show AWS" without cutting to a console.
3. **One-click preloaded scenarios, including a deliberate failure case.** Doc 10's fixtures already exist; exposing them as buttons is the cheapest Best-UI upgrade available and it converts doc 10 from a script into an interface.
4. **Per-decision explainability as bars and chips, not prose.** The disclosure meter and doc 04 idea #5's filling ID card are already this; HaqCheck proves the pattern reads.
5. **A visible version or provenance hash.** Our policy-version badge does this.
6. Multilingual toggles where the domain is Indian.

Also worth keeping from the AWS-hackathon data: a category winner used **React 18 + AWS Cloudscape** (AWS's own design system, Apache 2.0). It reads instantly as "a real AWS product" — but it also looks like the console, which is a liability in a prize explicitly for *design*. Doc 03 should keep its own system. Borrow only the semantics: **three verdict colours, no more, as filled pills with icons, never coloured text** (coloured text dies under video compression), monospace for everything machine-authored, sans-serif for everything human.

### 5.4 Demo and UI craft — specific borrows, with references

> **Status, 19 Sep.** Applied to `naka/web` by the build session: one-click scenarios, sticky nav, honesty states, icon-plus-word status rows, and the colour remap. **Not applied** (below the line on time): µs latency, a pinned engine version, Rego-style coverage tinting on the policy editor, and the Cloudscape token lift. Of those, **coverage tinting is the one to take first if any time reappears** — it is two CSS rules and nothing else in the field has it.
>
> Two things went further than these notes asked, and both are worth knowing:
> - **Honesty states became a live probe, not a label.** A `GET /diag` route on the control plane probes Comprehend, Textract and Bedrock server-side with a 60-second cache and returns per-tier `PASS` / `NOT_RUN` / `FAIL`. The panel therefore reports *this account, right now*, rather than a claim baked into the page — and `AccessDenied` / `SubscriptionRequired` map to **NOT_RUN in neutral grey**, never FAIL in red, because gated is a provisioning state and not a defect. Given §3A.1, this converts the weekend's worst problem into the most credible thing on the screen.
> - **Each scenario mints a fresh session id**, so scenario 2 cannot inherit scenario 1's spent ledger. Without that, "budget bites" fires before it is meant to and the demo tells a lie about its own mechanism.
>
> **The CDN-outage risk is now measured, not asserted.** With all five globals deleted and every external script tag stripped, re-rendered on the same origin so `motion.js` genuinely reads undefined for gsap, ScrollTrigger, Lenis, anime and lottie: 12/12 reveals visible, hero intact, 4 scenario buttons, sticky nav, 4 detector-tier rows, policy textarea loaded, agent URL prefilled, correct empty-state copy. **The console is fully usable with zero animation libraries loaded.** The concern was legitimate; the answer is now a measurement rather than a promise.
>
> The colour remap also **found a real bug**: `render.js` still referenced `var(--ok)`, `var(--warn)` and `var(--muted)` after a stylesheet rewrite renamed them, so every status pill was rendering with an undefined colour, silently. Custom properties have no build-time check in a no-build stack. See `03-ui-ux-design-spec.md`, superseding block, which now reconciles the spec against what shipped.


From a sweep of the reference tools (Cedar playground and the OPA Rego Playground were driven in a real browser; Langfuse, Datadog, Honeycomb, Grafana, MCP Inspector, Braintrust read off docs and screenshots) plus 2025–26 hackathon Best-UI/Best-Design winners. These feed **doc 03**, and several cost under an hour.

**The four cheapest, ranked:**

1. **Coverage tinting on the policy source.** OPA's Rego Playground, with Coverage on, paints **full-bleed row backgrounds across the whole editor**: pale green for lines that executed, pale red for lines that did not. Applied to Cedar: **tint the policy lines that were determining for this decision green, and the evaluated-but-unsatisfied ones red.** It makes "which rule actually fired" obvious with zero extra chrome. Cedar's own playground does not do this; neither does anything else in our field.
2. **Pin a version string.** Cedar's playground shows `Cedar v4.11.0` under its H1; OPA pins `OPA v1.20.2, Regal v0.42.1-…` bottom-right. Two tiny details that read as production software rather than a weekend build. We already have a policy-version badge — add the engine version beside it.
3. **A coverage ratio.** Bedrock Guardrails returns `guardrailCoverage.textCharacters { guarded, total }`. Rendering *"inspected 4,812 / 4,812 characters"* is a genuinely novel overlay — **nobody in the reference set shows this** — and it pre-empts "did you scan all of it?" without a word of narration.
4. **Microsecond latency above the result.** The Rego Playground prints a grey status line `Found 1 result in 38.763µs.` directly over the OUTPUT. A `cedarpy` evaluation genuinely is µs-scale. Doc 04 idea #3 already puts `latency_ms` on every chip; **printing the authorization step in µs rather than ms is strictly more persuasive**, because it proves the guardrail is free rather than merely cheap.

**⭐ The Cedar playground is built on AWS Cloudscape** (`@cloudscape-design/components`, confirmed in the `cedar-website` source). So the Cedar playground, the Verified Permissions console, the Bedrock Guardrails console and CloudWatch GenAI Observability are **all the same design system.** Doc 03 should keep its own visual identity — but lifting Cloudscape's *status tokens* costs nothing and makes the decision surface read as an AWS-grade policy tool rather than a hackathon dashboard.

Read off the playground's compiled CSS:

| State | Border | Background | Icon |
|---|---|---|---|
| success | `#00802f` | `#effff1` | `#00802f` |
| error | `#db0000` | `#fff5f5` | `#db0000` |
| warning | `#855900` | `#fffef0` | `#855900` |
| info | `#006ce0` | `#f0fbff` | `#006ce0` |

Alert geometry, measured: radius **12px**, border **1.5873px**, padding **8px 16px**, header **700 weight, 14px Open Sans**, filled circle glyph left of the header. Primary button: `#006CE0`, white, weight 700, 14px, **border-radius 20px — a full pill, not a 4px rectangle.** That pill radius is reportedly the single detail that makes a UI read as AWS-native.

**⚠️ The colour semantics are not what I would have guessed, and most hackathon projects get this wrong.** Across all four AWS products: **green = allowed / no action taken · red = denied *or evaluation error* · amber = intervened, content modified but not fatal · blue = informational.** In Bedrock Guardrails specifically, a successful *block* renders as **amber** — `⚠ Intervened (3 instances)`, plain amber text, no filled badge — because **red is reserved for something failing, and a block is the system working as designed.**

For us that maps: **allow = green · redact/degrade = amber · deny = amber, not red · a detector or policy error = red.** This is a better semantic than the three-colour scheme I would otherwise have specified, and it is the one a judge from AWS will read fluently.

**The verdict component.** Cedar's playground renders decisions as a **full-width alert sitting immediately below the card description and *above* the form fields** — the result appears at the top of the input form, so you never scroll to find it. One sentence, sentence case, ending in a period: `Authorization decision: allow.` / `Authorization denied.`, with **diagnostics nested inside the same alert** under a bold `Errors:` heading. (Note: the playground is a **single-column stack of Cloudscape Container cards**, not a multi-pane IDE — don't copy a layout it doesn't have.)

**Steal the error template verbatim:** `${error.code || 'Error'} at ${policyId}: ${error.message}; ${error.help || ''}` — code, policy id, message, help, one line. There is a parallel bold `Warnings:` block.

**On surfacing determining policies — corrected.** The Cedar playground **never lists them** (confirmed in source; it renders only `decision` and `diagnostics.errors`). But the **AWS Verified Permissions test bench does** — its result is three blocks: the decision, **the policies satisfied**, and the errors. So showing which policy decided beats the *public playground* and has an *AWS precedent to point at*, which is a better position than "we invented this."

**Two more patterns worth lifting, both cheap:**

- **List every policy category, including the ones that did nothing.** The Guardrails trace is a three-column table — Category | Test result | Details — that shows `Sensitive information filters · ⚠ Masked · Detected PII type 'Jane Doe (NAME)', guardrail behavior: mask` alongside `Content filters · ✅ No action · —` and two more quiet rows. **That completeness is what makes it an audit rather than an error log.** Result is icon + coloured word with **no pill background**; Details is one sentence in a fixed shape.
- **Show raw next to redacted.** The Guardrails test drawer pairs **`Model response`** (raw, unmodified) directly above **`Final response`** (post-guardrail) — `Jane Doe` / `jane.doe@gmail.com` above `{NAME}` / `{EMAIL}`. This is the clearest ten-second proof that redaction works, and doc 04 idea #5's ID card is the same idea in a different grammar. Both can ship.

**Do not hand-roll a Cedar grammar** — the Cedar org publishes **`highlightjs-cedar`** and **`prism-cedar`**. It also publishes a repo called **`cedar-for-agents`**, which is worth ten minutes before finalising any novelty wording.

**OPA's coverage highlighting is literally two CSS rules:**

```css
._lineCovered    { background: rgba(0, 255, 0, 0.35); }
._lineNotCovered { background: rgba(255, 0, 0, 0.35); }
```

Full-width line backgrounds, not gutter markers. Their in-product wording is worth adapting: *"Red expressions were never evaluated. Red rule heads were never defined. Green expressions were evaluated at least once."*

**Honesty states.** `ContextSeal` (honourable mention, DataHub Agent Hackathon 2026) shipped evidence states **`PASS` / `NOT_RUN` / `FIXTURE`** — deliberately refusing to collapse "not evaluated" into a green tick — and was credited for it. That is exactly this project's register, and it applies directly to the shadow-mode rows and to any detection tier that did not run.

**Three states, not two.** Every winner surveyed shipped three or four: `GO / NEEDS_REVIEW / BLOCK` (Launch Control), `APPROVE / ESCALATE / REJECT` (HealthVet), `ALLOW / DENY / ASK / MODIFY` (`mcp-guard`). **A binary looks like a demo; three states look like a product.** Doc 04 idea #6's allow/degrade/deny is already this — it is worth building for that reason alone, not only for the UIDAI last-four rule.

**Waterfall and table craft**, if any trace view ships: rows 30–34px with faint zebra (Honeycomb ≈33px, Grafana ≈32px); **colour encodes identity, never severity** — Datadog colours frames by service and marks errors with a 2px crimson stroke plus a red `!` badge that *ancestors inherit*, so the error path reads as a red spine; duration label **inside** the bar when wide, **outside** when narrow, and sub-millisecond spans collapse to a single coloured dot; count pills in tab labels, **red only when non-zero**. Grafana's shipped dark tokens are worth lifting wholesale: canvas `#111217`, surface `#181b1f`, elevated `#22252b`, border `#383b42`, blue `#3d71d9`, red `#d10e5c`, green `#1a7f4b`, orange `#ff9900`.

**Two narrative beats that cost nothing:**

- **Name which leg of the lethal trifecta the guardrail breaks.** Simon Willison's framing — private data + untrusted content + external communication — is the most widely understood statement of this threat class. Saying on camera which leg is severed is one sentence and it locates the project instantly for anyone who has read it.
- **Quote the Claude Code finding that 93% of permission prompts were being approved reflexively rather than reviewed.** That is the argument for why a guardrail must *decide* rather than *prompt* — and it pre-empts "why not just ask the user?"

**Rubric language worth knowing**, because it is how design gets scored elsewhere and it sharpens what to show: the SANS FIND EVIL! 2026 rubric is the closest published rubric to this project — *"**Constraint Implementation** — whether guardrails are architectural versus prompt-based; testing for bypass vulnerabilities"* and *"**Audit Trail Quality** — traceability from findings to specific tool executions producing them."* Devpost's default rubric makes **Design a full quarter of the score**, defined as *"Is the user experience and design of the project well thought out?"* And UC Berkeley's Best UI/UX judges explicitly score legibility at a glance: *"if we're having a hard time understanding the project by looking at it, there may be a problem."*

⚠️ **Caveat on this sweep:** it hit a search-call cap partway through, so a few threads (exact Datadog and Jaeger token values, one competitor's UI) are unresolved. The Grafana hexes were read from the repo source and are solid.

---

## 6. New facts that touch the architecture

### 6.1 Hindi: Comprehend cannot, Guardrails can — and the inverse holds too

This resolves README pre-flight item #4.

| | Amazon Comprehend PII | Bedrock Guardrails sensitive-information filter |
|---|---|---|
| **Hindi** | ❌ Dev guide: English and Spanish only. The `hi` enum value **is accepted by the API and will not do what you want.** | ✅ 17 languages, all "Optimized and supported," Hindi among them |
| **Indian entity types** | ✅ `IN_AADHAAR`, `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER`, `IN_NREGA` | ❌ **None.** General/Finance/IT/USA/Canada/UK only. Aadhaar and PAN require custom regex — and **regex lookarounds are not supported.** |

**Each service has exactly what the other lacks.** That is a real architecture sentence the package does not currently contain, and the honest version of it — *"we assumed Comprehend covered Hindi, tested it, were wrong, and routed Hindi differently"* — is precisely what scored criterion #03 rewards. It is also the strongest single item for doc 12's "what fought back" section.

### 6.2 Verified regional facts

| | `ap-south-1` |
|---|---|
| Bedrock, AgentCore (Runtime, Memory, Gateway, Identity, Observability), Comprehend, Textract, Transcribe, Translate, Rekognition, DynamoDB, X-Ray, CloudWatch, **Amazon Verified Permissions** | ✅ |
| **Guardrails as an information provider in Cedar policy** | ❌ (7 regions, not Mumbai) |
| Bedrock Guardrails **Automated Reasoning checks** | ❌ (7 regions, not Mumbai) — do not claim it |
| Amazon Q Developer · Q Business · Lex · Managed Grafana · AgentCore Registry | ❌ |

**AVP is `$0.000005` per `IsAuthorized` call and is in `ap-south-1`.** The cost argument against it does not exist. See §2.1.

### 6.3 Worth checking, cheap

**CloudWatch Transaction Search must be enabled once per account and takes ~10 minutes before spans are searchable.** If any trace view is wanted in the video, enable it early rather than discovering the delay on Sunday.

---

## 7. What to do with this

Ordered by (impact ÷ hours), and **nothing here contradicts doc 04's kill list**.

| | Action | Cost | Why |
|---|---|---|---|
| 0 | **Test `InvokeModel` the moment the AWS account exists**, and put a deterministic fallback flag behind every LLM step | 0.5 h | §3A.1. Bedrock is returning quota-0 on new accounts this weekend. Not recoverable on Sunday. |
| 1 | **Add "what I learned" + AI-tools list to doc 11; give doc 12 the WeMakeDevs Space venue and the three-beat order** | ~1 h | One scored criterion, one hard rule, one prize — all currently unmet. The blog prize is winnable on current volume (§1.1). |
| 1b | **Expose doc 10's fixtures as one-click scenario buttons, including the failure case** | ~1 h | §5.3. The cheapest Best-UI upgrade available, and the category's strongest entrant has a bare UI. |
| 1c | **Put the data subject into every sentence about combination risk** | 0.25 h | §2.0. "Individually permitted, jointly dangerous" now reads as AgentShield unless the person is named. |
| 1d | **Establish in the first 15 seconds that this is about the payload, not the tool call** | 0.25 h | §2.0b. Six teams built "Cedar gates the agent"; the differentiator is that we authorize the *data coming back*, and nobody else in the event does PII at all. |
| 2 | **Do NOT use the "permits or denies" quote - it is not real (§1.4).** Put the AWS *"Response modification - Use Policy: Not supported"* table row in the README instead, and sharpen the novelty claim to "authorization returns a decision, not a document" | 0.5 h | A fabricated citation in front of AWS SAs is the worst available error; the real table row makes the point better, and "we authorize responses" is falsifiable in one search. |
| 3 | **Move the counterfactual number into the README's first paragraph** | 0.25 h | Strongest single correlate among AWS hackathon winners. Already built (doc 04 #1). |
| 4 | **Fix "GA in Mumbai" → "available"; state the information-provider region gap accurately** | 0.25 h | Doc 07's rule 2: never defend a claim you cannot support. |
| 5 | **The Hindi routing sentence, and its "what fought back" version in the blog** | 0.5 h | Real architecture, and criterion #03 is scored. |
| 6 | **A "why this, not that" beat — Lambda/EC2, DynamoDB/RDS, cedarpy/AVP** | 0.5 h | Aimed squarely at this specific panel. Reasoning exists in doc 02. |
| 7 | **Sharpen the AVP rebuttal to latency and design, not cost** | 0.25 h | Two AVP projects in the room; the cost argument is gone. |
| 8 | **Incremental commits from here** | 0 | Removes the only DQ-adjacent read on the repo. |

### The one demo beat worth adding if anything is added

**The same tool call, three times, in one session — progressively more redacted as the ledger fills.** Call 1 returns the full record. Call 3 returns the same record with the DOB now a placeholder, *because the session already holds name and PIN code for that person*.

Nothing in the field can show this. Every other accumulation mechanism found — OCELOT (trajectory), CAMP (session), Dogwood (session, pinned to caller principal), aperture (audience), hoop.dev and toolmask (caller role) — keys to something other than **the person the data is about**. That keying is the one load-bearing claim that survived the entire sweep, and this beat demonstrates it rather than asserting it.

---

## 8. Confidence and coverage

- **Verbatim quotes** from `wemakedevs.org` pages were taken from raw HTML, not summaries.
- **Judge profiling** is first-hand for blog/GitHub/AWS-blog sources, snippet-derived for LinkedIn. Two of eight judges are unprofiled. The Hitesh Choudhary README-auditing claim is second-hand.
- **In-hackathon enumeration depends on repo descriptions mentioning the event** plus AWS Builder Center posts. A submission with a generic description and no blog post is invisible to this method, so §2 is near-complete, not exhaustive.
- **X/Twitter and LinkedIn were not readable** — the browser profile is not signed in, so build-in-public threads under #BharatBuilds are unswept. The Discord `hackathon` category was left unread by instruction. Both are follow-ups if wanted.
- **The `AgentShield` assessment is from its README, Builder Center post and live demo**, not its source. Its benchmark numbers are self-reported, as are `leash`'s and `Pocket Change`'s.
- **The service-popularity counts in §2.0b are over 53 First Commit READMEs** read directly from `raw.githubusercontent.com`, out of ~230 repos created in the window and ~70 plausibly in this event. GitHub repo search does not index READMEs, so a project that never names the hackathon in its name or description is invisible.
- **The demo/UI sweep in §5.4 hit a search-call cap**; a few token values are unresolved. The Grafana hexes came from repo source and are solid.
- **`ap-south-1` support for AgentCore Policy** is doc-table-confirmed but contradicted by secondary sources — medium confidence, verify before stating on camera.
- **`suppressOutput` semantics are unverified** and are the one open item that could weaken §1.4's framing.
