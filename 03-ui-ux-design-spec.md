# Naka — UI/UX design specification

**Package:** chowki-hackathon · document 03
**Source of truth for product behaviour:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md` (data model §10, demo beats §12)
**Written:** 18 September 2026 · **Ships:** Sunday 20 September 2026, 20:00 IST
**Judged for:** Ship It track *and* Best UI (₹1,00,000 + $1,000 AWS credits), on the same submission

---

## ⚠️ Superseded in part by the shipped build · 19 September 2026

**Read this before citing any part of this document as a description of what exists.** Three decisions in here were overridden during implementation, deliberately and with the call put to the team explicitly. The spec is retained as written because the reasoning is still sound and the argument is worth having on the record — but `naka/web` is the product, and where the two disagree, the code is what a judge sees.

| §  | What this document specifies | What shipped | Why |
|---|---|---|---|
| **10.1** | Vite + React + TypeScript | **Plain HTML, CSS and ES modules** — `index.html`, `app.css`, `render.js`, `store.js`, `api.js`, `motion.js` | Six components did not justify a build step inside a Lambda zip. This one strengthens 10.1's own argument rather than contradicting it. |
| **10.1** | "No animation library" | **GSAP + ScrollTrigger + anime.js + Lottie + Lenis**, all deferred from CDN | The spec conflict was put to the team directly and the full motion treatment was chosen knowing what §7 says. Recorded here rather than quietly deleted. |
| **7, rule one** | "Nothing loops" | A looping Lottie in the hero | Same decision. §7's reasoning — that a looping element steals attention eight times across a three-minute video — still stands as the argument against it. |

**What did *not* change, and should not:** §7's distinction between motion that shows what changed and motion that decorates. The functional motion the spec asks for is all present and is the part to defend on camera — redaction bars wiping in, ledger slots filling left to right, the budget trip inverting the card. If anything is cut for time, the decorative layer goes first: hero glow, then the scroll cue.

**Two implementation findings that §7 and §10.1 could not have predicted, both verified on the deployed page:**

1. **Lenis suppresses native scroll events on `window` entirely.** Measured: `window.scrollY` advances to 1600 while a `window` `'scroll'` listener fires exactly zero times. This broke ScrollTrigger, then IntersectionObserver, then a plain scroll handler, in sequence — three mechanisms all waiting for a signal that never arrives. The fix is a rAF poll re-armed on `visibilitychange`, `scroll` and `resize`. **This is the concrete cost of the override**, and it is a better argument for §10.1 than §10.1 made for itself.
2. **The graceful-degradation claim was tested rather than asserted, and it holds.** With all five globals deleted and every external script tag stripped — so `motion.js` genuinely reads undefined for gsap, ScrollTrigger, Lenis, anime and lottie — the page renders 12/12 reveals visible, hero intact, four scenario buttons, sticky nav, four detector-tier rows, policy textarea loaded, agent URL prefilled and the correct empty-state copy. **The console is fully usable with zero animation libraries.** This is the answer to §10.1's CDN objection: the dependency is real but it is not load-bearing, and reveals are authored visible-by-default with the hiding class applied only once a working trigger exists.
3. **A token rename silently broke every status pill.** `render.js` still referenced `var(--ok)`, `var(--warn)` and `var(--muted)` after a stylesheet rewrite renamed them, so every pill rendered with an undefined colour and no error anywhere. Found only by auditing the colour semantics (§6.2). Custom properties fail silently; there is no build-time check for this in a no-build stack.

**One addition to §6.2's colour semantics, adopted 19 September**, after checking how AWS's own consoles encode state: **red is reserved for failure, not for denial.** Across the Cedar playground, the Verified Permissions console, Bedrock Guardrails and CloudWatch GenAI Observability, green means allowed or no action taken, amber means intervened — content modified but not fatal — and red means an error. A successful block is amber, because the system worked as designed. Shipped mapping: `--deny` is now amber `#e8913a`; a new `--fault` `#e0495f` is the **only** red in the product and is reserved for `withheld_detector`, `withheld_ledger` and `withheld_internal_error` — the states where Naka could not reach a decision at all.

**And one component this document does not contain**, added because the judging format demands it: **one-click scenario buttons**. Four, above the prompt, each carrying a complete payload and role, each minting a fresh session id so one scenario cannot inherit another's spent ledger. The judge never types. See §0 — it is the same constraint this document opens with, followed further than the original draft followed it.

---

## 0. The one constraint that decides everything below

Judges see a public repo, a written submission, and **a YouTube video of three minutes or less**. There is no live demo, no walkthrough call, no hover, no click from the judge. The interface is judged as a **moving image at 1080p, after YouTube's encoder has had it**.

Three consequences, applied throughout:

1. **Chroma subsampling (4:2:0) destroys thin coloured detail.** A 1px coloured hairline, a 12px coloured label, a saturated-red-on-dark edge — all smear. Meaning therefore lives in **luminance, area, and shape**. Hue is a third channel, never the first.
2. **Every screen change costs ~1.5s of viewer reorientation.** At 180 seconds across eight beats, you can afford about two. So: **one screen**, fixed spatial layout, everything the video needs already located.
3. **Nothing on screen is smaller than 13 CSS px.** At the capture setup in §11 that renders as 17.3 device px. Below that, text does not survive the encode.

Everything in this document that looks like an aesthetic preference is downstream of one of those three.

---

## 1. Information architecture

