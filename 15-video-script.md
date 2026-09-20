# 15 — The video script

**For:** whoever holds the microphone. **Ships:** Sunday 20 September 2026, 20:00 IST.
**Supersedes** the narration in `06-pitch-deck.md` §A.2 and the beat order in `13-depth-pass.md` §3. The production rules in `06` §A.0 still stand, and so does every word of `06` §A.4 — the list of sentences that must not be said.

This is the recording copy. Read the blockquotes aloud; everything else is direction.

It is written for the build that exists on the 20th, which is not the build `06` was written against. Bedrock, Comprehend and Textract are gated on the account, so the demo runs through the scripted driver and the model tiers are off. That is in the script, on camera, at 2:03, in thirty words. Saying it costs less than hiding it.

---

## The clock

Nine beats. 374 words over 2:53, which is 134 words a minute with six seconds of deliberate silence in it — unhurried, and roughly the pace `06` planned for. Three minutes is a ceiling, not a target: a video that runs 3:04 can be thrown out. Record it, time it, and if the read comes back over 2:55, use the cut order below instead of talking faster.

| # | In | Out | Words | Beat | Shot from |
|---|---|---|---|---|---|
| 1 | 0:00 | 0:15 | 29 | The record, and three green rows | fixture + live feed |
| 2 | 0:15 | 0:30 | 34 | What the tool actually returns | raw `fetch_customer` payload |
| 3 | 0:30 | 0:49 | 43 | Guard on — the meter moves | *Benign lookup* |
| 4 | 0:49 | 1:22 | 69 | Allowed a call ago. Denied now. | *Budget bites* |
| 5 | 1:22 | 1:43 | 46 | The task still completes | rehydration pane |
| 6 | 1:43 | 2:03 | 45 | A placeholder is not a bearer token | *Exfiltration attempt* |
| 7 | 2:03 | 2:16 | 30 | What it could not scan, it says so | Detectors view / `GET /diag` |
| 8 | 2:16 | 2:29 | 30 | One line of policy | Policy view |
| 9 | 2:29 | 2:53 | 48 | Prior art, then the live URL | browser |

---

## Beat 1 — 0:00–0:15 · The record, and three green rows

**On screen.** The KYC record for `cust_8814` filling the frame — name, phone, Aadhaar, PAN, large enough to read on a phone. Hold it two seconds with no voice. Hard cut to the live feed: three rows, all green, all `ALLOW`, no other UI.

**Caption.** `Each call was allowed. Together they identify him.`

> A customer record in a support queue. An agent is about to read it.
>
> Three tool calls, each one approved. Together they identify him. Nothing was counting the total.

Two full seconds on the record before the first word. Silence is the cheapest way to make an opening sound deliberate, and it is the only production trick in this video. Read the second paragraph flat — the content carries it, and emphasis will turn it into an advert.

**Pronoun.** The scenarios run on `cust_8814`, Anil Kumar Rao, so the script says *him* here and again at 2:52. The planning documents say *her* throughout, from an earlier fixture. Pick one and hold it: the callback at the end only lands if it is word-for-word the same sentence. If you open on the scanned KYC sheet instead, that page is Meera Nair, the pronoun becomes *her*, and the demo that follows is then about a different customer than the one you opened on. Not worth it. Open on the record.

---

## Beat 2 — 0:15–0:30 · What the tool actually returns

**On screen.** The unmodified tool result. Aadhaar, PAN, name and phone in plaintext, one payload, nothing redacted. A caption counts the fields as they land.

**Caption.** `One call. Four identifying fields. Nothing in the path.`

> Here is what that tool actually returns. Aadhaar, PAN, name, phone — four identifying fields about one person, in one call. With nothing in the path, all four reach the model, and nothing records it.

This beat exists because "it redacts PII" sounds obvious right up to the moment somebody watches the unguarded version hand everything over. Fifteen seconds here buys the rest of the video the benefit of the doubt.

If the operator key is to hand and you would rather shoot this against shadow mode — `enforce: false`, the same `DisclosureGuard`, the same decision path, nothing applied — do that instead, and say out loud that it is one codepath with a flag flipped. A judge will otherwise assume you filmed two different codepaths side by side. `selfcheck.py`'s `test_shadow_mode` is the receipt. Note that `POST /demo` takes no `enforce` field, so that version needs the agent route, which needs Bedrock. On the 20th, shoot the raw payload.

---

