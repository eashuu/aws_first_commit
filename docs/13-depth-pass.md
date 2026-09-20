# 13 — Depth pass

**Written:** 19 September 2026 · **Ships:** Sunday 20 September 2026, 20:00 IST
**Trigger:** a panel member said the project looks "very simple" — specifically that the *idea sounds trivial* and the *tech looks shallow*.
**Supersedes:** the beat order in `06-pitch-deck.md` §A.2 and the section order in `11-written-submission.md`. Everything else in both documents stands.

---

## 1. The diagnosis

Neither critique is about the build. 4,300 lines, Cedar at three decision points, an atomic cross-call ledger, a three-tier detection union and authorized rehydration is not a simple project. Both critiques are about **what the materials put in front of a judge, and in what order.**

### Why "the idea sounds trivial"

Compressed to one sentence, the pitch collapses to *"it redacts PII from agent tool calls."* Every hackathon has that, usually as thirty lines of regex. The distinguishing word — **cumulative** — is the one that does not survive compression, because a listener has no reason to think accumulation is hard until they have watched it bite.

Then the materials make it worse. `11-written-submission.md` puts prior art in **position two**, before anything about the build, and that section says, in the team's own words:

> *"It is our pitch, five months early, and better formalised."*
> *"AWS shipped the policy substrate for this six weeks ago."*

That honesty is right, and it must stay. But a judge reading six competitors and two self-deprecating verdicts *before* seeing what was built forms exactly one impression: **known idea, already solved, narrow remainder.** The same paragraph placed after the demo reads as command of the field. Placed before it, it reads as a confession.

The video repeats the pattern. Beats 2 and 3 spend **thirty seconds — one sixth of the runtime — on a competitor and a model-routing footnote before anything works on screen.** A judge decides whether a submission is interesting inside that window, and in it they see an AWS announcement page and a documentation line.

### Why "the tech looks shallow"

This one is literally accurate *as an account of what the video shows*. Walk the current beats: a card, a competitor, a model id, a meter filling, a redaction, a substitution, a PDF, a policy edit. Every one is an **outcome**. Not one is an **obstacle**.

An engineer judging a build is asking a single question — *what was hard here?* — and the current ninety seconds never answers it. Meanwhile the genuinely hard things exist in the repo and are invisible on camera:

| In the code | On camera |
|---|---|
| Rehydration is itself a Cedar question, because the naive version is an exfiltration primitive | not shown |
| DynamoDB atomic `ADD` on a String Set, because the SDK's session managers are last-writer-wins and silently drop ledger updates | not shown |
| Detection tiers **union**, never subtract, so a confident checksum cannot be erased by a vaguer model | not shown |
| Redaction applied right-to-left by offset, with overlapping spans collapsed first | not shown |
| `AuditHook` binds both events at `SDK_LAST`, because the default hook order fires before interventions decide and drops every Q1 denial from the trail | not shown |

**Fix both by re-ordering, not by building.** Two new beats, one re-order, no new subsystems.

---

## 2. The one structural change

> The same sentence about prior art reads as **weakness at 0:14** and as **expertise at 2:35.**

Move it. In the video and in the submission. Nothing is cut, nothing is softened, nothing becomes less honest — the competitors, the six falsifiers and the "narrow remainder" verdict all survive verbatim. They simply stop being the first thing a judge learns.

---

## 3. Revised video beat order

Total 2:50. Word budget ≈ 365 at 129 wpm. Beats marked **NEW** or **MOVED** are the only changes; the rest carry over from `06-pitch-deck.md` §A.2 unedited.

| # | Time | Beat | Change |
|---|---|---|---|
| 1 | 0:00–0:12 | Cold open — the Aadhaar card, three green ALLOWs | unchanged |
| 2 | 0:12–0:26 | **The same agent with the guard off** | **NEW** |
| 3 | 0:26–0:52 | Guard on: the meter fills 1/3, 2/3 | was beat 4 |
| 4 | 0:52–1:20 | **Allowed at call two. Denied now.** | was beat 5 |
| 5 | 1:20–1:42 | Rehydration — the task still completes | was beat 6 |
| 6 | 1:42–1:58 | **The placeholder is not a bearer token** | **NEW** |
| 7 | 1:58–2:14 | One attachment, the whole budget | was beat 7 |
| 8 | 2:14–2:32 | One policy, two agents | was beat 8 |
| 9 | 2:32–2:50 | **Prior art, then close** | **MOVED** — was beat 2 |

**Cut entirely: the Nova-vs-Claude routing beat (old beat 3, 14s).** It is a genuinely good decision and it is the wrong use of the freshest thirty seconds of a three-minute video — it argues a build decision to a viewer who does not yet care about the build. It survives as a **burned-in caption during beat 3** (`Nova on apac.* — Claude in Mumbai is global-profile only`) and as its own paragraph in the written submission, where a judge who cares will find it. That recovers the fourteen seconds the two new beats need.