### 1.1 One screen. No routes, no nav.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ▣ Naka            │ Session   │ Role     │ Policy    │  [ Run session ]    │ 56
│                   │ s-9f3a    │ analyst  │ etag c4f1 │                     │
├──────────────────────────┬─────────────────────────────────────────────────┤
│ Disclosure ledger        │ Call 6 · read_attachment · cust_8814            │
│                    440px │  ▌▌▌▌▌▌░░░░  session spend strip                 │
│ ┌──────────────────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │ cust_8814      FOCUS │ │ │ What the tool returned │ What reached model │ │
│ │                      │ │ │                        │                    │ │
│ │       3              │ │ │  Ravi Kumar            │  Ravi Kumar        │ │
│ │       of 3 fields    │ │ │  9812 3456 7788 ①──────│──▶ [IN_AADHAAR_1]① │ │
│ │                      │ │ │  +91 98••• •••••   ②───│──▶ [PHONE_2]     ② │ │
│ │  ▓NAME ▓PHONE ▓EMAIL ▐│▨│ └─────────────────────────────────────────────┘ │
│ │   c1     c2    c4     │ │ Substitutions (2)                              │
│ │                       │ │ ① Aadhaar number → IN_AADHAAR_1  forbid-aadhaar│
│ │ Budget exhausted      │ │ ② Phone number   → PHONE_2       budget-ceiling│
│ └──────────────────────┘ │ ├─────────────────────────────────────────────┤ │
│ ┌──────────────────────┐ │ │ Policy  budget-ceiling                    ⌄ │ │
│ │ cust_2290   ▓░░   1/3│ │ │ seen_count → 3 ≥ budget → 3   ⇒ forbid      │ │
│ └──────────────────────┘ │ └─────────────────────────────────────────────┘ │
├──────────────────────────┴─────────────────────────────────────────────────┤
│ Calls                                                                      │
│ ▌6  read_attachment  cust_8814  Redacted   3→3  ▨2  312ms  20:14:08        │ 36
│ ▌5  fetch_customer   cust_2290  Allowed    0→1  ●0   88ms  20:14:04        │ /row
│ ▌4  fetch_customer   cust_8814  Allowed    2→3  ●0   91ms  20:13:58        │
└────────────────────────────────────────────────────────────────────────────┘
```

Regions, and what each is worth in video seconds:

| Region | Position | Seconds on camera | Why |
|---|---|---|---|
| **Disclosure ledger** (the meter) | Left column, top, 440px | ~110 s (0:35–2:25) | The hero. The claim of the whole project is cumulative state; the meter *is* cumulative state |
| **Decision** (diff + policy reason) | Right column, top | ~100 s (0:35–2:25) | The proof. Without the diff, the meter is an assertion |
| **Session spend strip** | Right column, above the diff, 24px | Always | Supplies motion and history in 24 pixels; also the scrubber |
| **Calls** (feed → audit) | Full-width bottom band, 240px | Always, read for ~15 s | Liveness. The viewer must never read it; they must see it move |
| **Policy** | Right column, bottom, collapsed to 2 lines | ~20 s (2:25–2:45) | Expands only for the hot-reload beat |

### 1.2 Why this hierarchy, and what it would be for a daily user

**Screen area is allocated in proportion to seconds of video, not to frequency of use.** This is the whole justification and it is deliberately not the usual one.

A real analyst living in Naka would want the **audit table primary** — it is where investigations happen — with the meter as a sidebar summary and the diff behind a row click. That product is correct and it is not this product. Here the audit table is a 240px band, because it earns 15 seconds; and the meter, which a daily user would glance at twice a day, owns the most valuable 440×420 rectangle on screen because it owns 110 seconds of the judging surface.

If Naka survives the hackathon, **the first post-hackathon IA change is inverting this**: audit becomes a route, the meter becomes a persistent header strip. Note that in the writeup. Judges reward a team that knows which decisions were for the camera.

### 1.3 The three rejected architectures

| Rejected | Why |
|---|---|
| **Tabbed console** (Ledger / Decisions / Policy / Audit) | Four tabs is four context switches — ~6 s of the 180. Worse: the meter and the diff would never be in frame together, and the project's entire argument is that those two things are the same fact seen twice |
| **Timeline-first** (a big horizontal session timeline as the primary object, panels below) | Reads beautifully and shows the cumulative story — but it puts the *sequence* first when the claim is about the *total*. Demoted to the 24px spend strip, which keeps the best 10% of it for 3% of the space |
| **Split by agent** (two agent columns for the §12 hot-reload beat) | The two-agent beat is 20 seconds. Paying a permanent column split for it halves the diff's width for the other 160. Solved instead by a second browser tab with a different `session_id` — see §10.4 |

### 1.4 Focus model

Exactly one **focus subject** at a time. Its card is expanded (full meter, 48px figure, field labels); every other subject is a 44px compact row with a mini-strip. Selecting a call in the feed or the spend strip **sets the focus subject to that call's subject** — so the meter and the diff are always describing the same thing. That coupling is what lets the video cut between them without a transition.

---

## 2. The hero component — the disclosure meter

### 2.1 What the data actually is

From the PRD §6.1, the ledger snapshot is:

```
{"subject": "cust_8814", "seen": ["NAME","PHONE"], "seen_count": 2, "budget": 3}
```

**The budget is a small integer — 3 — and each unit spent has an identity.** That single observation kills most of the obvious designs. This is not a percentage. It is a set of three slots, each of which was spent by a *named field* on a *numbered call*.

### 2.2 Two alternatives, considered and rejected

**Alternative A — radial gauge / arc.** Rejected on five counts. (1) It encodes a discrete 0/1/2/3 as a continuous sweep, which misstates the data. (2) Angle is a weaker perceptual channel than position on a common scale, so a 1-of-3 step is harder to read than the same step on a strip. (3) At 1080p an arc needs ~180px of diameter before a one-third increment is unambiguous, and it wastes the centre. (4) It is the single most-clichéd object in the security-dashboard genre, and this project is already fighting a crowded category (PRD §2.3) — looking like the category is a positioning cost. (5) It cannot carry per-slot labels without a legend, so the *identity* of what was learned is lost.

**Alternative B — continuous progress bar with a threshold tick.** Rejected on four counts. (1) Same continuous-for-discrete error. (2) The trip reads as "a bar reached a line" — visually undramatic, and easily missed in the 2-3 seconds the beat gets. (3) Its segments have no identity, so it cannot show *which* field spent which unit. (4) Fatal: it has no memory of its segments, so it **cannot express the denied-now beat** — the §12 1:10–1:40 beat where the phone number that was allowed on call 2 is denied on call 6. That beat is described in the PRD as "the beat that wins it." A component that cannot show it disqualifies itself.

*(Also considered and dropped: a stacked bar coloured by entity type. Segment size would encode count while the reader expects it to encode identity, and it would need 4+ categorical hues, which then collide with the status palette — see §5.4.)*

### 2.3 Recommended: the segmented ledger strip

**One cell per unit of budget, left to right, plus a heavy budget rule, plus an overflow cell that is stopped dead against it.** A checkpoint: three got through the gate, the fourth is held at the barrier.

```
ANATOMY (focus card, 392px content width)

┌ card ─────────────────────────────────────────────────────┐
│                                                           │ 24 pad
│  cust_8814                              ● Within budget   │ ← 26px name · state chip
│  Ravi Kumar · customer                                    │ ← 15px ink-500
│                                                           │ 20
│   2                                                       │ ← hero figure 48px
│   of 3 fields disclosed                                   │ ← 17px ink-700
│                                                           │ 16
│   ┌──────────┐ ┌──────────┐ ┌ ─ ─ ─ ─ ┐ ▐   ┌ ─ ─ ─ ┐    │
│   │██████████│ │██████████│ │         │ ▐   │       │    │ ← slots 32px tall
│   └──────────┘ └──────────┘ └ ─ ─ ─ ─ ┘ ▐   └ ─ ─ ─ ┘    │   4px gap · 3px radius
│     NAME         PHONE        open      ▐    overflow     │ ← 13px labels, ink-700
│     call 1       call 2                 ▐                 │
│                                       budget              │
│                                        rule               │
└───────────────────────────────────────────────────────────┘
```

**Parts.**

| Part | Spec |
|---|---|
| Slot | flex-1, height 32px, radius 3px, 4px gap between slots |
| Filled slot | ordinal ochre ramp by index (§5.4): slot 1 `#DCA646`, slot 2 `#C98A16`, slot 3 `#B0700A`. More spent = darker = closer to redaction |
| Open slot | track `#EFDCBA` fill + 1px `#C9CEDA` inset ring. A lighter step of the same ramp, so the reader sees the headroom in the same colour language |
| Slot label | **under** the slot, never inside it: field name at 13px/600 ink-700, call number at 13px/400 ink-500. (Inside would be 13px on an ochre fill at 4.3:1 — under the AA floor, and the dataviz rule is never to place a label inside a mark it does not fit) |
| Budget rule | 3px wide, full slot height + 8px overhang top and bottom, `#10141F`, 12px to the left of the overflow slot |
| Overflow slot | same geometry, `--hatch-solid` in denied `#9A1428` over its 10% tint, 2px denied ring, deny glyph centred. Appears **only** once the budget is spent |
| Hero figure | the spent count, 48px/700, proportional figures (never `tabular-nums` at display size), ink-900 |
| State chip | see §6 |

**Compact rows** (non-focus subjects): the same strip at 10px tall with no labels and no hero figure, plus `1/3` at 15px tabular. 44px row height. Selecting one promotes it to focus.

### 2.4 The trip — what happens at the moment the budget is spent

This is the most important 760 milliseconds in the submission. Four things happen in sequence, and they are sequenced (not simultaneous) so that at 30fps a viewer perceives *causation*, not just a change.

| t | What | Timing |
|---|---|---|
| 0 ms | The overflow slot spawns 24px right of the budget rule at opacity 1 and translates left into it | 200 ms, `--ease-hard` — it **stops dead**. 6px recoil, no bounce past the rule |
| 200 ms | The budget rule thickens 3px → 5px and flashes once from ink-900 to denied and back | 80 ms in, 80 ms out. **One flash. Never a loop** |
| 240 ms | `--hatch-wash` wipes across the filled slots left-to-right | 180 ms each, staggered 70 ms (slots 1, 2, 3 → completes at 560 ms) |
| 560 ms | **The card inverts.** Background crossfades panel → `#10141F`; text colours swap instantly at the 50% mark | 200 ms background, 0 ms text |
| 760 ms | State chip label swaps to "Budget exhausted"; banner line appears under the strip | 120 ms fade |

**Why inversion.** The card flipping from paper to a solid dark block is the most compression-proof state change available: it is a large-area luminance inversion, which survives any bitrate, any colourblindness, any grayscale print, and reads at thumbnail size. It costs zero new hue. And it is the reason §5.1 makes light mode the default — **a dark UI has nothing more dramatic to invert to.** The hero moment requires a light base.

**The banner under the strip, verbatim:**

> Budget exhausted for cust_8814. Identifying fields are now redacted, including fields that passed earlier.

That last clause is the project's entire thesis in nine words, on screen, in the frame, at 17px. It is the single most valuable string in the product.

### 2.5 What the meter must also show

