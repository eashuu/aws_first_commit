# 15 — The shooting script

**For:** whoever drives the screen and reads the words. **Ships:** Sunday 20 September 2026, 20:00 IST.
**Supersedes** the narration in `06-pitch-deck.md` §A.2 and the beat order in `13-depth-pass.md` §3. The production rules in `06` §A.0 still stand, and so does `06` §A.4, the list of sentences that must not be said.

Every beat below is **Do** (what to click, in order) and **Say** (read it aloud). Nothing here is aspirational: each beat was run against the shipped code on the 20th, and the numbers in the narration are the numbers that come back. The verified output of all four scenarios is in the appendix — check the narration against it before you record, and again if anyone touches `agent.cedar`.

**Three things changed from the earlier plan, because the shipped build does not do what `06` assumed.** Details in the appendix.

1. There is no live agent loop — Bedrock is gated — so every beat runs off the four one-click scenarios, which drive the real guard.
2. There is no successful-rehydration beat. No scenario sends to an authorized destination, so beat 6 proves the Q3 boundary from the *denial* plus the policy rule itself.
3. The budget is not editable from the console. It lives in the JSON bundle, not the Cedar text, so beat 7 makes a different one-line edit — one that is editable, and tested.

---

## Set up before you record

1. Open the console: `<control-plane-url>/console.html`. Leave it on **Overview**.
2. Check the **Agent Function URL** field on *Agent Egress* is filled. It comes from `localStorage` or the health probe; if it is blank, paste the agent Function URL once and tab out.
3. Set **User (principal)** to `analyst@example.com`.
4. Put the `X-Naka-Key` into the field on the **Policy** view now, so you are not typing a secret on camera at 2:10.
5. Second tab: `naka/fixtures/customers.json` open at `cust_8814`, or the same block in your editor. That is beat 2.
6. Third tab: a blank tab for the closing URL load.
7. Browser at 100% zoom, window at 1920×1080, bookmarks bar hidden, notifications off.
8. Run each scenario once as a rehearsal, then reload the page, so the feed is warm but the take is clean.

Record the narration separately and cut the screen to it. Burn in the captions — judges watch on phones, muted.

---

## The clock

Eight beats, 362 words of narration — 2:42 of speech at 134 words a minute. The clock runs to 2:53, and the spare eleven seconds are the silence at the open, the hold on beat 5, and the page load at the end. Three minutes is a ceiling: a video that runs 3:04 can be thrown out.

| # | In | Out | Words | Beat | Where |
|---|---|---|---|---|---|
| 1 | 0:00 | 0:15 | 29 | The record, and three green rows | fixture + Overview |
| 2 | 0:15 | 0:31 | 35 | What the tool hands back | `customers.json` |
| 3 | 0:31 | 0:52 | 47 | Guard on — one of three | *Benign lookup* |
| 4 | 0:52 | 1:11 | 41 | What it could not scan, it says so | Detector coverage |
| 5 | 1:11 | 1:44 | 70 | The fourth call is denied | *Budget bites* |
| 6 | 1:44 | 2:08 | 53 | A placeholder is not a bearer token | *Exfiltration attempt* + Policy |
| 7 | 2:08 | 2:27 | 39 | One line of policy | *Compliance role* + Policy |
| 8 | 2:27 | 2:53 | 48 | Prior art, then the live URL | browser |

---

## Beat 1 · 0:00–0:15 — The record, and three green rows

**Do**

1. Full-frame still of the `cust_8814` KYC block — name, phone, Aadhaar, PAN. Hold **two seconds, silent**.
2. Hard cut to the console on **Overview**, recent-calls table showing green rows.

**Caption:** `Each call was allowed. Together they identify him.`

**Say**

> A customer record in a support queue. An agent is about to read it.
>
> Three tool calls, each one approved. Together they identify him. Nothing was counting the total.

**Watch for.** Two full seconds on the record before the first word. It is the only production trick in this video. Read the second paragraph flat — emphasis turns it into an advert.

**Pronoun.** `cust_8814` is Anil Kumar Rao, so it is *him*, here and at 2:50. The planning docs say *her* throughout, from the KYC-sheet fixture, which is a different customer (Meera Nair). Pick one and keep it: the close only lands because it repeats the open word for word.

---