## Beat 3 — 0:30–0:49 · Guard on, and the meter moves

**On screen.** *Benign lookup*, one click. The feed fills on the left; the disclosure meter is the hero object on the right and must be large, animated, and legible down to the subject id `cust_8814`. Lower third with the project name appears here and holds four seconds.

**Caption.** `Q1: may this call happen? · Q2: may this principal learn this field about this person?`

> Same call, through the guard. Cedar authorizes the call itself. Then the result is normalized, scanned, and every field found is authorized again — one question per field, per person. The name is released. The meter for this customer moves to one of three.

Do not speed up. The viewer has to feel the meter fill, or beat 4 lands on nothing.

---

## Beat 4 — 0:49–1:22 · Allowed a call ago. Denied now.

**On screen.** *Budget bites*, one click, and then do not cut. GSTIN, IFSC, voter ID. The meter steps to two, to three, then changes state. In the decision pane the fourth field is refused — and in the same frame, above it, a field released a call ago is now a numbered placeholder. **Both have to be visible in one uncut take.** Slow the playback if you must. Never splice.

**Caption.** `Allowed at call two. Denied now.`

> Now a GST number — two of three. A bank code — three of three. Each fine on its own; that is the point. Then the fourth. Voter ID, denied — the budget is spent. And watch the field above it. Allowed a call ago. Denied now, and out of context going forward, because the decision is not about this payload. It is about what this analyst already knows about this person.

Land on "this person" and hold the frame two seconds before cutting. Those two seconds are in the clock.

**The sentence that ends the conversation.** Never say the model no longer knows something. It read it; it cannot un-read it. Say *denied now*, say *out of context going forward*, and stop there. A technical judge who hears "the model no longer knows it" stops evaluating the submission and starts evaluating the claim.

---

## Beat 5 — 1:22–1:43 · The task still completes

**On screen.** The agent calls `send_summary` carrying `[IN_AADHAAR_1]`. Two panes: the outbound message with the real value in it, and the model's context with only the placeholder. That contrast is the entire shot — frame it so both are readable at once.

**Caption.** `The task completes. The model held a placeholder.`

> The agent still needs that number. It sends the summary with the placeholder in it. That destination is authorized, so the real value goes back in on the trusted side, outside the model. Redaction that breaks the task is not a control. It is an outage.

That last sentence is the one to keep if this beat has to lose time. It answers "so your thing just breaks agents" before anyone gets to ask it.

---

## Beat 6 — 1:43–2:03 · A placeholder is not a bearer token

**On screen.** *Exfiltration attempt*, one click. The same placeholder, addressed to `pastebin.example.com`. Cedar denies at Q3 and the placeholder leaves as a placeholder. Hard cut back to the authorized destination from beat 5, resolving correctly. Same token, two destinations, two answers.

**Caption.** `Same token. Different destination. Denied.`

> One thing this has to get right. If a placeholder can be cashed anywhere, the guardrail is an exfiltration channel — an injected agent just asks for the value back. So restoring it is its own authorization question, against the destination. Same token. Different destination. Denied.

This is the beat that answers "the tech looks shallow", and it costs nothing to shoot because it is already built and already tested. It shows a team that found a way its own design could be worse than shipping nothing, and closed it. **If you can only shoot one of beats 2 and 6, shoot this one.**

---

## Beat 7 — 2:03–2:16 · What it could not scan, it says so

**On screen.** The detector tier table, live from `GET /diag`. Tier 1 green. Comprehend and the Indic tier in grey, marked *not run*. Then a feed row with `tiers_unavailable` visible, and the *unscanned* counter on the overview.

**Caption.** `Model tiers gated on this account · a narrower scan is labelled as one`

> The model tiers are gated on this account, so this ran on local checksums alone — and every row says so. It never reports a narrow scan as a clean one.

Thirteen seconds, said evenly, with no apology in the voice. A provisioning state is not a defect, the page works it out live rather than asserting it, and a control plane that admits what it could not see is a more convincing product than one that cannot tell the difference.

---

## Beat 8 — 2:16–2:29 · One line of policy

**On screen.** `agent.cedar` open in the policy view. Change the budget from three to one. Save; the ETag changes. Run a scenario again and the answer is different. Cut to the audit table carrying both.

**Caption.** `Edit one line. No redeploy.`

> The policy lives on a control plane. One line here — budget three to one. Save. Next call, different answer. No redeploy, and both decisions land in the same audit table.