**The denied-now beat** is visible because each slot carries the call number that spent it. When call 6 denies a phone number that call 2 allowed, the viewer can see `PHONE · call 2` sitting in a hatched slot while the feed row for call 6 says Redacted. The meter is the receipt for the claim. Note what the picture must never be narrated as: nothing is being retracted from what the model already read — the field is denied *now*, and removed from context going forward (PRD §12's narration rule).

**Multiple subjects** are the compact rows. The video only ever focuses one, but the presence of `cust_2290 ▓░░ 1/3` underneath proves the ledger is per-subject and not a global counter — a distinction a judge will test for.

---

## 3. The redaction diff

### 3.1 It is not a code diff

The change here is **substitution at character spans**, not insertion and deletion of lines. Comprehend already returns offsets (PRD §7); there is nothing to compute. Rendering this as a git-style diff — green added lines, red removed lines — would be wrong twice over: wrong model of the change, and the red/green trap §6 exists to avoid.

### 3.2 Side-by-side, span-locked

**Recommended: side-by-side**, rejecting inline-unified. Inline is more compact and reads better on a phone, but the panes' *headings* — "What the tool returned" / "What reached the model" — are half the proof. Collapse them into one column and the claim becomes invisible.

The cost of side-by-side is width, and the fix is **span-locked alignment**: both panes are the same document, so both render the same logical lines, and each logical line is one grid row spanning both panes.

```
.diff { display: grid; grid-template-columns: 1fr 56px 1fr; }
/* one row per logical line; row height = max(left, right) */
```

Because line *n* sits at the same y on both sides, every connector is a **straight horizontal rule**, never a bezier. That is not a stylistic preference: a 1px diagonal curve is exactly the shape 4:2:0 chroma subsampling annihilates, and a 2px horizontal rule is exactly what survives.

### 3.3 How entities are marked

```
LEFT — What the tool returned          GUTTER        RIGHT — What reached the model
                                        56px
  Name:  Ravi Kumar                                    Name:  Ravi Kumar
         ╰────────────╯ teal tint, no connector               ╰────────────╯
  UID:   9812 3456 7788 ①            ①━━━━━━━━━━━━▶   UID:   ①[IN_AADHAAR_1]
         ╰────────────╯ ochre tint, 3px ochre rule            └ boxed mono token ┘
  Phone: +91 98••• ••••• ②           ②━━━━━━━━━━━━▶   Phone: ②[PHONE_2]
```

| Element | Spec | Reason |
|---|---|---|
| Detected-and-**revealed** span (left and right, identical) | allowed tint `#e3f1f0` background, 3px bottom rule `#12997A`, no connector | Proves the scanner *saw* it and policy let it pass. Without this mark, an unmarked right pane is ambiguous between "clean" and "not scanned" |
| Detected-and-**redacted** span (left only) | redacted tint `#f5eee4`, 3px bottom rule `#C77400`, index badge | Text stays ink-900 at 17.76:1 — the digits are the evidence, they must not be tinted |
| Index badge | 16×16, 3px radius, hue fill, ink or paper label at 13px/600, sits as a leading superscript on both sides | **The number is the tie, not the colour.** Colour can fail; an integer cannot |
| Placeholder token (right) | mono 15px, 3px radius box, 1px hue ring, hue tint fill, 3px horizontal padding | Reads as a token, not as prose. Mono is earned here — it is a literal system identifier |
| Connector | 2px horizontal rule in the substitution's hue, 6px terminal square at each end, at the token's baseline + 2px | Straight, thick, hue-coded, ends squared so the terminal is 6px of solid colour rather than a tapering line |
| More than 6 substitutions | Drop connectors entirely; the substitutions list (§3.5) carries the mapping | 12 connectors is noise, not proof |

**Never** a coloured text colour on a detected span, and **never** a full-saturation highlight behind it. Both cost the digits their contrast, and the digits are the thing being proved.

### 3.4 Aadhaar on camera — the masking default

The console that prevents disclosure must not itself disclose. The left pane defaults to **masked**: `XXXX XXXX 7788`. A "Reveal source" control unmasks it, and a persistent **Synthetic fixture** chip sits in the left pane's header.

For the video, one deliberate unmask on a synthetic, Verhoeff-valid, never-issued number, with the Synthetic fixture chip in frame. This is both dramatic and defensible, and it pre-empts the obvious judge question (Aadhaar Act s.29(4), PRD §13) by answering it in the interface rather than the writeup.

The placeholder-to-value map is **never rendered, never copyable, never in the DOM.** It lives only on the trusted side (PRD §6.2). There is no "show original" affordance on the right pane, by design — say so in a tooltip on the pane header: *"The model's view. The original values are not available to this page."*

### 3.5 The substitutions list

Directly under the diff, always present, never collapsed:

```
Substitutions (2)
①  Aadhaar number  → IN_AADHAAR_1   forbid-reveal-aadhaar-analyst
②  Phone number    → PHONE_2        budget-ceiling
```

This is a real, visible UI element that **also happens to be the accessible primary representation** (§9.3). Building a screen-reader-only twin of a visual diff is the standard mistake; building one visible list that serves both is the fix. Each row is focusable; focusing it highlights its span pair and its connector.

### 3.6 Readability under compression

At the §11 capture setup, every meaningful element here renders at ≥17 device px or ≥4 device px of stroke:

- Tint blocks: large flat areas — the most codec-robust thing on screen.
- 3px rules: 4 device px. Survives.
- Index badges: 16px → 21 device px. Survives.
- Mono at 15px: 20 device px. Survives.
- Connectors at 2px horizontal: 2.7 device px, but horizontal and solid-coloured — survives where a diagonal would not.

---

## 4. Feed, audit, policy

### 4.1 The session spend strip (24px, above the diff)

One tick per tool call, appended as calls happen. 10px wide × 24px tall, 3px radius, 2px gap, filled with the call's decision hue. Selected tick carries a 2px ink-900 ring plus a 2px surface ring (so it stays legible where it abuts its neighbours).

It does three jobs for 24 pixels: it supplies the video's sense of *liveness* without animating anything gratuitously; it shows the whole session's shape at a glance (a run of allows, then a redact, then the exhausted block); and it is the scrubber — click or arrow-key a tick to load that call.

### 4.2 Calls — one component, two densities

The "live decision feed" and the "audit table" are **the same component**. Building two is the classic hackathon time sink for zero judged benefit.

- **Feed density** (default, bottom band, 240px): 36px rows, newest at top, capped at 50, `overflow-y: auto`. Columns: seq · tool · subject · decision chip · ledger before→after · entity count · latency · time.
- **Audit density** (`A` expands the band to 560px): adds content type, detector tiers, deny policy id, and the per-phase latency breakdown from PRD §10.

**Row anatomy.**

| Column | Spec |
|---|---|
| State rule | 3px left rule, full row height, decision hue. This is the state channel, identical to the chips |
| seq | 13px mono tabular, ink-500 |
| tool | 15px/500 ink-900 |
| subject | 15px mono ink-700 |
| decision | chip (§6) |
| ledger before→after | **two mini-strips of 8×8 slots with a 12px arrow between.** A sparkline of the ledger, scannable at video speed |
| entities | glyph + count, e.g. `▨2` |
| latency | 13px tabular ink-500, right-aligned |
| time | 13px tabular ink-500 |

**No zebra striping.** Zebra plus hue tints plus 3px state rules is mud. Rows are separated by a 1px `#DDE1EA` rule. Sticky header. No pagination controls — a capped list needs none, and building pagination is 90 minutes for a control nobody will press on camera.

### 4.3 Policy view

**Collapsed by default to the reason, expandable to the policy.** Always in frame:

```
┌ Policy   budget-ceiling                                          [⌄] ┐
│ context.session.seen_count → 3   ≥   context.session.budget → 3      │
│ ⇒ forbid                                                             │
└──────────────────────────────────────────────────────────────────────┘
```

That is the 80% case: a reader wants *why*, not the file. The evaluated annotation — real runtime values inlined beside the clause — is what converts a Cedar listing into an explanation. Set the clause in mono 15px ink-900 on the inset, the `→ 3` values in mono 15px in the decision hue, and the `⇒ forbid` at 15px/600 in the decision hue.

**Expanded** (`P`): the full `agent.cedar`, matched policy carrying a 3px left rule in the decision hue, everything else at ink-500. Panel header holds the policy id, an **etag chip**, "fetched 4s ago", and the source: `control plane` or `packaged fallback`.

**The hot-reload beat (§12, 2:25–2:45)** needs exactly three visible things:

1. The etag chip crossfades to its new value (200 ms) with a 3px brand left-rule wiping down the changed line (300 ms).
2. A two-line change strip above the policy:
   ```
   −  when { context.session.seen_count >= context.session.budget }   ← ink-500, 1px strikethrough
   +  when { context.session.seen_count >= 1 }                        ← ink-900, 3px brand left rule
   ```
   **Not red/green.** Removed is struck-through and muted; added is full-contrast with a brand rule. Consistent with §6, and it survives the encode where a red/green line pair does not.
3. The second agent's session chip in the header updating on its next call.

---

## 5. Visual system

### 5.1 The genre question, answered

**The genre of a security console is: near-black background, one acid accent (matrix green or vermilion), monospace everywhere, dense telemetry.** I am breaking it, on four grounds, in descending order of how much I believe them:

1. **The hero moment structurally requires a light base.** The trip (§2.4) is a luminance inversion to a solid dark block. From a dark base there is nothing to invert *to*. The single most memorable thing in the submission is only available on paper.
2. **Naka is a governance product, not an offensive-security product.** The dark-terminal genre signals *offence* — pentest, SOC, hunt. Naka's user (PRD §3) is a small Indian team with no security engineer, and its output is an audit record for a DPDP compliance conversation. The correct register is **the audited register**: ruled rows, a running balance, entries that are struck through rather than erased, a stamp on each decision. That vernacular is where every structural device below comes from, and it is a genuine match — the product's core object is literally called a *disclosure ledger*.
3. **Light text on a light field encodes better at 1080p.** Dark UIs at YouTube's bitrate band, and a neon accent on near-black is the worst case for ringing around text edges.
4. **In a field of several hundred hackathon entries, roughly all of the security submissions will be dark-on-neon.** Differentiation is free here.

Dark mode still ships (tokens below, all measured). It is not what gets recorded.

### 5.2 Colour tokens — light

Every value below was computed, not chosen: OKLCH lightness and chroma from `validate_palette.js`, WCAG ratios measured against the actual surfaces. The four-colour status set passes all five computable checks at `--pairs all` on the light surface (worst CVD ΔE 10.8 protan, worst normal-vision ΔE 21.3, all ≥3:1).

```css
:root {
  color-scheme: light;

  /* surfaces — cool blue-grey paper. NOT cream (#F4F1EA is a tell), not white */
  --page:        #E9ECF1;   /* the plane the panels sit on */
  --panel:       #FAFBFD;   /* panel/card surface */
  --inset:       #F2F4F8;   /* diff panes, policy, code */

  /* ink */
  --ink-900:     #10141F;   /* 17.76:1 on panel · also the inversion surface */
  --ink-700:     #454B5C;   /*  8.40:1 */
  --ink-500:     #6B7285;   /*  4.64:1 on panel, 4.36:1 on inset */
  --ink-300:     #C9CEDA;   /* rules, slot rings */
  --ink-200:     #DDE1EA;   /* row separators, gridlines */

  /* brand + status — measured, all ≥3:1 as marks */
  --brand:       #3F4EB3;   /* 6.87:1 · L .471 C .160 · focus ring, rehydrated */
  --allow:       #12997A;   /* 3.46:1 · L .610 C .116 */
  --redact:      #C77400;   /* 3.42:1 · L .637 C .145 */
  --deny:        #9A1428;   /* 8.10:1 · L .443 C .166 */

  /* text-safe variants — for the one place a state word is set in hue */
  --brand-text:  #3F4EB3;   /* 5.93:1 on its tint */
  --allow-text:  #0B6B54;   /* 5.58:1 on its tint */
  --redact-text: #8F5804;   /* 5.11:1 on its tint */
  --deny-text:   #9A1428;   /* 6.77:1 on its tint */

  /* 10% tints, pre-flattened over --panel */
  --brand-tint:  #E7EAF6;
  --allow-tint:  #E3F1F0;
  --redact-tint: #F5EEE4;
  --deny-tint:   #F0E4E8;

  /* meter ordinal ramp — one hue, monotone L, ΔL ≥ .078, light end 2.12:1 */
  --slot-track:  #EFDCBA;   /* L .901 */
  --slot-1:      #DCA646;   /* L .758 · 2.12:1 */
  --slot-2:      #C98A16;   /* L .680 · 2.84:1 */
  --slot-3:      #B0700A;   /* L .600 · 3.92:1 */
}
```

### 5.3 Colour tokens — dark

Same four hues, re-stepped for the dark surface and re-validated as a set (worst CVD ΔE 11.2 deutan, tritan 8.7, normal-vision 18.7, all ≥3:1 on `#151A26`). Declared under both the media query and the `data-theme` scope so a manual toggle wins either way.

```css
@media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) { /* …as below… */ } }
:root[data-theme="dark"] {
  color-scheme: dark;
  --page:        #0C0F18;
  --panel:       #151A26;
  --inset:       #10141E;

  --ink-900:     #F2F4F9;   /* 15.80:1 on panel */
  --ink-700:     #A8B0C2;   /*  7.99:1 */
  --ink-500:     #7A8398;   /*  4.58:1 */
  --ink-300:     #2A3142;
  --ink-200:     #222839;

  --brand:       #6B7AE4;   /* 4.58:1 · L .619 */
  --allow:       #27AD8B;   /* 6.16:1 · L .670 */
  --redact:      #C8841B;   /* 5.61:1 · L .668 */
  --deny:        #C23A52;   /* 3.33:1 · L .554 */
  --deny-text:   #E0697E;   /* 5.38:1 — the dark deny step is mark-safe, not text-safe */

  --brand-tint:  #242B48; --allow-tint: #183438;
  --redact-tint: #352D24; --deny-tint:  #34202E;

  /* ramp anchor flips: more spent = brighter */
  --slot-track:  #54401A;   /* L .385 */
  --slot-1:      #A07314;   /* L .586 · 4.10:1 */
  --slot-2:      #C8841B;   /* L .668 · 5.61:1 */
  --slot-3:      #DFA23F;   /* L .753 · 7.77:1 */
}
```

**One asymmetry, deliberate:** in light mode a chip's state word is set in its `*-text` hue; in dark mode chip labels are **ink-900** (`#F2F4F9`). The dark hue steps are bright enough that a 13px coloured label blooms under video compression; ink does not. Measured: `--redact` on its dark tint is 4.36:1, under the AA floor, which independently forces the same answer.

### 5.4 The categorical palette that does not exist

Naka ships **no 8-hue categorical palette.** Every colour above is status or brand.

This was a decision, not an omission. The only candidate for categorical encoding is entity type (NAME, PHONE, IN_AADHAAR, PAN, …), and colouring those would burn the identity channel on information the *label already carries*, while colliding with the status palette that has to stay unambiguous. Entity types get a table and a single-hue bar (§5.9). Fewer tokens, fewer collisions, nothing to validate, and the status colours never have to compete with a series colour for meaning.

### 5.5 Typography

**IBM Plex Sans · IBM Plex Sans Devanagari · IBM Plex Mono.** One superfamily, three scripts, matched metrics and colour.

The reason is subject matter, not taste: **the interface has to render Devanagari.** An Aadhaar card prints the holder's name in a regional script beside the English, and the PRD's tier-3 detector (§8) exists precisely to catch it. A UI that cannot set the string it just detected is a UI that cannot demo its own best feature. IBM Plex is the only free superfamily with a Devanagari cut whose metrics match its Latin, plus a mono sibling for the diff and the policy.

*Rejected:* **Inter** — no Devanagari, and it is the default every generated interface reaches for. **Noto Sans + Noto Sans Devanagari** — engineered to have no opinion; that is its purpose and it is the wrong purpose here. **Mukta** — excellent Indian-designed Devanagari, but no mono sibling and a warmer, friendlier tone that undersells an enforcement product.

**Scale** (1.25 modular, base 15):

| px / line-height | Weight | Use |
|---|---|---|
| 13 / 18 | 400 · 500 · 600 | **Floor.** Slot labels, table cells, gutter captions, badges |
| 15 / 22 | 400 · 500 | Body, table primary cells, mono code, placeholder tokens |
| 17 / 24 | 400 · 600 | Panel values, the banner line, substitution rows |
| 20 / 26 | 600 | Panel titles |
| 26 / 32 | 600 | Subject name |
| 48 / 48 | 700 | Hero figure. Proportional figures, `-0.02em` |

Tracking: `+0.01em` at 13px, `0` at 15–20px, `-0.01em` at 26px, `-0.02em` at 48px.
Figures: `font-variant-numeric: tabular-nums` **only** in table columns, latency values, and the spend strip's tooltips. Proportional everywhere else, and never on the hero figure.

**Three typographic bans.**

1. **No all-caps labels.** Not for eyebrows, not for column headers, not for chips. Sentence case throughout. The one exception is a literal system identifier — `IN_AADHAAR`, `[PHONE_2]`, `fetch_customer` — which is *data*, set in Plex Mono, and all-caps because the source string is.
2. **No monospace on labels.** Mono appears only on code, identifiers, placeholder tokens, tabular numerals and payload text. Mono-for-small-labels is decoration pretending to be precision.
3. **No middle-dot meta strings** (`Session · s-9f3a · analyst`). The header's metadata is three key/value stacks separated by 1px vertical rules — a real information structure, not a dot-joined string.

### 5.6 Spacing, radius, elevation

**Grid:** 4px base. Steps 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64. Panel padding 24. Column gutter 24. Feed row 36. Compact subject row 44. Header 56.

**Radius encodes hierarchy, and nothing else.**

| Radius | Applies to | Why |
|---|---|---|
| 0 | Table rows, page rules, diff panes, the structural grid | The register is ruled, not rounded |
| 3px | Chips, badges, meter slots, placeholder tokens, spend ticks | The data-mark radius — a slot *is* a bar |
| 6px | Panels | The only container radius |
| — | **No pills.** No `border-radius: 999px` anywhere | A squared chip reads as a stamp; a pill reads as a tag. Stamp is the brand |

**Elevation: there are no shadows.** A ledger has rules, not shadows. Depth is expressed by (a) a surface lightness step — `--page` → `--panel` → `--inset` — and (b) a 1px `--ink-300` ring. The **only** shadow in the product is on the one true overlay (the role selector's dropdown): `0 8px 24px rgba(16, 20, 31, 0.12)`.

This is the explicit rejection of the SaaS-card kit: no identical rounded cards, no uniform `rgba(0,0,0,.1)` drop shadow on everything, no gradient washes, and no card hover lift.

### 5.7 Iconography

**No icon library.** Seven glyphs, hand-drawn on a 16×16 grid with a uniform **2px stroke** and square caps, inlined as SVG.

Three reasons, in order: a library imports someone else's visual voice; seven glyphs is about forty lines of markup, so a dependency is pure cost; and library icons are drawn at 1.5px hairline, which smears at 1080p — a uniform 2px stroke does not.

| Glyph | Drawing | Means |
|---|---|---|
| Allow | filled disc, r=5 | Call authorised, nothing withheld |
| Redact | square with 45° hatch | Fields replaced with placeholders |
| Deny | square with a single 2px horizontal bar across it | The barrier down — the call never ran |
| Exhausted | filled square with a 3px vertical rule at its right edge | The gate closed |
| Rehydrate | square with an arrow returning into it from the right | Real value restored on the trusted side |
| Attachment | rectangle with a folded corner | A binary payload was normalised |
| Policy | square with a notch cut from one corner | A stamp. Opens the policy panel |

### 5.8 The hatch

The texture channel, doing the work hue cannot. Two densities:

```css
--hatch-solid: repeating-linear-gradient(45deg,
  transparent 0 3px,
  color-mix(in srgb, var(--redact) 34%, transparent) 3px 8px);   /* meter slots, glyphs */

--hatch-wash: repeating-linear-gradient(45deg,
  transparent 0 2px,
  color-mix(in srgb, var(--redact) 18%, transparent) 2px 8px);   /* behind text in the diff */
```

45° and its 135° mirror only — never horizontal or vertical, which read as gridlines. The 8px period gives a ~5.7px perpendicular spacing, 7.5 device px at capture scale: coarse enough to survive the encode, fine enough not to be a vestibular problem. Under `forced-colors` and in print the hatch is the *only* state channel, and it holds.

### 5.9 The one real chart

Everything else on screen is a meter, a strip, or a table. One actual chart earns its place, in the session summary at bottom-right:

**Entities found vs withheld, by type.** Horizontal stacked bars, ≤6 rows, sorted by total descending.

- 20px bar thickness, 4px rounded data-end at the right, **square at the baseline**.
- Two segments: *revealed* in `--ink-500` solid, *withheld* in `--redact` with `--hatch-solid`.
- **2px gap in the surface colour between the segments** — never a border drawn around them.
- Legend above (two series, so a legend is mandatory), plus the total direct-labelled at the tip of each bar. No number on every segment.
- **No axis, no gridlines.** With ≤6 rows all direct-labelled, gridlines are ink without information.
- Table twin: the audit table's `entities_found` / `entities_masked` columns already are it. Say so in the chart's caption so the WCAG-clean equivalent is discoverable.

---

## 6. Semantics of severity

### 6.1 Three chips and one condition

The four states in the brief are not four peers. Allowed, redacted and denied are **per-decision**; budget-exhausted is a **per-subject condition**. Encoding a condition as a fourth chip would put it in competition with the decision it causes. So:

| State | Hue | Shape channel | Luminance | Glyph | Label |
|---|---|---|---|---|---|
| **Allowed** | `--allow` teal-green | 3px solid left rule | mid (L .610) | filled disc | "Allowed" |
| **Redacted** | `--redact` ochre | 3px left rule + `--hatch-wash` field | mid (L .637) | hatched square | "Redacted" |
| **Denied** | `--deny` crimson | **5px** solid left rule (double weight) | dark (L .443) | barred square | "Denied" |
| **Rehydrated** | `--brand` indigo | 3px solid left rule | dark (L .471) | returning arrow | "Restored" |
| **Not scanned** | `--ink-500` neutral | 3px **dashed** outline, no fill | — | hollow square | "Not scanned" |
| **Budget exhausted** | *no hue* | **full-card luminance inversion** | — | closed gate | "Budget exhausted" |

**Chip anatomy:** left rule · 8px · 16px glyph · 6px · label at 13px/600 · 10px trailing pad · 3px radius · tint background at 10% (light) / 18% (dark).

### 6.2 How this survives colourblindness and compression

**Four independent channels, in order of robustness:**

1. **Shape.** Disc / hatched square / barred square / returning arrow / hollow dashed square. Discriminable in pure grayscale.
2. **Rule weight.** 3px vs 5px. Deny is the only 5px rule in the product.
3. **Texture.** Redacted is the only state with a hatch. Not-scanned is the only state with a dashed outline.
4. **Luminance.** The status colours were stepped for luminance separation as well as hue: deny sits at L .443 and allow at L .610, a gap of .167, which is why `deny ↔ allow` clears CVD ΔE 10.8 protan (a red/green pair — the hardest case in the set — and the reason both were re-stepped rather than hue-shifted).

Plus: **every chip carries its word.** There is no colour-only state anywhere in the product.

Red/green is never load-bearing. The deny hue is a dark crimson at 8.10:1 against the paper and the allow hue is a mid teal-green at 3.46:1 — a factor of 2.3 in contrast, and an OKLCH lightness gap of 0.167, before hue is considered at all. In a grayscale print of this interface, every state is still readable.

### 6.3 "Not scanned" — the state the brief did not ask for and the product needs

PRD §3 names the failure precisely: a base64 attachment passes straight through and the audit row reads "0 entities found." That is **not** the clean state — it is a blind spot wearing the clean state's clothes. Conflating them is the exact bug the product exists to fix, so the interface must not repeat it.

`Not scanned` is therefore a distinct state with a neutral hue, a hollow dashed outline and the label *"Not scanned — no extractor matched this payload."* It is the most honest thing in the UI and a judge who notices it will grade the submission up, not down.

---

## 7. Motion

### 7.1 Easings and the two rules

```css
--ease-out:  cubic-bezier(0.16, 1, 0.30, 1);   /* decisive settle — default */
--ease-hard: cubic-bezier(0.30, 0, 0.00, 1);   /* fast start, dead stop — the barrier */
--ease-soft: cubic-bezier(0.65, 0, 0.35, 1);   /* crossfades only */
```

**Rule one: nothing loops.** No pulse, no shimmer, no breathing glow, no idle animation of any kind. Every animation in this product is triggered by a state change and runs once. A looping element on a three-minute video steals attention eight times.

**Rule two: motion only where it shows what changed.** Entrances on every panel, hover lifts on every card, and staggered section reveals are the generated-page default and read as such.

### 7.2 What animates

| Event | Motion | Timing |
|---|---|---|
| Feed row enters | `translateY(-6px) → 0`, opacity 0 → 1 | 140 ms `--ease-out` |
| Spend tick appends | `scaleY(0.4) → 1` from the baseline | 120 ms `--ease-out` |
| Meter slot fills | width 0 → 100% of the slot; label fades in at +120 ms | 220 ms `--ease-out` |
| **The trip** | four-part sequence | 760 ms — see §2.4 |
| Placeholder tokens appear | `scale(0.96) → 1` + opacity, staggered 40 ms | 160 ms `--ease-out` |
| Connectors draw | `scaleX(0) → 1`, `transform-origin: left` | 200 ms `--ease-out` |
| Policy etag changes | crossfade + 3px brand rule wipes down the changed line | 200 / 300 ms |
| Focus subject changes | card content crossfade, **geometry does not move** | 120 ms `--ease-soft` |

### 7.3 What must not animate

- **Table reflow and column widths.** Ever. Column widths are fixed in `ch` units.
- **Numbers counting up.** A count-up on "2 of 3" is a gimmick that makes the number unreadable for its whole duration, and it misstates a discrete event as a continuous one.
- **Text colour tweening.** At the inversion the text colour swaps instantly at the 50% mark; tweening ink through mid-grey looks broken for 100 ms.
- **Skeleton shimmer.** See §8.2.
- **Anything on hover in the panels.** The video has no cursor (§11.3), so hover states are wasted work, and hover-lift on cards is the kit tell.

### 7.4 Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 1ms !important; transition-duration: 1ms !important; }
}
```

…with one deliberate addition: the trip becomes an instant state swap **plus a 1500 ms static banner**, so the event stays legible to someone who has turned motion off. A reduced-motion user must not lose the information the animation was carrying — they lose only the animation.

---

## 8. States

### 8.1 Nothing sensitive found — the common case, designed

This is the state that occurs on most calls and the one hackathon projects leave as a blank pane. Designing it well is cheap and disproportionately convincing.

**An empty diff must prove it looked.** So when a call returns zero entities, the Decision panel does *not* split into two panes. It shows one pane, the payload, plus a **proof strip** under it:

```
┌ What the tool returned ──────────────────────── ● Nothing sensitive found ┐
│  { "customer_id": "cust_2290", "tier": "gold", "opened": "2024-03-11" }   │
├───────────────────────────────────────────────────────────────────────────┤
│  Scanned 1,284 characters · checksum + comprehend · threshold 0.5         │
│  0 entities · ledger unchanged (1 of 3) · 41 ms                           │
└───────────────────────────────────────────────────────────────────────────┘
```

The proof strip names **what ran**, not just what was found — which is precisely the distinction between "clean" and "blind" (§6.3). For a normalised payload it also names the normalisation: `normalize: pdf → markdown (1 page) · textract`.

Copy: **"Nothing sensitive found."** Not "No PII detected" (system vocabulary), not "All clear" (overclaims), not an empty state illustration.

### 8.2 Loading

**No skeleton shimmer.** Two cases:

- **Refetch** (something is already rendered): hold the previous render at 60% opacity and run a 2px indeterminate rule under the panel header, 1.2 s cycle. No layout jump, no flash.
- **First load** (nothing to hold): static blocks at the *exact final geometry* in `--ink-200`. No animation at all. A shimmering skeleton animates for 400 ms and then is replaced — 400 ms of noise for zero information.

### 8.3 Empty — no session yet

The ledger panel holds two lines and one button. No illustration.

> **No calls yet.**
> Naka records every tool call a session makes, and what each one disclosed.
>
> `[ Run the demo session ]`

An empty screen is an invitation to act, so it contains the action. Under the button, a 13px line naming the fixtures that will run: *"Six calls against a seeded support ticket, including one scanned Aadhaar card."*

### 8.4 Error — control plane unreachable

This is a **designed state, not a failure**: PRD §5 requires failing closed to the packaged policy. So it is not a red toast that disappears. It is a persistent banner **inside the policy panel**:

> **Control plane unreachable.** Enforcing the packaged fallback policy (etag `pkg-1`). Decisions are still being made.
> `[ Retry fetch ]`

Deny-tinted, deny glyph, and it stays until the fetch succeeds. Presented this way it is a *feature on camera* rather than a bug.

Other errors, in the interface's voice, never apologising and never vague:

| Condition | Copy |
|---|---|
| Agent Lambda timeout | "The agent did not respond within 60 seconds. The session is unchanged." `[ Retry ]` |
| Payload over the Comprehend limit | "Payload exceeded 100 KB and was scanned in 3 chunks. Offsets are per chunk." |
| Multi-page PDF | "Only page 1 was extracted. Naka uses synchronous Textract, which reads one page." |

Banned strings: "Oops", "Something went wrong", "Please try again later", "Submit", "AI-powered", "seamless".

### 8.5 State matrix

| Region | Empty | Loading | Error | Nothing found |
|---|---|---|---|---|
| Ledger | Invitation + action | Static blocks | Subjects shown from last snapshot, banner in header | Meter unchanged; the strip is the empty state |
| Decision | "Select a call" + a hint to press `J` | Previous at 60% + progress rule | Inline message in the pane, payload still shown | Single pane + proof strip (§8.1) |
| Spend strip | Hidden entirely (not an empty track) | — | Ticks stay; new ones stop appending | Tick appends in `--allow` |
| Calls | Header row + one line: "Calls will appear here as the agent runs." | Rows at 60% | Last rows retained | Row with the allow chip |
| Policy | "No policy fetched." | Static block | The fallback banner (§8.4) | Collapsed reason line |

---

## 9. Accessibility baseline

### 9.1 Contrast — measured, not asserted

Every pairing that carries meaning was computed against the surface it actually renders on. Light mode: ink-900 17.76:1, ink-700 8.40:1, ink-500 4.64:1 (4.36:1 on the inset), brand 6.87:1, deny 8.10:1, allow 3.46:1, redact 3.42:1. All chip labels use the `*-text` variants and measure 5.11–6.77:1 on their own tints. Meter slot labels sit *below* the slot on the panel (17.76:1) rather than inside the fill, which is what keeps them AA at 13px. Dark mode: ink 15.80 / 7.99 / 4.58:1; brand 4.58:1; allow 6.16:1; redact 5.61:1; deny 3.33:1 as a mark with `--deny-text` at 5.38:1 for any state word.

Two colours sit between 3:1 and 4.5:1 (`--allow`, `--redact` in light). They are used **only as marks** — glyph fills, rules, slot fills — never as text, and every one is accompanied by a word. That is the relief condition, satisfied.

### 9.2 The meter's screen-reader story

`<meter>` is semantically right and unstylable in the ways this design needs; `role="progressbar"` is wrong because this is not progress. Use a group with an authored summary:

```
<section role="group" aria-labelledby="m-8814-h" aria-describedby="m-8814-s">
  <h3 id="m-8814-h">Disclosure budget, cust_8814</h3>
  <p id="m-8814-s" class="sr-only">
    3 of 3 identifying fields disclosed. Budget exhausted.
    Disclosed: name on call 1, phone on call 2, email address on call 4.
    Blocked: Aadhaar number on call 6.
  </p>
  <ol> <!-- one li per slot, each with its own text --> </ol>
</section>
```

An `aria-live="polite"` region announces **transitions only** — budget trips, denies, and restorations. It does **not** announce allows. Announcing every call makes the page unusable inside thirty seconds; announcing the exceptions is the whole point of the product.

### 9.3 The diff's screen-reader story

The visual diff's connectors are `aria-hidden` (they are decorative reinforcement of an index that is already in the text). Both panes are readable regions. The **substitutions list (§3.5) is the accessible primary** — a real, visible, focusable ordered list that states each mapping in words:

> ① Aadhaar number, redacted to placeholder IN\_AADHAAR\_1 by policy forbid-reveal-aadhaar-analyst.

Each detected span carries `aria-label` naming its entity type, its verdict and its index, so reading the left pane linearly still yields the verdicts. Placeholder tokens on the right carry `aria-label="placeholder IN_AADHAAR_1, replaces an Aadhaar number"`.

### 9.4 Focus order and keyboard

Tab order follows visual order: header controls → subject list → spend strip → diff panes → substitutions list → policy → calls table.

| Pattern | Behaviour |
|---|---|
| Subject list | Roving `tabindex`; `↑`/`↓` move, `Enter` focuses that subject |
| Spend strip | Single tab stop; `←`/`→` move between calls, `Enter` loads |
| Calls table | `role="grid"`; arrow keys move by cell, `Enter` opens the decision |
| Diff panes | `tabindex="0"` scroll regions with `aria-label` |
| `J` / `K` | Previous / next call — **works from anywhere** |
| `P` | Expand / collapse the policy |
| `A` | Expand / collapse the audit density |
| `R` | Reveal / mask the left pane source |

Those four single-key shortcuts exist for a reason beyond convenience: **they let the whole demo be driven from the keyboard, so the recording has no cursor in frame** (§11.3). Every one of them is also reachable by tab and Enter, so they are an accelerator rather than the only path.

**Focus ring:** `outline: 2px solid var(--brand); outline-offset: 2px;` — never removed, and the 2px offset in the surface colour is what keeps it visible on tinted chips and dark inverted cards alike. On the inverted (exhausted) card the ring switches to `--ink-900` light (`#F2F4F9`) to hold contrast.

**Never position-only.** The overflow slot is not conveyed by "it is past the line" — it carries the deny glyph and the word "Blocked".

### 9.5 Reduced motion, forced colors, print

Reduced motion per §7.4, with the static banner substitution. Under `forced-colors: active` all tints drop out and the hatch, the rule weights and the glyph shapes are the only state channels — which is why §6.2 has four channels rather than one. The same is true of a grayscale print of the audit table, which is a plausible artefact of a real compliance conversation.

---

## 10. Build guidance under a hard deadline

### 10.1 Stack

**Vite + React + TypeScript, one `tokens.css`, no UI kit, no chart library, no animation library.**

- **No UI kit.** There are six components. A kit's defaults would take longer to override than the components take to write, and overriding them is how a distinctive design becomes a themed default.
- **No chart library.** The meter is a flex row of divs. The spend strip is divs. The stacked bar is two divs and a gap. Recharts/visx would cost more in configuring away axes, legends, tooltips and margins than the marks cost to write.
- **No animation library.** The trip sequence is four CSS transitions orchestrated with `transition-delay`. Framer Motion is a 40 KB dependency for `transition-delay`.
- **Plain CSS with custom properties**, not a utility framework — because §5 *is* the stylesheet. Paste the token blocks into `tokens.css` and the visual system is done. (If the team already has Tailwind muscle memory, use it and put the tokens in `@theme`; the spec is stack-independent either way.)
- **Self-host the fonts.** Subset IBM Plex Sans 400/600, Plex Sans Devanagari 400/600 and Plex Mono 400 as woff2 into the Lambda zip. A Google Fonts request is a third-party dependency that can stall on venue wifi at the worst possible moment.

### 10.2 Build order (this is §11.1 step 9, expanded)

| # | Item | Budget | Note |
|---|---|---|---|
| 1 | `tokens.css` + the three-region layout shell | 30 min | **First.** Every screenshot from this moment on looks finished, which matters if you run out of time |
| 2 | The meter, including the trip | 90 min | It is the prize. Build it before anything reads real data — drive it from a hardcoded array first |
| 3 | The diff, from real Comprehend offsets | 90 min | See the traps below |
| 4 | The calls table at feed density | 45 min | |
| 5 | The policy panel, collapsed reason only | 30 min | Expanded view is 15 more minutes; do it only if beat 2:25 is still in the cut |
| 6 | The proof strip / nothing-found state | 20 min | Highest ratio of judge-impression to minutes in the list |
| 7 | Audit density, session summary chart | 40 min | Cut first if time runs out |
| 8 | Dark mode | 25 min | CSS only, if steps 1–6 are done. Put `data-theme` on `<html>` in step 1 so this stays a stylesheet change |

**Put `data-theme` on `<html>` from hour one even if you never build dark mode.** It costs one attribute and it is the difference between dark mode being a 25-minute stylesheet and a two-hour refactor.

### 10.3 What must be real

If a judge opens the repo and finds these hardcoded, the submission is over:

- The meter's counts and slot identities — they come from `ledger_before` / `ledger_after` in the audit row.
- The diff's spans and placeholder indices — from Comprehend offsets and the placeholder map's keys.
- The policy text and the etag.
- The latency values.

### 10.4 What can be faked, convincingly and honourably

- **The audit table's backing store.** Read a static JSON snapshot rather than paginating DynamoDB. It is on camera for four seconds. (Write the real DynamoDB row regardless — PRD §11 Must #8 — just don't build the query layer for the read path.)
- **The two-agent hot-reload beat.** Two browser tabs on the same UI with different `session_id`s. Zero new UI, and it is a *true* demonstration: they genuinely are two agents sharing one control plane.
- **Textract bounding boxes** (PRD §11 Should #13). Pre-render one recorded Textract response as a PNG overlay. Do **not** build a live PDF renderer.
- **The Devanagari string.** A fixture renders correctly through the font stack whether or not the Nova tier is live. The UI is right either way.
- **Empty/loading/error states.** Drive them from a query param (`?state=error`) so you can film them without breaking the backend. This is 10 minutes and it is how you film §8 at all.

### 10.5 Five traps that will eat hours

1. **Writing a diff algorithm.** There is no diff to compute — Comprehend returns offsets and the redactor already knows every span it replaced. Render from offsets. Reaching for Myers diff is three hours spent producing a *worse* result, because a text diff will align on the wrong boundaries when `9812 3456 7788` becomes `[IN_AADHAAR_1]`.
2. **Virtualised / infinite-scroll feed.** Cap at 50 rows with `overflow-y: auto`. Three hours saved, zero judged difference.
3. **A mobile layout.** One breakpoint at 1100px that stacks the three regions vertically and reorders meter → decision → calls. Twenty minutes. Anything beyond that is time spent on a viewport no judge will use.
4. **Chart library theming.** See §10.1. If someone has already installed Recharts by the time you read this, delete it rather than theme it.
5. **Building dark mode before light mode is finished.** The video is light. Dark is a nice-to-have that will silently consume an evening if it is allowed to start early.

---

## 11. Video direction

### 11.1 Capture setup, and the number that matters

Display at 1920×1080. Browser full-screen, **page zoom 133%**, giving a CSS viewport of ~1444×790. Record at 1920×1080, 60 fps, and export at 1080p.

Everything the design calls 13px renders at **17.3 device px**. Everything called 15px renders at 20. A 3px rule renders at 4. Those are the numbers the encoder has to hold, and they are the reason §0 sets a 13px floor and §6 puts state on 3px rules rather than 1px hairlines.

**Two hard rules that follow:**

- Nothing that carries meaning may be a 1px line. Structural hairlines (row separators, panel rings) at 1px are fine — they are structure, and losing them costs nothing.
- Keep all meaningful content inside a 5% inset — 96px at 1080p — clear of YouTube's player chrome and mobile cropping.

### 11.2 Beat sheet — what is on screen, per PRD §12

| Time | Beat | On screen | Highlighted | Not on screen |
|---|---|---|---|---|
| 0:00–0:15 | The scanned Aadhaar card | Full-frame document image, then a 400 ms cut to the console at rest | — | No UI chrome over the card |
| 0:15–0:35 | The gap, precisely | The AWS doc line as a full-frame still, 1.4× punch-in on the relevant sentence | The sentence, underlined in post | Do not cut to the console — the claim needs a clean frame |
| 0:35–1:10 | Three calls, meter fills | Full console. Feed rows append bottom; meter slots fill left | 1.3× punch-in on the ledger column at 0:52 | Policy panel stays collapsed |
| **1:10–1:40** | **The trip** | **1.6× punch-in on the focus card, centred on the budget rule.** The trip runs once, then hold 2 s on the inverted card, then pull back to full console | The banner line at 17px must be legible — this is the frame the whole submission rests on | Nothing. One object in frame |
| 1:40–2:05 | Rehydration | Diff panel, 1.4× on the right pane; the substitutions list shows the restored row | The `[IN_AADHAAR_1]` token and the "Restored" chip | Left pane stays masked here — the point is the model never held it |
| 2:05–2:25 | The PDF exhausts the budget in one call | Full console. Attachment glyph in the feed row; the meter fills three slots in one event | The proof strip's `normalize: pdf → markdown (1 page)` line | |
| 2:25–2:45 | Policy hot-reload, two agents | Split screen: two browser windows, policy panel expanded in both | The etag chip changing, and the `−`/`+` change strip | |
| 2:45–3:00 | Close | Full console at rest, inverted card still visible, URL overlaid bottom-centre | The URL at ≥40px | No logo animation, no music sting |

### 11.3 Six directions that are worth more than they cost

1. **Drive it from the keyboard. No cursor in frame.** `J`/`K`/`P`/`R` cover every action in the beat sheet. A cursor tracking across the screen is the single most amateur-looking thing in a software demo, and removing it costs four keybindings you were going to build anyway (§9.4).
2. **Punch in in post, never in the browser.** Zooming the page reflows the layout and the viewer loses their place. A post-production scale keeps the geometry fixed and the motion continuous.
3. **The trip runs exactly once, on a clean take.** Do not loop it, do not slow-motion it. 760 ms at 60 fps is 46 frames — enough. If you must, hold the *result* for 2 s rather than stretching the transition.
4. **Burn in captions for the claim lines.** YouTube's auto-captions will mangle "Aadhaar", "Cedar" and "Naka". The three lines worth burning: the banner at 1:10, the residency claim at 0:15, and the URL at 2:45.
5. **Talking-head overlay, if any, bottom-left only, and never over the meter or the diff.** Better: none.
6. **Thumbnail: the inverted card on the light field, 1280×720.** One dark block, one number, four words. It is the most distinctive frame the product can produce and it is legible at 120px wide in a results list.

### 11.4 The other two judged surfaces

The video is not the only place the UI is graded — the repo and the writeup are Best UI surfaces too.

- **README hero screenshot:** 1600×900, light mode, the console in the exhausted state with the diff loaded. **PNG, never JPEG** — JPEG's chroma subsampling does to the screenshot exactly what §0 spends this document avoiding.
- **Three more README screenshots**, in this order: the nothing-found proof strip, the policy panel expanded with its evaluated annotation, the audit table at audit density. That order tells the story *honest → explainable → auditable*, which is the story the writeup is making.
- **`og:image`:** the thumbnail from §11.3. It is what renders when the submission link is pasted into a judging channel.

---

## Appendix A — Copy deck

Every string below is final. They are short because each does one job.

| Where | String |
|---|---|
| Header | `Naka` · `Session` / `s-9f3a` · `Role` / `analyst` · `Policy` / `etag c4f1` |
| Panel titles | "Disclosure ledger" · "Decision" · "What the tool returned" · "What reached the model" · "Substitutions" · "Policy" · "Calls" |
| Meter, within budget | "2 of 3 fields disclosed" |
| Meter, exhausted | "3 of 3 fields disclosed. Budget exhausted." |
| Trip banner | "Budget exhausted for cust_8814. Identifying fields are now redacted, including fields that passed earlier." |
| Overflow slot | "Blocked" |
| Rehydration | "Placeholder IN_AADHAAR_1 was restored on the trusted side. The model never held this value." |
| Right pane tooltip | "The model's view. The original values are not available to this page." |
| Nothing found | "Nothing sensitive found." |
| Not scanned | "Not scanned — no extractor matched this payload." |
| Denied | "Call denied before it ran." |
| Empty ledger | "No calls yet." / "Naka records every tool call a session makes, and what each one disclosed." / `Run the demo session` |
| Empty decision | "Select a call. Press J." |
| Control plane down | "Control plane unreachable. Enforcing the packaged fallback policy (etag pkg-1). Decisions are still being made." / `Retry fetch` |
| Left pane badge | "Synthetic fixture" |
| Reveal control | `Reveal source` / `Mask source` |

Banned throughout: "Oops" · "Something went wrong" · "Please try again later" · "Submit" · "AI-powered" · "seamless" · "powerful" · "No PII detected" · "All clear" · any `→` inside button text.

---

## Appendix B — What was rejected, and why

| Rejected | In favour of | Reason |
|---|---|---|
| Dark console with a neon accent | Light "audited register" | The hero moment is a luminance inversion and needs a light base; the product is governance, not offence; light encodes better at 1080p; and the genre is what every competing submission will look like |
| Radial gauge for the meter | Segmented ledger strip | Continuous encoding for discrete data, weak perceptual channel, category cliché, and no room for per-slot identity |
| Continuous progress bar for the meter | Segmented ledger strip | Cannot express the denied-now beat — which the PRD calls the beat that wins it |
| Stacked bar by entity type for the meter | Segmented ledger strip | Segment size would encode count where the reader expects identity, and it needs categorical hues that collide with status |
| Tabbed console | One screen | Four tabs is ~6 s of a 180 s video, and it never puts the meter and the diff in frame together |
| Timeline-first layout | 24px spend strip | Puts sequence first when the claim is about the total |
| Inline unified diff | Side-by-side, span-locked | The pane headings are half the proof |
| Git-style red/green diff | Tint + hatch + index badge | Wrong model of the change (substitution, not insert/delete) and the exact red/green trap §6 exists to avoid |
| Bezier connectors between panes | Straight horizontal rules | A 1px diagonal curve is what chroma subsampling destroys |
| Eight-hue categorical palette | Status + brand only | Nothing in this product encodes identity by hue; the tokens would only collide with status |
| Inter | IBM Plex superfamily | No Devanagari cut, and it is the default |
| Noto Sans | IBM Plex superfamily | Engineered to have no opinion |
| Mukta | IBM Plex superfamily | No mono sibling; tone undersells an enforcement product |
| Icon library | Seven hand-drawn 2px glyphs | Imports another product's voice, and 1.5px library hairlines smear at 1080p |
| Card shadows | Surface steps + 1px rings | The SaaS-card tell; a ledger has rules, not shadows |
| Pills | 3px squared chips | A stamp, not a tag |
| All-caps eyebrow labels | Sentence case | The most common generated-page tell |
| Monospace for small labels | Mono for code and identifiers only | Decoration pretending to be precision |
| Skeleton shimmer | Held render at 60% / static blocks | 400 ms of animated noise carrying no information |
| Count-up on the hero figure | Instant value | Unreadable while it runs, and it misstates a discrete event |
| Separate feed and audit components | One component, two densities | Two builds, one judged second |
| Virtualised feed, real diff algorithm, live PDF renderer, mobile layout, chart library | Capped list, offset rendering, pre-rendered overlay, one breakpoint, divs | Each is hours for no judged difference |

---

## Appendix C — Validation record

The status palette was computed with the data-viz validator rather than chosen by eye. Runs, and results:

**Light, `--pairs all`, surface `#FAFBFD`** — `#12997A, #C77400, #9A1428, #3F4EB3`
Lightness band PASS (all within L 0.43–0.77) · Chroma floor PASS (all ≥ 0.10) · CVD separation PASS, worst all-pairs `#C77400 ↔ #12997A` ΔE 10.8 protan · Normal-vision floor PASS, worst ΔE 21.3 · Contrast PASS, all ≥ 3:1. **All checks pass.**

**Dark, `--pairs all`, surface `#151A26`** — `#27AD8B, #C8841B, #C23A52, #6B7AE4`
Lightness band PASS (all within L 0.48–0.67) · Chroma floor PASS · CVD separation PASS, worst all-pairs `#C23A52 ↔ #27AD8B` ΔE 11.2 deutan, tritan 8.7 · Normal-vision floor PASS, worst ΔE 18.7 · Contrast PASS. **All checks pass.**

The crimson was re-stepped twice: `#8C1022` failed the light lightness band at L 0.412, and the first dark candidate `#E5556B` collapsed against the teal at ΔE 6.3 deutan. Both were fixed by moving lightness and holding hue — which is also what produced the luminance separation §6.2 depends on. The meter's ochre ramp is monotone in L with adjacent ΔL ≥ 0.078 and a light end at 2.12:1, clearing the ordinal light-end floor of 2:1.

*Re-run `validate_palette.js` against any substituted hex before it ships. The numbers above are measurements, not opinions, and they stop being true the moment a value is nudged by eye.*