## Beat 2 · 0:15–0:31 — What the tool hands back

**Do**

1. Switch to the `customers.json` tab, at the `cust_8814` → `kyc` block.
2. Let the four lines sit on screen: `aadhaar`, `name`, `phone`, `pan`.

**Caption:** `One call. Four identifying fields. Nothing in the path.`

**Say**

> This is what one of those tools hands back. Aadhaar, name, phone, PAN — four identifying fields about one person, in a single call. With nothing in the path, all four go straight to the model.

**Watch for.** Say *nothing in the path*, not "without our product". The point is the absence of any control, not the absence of ours.

---

## Beat 3 · 0:31–0:52 — Guard on, one of three

**Do**

1. Sidebar → **Agent Egress**.
2. Click the **Benign lookup** scenario button.
3. When the feed row lands, click it. The **Decision detail** pane fills on the right.
4. Let the **Disclosure meter** animate to 1 of 3 for `cust_8814`.

**Caption:** `Q1: may this call happen? · Q2: may this principal learn this field about this person?`

**Say**

> Same call, through the guard. Cedar authorizes the call. The result is scanned, and every field found is authorized again — one question per field, per person. The Aadhaar is masked outright: an analyst never sees one, whatever the budget says. The PAN is released. One of three.

**Watch for.** Two different denial reasons are on screen in this one row, and the difference matters: the Aadhaar is masked by a **statutory** rule that ignores the ledger entirely, while everything else is governed by the budget. If the meter does not animate, reload and re-shoot — it is the hero object.

---

## Beat 4 · 0:52–1:11 — What it could not scan, it says so

**Do**

1. Sidebar → **Detector coverage**. The tier table loads live from `GET /diag`.
2. Hold on Tier 1 in green, Comprehend and the Indic tier in grey, marked *not run*.
3. Cut back to the feed row and show `tiers_unavailable` on it.

**Caption:** `Model tiers gated on this account · a narrower scan is labelled as one`

**Say**

> The name and phone need Comprehend, and the model tiers are gated on this new account — so this ran on local checksums alone. Every row says which tiers did not run. It never reports a narrow scan as a clean one.

**Watch for.** This beat is here, and not at the end, because the viewer has just watched the name and phone survive beat 3 and is already asking why. Answer it while they are asking. Say it evenly, with no apology in the voice: a provisioning state is not a defect, and the page works it out live rather than asserting it.

---

## Beat 5 · 1:11–1:44 — The fourth call is denied

**Do**

1. Sidebar → **Agent Egress**.
2. Click **Budget bites**. It mints a fresh session, so the meter starts empty.
3. **Do not cut for the whole run.** Four rows land: PAN released, GSTIN released, IFSC released, voter ID masked. The meter steps 1 → 2 → 3, then changes state.
4. Click the fourth row. The detail pane names the rule that denied it.
5. Hold the frame two seconds.

**Caption:** `Three fields spent. The fourth is refused.`

**Say**

> A fresh session. The PAN again — one of three. A GST number — two. An IFSC code — three. Each one fine on its own; that is the point. Then the fourth call returns a voter ID. A call earlier it would have been released. The budget is spent, so it is denied — because the decision is not about this payload. It is about what this analyst already knows about this person.

**Watch for.** This is the beat that wins it. One continuous take, no edit that could be read as a splice, and land on "this person" before cutting.

**"A call earlier it would have been released" is a counterfactual, and it is true** — the voter ID is denied by the ceiling rule, not by anything about voter IDs. Do not upgrade it into a claim that a field already released was taken back. Nothing is retracted from what the model has read; it cannot be, and a technical judge ends the conversation in one sentence if you say otherwise. *Denied now.* *Out of context going forward.* Never "the model no longer knows it".

---

## Beat 6 · 1:44–2:08 — A placeholder is not a bearer token

**Do**

1. Click **Exfiltration attempt**.
2. Two rows land. The second is `send_summary` to `pastebin.example.com`, outcome **`denied_placeholder`** — the placeholder leaves as a placeholder.
3. Sidebar → **Policy**. Scroll to `q3_rehydrate_aadhaar_kyc_vault_only` and let the `Destination::"kyc-vault.internal"` line sit on screen.

**Caption:** `Same token. One destination. Pastebin is not it.`

**Say**