This is the beat most likely to misbehave on camera, because it depends on cache timing. Rehearse it. If it will not cooperate, cut it and give the seconds to beats 4 and 6 rather than shipping a take where nothing visibly changes.

---

## Beat 9 — 2:29–2:53 · Prior art, then the live URL

**On screen.** Four names in a live browser with the dates visible: AgentCore Policy, Dogwood, CAMP, OCELOT. Then the audit table scrolling — `entities_found`, `entities_masked`, `ledger_before`, `ledger_after`. Then the Function URL typed into the address bar and loading, actually loading, on camera. End card: project name, one line, repo URL, live URL.

**Caption.** `AgentCore Policy · Dogwood · CAMP · OCELOT`

> None of this is unclaimed ground. AgentCore Policy went GA in March. Dogwood put session history into Cedar in August. Nobody joined them up — and in production, this ledger belongs inside Dogwood, not against it.
>
> Each call was allowed. Together they identify him. This time, something was counting.

**The two arXiv papers are on the caption, not in the voice.** CAMP and OCELOT are the closest published work and they are named in the submission, the README and on screen here. The spoken seconds go to AgentCore Policy and Dogwood because those are AWS's own, and a judge at an AWS hackathon is far likelier to know them. The insurance is in volunteering what the judge already knows before they raise it.

**Why this sits at 2:29 and not at 0:14.** Same facts, opposite impression. Early, it is a list of people who got there first. Here, after eight beats of working system, it is a team that read the field and knows where its piece fits inside somebody else's architecture.

End on the held frame, not on a word. Showing the URL load is not decoration: the Ship It track is judged on a reachable URL, so that shot is evidence for the prize criterion.

---

## If you run long, cut in this order

1. **Beat 7** (13s). The gating is covered in the written submission and by the console itself.
2. **Beat 8** (13s). Painful, but the policy edit survives as a screenshot in the submission.
3. **Beat 9's first paragraph** (11s). You lose the prior-art insurance, so take this only if the alternative is 3:01.

Never cut beat 4 or beat 6. Everything before beat 4 exists to set it up, and everything after exists to show it was not staged.

---

## Before you press record

Say none of these, in any phrasing. They are the ones that come out naturally under narration pressure, which is exactly why they are written down.

- "The model no longer knows it." → *denied now, out of context going forward.*
- "Stays in India." → *stays in APAC.* The destination regions inside an APAC profile are not published, and one `get-inference-profile` call punctures the over-claim.
- "First of its kind." · "Nobody else is doing this." · "Nobody carries state across calls." Several do. The claim is subject-scoped accumulation feeding a redaction decision, and beat 9 makes it properly.
- "AWS's Cedar library." `cedarpy` is a community binding.
- "Tamper-proof." The audit rows are unsigned. *Audit trail* is fair; *evidence* is not.
- "This makes you DPDP compliant." · "You'll be fined ₹250 crore."
- Any accuracy figure for Aadhaar or PAN detection. AWS publishes none.
- "Differential privacy." This is a quasi-identifier accumulator and does not borrow that vocabulary.

---

## Capture list

Two takes each; ninety minutes with the retakes. Schedule it, and do not leave it to the last hour before a 20:00 deadline.

- [ ] `cust_8814` KYC record, full frame, obviously synthetic, SPECIMEN watermark visible
- [ ] Live feed with three green `ALLOW` rows, no dev chrome, no console errors
- [ ] Raw `fetch_customer` payload, all four fields in plaintext
- [ ] *Benign lookup*: meter moving to 1 of 3, subject id legible
- [ ] **Beat 4 in one uncut take** — the fourth field denied *and* the earlier field now a placeholder, same frame
- [ ] Rehydration: outbound message and model context side by side
- [ ] *Exfiltration attempt*: Q3 denial, then the authorized destination resolving
- [ ] Detector tier table with the gated tiers in grey, and a row showing `tiers_unavailable`
- [ ] Policy edit, ETag change, a scenario answering differently afterwards
- [ ] Audit table scrolling with `ledger_before` / `ledger_after`
- [ ] The live Function URL loading in a browser, on camera
- [ ] End card with both URLs

Record the narration separately and cut the screen to the audio. Narrating live while driving a demo is how a three-minute video becomes a four-minute video. Burn in the captions — judges watch on phones, often muted, and every caption above is doing work on its own.

**Deploy before you record.** A judge who clicks a dead link stops evaluating and does not come back, and none of this is worth anything behind a 403.
