# Naka — planning package

**Hackathon:** WeMakeDevs × AWS "First Commit", Bharat Builds Tour
**Deadline:** Sunday 20 September 2026, 20:00 IST
**Track:** Ship It (₹2,00,000 + $3,000 AWS credits) — requires a deployed, publicly reachable URL. Same submission is judged for Best UI (₹1,00,000 + $1,000).
**Status:** planning complete, nothing built.

---

## What this is

A guardrail on an AI agent's tool boundary. Cedar authorizes each tool call; when the call returns, the payload is normalized to markdown, scanned for personal data, and each detected field is authorized *separately* — taking into account a running ledger of what this session has already learned about that person. Denied fields become numbered placeholders, rehydrated later only if the destination call is itself authorized.

**The one-line claim, and it is deliberately narrow:**

> Subject-scoped semantic accumulation, fed back into the authorizer as a redaction decision.

Say "cumulative state" instead and you lose the room — see document 01 for why.

---

## Read in this order

**If you are building:** the PRD, then 08 (technical design), then 10 (fixtures), then 09 (diagrams).
**If you are recording the video:** PRD §12, then 06 (pitch deck), then 03 (UI spec), then 10.
**If you are about to be asked hard questions:** 07, then 01.

| # | Document | What it is |
|---|---|---|
| — | `hackathon-agent-egress-guardrail-prd-2026-09-18.md` | **The master PRD. Source of truth.** Concept, verified SDK and AWS facts, architecture, scope, build order, demo beats, legal framing. Every other document reconciles to this one. |
| 01 | `chowki-hackathon/01-competitive-landscape.md` | The adversarial prior-art review. Supersedes the PRD's §2.3. Read before writing any copy. |
| 02 | `chowki-hackathon/02-aws-services-and-access.md` | What you can actually use, what it costs, quotas, IAM, and the account-plan decision. |
| 03 | `chowki-hackathon/03-ui-ux-design-spec.md` | Best UI is a separate prize. Hero component, visual system, motion, video framing. |
| 04 | `chowki-hackathon/04-innovation-pass.md` | Cheap-wow features ranked by impact ÷ hours, better framings considered, what to kill. |
| 05 | `chowki-hackathon/05-gtm-and-positioning.md` | ICP, value prop, naming analysis, messaging, honest economics. |
| 06 | `chowki-hackathon/06-pitch-deck.md` | The three-minute video script timed to the second, plus a deck for afterwards. |
| 07 | `chowki-hackathon/07-judge-qa-prep.md` | ~70 anticipated questions with answers, including the two where the honest answer is weakest. |
| 08 | `chowki-hackathon/08-technical-design.md` | Module interfaces, request flows, data model, failure modes, concurrency, threat model, test plan. |
| 09 | `chowki-hackathon/09-diagrams.md` | Mermaid diagrams for architecture, flows, state, data model, threat boundaries, deploy. |
| 10 | `chowki-hackathon/10-demo-fixtures.md` | The seeded data and the exact call sequence that produces each demo beat. |
| 11 | `chowki-hackathon/11-written-submission.md` | Finished prose for the submission form. |
| 12 | `chowki-hackathon/12-blog-post.md` | For the top-five-blogger prize. The research is the asset. |

*(The `chowki-hackathon/` folder name predates the rename to Naka. Cosmetic; leave it until after submission.)*

---

## Decisions locked

| | |
|---|---|
| **Name** | **Naka.** "Chowki" was dropped — a PyPI package of that name exists in the same category, and it has four romanisations, which is disqualifying when the only channel is a spoken video. |
| Region | `ap-south-1` (Mumbai) |
| Compute | Lambda, arm64, Python 3.12, **Function URL** — not API Gateway (30s cap), not AgentCore Runtime (no public URL) |
| Model | `apac.amazon.nova-lite-v1:0` for the agent loop, Pro only for the image call. Claude in Mumbai is `global.*` only and routes outside the region |
| Detection | Local Verhoeff/format checksum → Comprehend → multimodal Indic tier. Tiers **union**, never subtract |
| Ledger | DynamoDB is authoritative (atomic `ADD` on a String Set); `S3SessionManager` is a cache and is **not** thread-safe |
| Policy | `cedarpy` embedded, not Amazon Verified Permissions |
| Deploy | Plain zip + AWS CLI, not CDK |
| Budget grounding | Sweeney / Golle on three quasi-identifiers. **Not** HIPAA Safe Harbor, which says remove all 18 |

---

## Before you write a line of code

1. **Create the AWS account on the Paid plan.** A Free-plan account cannot redeem promotional credits, so the $3,000 prize would be unusable — and it auto-closes at six months, taking the demo URL with it. Same $100 + $100 either way. (02 §Job 1)
2. **Ask the organisers for credits.** The rules permit it. Nothing else arrives inside 48 hours.
3. **Verify `context_enricher` returns a dict into `context.session`.** The API reference renders it as returning `None` while every example returns a dict. The entire design rests on this. Five minutes.
4. **Test `LanguageCode="hi"` on Comprehend.** The API enum lists it; the developer guide says English and Spanish only. If it works, a generative model leaves the enforcement path entirely.
5. **Deploy a hello-world agent behind a Function URL before any logic exists.** Include **both** `add-permission` calls — `lambda:InvokeFunctionUrl` *and* `lambda:InvokeFunction`. The console adds them; the CLI does not; you get a 403 that reads like a code bug. This is the one failure that cannot be recovered on Sunday afternoon.

---

## Known holes — concede these, do not defend them

- **Entity-to-subject attribution is assumed, not solved.** It is the ledger's key. Attribute only where the tool schema declares a subject.
- **The budget is over *detected* disclosure.** A missed detection is never counted and the ceiling never binds. There is no eval set, and Comprehend's Service Card publishes no figure for Aadhaar or PAN.
- **`AuthType=NONE` means the principal is asserted, not authenticated** — and the whole policy model is principal-based.
- **A fresh session, or a fresh subject id, resets the budget.** Canonicalisation kills the trivial variants; a `session_ceiling` backstops the rest.
- **Audit rows are unsigned.** "Audit trail" is fair. "Tamper-proof evidence" is not.

---

## Narration rule for the video

Never say a field was retracted from what the model already read — it cannot be, and a technical judge ends the conversation in one sentence.

- ✅ "Allowed at call two. Denied now."
- ✅ "Removed from context going forward."
- ❌ "The model no longer knows it."

---

## The honest position on novelty

The concept is published (CAMP, OCELOT — arXiv, 2026). AWS shipped the policy substrate six weeks ago (Dogwood, inside AgentCore Policy, GA in Mumbai). Sixteen commercial vendors carry cross-call state, but it is attack-sequence state, not disclosure accumulation. One zero-star open-source project has built most of the mechanism.

**Nobody has connected them.** That is the contribution. Volunteer Dogwood before a judge raises it, and position the ledger as a Dogwood *information provider* — composable, not competing. Document 01 has the full analysis and a list of sentences that are falsifiable in one link.
