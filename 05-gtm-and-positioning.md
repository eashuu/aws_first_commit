# GTM and Positioning

**Project:** disclosure budgets for AI agent tool calls (name: **Naka** — see §4 for how it was chosen and what it replaced)
**Parent document:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md`. Every factual claim here traces to that PRD or to a source cited inline.
**Written:** 18 September 2026
**Constraint:** PRD §13 lists claims that are factually wrong. None of them appear here, and §9 of this document restates the prohibitions so that anyone writing copy from this file cannot miss them.

**What this document is for.** The hackathon needs a repo, a writeup and a video — not a go-to-market plan. This exists because two of the prizes (Ship It, and the fast-track interview) put this project in front of people who will ask commercial questions, and because the team should know before Sunday which sentences it can defend and which it cannot. Nothing here should slow the build down. The only part with a Sunday deadline is §4 (naming) and §5 (messaging), because both go into the video.

---

## 1. Ideal customer profile — and who actually pays first

### 1.1 The obvious ICP

PRD §3 names the user precisely: *a small Indian team shipping an agent over a customer database, support desk or document store; no security engineer, no compliance budget.*

That description is accurate about who has the **problem**. It is close to a definition of someone who does not have a **budget**. "No compliance budget" is in the sentence.

### 1.2 Testing whether the user is the buyer

Four questions decide this:

| Question | Answer for the small-team ICP |
|---|---|
| Do they feel the pain before an incident? | No. The failure is invisible by construction — PRD §3: every individual call looks clean and the audit row says "0 entities found." Nobody feels an aggregation leak until someone else points at it. |
| Is there an existing line item this replaces? | No. They are not currently paying anyone for agent data controls. New line items are the hardest sale there is. |
| Who signs? | The founder or CTO, who is also the user. Short chain, which is good — but the same person is prioritising revenue features. |
| What would make them act this quarter? | An external demand. Nothing internal to a five-person team generates urgency about a low-probability event. |

**Conclusion: the small team is the user, not the buyer.** They will run the open-source version, star the repo, file issues, and never pay. That is not a failure — it is the distribution channel. Treating them as the buyer is the failure.

### 1.3 Who actually pays first

The buyer is the person who owns the answer to *"what happens when our agent hands a customer's Aadhaar number to a model?"* — and who is being asked that question by someone outside the company. Ranked by how soon money moves:

**1. The Indian services firm building agents on a client's data.** (Most likely first cheque.) An IT services, BPO or product-engineering firm deploying an agent over a client's customer records is contractually a Data Processor. DPDP s.8(2) makes processor engagement valid only under contract, and s.8(1) keeps the Fiduciary liable regardless of what the contract says (PRD §13) — so the client will push controls down the chain and will want them evidenced. This buyer pays because a contract clause requires it, not because they believe in it. That is the most reliable kind of buyer. India's services industry is also the single largest concentration of teams building agents over *other people's* regulated data, which makes it a structurally Indian wedge rather than an accident of where the team is.

**2. The 50–500 person company selling into a bank, insurer or hospital.** They have one security person or a CTO who owns compliance. Their trigger is a security questionnaire from a prospect: a deal is blocked, and this unblocks it. They are buying a *sales artifact* — the audit log in PRD §10 — as much as a control. Expect them to ask for the log format before they ask for the redaction.

**3. Regulated Indian sectors, where the rules are already in force.** RBI's 2018 payment-data localisation directive and the CERT-In 2022 directions bind today; DPDP's substantive obligations do not commence until around May 2027 (PRD §13). Aadhaar Act s.29(4) — no public display of Aadhaar numbers, UIDAI permitting display of only the last four digits, with a civil penalty of up to ₹1 crore per contravention under s.33A — is also in force today. A BFSI or health buyer has a live obligation, not a future one. They are slower to sell to and harder to satisfy, but they have the budget.

**4. The security team at a large enterprise adopting agents.** Real budget, longest cycle, and the one most likely to already be inside an AWS enterprise agreement — which makes AgentCore Policy the incumbent and this a feature request rather than a purchase. Not a first customer.

### 1.4 The honest shape of the first revenue

The first money is more likely to be **design-partner or implementation money than a subscription**: someone paying for the policy to be written for their tool surface and the ledger wired into their agent, with the software thrown in. That is not a venture-scale motion and it should not be dressed up as one. It is, however, how you find out what the policy language needs to express before you build a product around a guess.

**The buyer's actual job-to-be-done, in their words:** *"I need to be able to say what our agent is allowed to learn, and show someone a log proving it held."* PRD §3 states the same thing as an absence: this is what the user cannot do today.

---

## 2. Value proposition

### 2.1 One sentence

> An AI agent gets a budget for how much it may learn about any one person, and that budget is enforced across every tool call in the session — not one call at a time.

**Skeptic:** *"Budget is a metaphor. What is actually enforced?"*
**Answer:** A count of distinct identifying field types disclosed about one data subject within one session, held in agent state, passed into the policy engine as a set and a number, and evaluated by Cedar before each field is revealed (PRD §6.1). When the count reaches the threshold, further identifying fields are replaced with numbered placeholders. It is a quasi-identifier accumulator with a hard ceiling. It is not differential privacy, and we never use that vocabulary (PRD §6.3).

### 2.2 One paragraph

> Guardrails for AI agents decide one call at a time. A tool returns a name — allowed. The next returns a phone number — allowed. The next returns the last four digits of an Aadhaar — allowed, because none of them is an Aadhaar number. Together they identify a real person, and no control in the path noticed, because each was designed to answer a question about a single payload. This project tracks what a session has cumulatively disclosed about each data subject and feeds that back into the authorization decision, so the fourth call is judged against the first three. Redaction is expressed in the same policy language as the allow/deny decision, over the same principal, producing one audit record. Denied values become numbered placeholders that can be substituted back on the trusted side if a later authorized call needs them, so the task still completes — the model just never held the digits.

**Skeptic:** *"An agent with a large context window sees the whole conversation anyway. What stops it recombining across sessions?"*
**Answer:** Nothing, and we say so. The ledger is per session — authoritative in DynamoDB, keyed on the session, with `S3SessionManager` holding a cached copy in agent state (PRD §5, §11.2). Cross-session accumulation by the same principal is a real gap and is named as one. What the ledger does prevent is the unbounded case — an agent making three hundred autonomous calls inside one task, which is the mechanism PRD §1 identifies as new with agents.

**Skeptic:** *"Your detector will miss things."*
**Answer:** Yes. PRD §8 records that the Comprehend AI Service Card is dated November 2023, publishes no per-entity accuracy table, states name F1 ≥0.87 / phone ≥0.88 / address ≥0.91 on internal datasets, publishes **nothing** for Aadhaar or PAN, and names degraded performance on OCR and transcribed text. PRD §9 names embedded images inside text-layer PDFs as the hole a judge could puncture. Detection quality is the floor under every DLP product in this category, ours included. The contribution is what happens to a detection *after* it is made, not the detection itself.

### 2.3 Three bullets

- **Subject-scoped, not actor-scoped, not call-scoped.** Cross-call state exists and is not rare — AWS's Dogwood counts over tool-response history, Pipelock carries a per-session threat score, Microsoft Purview accumulates exfiltration signal into DLP enforcement, and CAMP and OCELOT formalised cumulative disclosure in papers this year (`01-competitive-landscape.md` §1.2). What none of them does is accumulate **per data subject** and turn that accumulation into a **redaction** decision expressed in the same policy language as the allow/deny. *Skeptic: "Prove nobody else does this." We cannot prove a negative. We name what we surveyed and what each one does, in §3 and in the writeup, and invite correction. The claim is about a composition, not about being first to a category.*
- **Redaction is a policy decision, in the same language as the access decision.** AWS gives you Cedar for allow/deny and leaves redaction to a hand-written Lambda. Pipelock redacts from YAML patterns rather than identity-aware policy. LangChain redacts with no authorization layer at all. Here both questions go to Cedar with the same principal and land in one audit row. *Skeptic: "So it is a code-organisation argument." Partly, yes — and that is what makes it operable: one place to change, one record to read, one thing to show an auditor.*
- **The Indic-script gap — not "Indian identifiers", which is not a differentiator.** Presidio ships `IN_AADHAAR` *with checksum validation*, plus PAN, Voter, Passport, Vehicle Registration and GSTIN, free; Comprehend carries four Indian types. Claiming those as novel is falsifiable in one link. **The real gap is script:** Comprehend does English and Spanish, Textract OCRs Latin script only, so the regional-script name printed beside the English on every Indian identity document is invisible to the whole stack (PRD §4 claim 3). The model is Nova on the `apac.*` inference profile because Claude on Bedrock in Mumbai is available only through the `global.*` profile, which AWS states can route requests outside the source Region (PRD §2.2). *Skeptic: "Cross-border transfer is legal under DPDP." Correct — s.16 uses a negative list and no country has been notified (PRD §13). This is data minimisation and defence in depth, not a transfer block, and we say exactly that.*

---

## 3. Competitive positioning

Source for all prior-art facts: PRD §2.3, which corrected an earlier draft that claimed nobody governs agent tool traffic. That claim was false and would have failed in front of an AWS audience.

### 3.1 The field

| What it is | What it does | Where it is strictly better than us | The gap we address |
|---|---|---|---|
| **Amazon Bedrock AgentCore Policy** (GA 3 March 2026, available in Mumbai) | Cedar, default-deny, principal from JWT, action from the MCP tool call, every decision logged to CloudWatch | Managed, supported, in-region, integrated with the rest of AgentCore, and it is AWS's own roadmap. On any question of operational maturity it wins. | Decides *whether a call happens*. It does not evaluate the returned fields against what the session already learned. |
| **AgentCore Gateway RESPONSE interceptors** | A Lambda with read/write on tool payloads | The supported extension point for exactly this kind of work; the production path for this idea. | The interceptor is where you would *put* a disclosure ledger. It does not give you one — it is stateless per request, so the ledger has nowhere to live. |
| **Pipelock** (884★, open source) | Placeholder redaction with signed receipts; a per-session threat score and taint escalation across task boundaries | Signed receipts are a real feature we deliberately excluded (PRD §11, "Will not"), and its numbered typed placeholders predate ours. | Redacts from YAML patterns, not identity-aware policy. Its accumulation is a behavioural threat score about the agent — no notion of a data subject, and no disclosure total per person. |
| **Bedrock Data — Agent DLP** (commercial, 30 July 2026) | Runtime DLP for agents | A shipped commercial product with a support contract. | Per-payload, like the rest. |
| **LangChain 1.0 `PIIMiddleware`** | Detects five types only — email, credit card, IP, MAC, URL — and blocks/redacts/masks/hashes them. `apply_to_tool_results` **defaults to `False`**, there is no restore, and it does not touch tool *arguments* at all | It ships in the most widely used agent framework, so it is the default answer most teams will reach for. | Not equivalent prior art for rehydration, and not Indian-identifier aware. Redaction with no authorization layer — no principal, no policy, no decision record. |
| **AI-DLP / AI-security-posture vendors** | Inspect traffic between people and AI applications, at the browser or the network | Mature detection, broad app coverage, enterprise deployment stories. | A different chokepoint. They watch a human sending data to an application. The agent's tool loop happens server-side and never crosses that boundary. |

### 3.2 The positioning sentence

> The per-call guardrail is a solved and crowded category. What none of these does is accumulate **per data subject** and feed that accumulation back into the authorizer as a **redaction** decision, in the same policy language as the allow/deny.

That is the whole claim, and PRD §2.3 says it survives contact. **Do not extend it to "none of them carries state across calls" — that is false six ways** (Dogwood, CAMP, OCELOT, Noisegate, Purview, Pipelock; `01-competitive-landscape.md` §1.2).

### 3.3 The three questions to prepare for

1. **"AgentCore Policy already shipped — and so did Dogwood. What is left?"** — Agreed, and we open with both rather than waiting to be caught (PRD §14). AgentCore Policy answers *may this call happen*; Dogwood adds temporal operators and `count`/`sum` over session event history, so a cumulative budget is already *expressible* from the vendor. What nothing in AgentCore does is populate those events with detected entity types attributed to a person, or produce a field-level redaction as the outcome. This answers a second question — *may this principal learn this field about this subject, given what it already knows* — and our ledger would drop straight into a Dogwood information provider, which is the production path. In production the right home for this is a Gateway RESPONSE interceptor with Amazon Verified Permissions behind it. That is a roadmap answer, not a competitive one.
2. **"Why not just put PII rules in Guardrails?"** — Bedrock Guardrails' sensitive-information filter does not evaluate tool fields, and it has no Indian entity types (PRD §12 beat 2; show the AWS doc line on camera).
3. **"Isn't this just DLP with extra steps?"** — DLP asks "is there PII in this payload." This asks "has this principal now learned enough to identify this person." The unit of analysis is the data subject across a session, not the payload. Use the established vocabulary — *agent firewall, agentic DLP, MCP guardrails, tool-level policy enforcement* — and anchor on OWASP Top 10 for Agentic Applications 2026, **ASI02 Tool Misuse and Exploitation** (with ASI03 second), never "T2", which belongs to OWASP's older threats-and-mitigations paper (PRD §2.3). Stronger still, and true: the 2026 list has no entry for cumulative sensitive-information disclosure. Inventing a term reads as not having looked.

### 3.4 What we are not positioned against

Not against AWS. The project runs entirely on AWS, in Mumbai, and the honest framing is that this is a missing layer *in* the AWS agent stack, demonstrated with AWS primitives. For a hackathon run with AWS, and for a fast-track interview at Amazon, this is also the only framing that makes sense.

---

## 4. Naming

> **Decided: the project is `Naka`.** The analysis below is kept intact because it is the record of why. Summary: the working name `Chowki` collided with a live PyPI package in the same category (§4.1), carried a political register in India (§4.2), and could not be spelled from hearing it once — which is fatal for a project whose only distribution channel is a spoken three-minute video. `Naka` clears all three and keeps the checkpoint image. Every other document in this package has been renamed; this section deliberately still says "Chowki" where it is discussing the rejected name.

### 4.1 The finding that decided it

**A Python package named `chowki` already exists on PyPI, and it is in the adjacent category.**

- `chowki` 0.2.0 on PyPI, MIT, alpha, Python 3.11–3.13, repo `github.com/Git-Uzair/chowki` (verified 18 September 2026; the repo currently shows 0 stars).
- It describes itself as *"a durable execution control plane for LLM agents"* and lists **secret redaction**, **token budgets**, approval gates and crash recovery. It integrates with LangChain, CrewAI, OpenAI Agents SDK and Pydantic AI.

So the collision is not a distant one. It is the same name, in the same category, using two of the same words this project uses — "control plane" and "budget". A judge who hears "Chowki" in the video and searches for it finds an unrelated agent-guardrail project that also redacts and also budgets. That is a credibility problem in the exact channel the project is judged in.

The npm name `chowki` is free and the GitHub org name `chowki` is taken, but neither matters much: this is a Python project, and every short word is already taken as a GitHub org, so the repo lives under a personal account whatever it is called.

This is a confusion problem, not a legal one. A common Hindi noun used by a zero-star alpha project generates no meaningful exclusive rights in either direction, and we make no claim about the other project's rights or ours. **Trademark status was not established:** the Indian register at `ipindia.gov.in` must be searched directly for Class 9 and Class 42, and a general web search does not substitute for that. If the project ever becomes commercial, that search is a prerequisite, not a formality.

### 4.2 Assessment of "Chowki"

**For an Indian audience — mostly good, with one live problem.**
- *Chowki* (चौकी) is understood immediately: a police outpost, the basic unit of police presence in an area. The metaphor of a checkpoint everything must pass through is exactly right for a tool boundary.
- It also means a low wooden stool or bench, which is the first meaning many people reach for domestically. Ambiguous, though harmless.
- The live problem: **`chowkidar` is politically loaded in India.** "Chowkidar chor hai" and the BJP's "Main Bhi Chowkidar" campaign made the watchman word a partisan object in 2019, with the hashtag reported in the millions of mentions. *Chowki* is the post, not the watchman, so it is one degree removed — but the association is close enough that a segment of an Indian audience will hear a political register in a security product. There is no upside to carrying that.

**For an international audience — weak.**
- It carries no meaning at all. That is survivable; many good names don't.
- What is not survivable is that an English-speaking reader parses the first syllable as "chow", which in English is food slang. Searching for software companies with this shape returns Chowbus and ChowNow — both restaurant technology companies. The name points at the wrong industry for half the world.
- **Romanisation is the deciding flaw.** *chowki / chauki / chowky / chaukee* are all attested spellings. The distribution channel for this project is a **spoken three-minute video**. A name that cannot be spelled from hearing it once is the wrong name for a project whose only channel is audio.

### 4.3 Alternatives

Availability checked 18 September 2026 against the PyPI JSON API and the npm registry. Availability changes; re-check before committing.

| Name | Meaning | PyPI | npm | For it | Against it |
|---|---|---|---|---|---|
| **Naka** | A police checkpoint set up to stop and check everything passing (*nakabandi*). Everyday, secular Indian usage. | free | taken | Four letters. One spelling — hear it, type it. No political register. "Chokepoint" is precisely what a tool boundary is. npm being taken is irrelevant for a Python project. | Meaningless outside India. Also a common Japanese place name and surname (Naka-ku, Naka River), so it is generic in search and needs a qualifier in every mention. |
| **Maryada** | The limit that must not be exceeded; propriety, bounds. | free | free | Semantically the most exact word available — the product *is* a limit. Free everywhere. One dominant romanisation. | Four syllables and non-obvious stress for a non-Indian speaker. Carries moral and religious connotations (*Maryada Purushottam*), and the same word appears in gendered "stay within your limits" discourse. Avoid for the same reason as the next row. |
| **Sanchay** | Accumulation. | free | free | Describes the mechanism better than any checkpoint word: the risk is accumulation, not passage. | Spelling is not recoverable from the sound (*sanchay / sanchai / sanchey*). India Post's Sanchay savings schemes occupy the term domestically. A common given name. |
| **Tallymark** | The counting notches that fill toward a limit. | free | free | Legible in India and internationally with no translation. Matches the hero UI object — a meter filling. Spellable from hearing it. | A compound, so slightly clumsy. The "Tally" prefix sits in the shadow of Tally Solutions, which in India means accounting software to everyone. |
| **Lakshman Rekha** *(rejected — recorded so nobody proposes it later)* | The line that must not be crossed. | `rekha` taken | `rekha` taken | The single most recognised Indian metaphor for an inviolable boundary. | Two hard blocks. **Laxman Rekhaa is a registered trademark of Midas for household insecticide chalk** — a mass-market Indian product everyone knows. And the idiom is heavily entangled with public discourse about female chastity. Both disqualify it. |
| **RedLine** *(rejected — recorded for the same reason)* | Crossing a red line. | taken | taken | Reads well in English. | **RedLine Stealer is one of the best-known information-stealing malware families**, catalogued by MITRE ATT&CK as S1240 and the subject of a CERT-In advisory. Naming a data-protection product after an infostealer is disqualifying. Checking the security namespace is a step most naming exercises skip. |

### 4.4 What was picked

**Two decisions, in priority order. Both are now made.**

**First, and far more important: the thing worth owning is the phrase, not the product name.** Spend the branding on **"disclosure budget."** It is short, it is spellable, it describes the mechanism, it survives translation, and it is what someone will repeat to a colleague. If in a year people are arguing about whether disclosure budgets are a good idea, the project has won regardless of what the binary is called. Every piece of copy in §5 leads with the phrase and treats the product name as a label.

**Second: renamed to `Naka` — done.** It clears the PyPI collision, is spellable from hearing it once, drops the political register, and keeps the checkpoint image the team already likes. It cost about twenty minutes — a find-and-replace, a README and a repo name — and the collision it removes is specific and lands in the judging channel. The one cost accepted: *Naka* is also a common Japanese place name and surname, so it is generic in search and needs the qualifier in every mention.

**Still never write the bare word.** Always write **"Naka — disclosure budgets for agent tool calls"**, in the video title, the repo description, the first line of the README and the first frame of the video. That disambiguates in search and puts the phrase in front of the name, which is where it belongs anyway. If anything about the rename threatens the deploy on Sunday, the deploy wins — a live URL under any name beats a dead one under the right name.

---

## 5. Messaging hierarchy

### 5.1 Headline

> **Your AI agent learns one field at a time. Nothing is counting the total.**

### 5.2 Subhead

> Every guardrail we surveyed decides one tool call at a time. This one gives the session a budget for what it may learn about any one person, enforces it in Cedar, and keeps a log that shows what was withheld.

### 5.3 Three proof points

1. **The phone number that was allowed on the second call is denied on the fourth.** The decision is made against the running total, not the payload, and the field is removed from context going forward. Visible in the demo, in one shot. (Never narrate it as the model un-learning something — PRD §12's narration rule.)
2. **Both questions are Cedar, one audit row.** *May this call happen* and *may this principal learn this field about this subject* — same policy language, same principal, one record. Edit one line of policy on the control plane and two separate agents change behaviour on their next call.
3. **The Indic-script gap, and the model chosen to match.** Detecting Aadhaar is not the claim — Presidio has done it with a Verhoeff checksum for years, free. The claim is that Comprehend is English/Spanish only and Textract OCRs Latin script only, so the regional-script half of every Indian identity document is invisible to the whole stack; our third tier reads it off the image. (Bedrock Guardrails carries no Indian entity types at all, which is the AWS-audience comparison worth showing.) The model is Nova on `apac.*` because Claude on Bedrock in Mumbai is `global.*` only, and AWS states that profile can route requests outside the source Region — so the claim is **"stays in APAC"**, never "stays in India".

### 5.4 The sentence that gets repeated everywhere

> **Each call was allowed. Together they identify her. Nobody was counting.**

Use it in the video cold open, the README's first line, the submission's first line, the blog post's opening, and slide 2 of the deck. Three short sentences, one idea, no jargon, and a listener can relay it to someone else after hearing it once — which is the only real test of a message.

### 5.5 Words we do not use

"Revolutionary", "first-ever", "unprecedented", "game-changing", "bulletproof", "military-grade", "AI-powered" (it *is* AI; saying so adds nothing), "differential privacy" (PRD §6.3), "zero-trust" unless describing an actual default-deny configuration.

---

## 6. The economic case

### 6.1 The honest answer

**This does not save money. It is insurance against a low-probability, high-cost event, and we cannot quote the probability — nobody can.**

The agent still runs. It still makes the same calls and costs the same to run. This adds latency and a few dollars of AWS. There is no efficiency story and any ROI model built here would be a spreadsheet dressed as evidence.

Anyone who offers you a breach-probability number for *aggregation leaks by autonomous agents over Indian personal data* is extrapolating from a different phenomenon. The category is roughly a year old. There is no actuarial base.

### 6.2 What can actually be quantified

| Quantity | Value | Source |
|---|---|---|
| Cost to run, demo scale (500 invocations × 3 tool calls, 50 document pages) | **~$2.25/month** on Nova **Lite** for the agent loop (Pro only for the Indic image call), ~$9.20 if Pro is used throughout; Textract 50 pages ≈ $0.08 | PRD §7 |
| Same shape on Claude | ~$30–35/month **and** it breaks the residency premise | estimate, not in the PRD |
| Cost trap to avoid | anything in a VPC pulls a NAT Gateway — more than the workload | `02-aws-services-and-access.md` §A.5 #6 (the ~$33 figure is unverified for `ap-south-1`) |
| Aadhaar Act s.33A civil penalty, **in force today** | up to **₹1 crore per contravention**; s.29(4) bars public display of Aadhaar numbers, UIDAI permits display of only the last four digits | PRD §13 |
| DPDP Rule 6 log retention, **from ~May 2027** | logs and monitoring retained for **one year**; safeguards expressly include "encryption, obfuscation or masking or the use of virtual tokens" | PRD §13 |

The ₹1 crore figure is the only penalty number that may be used, and only with "up to", "per contravention", and "under the Aadhaar Act" attached. **Do not** use ₹250 crore — that is a discretionary ceiling for security-safeguard failures under DPDP and is not yet live (PRD §13).

### 6.3 The three things a buyer is actually paying for

1. **An answer to a question they currently cannot answer.** PRD §3: today the user cannot state "an analyst may query customers, but may never accumulate enough about any one customer to identify them" and hold a log that proves it held. Being unable to answer a written question from a customer's security team is a present, dated cost — a blocked deal — not a hypothetical one.
2. **Evidence, not just prevention.** DPDP Rule 6 requires logs and monitoring retained for one year (PRD §13). The audit record in PRD §10 is that artifact: it records what was withheld without becoming the leak it prevents — no raw values, no placeholder map. A control with no log produces nothing to show; the log is the deliverable.
3. **Not having to discover the ten things we discovered.** PRD §2 is the product of two research passes that corrected the stack: sync Textract is one page for PDF; Textract OCR is Latin-script only, so it cannot read the Devanagari half of an Aadhaar card; Cedar has no set cardinality operator so counts must be computed in Python; Comprehend bills a 300-character minimum per request, so naive per-field scanning costs roughly ten times what you expect; AgentCore Runtime has no public URL; API Gateway HTTP API caps at 30 seconds. Each of those is a day someone else does not lose.

### 6.4 The sentence to say when asked for ROI

> We are not going to model your breach probability, because the honest number is that nobody knows it yet for this failure mode. What we can tell you is what the control costs to run — single-digit dollars a month at this scale — and that it produces the log your customer's security questionnaire is asking for.

That answer is more persuasive to a technical buyer than a fabricated payback period, and it is the only one that survives follow-up.

---

## 7. Where the first ten users come from

Concrete, named, in order. None of these is "launch on Product Hunt."

1. **The hackathon itself.** Judges, the WeMakeDevs Discord and the other entrants are the first audience and they are already assembled. The submission *is* the first distribution event.
2. **The blog post, not the product.** The highest-value asset here is not the binary — it is the finding that **Claude on Bedrock in Mumbai is available only through the `global.*` profile, which AWS states can route outside the source Region, while Nova's `apac.*` profile stays in APAC.** Any team in India with a data-residency requirement is going to search for exactly that, and there is very little written about it. Publish it as a standalone post that answers the question and mentions the project at the end. Do the same for the AgentCore Policy / Guardrails tool-field gap. PRD §12 already notes both are useful independent of this project.
3. **The Strands Agents community.** Using `context_enricher` to feed computed state into Cedar, and `cedarpy.is_authorized_batch` for per-entity decisions, is a genuine pattern contribution — including the open question in PRD §15.1 about whether `ContextEnricher` returns `None` or a dict, which the docs and the examples disagree about. Filing that as an issue with a runtime answer is a contribution, not marketing.
4. **The Cedar community.** "Cedar has no set cardinality operator, so counts must be computed outside policy and injected as longs" is a real constraint that other people will hit. Post the workaround where Cedar users are.
5. **OWASP Top 10 for Agentic Applications 2026, ASI02 Tool Misuse and Exploitation.** Cumulative disclosure is a concrete instance of ASI02 with a working reference implementation — and the stronger line is that the 2026 list has no entry for it yet. Contributing an example to a community threat catalogue reaches exactly the people who would deploy this.
6. **AWS User Group Bengaluru / AWS Community Day.** A twenty-minute talk on "what we learned deploying a Strands agent to Lambda in ap-south-1" reaches a room of people with the problem, and the deployment content in PRD §7 stands on its own.
7. **Five companies the team can already name.** Every team in this position knows five firms in Bangalore, Pune or Hyderabad building an agent over customer data. Direct approach, no product pitch: "we built this, can we watch you try to break it for an hour." Those hours produce the policy vocabulary you cannot guess.
8. **The services firm through a personal connection.** Per §1.3, the likeliest first buyer. Do not cold-approach; go through someone who already trusts the team. Ask what their client's contract requires them to evidence.
9. **Show HN / r/LocalLLaMA / r/devops.** Title it after the mechanism — "Cumulative disclosure budgets for AI agent tool calls" — not the product name. Lead with the prior-art section. An honest competitive section is the single most upvoted thing a first-time project can include.
10. **DPDP practitioners.** Law firms and consultancies are publishing DPDP readiness material for the ~May 2027 commencement and have client lists with no technical product to point at. One conversation there is worth ten cold emails. Be careful: the framing must stay inside PRD §13 — this is data minimisation and defence in depth, not a transfer block, and DPDP is not in force today.

**The one that matters most is #2.** A research finding that answers a question people are already searching for outperforms a product launch, and it keeps working after the hackathon ends.

---

## 8. Market context, sized honestly

### 8.1 What I will not do

**I am not going to give you a TAM number.** Every "AI security market will reach $X billion by 2030" figure circulating is traceable to a commissioned market-research report whose methodology cannot be inspected, and quoting one in front of an AWS audience invites a question that cannot be answered. PRD §14 already treats "the judge knows more than us" as the live risk. The same applies here.

I could not find a defensible figure for any of these, and the honest response is to say so:

- The size of the market for agent-level data controls. The category is roughly a year old; nobody has measured it.
- The number of Indian organisations deploying agents over regulated personal data. Unmeasured.
- The frequency or cost of aggregation-style disclosure leaks by AI agents. No incident base exists. This failure mode is invisible by construction (PRD §3), which means even if it is happening it is not being counted.

### 8.2 What is defensible

**The developer base is measured, by a primary source with a stated method.** GitHub's Octoverse 2025 (published 28 October 2025, updated 28 February 2026) reports: over 180 million developers on GitHub; **21.9 million developers in India**; **more than 5 million added in India during 2025** (5.2M, about 14% of GitHub's +36M new developers that year); India now holding the largest public and open-source contributor base in the world; and a projection of **57.5 million developers in India by 2030**, more than one in three of projected worldwide signups. That establishes the size of the *builder* population an open-source developer tool can reach in India. It says nothing about willingness to pay, and should not be used as if it did.

**The regulatory clock is dated and public.** India's DPDP Act 2023 and the DPDP Rules 2025 (notified November 2025) set a phased timeline with substantive obligations for organisations commencing around **May 2027** (PRD §13). That date is the single most useful market fact in this document, because it is when a compliance budget line appears that does not exist today. It also means the honest statement about timing is: *the buyer for this is not fully formed yet.* Meanwhile RBI's 2018 payment-data localisation directive, the CERT-In 2022 directions, and Aadhaar Act s.29(4) are already in force, which is where the present-tense demand sits.

**Direction of travel, labelled as prediction.** Gartner's own newsroom, cited by headline only — the bodies are behind a block and I did not read them, so only the titles are quoted:

- *"Gartner Predicts that Guardian Agents will Capture 10-15% of the Agentic AI Market by 2030"* (11 June 2025)
- *"Gartner Predicts 25% of All Enterprise GenAI Applications Will Experience At Least Five Minor Security Incidents Per Year By 2028"* (9 April 2026)
- *"Gartner Says Applying Uniform Governance Across AI Agents Will Lead to Enterprise AI Agent Failure"* (26 May 2026)

These are analyst predictions about a future, not measurements of a present. Cite them as such or not at all.

**And the counter-evidence, which belongs in the same paragraph:** *"Gartner Predicts Over 40% of Agentic AI Projects Will Be Canceled by End of 2027"* (25 June 2025). If a large share of agentic projects are cancelled, a large share of the addressable base for agent-layer controls disappears with them. Including this is not modesty; it is the difference between a market section a skeptic trusts and one they stop reading.

### 8.3 The one-paragraph market statement, safe to reuse verbatim

> India has the largest and fastest-growing developer population on GitHub — 21.9 million developers, more than five million added in 2025, projected to reach 57.5 million by 2030 (GitHub Octoverse 2025). India's DPDP Act and its 2025 Rules put substantive obligations on organisations from around May 2027, which is when a budget line for data controls appears where none exists today; RBI's 2018 localisation directive, the CERT-In 2022 directions and the Aadhaar Act's restrictions on displaying Aadhaar numbers already bind. We are not going to size the market for agent-layer data controls, because the category is about a year old and every available figure comes from a commissioned report we cannot check. What we can say is that the builders are here in measured numbers, the obligation has a date on it, and the specific failure this addresses — an agent accumulating enough about one person across many individually-approved calls — is not currently being counted by anyone, which is also why there is no incident data to quote.

---

## 9. The do-not-claim list, restated

Copied forward from PRD §4 and §13 so that nobody writing copy from this file has to go and look. **Never write:**

- "First of its kind", "first-ever", "nobody governs agent traffic", "existing DLP only watches browsers." *(PRD §4)*
- That no existing guardrail carries state across calls. False six ways — Dogwood, CAMP, OCELOT, Noisegate, Purview, Pipelock. The surviving claim is **subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision**. *(PRD §2.3)*
- That Indian identifier detection is a differentiator. Presidio ships `IN_AADHAAR` with checksum validation, free. The claim is the **Indic-script** gap. *(PRD §4 claim 3)*
- That anything "stays in India." The APAC geo profile's destination regions are not published — say **"stays in APAC"**. *(PRD §4)*
- "OWASP T2 Tool Misuse" against the 2026 Agentic list. It is **ASI02**. *(PRD §2.3)*
- That DPDP is in force today. Obligations commence around **May 2027**. *(PRD §13)*
- That DPDP restricts sending data to US LLM providers. s.16 uses a negative list and no country has been notified. *(PRD §13)*
- That DPDP mandates masking Aadhaar. Rule 6 lists masking as **one option** among safeguards. *(PRD §13)*
- Any right to explanation for automated decisions. No Article 22 equivalent exists in DPDP. *(PRD §13)*
- That ₹250 crore penalties apply. It is a discretionary ceiling, not yet live. *(PRD §13)*
- That Aadhaar Data Vault tokenisation is required of the reader. It binds AUA/KUA ecosystem entities only. *(PRD §13)*
- Any "PAN privacy law". None exists. *(PRD §13)*
- "Differential privacy", or any vocabulary borrowed from it. This is a quasi-identifier accumulator. *(PRD §6.3)*
- That `cedarpy` is an AWS library. It is a community binding, and its own page states it is not officially supported by AWS or the Cedar Policy team. *(PRD §2.2)*
- General-purpose entity-to-subject attribution. The demo uses seeded structured fixtures, which makes attribution trivial; the general problem is hard and we do not claim to have solved it. *(PRD §15.5)*
- Precise dates for DPDP milestones. Say "November 2025" and "May 2027" — sources disagree on exact days. *(PRD §13)*

Fair to cite as context: MeitY's **India AI Governance Guidelines** (5 November 2025), explicitly voluntary and non-binding. *(PRD §13)*

---

## Sources

**Naming checks** (all verified 18 September 2026)
- PyPI `chowki` 0.2.0 — https://pypi.org/pypi/chowki/json · repository https://github.com/Git-Uzair/chowki
- npm registry queried at `https://registry.npmjs.org/<name>`; PyPI at `https://pypi.org/pypi/<name>/json`; GitHub namespaces at `https://api.github.com/users/<name>`
- Chowki / chauki meanings — https://en.wiktionary.org/wiki/chowki · https://en.wikipedia.org/wiki/Chowky
- "Main Bhi Chowkidar" — https://en.wikipedia.org/wiki/Main_Bhi_Chowkidar · https://en.wikipedia.org/wiki/Chowkidar_Chor_Hai
- Lakshmana rekha — https://en.wikipedia.org/wiki/Lakshmana_rekha · Laxman Rekhaa insecticide chalk, trademark of Midas — https://www.bigbasket.com/pd/30005875/laxman-rekhaa-chalk-for-cockroaches-1-pc-carton/
- RedLine Stealer, MITRE ATT&CK S1240 — https://attack.mitre.org/software/S1240/ · CERT-In advisory — https://www.csk.gov.in/alerts/RedLine_infostealer_malware.html

**Market context**
- GitHub Octoverse 2025 (28 October 2025, updated 28 February 2026) — https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
- Gartner newsroom, headline claims only (page bodies returned HTTP 403 and were not read):
  - https://www.gartner.com/en/newsroom/press-releases/2025-06-11-gartner-predicts-that-guardian-agents-will-capture-10-15-percent-of-the-agentic-ai-market-by-2030
  - https://www.gartner.com/en/newsroom/press-releases/2026-04-09-gartner-predicts-25-percent-of-all-enterprise-gen-ai-applications-will-experience-at-least-five-minor-security-incidents-per-year-by-2028
  - https://www.gartner.com/en/newsroom/press-releases/2026-05-26-gartner-says-applying-uniform-governance-across-ai-agents-will-lead-to-enterprise-ai-agent-failure
  - https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027

**Everything else** — `hackathon-agent-egress-guardrail-prd-2026-09-18.md`, whose own Sources section carries the AWS, Strands, Cedar, prior-art and legal citations. Prior-art facts in §3 are from PRD §2.3; cost figures in §6 from PRD §7; legal framing in §6 and §9 from PRD §13.