### Beat 2 — 0:12–0:26 · The same agent with the guard off · **NEW** (38 words)

**Headline:** `Same agent. Same prompt. Guard in shadow mode.`

**On screen:** Split frame, both panels running the identical prompt. Left panel `enforce: false`. The tool results scroll past with the Aadhaar, the PAN, the name and the address all in plaintext. A counter in the corner climbs: `6 identifying fields disclosed · budget was 3`.

**Narration:**
> Same agent, same prompt, same policy — with enforcement switched off. This is shadow mode: it decides everything and applies nothing. Four calls in, six identifying fields about one customer have reached the model. The policy ceiling was three.

**Why this beat exists.** It is the entire answer to "the idea sounds trivial." Nobody can call a control obvious while watching what happens without it. It also pre-empts the judge's real suspicion — *would anything actually have leaked?* — in fourteen seconds rather than leaving it unanswered.

**It must be said out loud that this is the same code.** Shadow mode is `enforce=False` on the same `DisclosureGuard`: identical normalize → detect → Cedar → redact path, and the only difference is that the result is not applied. Two different codepaths filmed side by side would prove nothing, and a judge will assume that is what they are looking at unless told otherwise. `selfcheck.py`'s `test_shadow_mode` asserts the two runs detect identically and diverge only at enforcement — worth one on-screen line.

### Beat 6 — 1:42–1:58 · The placeholder is not a bearer token · **NEW** (42 words)

**Headline:** `An injected agent asks for the same placeholder. Different destination.`

**On screen:** The prompt-injection fixture. The agent emits `[IN_AADHAAR_1]` into a `send_summary` call addressed to `notes.pastebin.example` instead of `kyc-vault.internal`. Cedar Q3 denies. The placeholder goes out as a placeholder. Then a hard cut back to the authorized destination from beat 5, resolving correctly — the same token, two destinations, two answers.

**Narration:**
> One thing this has to get right. If a placeholder can be exchanged for its value anywhere, the guardrail is an exfiltration primitive — an injected agent just asks for it back. So rehydration is its own authorization question, against the destination. Same token. Different destination. Denied.

**Why this beat exists.** It is the entire answer to "the tech looks shallow," and it is the cheapest depth signal in the repo because it is already built and already tested (`test_rehydrator`: *denies rehydration into an unauthorized destination*, *an unminted token is denied, never passed through*). It shows the team found a way their own design could be **worse than no design at all**, and closed it. That reads as engineering judgement in a way no architecture diagram does.

If only one of the two new beats can be shot, **shoot this one.** "Trivial idea" costs you novelty points; "shallow tech" costs you the technical judge entirely.

### Beat 9 — 2:32–2:50 · Prior art, then close · **MOVED** (46 words)

**Headline:** `AgentCore Policy · Dogwood · CAMP · OCELOT`

**On screen:** The four names, live browser, dates visible. Then the audit table scrolling. Then the Function URL typed into a browser and loading, on camera.

**Narration:**
> None of this is unclaimed ground. AgentCore Policy went GA in March. Dogwood added session history to Cedar in August. CAMP formalised cumulative exposure in April. Nobody connected them — and in production our ledger should be a Dogwood information provider, not a competitor. Each call was allowed. Together they identify her. This time, something was counting.

**Why the move works.** At 0:14 this is a list of people who got there first. At 2:32, after eight beats of working system, it is a team that read the field, names the closest work unprompted, and knows where their piece fits in someone else's architecture. **Same facts. Opposite impression.** The insurance value against a judge who already knows AgentCore Policy is fully preserved — it is still volunteered, never extracted.

---

## 4. Submission restructure

`11-written-submission.md` keeps every word. Only the order changes, plus one new paragraph.

| Now | Becomes |
|---|---|
| 1. The problem | 1. The problem *(unchanged)* |
| 2. Prior art, before anything about us | 2. **What we built** |
| 3. What we built | 3. **What was hard** ← new, ~250 words |
| 4. Where AWS fits | 4. Prior art *(verbatim, retitled)* |
| 5. What this does not do | 5. Where AWS fits |
| 6. Compliance framing | 6. What this does not do |
| 7. Fixtures and AI disclosure | 7. Compliance framing |
| | 8. Fixtures and AI disclosure |

**Retitle section 4** from *"Prior art, before anything about us"* to **"Prior art, and where this sits in it."** The old title was a promise about position that the new order no longer keeps, and the new one claims something stronger anyway.