> One thing this has to get right. If a placeholder can be cashed anywhere, the guardrail is an exfiltration channel — an injected agent just asks for the value back. So restoring it is its own authorization question, against the destination. Here it is in the policy: one destination, named. Pastebin is not it.

**Watch for.** This is the answer to "the tech looks shallow", and it is the cheapest depth signal in the repo because it is already built and already tested. It shows a team that found a way its own design could be worse than shipping nothing, and closed it. **If you can only shoot one beat besides 5, shoot this one.**

Cedar is default-deny here, so showing the single permit *is* showing the boundary — every destination not on that line is refused, with no forbid rule needed. Say "one destination, named", not "we block pastebin".

---

## Beat 7 · 2:08–2:27 — One line of policy

**Do**

1. Set **Role** to `compliance`, click **Compliance role**. The row lands with **nothing masked** — the Aadhaar is released, and the ledger shows both fields.
2. Sidebar → **Policy**. Put the cursor at the end of the Cedar text and paste:

   ```cedar
   @id("q2_forbid_aadhaar_compliance")
   forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)
   when { context.session has role && context.session.role == "compliance" };
   ```

3. Click **Save**. The green line reads `saved — version …` and the ETag changes.
4. Sidebar → **Agent Egress**, click **Compliance role** again. Same call, and the Aadhaar is masked this time.

**Caption:** `Edit one line. No redeploy.`

**Say**

> Same call, same customer, different principal. Compliance is exempt from the budget, so the Aadhaar comes back. Now watch the policy. One line — compliance may not see one either. Save, run it again, and it is masked. No redeploy.

**Watch for.** Rehearse this one; it is the beat most likely to misbehave on camera. Have the key already in the field. If the save fails, read the error before re-shooting: `POLICY_FLOOR_VIOLATION` means you deleted something you should not have, `ETAG_MISMATCH` means reload first. This exact edit was tested end to end — it parses, it passes the policy floor, and it flips the outcome. **Put the original text back afterwards.**

---

## Beat 8 · 2:27–2:53 — Prior art, then the live URL

**Do**

1. Live browser, four tabs or four names on screen with the dates visible: AgentCore Policy, Dogwood, CAMP, OCELOT.
2. Cut to the feed, scrolling, with `entities_found`, `entities_masked`, `ledger_before`, `ledger_after` visible on the rows.
3. Third tab: type the Function URL into the address bar and let it load. **On camera, actually loading.**
4. End card: project name, one line, repo URL, live URL. Hold two seconds in silence.

**Caption:** `AgentCore Policy · Dogwood · CAMP · OCELOT`

**Say**

> None of this is unclaimed ground. AgentCore Policy went GA in March. Dogwood put session history into Cedar in August. Nobody joined them up — and in production, this ledger belongs inside Dogwood, not against it.
>
> Each call was allowed. Together they identify him. This time, something was counting.

**Watch for.** CAMP and OCELOT are on the caption, not in the voice. They are the closest published work and they are named in the submission, the README and on screen here — but the spoken seconds go to AWS's own two, because a judge at an AWS hackathon is far likelier to know those, and the insurance is in volunteering what they already know before they raise it.

**Why prior art is at 2:27 and not at 0:14.** Same facts, opposite impression. Early, it is a list of people who got there first. Here, after seven beats of working system, it is a team that read the field and knows where its piece fits inside somebody else's architecture.

Showing the URL load is not decoration: the Ship It track is judged on a reachable URL, so that shot is the evidence.

---

## If you run long, cut in this order

1. **Beat 4** (19s). The gating is on the console and in the written submission. You lose the answer to "why is the name still there", so take this cut only if you must.
2. **Beat 7's first half** (9s) — drop the compliance run and make the policy edit against *Benign lookup* instead.
3. **Beat 8's first paragraph** (18s). You lose the prior-art insurance. Last resort.

Never cut beat 5 or beat 6. Everything before beat 5 sets it up, and beat 6 is the one a technical judge remembers.

---

## Before you press record

Say none of these, in any phrasing. They are the ones that come out naturally under narration pressure, which is exactly why they are written down.

