# 16 — Recording runbook

**For:** whoever is at the keyboard while recording. **Companion to** `15-video-script.md`, which holds the narration. This holds the clicks.

Every beat below was driven against the deployed stack and verified working before this file was written. Where a beat has a failure mode, it is named with its fallback rather than left to be discovered on camera.

---

## Before you press record

| # | Do | Why |
|---|---|---|
| 1 | Close every browser tab except the one you are shooting | The tab strip is in frame and a personal tab in a submission video is a real risk |
| 2 | Browser at 1920×1080, zoom 100% | The console's sidebar collapses under 900px |
| 3 | Open `console.html`, let it sit 5 seconds | First load probes `/diag`, which is cached 60s server-side — a cold probe on camera is a visible stall |
| 4 | Check the sidebar footer shows **control plane** and **data plane** both green | If either is grey, reload before shooting, not during |

**Sessions are already seeded.** `demo-benign`, `demo-budget`, `demo-exfiltration`, `demo-compliance` all exist with real audit rows. You do not need to run anything before the shoot; the scenario buttons re-run live on camera, which is the point.

---

## The URLs

```
landing   https://4q224okuvbrch3btkm3alvbvci0jlwbr.lambda-url.ap-south-1.on.aws/
console   https://4q224okuvbrch3btkm3alvbvci0jlwbr.lambda-url.ap-south-1.on.aws/console.html
```

Views are hash-routed, so `#overview`, `#egress`, `#endpoint`, `#files`, `#ledger`, `#detectors`, `#policy` are all directly linkable. Type the hash rather than clicking through the sidebar if you need a hard cut.

---

## Beat 1 — the record, and three green rows

Landing page, top. Hold two seconds in silence on the hero record card — `cust_8814`, name and city released, Aadhaar and PAN as `[AADHAAR_1]` / `[PAN_2]`.

Then hard cut to `console.html#egress` and let the live feed fill frame.

---

## Beat 2 — what the tool actually returns

**The script's original premise was wrong and is corrected here.** `fetch_customer` takes `(customer_id, field)` and returns **one field per call**. The only value that produces the four-field payload the narration describes is `field='kyc'`:

```bash
cd D:\aws_first_commit\naka
python -c "import sys;sys.path.insert(0,'.');import tools,json;print(json.dumps(tools.fetch_customer._tool_func(customer_id='cust_8814',field='kyc'),indent=2))"
```

```json
{
  "customer_id": "cust_8814",
  "aadhaar": "0482 7391 5604",
  "name": "Anil Kumar Rao",
  "phone": "+91 55501 84412",
  "pan": "AZKPR0000M"
}
```

Shoot the terminal. Any other `field` returns a single value and the narration will not match the screen.

---

## Beat 3 — guard on, the meter moves

`#egress` → click **Benign lookup**. Wait for the green confirmation line. Cut to the **Disclosure meter** panel as the slots fill.

---

## Beat 4 — allowed a call ago, denied now

`#egress` → click **Budget bites**.

**Point the camera at the disclosure meter, not the feed.** This is the one direction that differs from the script, and it matters: all four steps return `outcome: ok`, so there is no red DENIED row to cut to. The budget genuinely bites, but the evidence is in the meter and the ledger, not the outcome column:

```
step1  masked={IN_AADHAAR:1}       ledger=[PAN]
step2  masked={}                   ledger=[GSTIN, PAN]
step3  masked={}                   ledger=[GSTIN, IFSC, PAN]
step4  masked={IN_VOTER_NUMBER:1}  ledger=[GSTIN, IFSC, PAN]   ← unchanged. Budget full.
```

The meter reads **3/3 spent, exhausted** and plays the trip animation — a large-area inversion to ink. That is the shot.

Note also that step 1 masks for a *different* reason than step 4: Aadhaar is never released to an analyst regardless of budget, whereas the voter ID at step 4 is refused *because the budget is spent*. If the narration implies step 1 was a clean release, it contradicts the screen. Say "the fourth field" not "the first denial".

---

## Beat 5 — the task still completes

Click any feed row. The **Decision detail** pane shows before/after as entity chips. Say out loud that these are reconstructed from types and counts and that the API has no field that could carry a value — it is the claim the whole product rests on and it is visible right there.

---

## Beat 6 — a placeholder is not a bearer token

`#egress` → click **Exfiltration attempt**. This one *does* produce a visible refusal:

```
step2  send_summary  denied_placeholder
       "Restoring a IN_AADHAAR value into this destination is not authorized"
```

The refusal reads **amber**, not red. If anyone asks on camera: red is reserved for faults, and a block is the guardrail working.

---

## Beat 6a — the same policy, on a laptop

**Requires the endpoint agent running elevated.** If it will not start, use the fallback below; do not skip the beat, it is the strongest one in the video.

Full version: paste text containing an Aadhaar and a PAN into a consumer AI tool in the browser. The overlay stops it. Cut to `console.html#endpoint` and let the row arrive on camera — the view polls every 4 seconds, so there is a visible wait. **Let the wait show.** It is evidence that this is live, not a mock.

**Fallback if the agent will not start** (verified working):

```bash
cd D:\aws_first_commit\prompt_optimizer\agent
node -e "require('./src/naka/reporter').reportDecision({action:'block',findings:[{type:'aadhaar'},{type:'pan'}]},{action:'paste',destination:'chatgpt.com'})"
```

Then cut to `#endpoint`. A real device row arrives in AWS from a real machine. Say "recorded earlier" over anything that is not live.

This machine is already enrolled as `dev_23531c256ddf`. If you need to re-enrol:

```bash
node scripts/naka-enroll.js --control <control-url> --key <X-Naka-Key>
```

---

## Beat 7 — what it could not scan, it says so

`#detectors`. The table is probed live against the account:

```
Tier 1     Local checksum        PASS
Tier 2     Amazon Comprehend     NOT_RUN   SubscriptionRequiredException
Normalize  Amazon Textract       NOT_RUN   SubscriptionRequiredException
Tier 3     Nova Pro multimodal   NOT_RUN   ValidationException
```

Say this evenly, with no apology. A provisioning state is not a defect, the page works it out live rather than asserting it, and a control plane that admits what it could not see is more convincing than one that cannot tell the difference.

---

## Beat 8 — CUT BY DEFAULT

Restore only if the whole read comes in under 2:44. See the clock in `15-video-script.md`.

---

## Beat 9 — prior art, then the live URL

`#overview` for the closing frame: the four KPI cards with **unscanned egress = 0** highlighted. That number is the product's core claim and it is the right last thing on screen.

---

## Known failure modes, each with its fallback

| Risk | Signal | Do this |
|---|---|---|
| Endpoint agent will not start | CA or elevation error | Beat 6a fallback above |
| `/diag` shows a cold probe | Tier rows say "probing…" | Load `#detectors` 60s before shooting it |
| Feed shows old test rows | Rows named `verify-*` / `livecheck-*` | Harmless, but click a `demo-*` row for beat 5 |
| Scenario button appears to do nothing | No green line after ~3s | Check the sidebar health dots; reload |
| Recording over 3:00 | — | Beat 8 is already cut; next to go is beat 5 |

---

## After the recording

1. Trim the head and tail only. Resist doing more — a hackathon video that looks over-produced reads worse than one that looks live.
2. Burn in the captions from `15-video-script.md`. They carry the argument for a muted viewer, and judges do watch muted.
3. Check the total is under 3:00 before uploading. The ceiling is hard.