**Keep the cut-order rule** in the pre-paste notes, with one amendment: *Compliance framing* still goes first, but **"What was hard" is now cut-protected alongside "What this does not do."** A submission that keeps its limitations and drops its difficulties is the exact failure this document exists to correct.

### The new section 3 — "What was hard"

The submission currently states every hard thing as a subordinate clause inside a sentence about something else. Promote them. Four short paragraphs, roughly 250 words, one per row of the table in §1 above, each written the same way: **the naive version, why it fails, what we did instead.** That shape is what makes difficulty legible to a reader who cannot see the code.

Lead with rehydration-as-authorization, because it is the one where the naive implementation is *actively worse than shipping nothing* — a redaction layer whose placeholders can be cashed anywhere has built an exfiltration primitive and called it a control. Then the ledger's atomic `ADD` (last-writer-wins silently drops updates, and a dropped update is a budget that never binds). Then tier union (a confident checksum must not be erasable by a vaguer model). Then the `AuditHook` order bug (a hook at the default order fires before interventions decide, so every Q1 denial is missing from the audit trail — the control plane's own evidence, silently incomplete).

Close the section on the shadow-mode point, because it is the one that sounds like an operator wrote it rather than a hackathon team: **nobody turns on a blocking control in front of live traffic without first measuring what it would have blocked.** That single sentence does more for perceived maturity than any amount of architecture prose.

---

## 5. Shadow mode — what shipped

Implemented in the repo, tested, no AWS required to verify. `python naka/selfcheck.py` → 76 checks, all passing (12 of them new, covering shadow mode).

**API.** `POST <agent-url>` now accepts `"enforce": false`:

```bash
# Guarded — the demo's normal path
curl -s "$AGENT_URL" -H 'content-type: application/json' -d '{
  "prompt": "Summarise everything you can find about customer cust_8814.",
  "session_id": "demo-guarded", "role": "analyst" }'

# Unguarded — identical run, enforcement off. USE A DIFFERENT SESSION ID.
# Requires the operator key: enforce:false is an off-switch for the whole
# guardrail, and the Function URL is AuthType=NONE (public, by design, so
# judges can open it) -- without this gate any caller on the internet
# could disable the control. Set NAKA_KEY as the X-Naka-Key header.
curl -s "$AGENT_URL" -H 'content-type: application/json' -H "X-Naka-Key: $NAKA_KEY" -d '{
  "prompt": "Summarise everything you can find about customer cust_8814.",
  "session_id": "demo-shadow", "role": "analyst", "enforce": false }'
```

**Semantics.**

- Absent `enforce` means enforce. Only an explicit `false` disables it, and a non-boolean is a 400 rather than a coercion — `"false"` from a hand-written curl is truthy in Python and would silently enforce a run the operator asked to be a measurement.
- **`enforce: false` requires `X-Naka-Key`.** Enforcing needs no key — the protective path must never depend on a secret being present — but disabling it does, gated the same way as `PUT /policy`. Without this, a public URL with a shadow-mode flag is an anonymous off-switch for the entire guardrail. If `NAKA_KEY` isn't configured, shadow mode is unavailable rather than silently open (403, not a bypass).
- Shadow mode **never alters traffic.** Not on a policy denial, and not on a detector or normalizer outage either: the `_withhold` path returns `Proceed` instead of blanking the payload. Shadow mode is enabled on exactly one promise — that it cannot break anything — and a conservative default here would break it.
- Shadow mode **never writes the ledger cache.** Its in-memory ledger counts entities that were never spent, and `app_agent.py` merges that cache on top of the DynamoDB ledger at the start of every turn. Writing it would let a measurement run inflate a real session's budget — the one remaining way a non-enforcing mode could still change enforced behaviour. DynamoDB stays untouched, so `"ledger_persisted": false` comes back in the response.
- Every audit row carries `enforce`, and shadow rows carry `would_mask` — what the guard decided but did not apply. `entities_masked` stays empty on a shadow row, because nothing was masked; the counterfactual lives in its own field so a dashboard summing `entities_masked` can never count a measurement as a prevented disclosure.

**Still to wire:** the control-plane UI has no compare view yet. For the video, two browser panels side by side against two session ids is sufficient and is what the beat sheet above assumes.

---

## 6. What not to do with the remaining hours

**Do not add a feature.** The judge's comment is not a request for more surface area, and a fourth subsystem shipped at 3 a.m. on Sunday is worth less than the rehydration beat that is already built and already tested.

**Do not remove a limitation.** The honesty is an asset and at least one judge will check. The problem was never that the limitations were stated — it was that they arrived before the achievements.

**Deploy first.** The Ship It track is judged on a reachable URL. A broken deploy makes every word of this document worthless, and a judge who clicks a dead link stops evaluating and does not come back.