- "The model no longer knows it." → *denied now, out of context going forward.*
- "Stays in India." → *stays in APAC.* The destination regions inside an APAC profile are not published, and one `get-inference-profile` call punctures the over-claim.
- "First of its kind." · "Nobody else is doing this." · "Nobody carries state across calls." Several do. The claim is subject-scoped accumulation feeding a redaction decision, and beat 8 makes it properly.
- "AWS's Cedar library." `cedarpy` is a community binding.
- "Tamper-proof." The audit rows are unsigned. *Audit trail* is fair; *evidence* is not.
- "This makes you DPDP compliant." · "You'll be fined ₹250 crore."
- Any accuracy figure for Aadhaar or PAN detection. AWS publishes none.
- "Differential privacy." This is a quasi-identifier accumulator and does not borrow that vocabulary.
- "The name was released." In a gated run the name is never **detected**. Not detected is not the same as allowed, and beat 4 is where that distinction gets made.

---

## Appendix — verified scenario output

Run against the shipped code on 20 September 2026: analyst budget 3, `package-fallback` bundle, Comprehend gated. These are the numbers the narration is built on.

**Benign lookup** — `fetch_customer kyc`

| | |
|---|---|
| found | `IN_AADHAAR` ×1, `IN_PERMANENT_ACCOUNT_NUMBER` ×1 |
| masked | `IN_AADHAAR` (rule `q2_forbid_aadhaar_analyst` — statutory, not budgetary) |
| ledger after | `[IN_PERMANENT_ACCOUNT_NUMBER]` → **1 of 3** |

**Budget bites** — four calls, fresh session

| call | found | outcome | ledger |
|---|---|---|---|
| 1 `kyc` | Aadhaar, PAN | Aadhaar masked, PAN released | 1 of 3 |
| 2 `tax` | GSTIN | released | 2 of 3 |
| 3 `bank` | IFSC | released | 3 of 3 |
| 4 `voter` | voter ID | **masked — budget exhausted** | 3 of 3 |

**Exfiltration attempt** — `fetch_customer kyc`, then `send_summary`

| | |
|---|---|
| call 2 | `send_summary` → `pastebin.example.com`, outcome **`denied_placeholder`** |
| meaning | the placeholder goes out as a placeholder; the value is never restored |

**Compliance role** — `fetch_customer kyc`, role `compliance`

| | |
|---|---|
| masked | none — the exemption applies |
| ledger after | `[IN_AADHAAR, IN_PERMANENT_ACCOUNT_NUMBER]` |

### Three things the earlier script assumed that the build does not do

**1. No live agent loop.** Bedrock, Comprehend and Textract are gated on this account, so the agent route cannot choose tools. The four scenarios drive the real `DisclosureGuard`, `AuditHook` and `Rehydrator` with a fixed call sequence instead — every Cedar decision, ledger write and audit row is real. `POST /demo` also takes no `enforce` field, so the shadow-mode side-by-side in `13-depth-pass.md` §3 cannot be shot; beat 2 shows the raw fixture instead, which makes the same point.

**2. No successful rehydration on screen.** The only `send_summary` in any scenario goes to `pastebin.example.com` and is denied. Nothing sends to `kyc-vault.internal`, so the "task completes, the real value is substituted on the trusted side" beat from `06` §A.2 has nothing to film. Beat 6 proves the same boundary from the other side — the denial, plus the single Q3 permit that names the only destination which could ever redeem the token. The round trip is covered by `test_rehydrator` in `selfcheck.py` if anyone asks.

**3. The budget cannot be edited in the console.** It lives in `budget.default` in the JSON bundle; the policy editor only sends `cedar`, carrying the rest of the bundle over untouched. "Drop the budget to one" is therefore not shootable there. The compliance-Aadhaar forbid in beat 7 is the substitute, and it was tested: it parses, `floor_ok` passes, and the outcome flips from released to masked.

**One gap worth knowing before a judge finds it.** `q2_forbid_phone_after_aadhaar` cannot fire for an analyst. It is keyed on `seen.containsAny(["IN_AADHAAR"])`, but only *released* fields enter the ledger, and an analyst's Aadhaar is always masked — so `IN_AADHAAR` never appears in `seen` for that role. The co-occurrence rule is unreachable on the analyst path. Do not narrate it, do not put it on screen, and if it comes up in questions, say so plainly: it is a live rule that needs the ledger to record detections as well as disclosures, and that is a design change, not a typo.
