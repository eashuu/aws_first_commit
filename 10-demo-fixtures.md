# Naka — Demo Fixtures and the Exact Demo Run

**Project name:** **Naka**. The rename is complete across every document, including the config keys in `08-technical-design.md` (`NAKA_KEY`, `naka_audit`, `X-Naka-Key`). Only the folder name and the `01`–`12` filenames retain the old spelling; cosmetic, and deliberately left until after submission.

**What this is:** the seeded data and the step-by-step call sequence the three-minute video is recorded against. Every identifier here has been computed and verified, not guessed. The verification commands are in §9.

**Companion docs:** PRD §6 (budget + Cedar), §8 (detection tiers), §10 (audit record), §12 (beat sheet); `08-technical-design.md` §1–§3.

---

## 0. Eight corrections this document makes to the specs above it

These were found while making the beat sheet and the policy agree. Each one silently breaks a beat if left.

| # | Where | Problem | Fix (applied below) |
|---|---|---|---|
| 1 | PRD §6.1 | `forbid reveal_PHONE when seen.containsAny(["NAME","IN_AADHAAR"])` denies the phone at **call 2**, because NAME is already in the ledger. PRD §12 requires the phone to be **green** at call 2. | Key the co-occurrence rule on `IN_AADHAAR` only. The call-4 deny is carried by the **budget-ceiling** rule, which is the beat PRD §12 actually describes. |
| 2 | PRD §6.1 / TD §3.4 | The ceiling `forbid(principal, action, resource)` is **unscoped on action**. Once the budget is spent it also denies `send_summary` — so the rehydration beat at 1:40 never runs. | Scope the ceiling to the `reveal_*` action set. |
| 3 | TD §1.8 | `FLOOR_RULES[1]` is a whole `when { … }` string. The corrected ceiling rule no longer contains it verbatim, so `floor_ok()` rejects Naka's own policy. | Change `FLOOR_RULES[1]` to the sub-expression `'context.session.seen_count >= context.session.budget'`. |
| 4 | PRD §12 2:25 | "Narrow the permit" produces a **default-deny**, which has no determining policy id — `deny_policy` is `null` and the UI has nothing to render. | The hot-reload edit **adds an explicit `forbid` with an `@id` and an `@advice`**, so the denial names and explains itself on camera. |
| 5 | TD §1.9 | `AuditRow.deny_policy` is a single field for the **Q1** decision. Q2's per-field policy ids (`FieldDecision.policy_id`) have **nowhere to go**, so the UI cannot say *why* a field was redacted — which is the Decision panel's whole job (UI spec §3). | Add `mask_policies: dict[str, str]` (entity type → policy id) to `AuditRow`. One field. |
| 6 | TD §2.2 step 18 | "`NAME`, `ADDRESS` allowed until the 3rd, then the ceiling rule denies" implies sequencing **inside** one `is_authorized_batch` call. It does not sequence: every request in the batch sees one pre-call snapshot. | State it: **the ceiling binds *between* calls, not mid-batch.** Fixtures are sized so the attachment lands on exactly 3/3 with no overshoot on camera. |
| 7 | TD §1.2 / §2.2 step 16 | Tier 3 sends an **image** to Bedrock (`ImageBlock.format` ∈ `png\|jpeg\|gif\|webp`). A PDF cannot be an image block, and there is no PDF rasterizer in the Lambda. | The Indic fixture ships as **PNG**, not PDF. The Must-item PDF stays Latin-only. |
| 8 | PRD §8 vs TD §1.3 | PRD: *"Write Verhoeff fresh… **Do not copy** the implementation that exists elsewhere on this machine — copied code with mismatched provenance disqualifies the whole team."* TD §1.3: *"Copy that function and its two tables **verbatim** from `detection-engine/recognizers/checksums.py`."* | **Direct contradiction, disqualification risk.** Resolve before writing `detect.py`. The tables in §2.2 below are the published D₅ tables and are not copyrightable; the twenty lines around them must be written during the event. |

Two tool-signature requirements the fixtures depend on, neither currently specified:

- **`fetch_customer(customer_id: str, field: str)`** — `field` ∈ `{"name","phone","email","address","kyc"}`. Without it, one call returns the whole record and the meter jumps 0→5 in one step; there is no three-call fill and no beat.
- **`DisclosureGuard.snapshot()` adds `dest`** when `tool_name == "send_summary"`, canonicalised from `tool_input["to"]`. Required by PRD §11.2 Must #5 (rehydration bound to an authorized destination).

---

## 1. The safety guarantee — read this before a judge asks

**A judge will ask "are those real Aadhaar numbers?" It is the single most likely hostile question in the Q&A.** The answer below takes eight seconds and ends the line of questioning.

### 1.1 Aadhaar — provably non-issuable, and still valid to the detector

> **Real Aadhaar numbers never begin with 0 or 1.** UIDAI reserves those leading digits, so the issued space is 2000 0000 0000 – 9999 9999 9999. Every Aadhaar number in these fixtures **begins with 0 or 1 and satisfies the Verhoeff check digit.** It is therefore simultaneously valid to any checksum-based detector — including ours, Presidio's `IN_AADHAAR` and Comprehend's — and guaranteed never to have been issued to a human being.

That is the whole answer. It is better than "we made them up", because "we made them up" invites *"so how do you know the detector fires?"* — and a random 12-digit string passes Verhoeff only ~10% of the time.

Print the line on the fixture file itself (§3) and on the PDF (§5) as a watermark, so it is on camera before it is asked.

### 1.2 PAN — the `0000` lever

There is no published unissued PAN block, and **the 10th-character check digit algorithm is deliberately unpublished by the Income Tax Department** — so a "checksum-valid but unissuable" PAN cannot be constructed the way an Aadhaar can. The available guarantee is the **sequence block**: characters 6–9 are a running sequence documented as **0001–9999**, so **`0000` is never allocated**.

Every PAN below is `XXX` + `P` (individual) + surname initial + **`0000`** + a letter. It matches `[A-Z]{5}[0-9]{4}[A-Z]`, passes the holder-type constraint that TD §1.3 says is "the difference between a PAN detector and a detector for any ten-character string", and cannot be anyone's PAN.

*Honest caveat, say it if pressed:* `0001–9999` is documented in secondary sources (Protean/NSDL explainers, Wikipedia), not in a primary ITD circular. The 10th character is arbitrary and unverifiable by anyone, including the detector. Naka's `pan_valid()` does not check it.

### 1.3 Phone — India has no 555, so the guarantee is structural

**Checked: India has no reserved fictitious-number range.** TRAI reserves `140xx` (promotional) and `1600xx` (BFSI/government transactional), but neither is a drama range. Wikipedia's *Fictitious telephone number* article has no India entry. The 2018 *Sacred Games* incident — a real number broadcast in a Netflix series, the holder harassed for months — is the proof of the absence, and is worth citing if a judge presses.

The available guarantee is the numbering plan itself: **Indian mobile numbers are 10 digits beginning with 6, 7, 8 or 9.** A 10-digit national number beginning with **5** is not an issuable mobile number.

Every phone below is `+91 555xx xxxxx` — leading digit 5 (structurally non-issuable) with a `555` head as a deliberate nod to the North American convention, so the intent reads instantly on screen.

> ⚠ **This is the highest-risk fixture in the set.** It is unverified whether Comprehend's `PHONE` recogniser fires on a `+91 5…` number, and the phone is the **headline beat** (PRD §12, 1:10–1:40 — *"the beat that wins it"*). **Pre-flight PF-5 is mandatory and blocking.** Contingency in §9.3.

### 1.4 Everything else

| Field | Guarantee | Strength |
|---|---|---|
| Email | `@example.com` — reserved for documentation by **RFC 2606**, can never be registered | Provable |
| Principal identities | `alice@example.com`, `ravi@example.com`, `priya@example.com` — same RFC 2606 basis. **Change TD's `alice@acme.com`: `acme.com` is a real registered domain.** | Provable |
| Destinations | `kyc-vault.internal`, `crm.internal`, `ops-notes.internal`, `notes.pastebin.example` — `.internal` is IANA-reserved for private use; `.example` is RFC 2606 | Provable |
| Names | Common Indian given/surname combinations; no attempt to match a real person | Not provable — say "synthetic", not "fictional" |
| Addresses | Real city + **real PIN code** + invented building/street. The real PIN is deliberate: a fake PIN measurably degrades Comprehend `ADDRESS` detection | Not provable. Say so. |
| Dates of birth | Synthetic, no reserved range exists | Not provable |

**The honest framing, if asked about names and addresses:** *"The two identifiers that can be proven non-issuable — Aadhaar and PAN — are constructed to be. A name and an address cannot be proven fictional by construction, so those are synthetic combinations attached to identifiers that provably belong to nobody."*

---

## 2. Verhoeff — the numbers, and the working

### 2.1 The four valid fixtures

All twelve digits. All begin with **0** or **1**. All verified `verhoeff_valid == True`.

| Subject | Aadhaar (raw) | As printed (card grouping) | Check digit | Lead |
|---|---|---|---|---|
| `cust_8814` Anil Kumar Rao | `048273915604` | `0482 7391 5604` | `4` | 0 ✅ |
| `cust_7326` Meera Nair | `163940582713` | `1639 4058 2713` | `3` | 1 ✅ |
| `cust_5501` Farhan Qureshi | `095713604829` | `0957 1360 4829` | `9` | 0 ✅ |
| `cust_2280` Sunita Deshpande | `137460298151` | `1374 6029 8151` | `1` | 1 ✅ |

### 2.2 The tables (published D₅ dihedral group — reproduce these exactly)

```python
# d — the D5 group multiplication table. d[j][k] = j * k
D = [[0,1,2,3,4,5,6,7,8,9],
     [1,2,3,4,0,6,7,8,9,5],
     [2,3,4,0,1,7,8,9,5,6],
     [3,4,0,1,2,8,9,5,6,7],
     [4,0,1,2,3,9,5,6,7,8],
     [5,9,8,7,6,0,4,3,2,1],
     [6,5,9,8,7,1,0,4,3,2],
     [7,6,5,9,8,2,1,0,4,3],
     [8,7,6,5,9,3,2,1,0,4],
     [9,8,7,6,5,4,3,2,1,0]]

# p — the permutation table, period 8. p[i % 8][digit]
P = [[0,1,2,3,4,5,6,7,8,9],
     [1,5,7,6,2,8,3,0,9,4],
     [5,8,0,3,7,9,6,1,4,2],
     [8,9,1,6,0,4,3,5,2,7],
     [9,4,5,3,1,2,6,8,7,0],
     [4,2,8,6,5,7,3,9,0,1],
     [2,7,9,3,8,0,6,4,1,5],
     [7,0,4,6,9,1,3,2,5,8]]

# inv — the multiplicative inverse in D5
INV = [0,4,3,2,1,5,6,7,8,9]
```

**Validate** (all 12 digits, right to left, `i` from 0):  `c = D[c][P[i % 8][digit]]`, valid iff `c == 0`.
**Generate** (11 digits, right to left, `i` from 0, note the `(i+1)`):  `c = D[c][P[(i+1) % 8][digit]]`, check digit `= INV[c]`.

### 2.3 Full working for `cust_8814` — verify this by hand

Payload `04827391560`, reversed `06519372840`.

| `i` | digit | P-row `(i+1)%8` | `P[row][digit]` | `c` before | `c` after = `D[c][·]` |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 1 | 0 | **1** |
| 1 | 6 | 2 | 6 | 1 | **7** |
| 2 | 5 | 3 | 4 | 7 | **8** |
| 3 | 1 | 4 | 4 | 8 | **9** |
| 4 | 9 | 5 | 1 | 9 | **8** |
| 5 | 3 | 6 | 3 | 8 | **5** |
| 6 | 7 | 7 | 2 | 5 | **8** |
| 7 | 2 | 0 | 2 | 8 | **6** |
| 8 | 8 | 1 | 9 | 6 | **2** |
| 9 | 4 | 2 | 7 | 2 | **9** |
| 10 | 0 | 3 | 8 | 9 | **1** |

Final `c = 1` → check digit `INV[1] = 4` → **`048273915604`**. Re-running the *validate* recurrence over all twelve digits returns `c = 0`. ✅

### 2.4 The invalid fixture — for the false-positive beat

| Value | Grouped | Verhoeff | Note |
|---|---|---|---|
| `163940582714` | `1639 4058 2714` | ❌ **False** | `cust_7326`'s number with the check digit **+1**. The hardest class of false positive: one digit from valid, and indistinguishable from an Aadhaar by regex alone. |

Used as `policy_ref` on `cust_2280`'s record (§3), so a single tool result contains one real-shaped-and-valid Aadhaar and one real-shaped-and-invalid twelve-digit string.

> **Conditional beat.** Tiers **union, never subtract** (PRD §8). Tier 1 rejecting this number does **not** stop Comprehend's `IN_AADHAAR` recogniser from flagging it, and whether Comprehend runs Verhoeff is unverified — **pre-flight PF-7**. Two narrations, pick after PF-7:
> - *Comprehend also rejects it:* "Two twelve-digit numbers. One is an Aadhaar. The checksum is what tells them apart — and it costs nothing and never leaves the process."
> - *Comprehend flags it:* "The managed detector can't tell these apart. Our checksum tier can — and because tiers only ever *add*, we still redact it. A false positive costs a redaction. A false negative costs a person."

> **On the OCR path this beat inverts, by design.** PRD §8: when `ocr_sourced=True`, a 12-digit run that *fails* Verhoeff still emits `IN_AADHAAR` at `score=0.45, ocr_derived=True`. So this same number is **ignored in JSON and flagged on a scan**. That is correct behaviour — checksum as a confidence signal, not a gate — and it is a better ten seconds than the plain version if there is room.

### 2.5 Properties verified on all four fixtures

| Check | Result | What a failure means |
|---|---|---|
| `verhoeff_valid(n)` | ✅ True, all four | — |
| Independent generation (brute-force over `validate`, never touching `INV`) agrees with the `INV` path | ✅ all four | A transposed `INV` table |
| Published vector: check digit of `236` is `3` | ✅ | Wrong `D` or `P` orientation |
| All 12 × 9 = 108 single-digit mutations rejected | ✅ 0 pass | A truncated `P` table |
| **All 11 adjacent-pair transpositions rejected** | ✅ 0 pass | **A Luhn implementation mislabelled as Verhoeff.** This is the discriminating assertion (PRD §8, TD §9.1). |
| Leading zero survives (`048273915604`) | ✅ | An `int(number)` anywhere in the path |
| Grouped form `0482 7391 5604` validates after digit-stripping | ✅ | The caller forgetting `only_digits()` — TD §9.1 puts that job on the caller |

---

## 3. The customer records

`fixtures/customers.json`. Four subjects. The first (`cust_8814`) drives the main sequence; the budget of 3 trips on its fourth disclosure.

```json
{
  "_SAFETY": "SYNTHETIC DATA. Every Aadhaar begins with 0 or 1 - a range UIDAI never issues - and satisfies the Verhoeff check digit, so it is valid to any detector and belongs to nobody. Every PAN uses sequence 0000, which is never allocated. Every phone is a 10-digit national number beginning with 5, which India never allocates to mobile. Emails and domains are RFC 2606 / IANA reserved.",

  "cust_8814": {
    "customer_id": "cust_8814",
    "name":    "Anil Kumar Rao",
    "phone":   "+91 55501 84412",
    "email":   "anil.rao@example.com",
    "address": "Flat 4B, Nandini Residency, 12 Sarjapur Cross Road, Bengaluru, Karnataka 560102",
    "dob":     "14/08/1987",
    "kyc": {
      "aadhaar": "0482 7391 5604",
      "name":    "Anil Kumar Rao",
      "phone":   "+91 55501 84412",
      "pan":     "AZKPR0000M"
    }
  },

  "cust_7326": {
    "customer_id": "cust_7326",
    "name":    "Meera Nair",
    "phone":   "+91 55502 37169",
    "email":   "meera.nair@example.com",
    "address": "27/3 Kadavanthra Lane, Panampilly Nagar, Kochi, Kerala 682036",
    "dob":     "02/11/1992",
    "kyc": {
      "aadhaar": "1639 4058 2713",
      "name":    "Meera Nair",
      "phone":   "+91 55502 37169",
      "pan":     "BQTPN0000K"
    }
  },

  "cust_5501": {
    "customer_id": "cust_5501",
    "name":    "Farhan Qureshi",
    "phone":   "+91 55503 66057",
    "email":   "farhan.qureshi@example.com",
    "address": "H.No. 8-2-119, Tulip Enclave, Road No. 5, Banjara Hills, Hyderabad, Telangana 500034",
    "dob":     "30/05/1984",
    "kyc": {
      "aadhaar": "0957 1360 4829",
      "name":    "Farhan Qureshi",
      "phone":   "+91 55503 66057",
      "pan":     "CLMPQ0000J"
    }
  },

  "cust_2280": {
    "customer_id": "cust_2280",
    "name":    "Sunita Deshpande",
    "phone":   "+91 55504 91283",
    "email":   "sunita.deshpande@example.com",
    "address": "Plot 61, Aster Society, Baner Road, Pune, Maharashtra 411045",
    "dob":     "19/03/1979",
    "kyc": {
      "aadhaar":    "1374 6029 8151",
      "policy_ref": "1639 4058 2714",
      "name":       "Sunita Deshpande",
      "phone":      "+91 55504 91283",
      "pan":        "DXVPD0000F"
    }
  }
}
```

### 3.1 Field ordering inside `kyc` is load-bearing

Placeholder ordinals are assigned in **ascending source-offset order** (see §4.4), so `aadhaar` first yields **`[IN_AADHAAR_1_<nonce>]`** — the exact token PRD §6.2 and TD §3.3 both print, and the shortest, most legible token on screen. Do not reorder these keys.

### 3.2 PAN construction, per fixture

| PAN | 1–3 | 4 (holder) | 5 (surname initial) | 6–9 (sequence) | 10 |
|---|---|---|---|---|---|
| `AZKPR0000M` | `AZK` | **`P`** = individual | `R` = **R**ao | **`0000`** never issued | `M` arbitrary |
| `BQTPN0000K` | `BQT` | `P` | `N` = **N**air | `0000` | `K` |
| `CLMPQ0000J` | `CLM` | `P` | `Q` = **Q**ureshi | `0000` | `J` |
| `DXVPD0000F` | `DXV` | `P` | `D` = **D**eshpande | `0000` | `F` |

All four verified against `^[A-Z]{5}[0-9]{4}[A-Z]$` with char 4 ∈ `{P,C,H,F,A,T,B,L,J,G}` and char 4 == `P`.

### 3.3 Tickets

`fixtures/tickets.json`:

```json
{
  "tkt_4471": { "ticket_id": "tkt_4471", "subject": "KYC re-verification - name mismatch",
                "attachment": "kyc-sheet-tkt-4471.pdf", "media_type": "application/pdf" },
  "tkt_4472": { "ticket_id": "tkt_4472", "subject": "KYC re-verification - regional script",
                "attachment": "kyc-sheet-tkt-4472.png", "media_type": "image/png" }
}
```

`tkt_4471` is the Must-item PDF (§5). `tkt_4472` is the same page as PNG, carrying the Devanagari line, for the Should-item Indic beat.

**`tkt_4471` and `tkt_4472` are their own data subjects.** Attribution is `SUBJECT_KEYS = ("customer_id","subject_id","ticket_id","account_id")` in order (TD §1.4) — `read_attachment(ticket_id=…)` has no `customer_id`, so the subject is the ticket. Each therefore gets a fresh budget of 3, which is exactly what the 2:05 beat needs, and it means the PDF beat can stay inside session A without disturbing `cust_8814`'s full meter.

---

## 4. The Cedar policy, complete

`agent.cedar`, baked into the zip as the fallback and served by the control plane as `bundle.cedar`.

### 4.1 Vocabulary

| | Values |
|---|---|
| Principals | `User::"alice@example.com"`, `User::"ravi@example.com"`, `User::"priya@example.com"` |
| Q1 actions (may the call happen) | `fetch_customer`, `read_attachment`, `send_summary` |
| Q1 resource | `Resource::"agent"` — static, per TD §2.1 step 7 |
| Q2 actions (may this field be learned) | `reveal_NAME`, `reveal_PHONE`, `reveal_EMAIL`, `reveal_ADDRESS`, `reveal_DATE_TIME`, `reveal_IN_AADHAAR`, `reveal_IN_PERMANENT_ACCOUNT_NUMBER` |
| Q2 resource | `Subject::"cust_8814"` — the **data subject** is the resource, per TD §1.7 |
| Q3 actions (may this value be restored into an outbound argument) | `rehydrate_<TYPE>` for the same type set |
| Q3 resource | `Destination::"kyc-vault.internal"` etc. |
| Roles | `analyst` (budget 3), `compliance` (budget 9999) |

`entities` stays `[]` and `schema` is omitted (PRD §2.1). Entity UIDs are compared with `==` only — never `in` — so nothing needs to exist in the store.

### 4.2 The file

```cedar
// ===========================================================================
// Naka - agent.cedar
// Q1  may this call happen?           action = the tool name
// Q2  may this principal learn this field about this subject, given the ledger?
// Q3  may this value be restored into an outbound tool argument?
//
// Cedar has no set cardinality operator. context.session.seen_count is a Long
// computed in Python by DisclosureGuard.snapshot() and injected per call.
//
// forbid ALWAYS beats permit. Every forbid below is therefore scoped on
// role == "analyst", or the compliance exemption cannot work. (TD s9.5)
// ===========================================================================

// --- Q1 -------------------------------------------------------------------

@id("q1_fetch_customer")
permit(principal, action == Action::"fetch_customer", resource)
when {
  context.session has role &&
  (context.session.role == "analyst" || context.session.role == "compliance")
};

@id("q1_read_attachment")
@advice("Attachments may be opened by analysts and by compliance.")
permit(principal, action == Action::"read_attachment", resource)
when {
  context.session has role &&
  (context.session.role == "analyst" || context.session.role == "compliance")
};

@id("q1_send_summary")
permit(principal, action == Action::"send_summary", resource)
when {
  context.session has role &&
  (context.session.role == "analyst" || context.session.role == "compliance")
};

// --- Q2: the baseline permit ---------------------------------------------

@id("q2_reveal_baseline")
permit(principal,
       action in [Action::"reveal_NAME", Action::"reveal_PHONE",
                  Action::"reveal_EMAIL", Action::"reveal_ADDRESS",
                  Action::"reveal_DATE_TIME", Action::"reveal_IN_AADHAAR",
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER"],
       resource)
when { context.session has role };

// --- Q2: the three forbids that do the work ------------------------------

// Absolute. An analyst never sees an Aadhaar, whatever the ledger says.
// (First FLOOR_RULES string must match this head line verbatim.)
@id("q2_forbid_aadhaar_analyst")
@advice("Aadhaar Act s.29(4) bars public display of an Aadhaar number; UIDAI guidance permits at most the last four digits.")
forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)
when {
  context.session has role && context.session.role == "analyst"
};

// Co-occurrence. A phone number beside an Aadhaar re-identifies. One or the
// other, never both, for the same subject in the same session.
// NOTE: keyed on IN_AADHAAR only - see s0 correction 1. Adding "NAME" here
// denies the phone at call 2 and destroys the PRD s12 beat sheet.
@id("q2_forbid_phone_after_aadhaar")
@advice("A phone number is withheld once an Aadhaar has been disclosed for this data subject.")
forbid(principal, action == Action::"reveal_PHONE", resource)
when {
  context.session has role && context.session.role == "analyst" &&
  context.session has seen &&
  context.session.seen.containsAny(["IN_AADHAAR"])
};

// The ceiling. Three identifying fields about one subject, per session.
// Scoped to reveal_* - see s0 correction 2. An unscoped forbid here also
// denies send_summary and kills the rehydration beat.
@id("q2_forbid_budget_exhausted")
@advice("The disclosure budget for this data subject is spent. Golle (2006) re-identified 63% of the US population from three quasi-identifiers; Sweeney (2000) found 87%.")
forbid(principal,
       action in [Action::"reveal_NAME", Action::"reveal_PHONE",
                  Action::"reveal_EMAIL", Action::"reveal_ADDRESS",
                  Action::"reveal_DATE_TIME", Action::"reveal_IN_AADHAAR",
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER"],
       resource)
when {
  context.session has role && context.session.role == "analyst" &&
  context.session has seen_count && context.session has budget &&
  context.session.seen_count >= context.session.budget
};

// --- Q3: rehydration is a policy question, not a substitution -------------
// PRD s11.2: without this, the guardrail is an exfiltration primitive.
// Cedar is default-deny, so every destination not named here is refused and
// the placeholder stays a placeholder. No forbid needed.

@id("q3_rehydrate_aadhaar_kyc_vault_only")
@advice("An Aadhaar may be restored only into the KYC vault.")
permit(principal,
       action == Action::"rehydrate_IN_AADHAAR",
       resource == Destination::"kyc-vault.internal");

@id("q3_rehydrate_other_internal")
permit(principal,
       action in [Action::"rehydrate_NAME", Action::"rehydrate_PHONE",
                  Action::"rehydrate_EMAIL", Action::"rehydrate_ADDRESS",
                  Action::"rehydrate_DATE_TIME",
                  Action::"rehydrate_IN_PERMANENT_ACCOUNT_NUMBER"],
       resource)
when {
  resource == Destination::"kyc-vault.internal" ||
  resource == Destination::"crm.internal"
};

// --- The compliance exemption --------------------------------------------
// Scoped to Q1 + Q2 only. TD s3.4 writes this unscoped, which would also
// exempt compliance from the destination rule and re-open the exfiltration
// hole for the one role that handles the most sensitive data.

@id("q2_permit_compliance")
@advice("Compliance review is exempt from the per-subject disclosure budget. Rehydration destinations still apply.")
permit(principal,
       action in [Action::"fetch_customer", Action::"read_attachment",
                  Action::"send_summary",
                  Action::"reveal_NAME", Action::"reveal_PHONE",
                  Action::"reveal_EMAIL", Action::"reveal_ADDRESS",
                  Action::"reveal_DATE_TIME", Action::"reveal_IN_AADHAAR",
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER"],
       resource)
when { context.session has role && context.session.role == "compliance" };
```

### 4.3 The bundle

```json
{
  "version": "2026-09-20T09:14:03Z",
  "cedar": "<the file above, escaped>",
  "entities": [],
  "budget": { "default": 3, "per_role": { "analyst": 3, "compliance": 9999 } },
  "session_ceiling": 25,
  "identifying_types": ["NAME","PHONE","EMAIL","ADDRESS","DATE_TIME",
                        "IN_AADHAAR","IN_PERMANENT_ACCOUNT_NUMBER",
                        "IN_VOTER_NUMBER","IN_NREGA","CREDIT_DEBIT_NUMBER","AGE"],
  "thresholds": { "comprehend_min_score": 0.5 }
}
```

And the one-line change to `policy.py` (§0 correction 3):

```python
FLOOR_RULES: tuple[str, ...] = (
    'forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)',
    'context.session.seen_count >= context.session.budget',
)
```

### 4.4 Two semantics the fixtures depend on

**Only revealed fields spend.** `ledger.spend()` is called with `revealed_types & identifying_types`. A field that was *detected and masked* never enters `seen` — otherwise the redaction that protected the subject would itself spend the budget, and the meter would be wrong on camera (TD §9.4).

**Placeholder ordinals are assigned left-to-right; replacement is applied right-to-left.** Two phases. Mint every token in ascending `begin` order so the token numbering matches reading order on screen, then apply the substitutions in descending `begin` order so the offsets stay valid (TD §9.2). Without the split, the first entity in the document gets the highest ordinal and the diff reads backwards.

---

## 5. The single-page document

### 5.1 What it is — and what it deliberately is not

**Not a replica of an Aadhaar card.** Reproducing the UIDAI card layout on a public video is an avoidable trademark and impersonation problem, and it makes the "are these real?" question *harder*. The fixture is an internal **KYC verification sheet**, watermarked `SPECIMEN — SYNTHETIC DATA`, which carries the same demo payload (name, address, DOB, Aadhaar on one OCR'd page) and answers the safety question in frame, without being asked.

Two exports of one HTML source:

| File | Format | Ticket | Purpose |
|---|---|---|---|
| `kyc-sheet-tkt-4471.pdf` | single-page PDF, A4, Latin only | `tkt_4471` | PRD §11 Must #2 and the 2:05 beat. Textract + Comprehend + bounding boxes. |
| `kyc-sheet-tkt-4472.png` | PNG, same page + one Devanagari line | `tkt_4472` | Should item 11, the Indic beat. **PNG because Bedrock `ImageBlock.format` is `png\|jpeg\|gif\|webp` and there is no PDF rasterizer in the Lambda** (§0 correction 7). |

### 5.2 Exact content and layout

A4 portrait, 210 × 297 mm, one page. Normalised bbox targets are for sanity-checking the Textract overlay (Should item 13); ±0.03 is fine.

| Block | Text (verbatim) | Position | Target bbox `L, T` |
|---|---|---|---|
| Header rule | `CUSTOMER ONBOARDING — KYC VERIFICATION SHEET` | top, centred, 14pt bold, letter-spaced | `0.18, 0.06` |
| Sub-header | `Internal use only · Form KV-2 · Rev 3` | under header, 9pt grey | `0.32, 0.10` |
| Watermark | `SPECIMEN — SYNTHETIC DATA` | 45° diagonal across the page, 48pt, 12% grey | centred |
| Field 1 | `Applicant Name:  Meera Nair` | left column, 12pt | `0.10, 0.24` |
| Field 2 | `Date of Birth:  02/11/1992` | left column | `0.10, 0.30` |
| Field 3 | `Residential Address:  27/3 Kadavanthra Lane,` | left column, wraps to 2 lines | `0.10, 0.36` |
| Field 3b | `Panampilly Nagar, Kochi, Kerala 682036` | continuation | `0.24, 0.40` |
| **Field 4** | **`Aadhaar Number:  1639 4058 2713`** | left column, 13pt **monospace** | **`0.10, 0.50`** |
| Field 5 | `Verification Status:  Pending officer review` | left column | `0.10, 0.56` |
| Indic line (PNG only) | `नाम: मीरा नायर` | directly under Field 1, 12pt IBM Plex Sans Devanagari | `0.10, 0.27` |
| Footer | `Generated for Naka demo. No real person's data appears on this sheet. The Aadhaar number above begins with 1 — a range UIDAI never issues — and satisfies the Verhoeff check digit.` | bottom, 8pt, full width | `0.10, 0.92` |

**Nothing else on the page.** Specifically: **no phone number and no PAN.** The budget arithmetic depends on it — see §5.4.

Use **monospace for the Aadhaar line**. Proportional digits at OCR resolution produce character-merge errors, and a single misread digit flips the fixture from `checksum, score 1.0` to `ocr_derived, score 0.45`, which changes the audit row on camera.

### 5.3 How to produce it

Laziest path that works, no new dependencies:

1. Write `fixtures/kyc-sheet.html` with the content above. `@page { size: A4; margin: 0 }`, absolute-positioned blocks, the watermark as a rotated `div` with `opacity: .12`.
2. Open in Chrome → **Ctrl+P** → Destination **Save as PDF**, Paper **A4**, Margins **None**, **Background graphics ON** (or the watermark and the rules vanish). Save as `kyc-sheet-tkt-4471.pdf`.
3. For the PNG: add the Devanagari line, then Chrome DevTools → Ctrl+Shift+P → **Capture full size screenshot** at 1240 × 1754 (A4 @ 150 dpi). Save as `kyc-sheet-tkt-4472.png`.

Optional "scanned" look, entirely cosmetic — a 0.8° rotation and a `#f7f6f2` page background in CSS gets it with zero tooling. If real raster artefacts are wanted and poppler is installed: `pdftoppm -r 200 -png in.pdf p && img2pdf p-1.png -o out.pdf`. Not required: TD §1.2 sends **every** PDF to Textract regardless of text layer, so `ocr_sourced=True` either way.

4. Verify page count before anything else: `pdfinfo kyc-sheet-tkt-4471.pdf | grep Pages` must read **`Pages: 1`**. A 2-page PDF produces `NormalizeError("multipage")` and the whole document is withheld — correct behaviour, dead beat.

### 5.4 What the page yields, and why exactly three

| Detected | Tier | Q2 (analyst, `seen=[]`, `seen_count=0`, budget 3) |
|---|---|---|
| `IN_AADHAAR` `1639 4058 2713` | 1 — checksum, score 1.0 | **DENY** — `q2_forbid_aadhaar_analyst` |
| `NAME` `Meera Nair` | 2 — Comprehend | ALLOW |
| `ADDRESS` `27/3 Kadavanthra Lane, … 682036` | 2 — Comprehend | ALLOW |
| `DATE_TIME` `02/11/1992` | 2 — Comprehend | ALLOW |

Three revealed → **meter 0 → 3/3 in a single call**, which is the 2:05 beat verbatim. One masked.

**This is why there is no phone and no PAN on the page.** A `PHONE` or an `IN_PERMANENT_ACCOUNT_NUMBER` would also be allowed (no forbid covers PAN), making four or five revealed against a budget of three. Because the batch shares one pre-call snapshot (§0 correction 6), the ceiling would *not* catch them mid-batch — the meter would render 5/3 on camera and the first question in Q&A would be about overshoot instead of about the product.

*If asked anyway, the honest answer is ready:* **"The budget binds between calls, not inside one. A single call is atomic — we evaluate it against the ledger as it stood before the call. A call that carries ten identifying fields overshoots, and the session ceiling is the backstop. Per-hop capping is the next thing we'd build."*

### 5.5 The Devanagari line — what actually happens

> **Textract OCR is Latin-script only. It will not read `नाम: मीरा नायर`.** That is not a limitation we are working around; it is the claim.

On the **PDF** (`tkt_4471`), the Devanagari is absent from the fixture entirely, so nothing is hoped for and nothing fails.

On the **PNG** (`tkt_4472`), the same page carries the line, and the demo is a controlled A/B on one config flag:

| Run | `INDIC_ENABLED` | `detector_tiers` | `entities_found.NAME` |
|---|---|---|---|
| A | `false` | `["checksum","comprehend"]` | **1** — the English name only |
| B | `true` | `["checksum","comprehend","indic"]` | **2** — English + Devanagari |

Same document, one flag, and the gap is a **number in the audit row** rather than an assertion. That is the strongest available version of PRD §4 claim 3, and it costs one extra call.

**Unverified, and it must be checked before recording (PF-8):** whether Nova Pro returns the Devanagari substring at demo quality, and whether it returns it byte-identically so `str.find()` locates it. PRD open question 4 says demote the Indic tier to Should if it does not. `str.find()` returning `-1` drops the finding silently — **if run B shows `NAME: 1`, the tier is not working, it is not a rendering problem.** Contingency: cut the beat, set `INDIC_ENABLED=false`, and make the claim in the writeup with the Textract documentation line as the evidence. It is still true.

---

## 6. The exact call sequence

**Session A** `s-naka-demo-a` · principal `User::"alice@example.com"` · role `analyst` · budget 3 · `session_ceiling` 25.
**Session B** `s-naka-demo-b` · principal `User::"ravi@example.com"` · role `analyst` — exists only for the 2:25 two-agent beat.
**Session C** `s-naka-demo-c` · principal `User::"priya@example.com"` · role `compliance` — optional.

`<n>` below is the per-invocation vault nonce (`secrets.token_hex(2)`), e.g. `7f3a`. It changes every HTTP turn; that is the point (TD §1.5).

### Beat 0:00–0:35 — no calls

`kyc-sheet-tkt-4471.pdf` on screen. Then the gap slide: the AgentCore Policy doc line ("decides *whether* a call happens") and the Bedrock Guardrails sensitive-information-filter page showing no Indian entity types and no tool-field scope.

---

### Beat 0:35–1:10 — three calls, the meter fills

#### Call 1 — NAME

```json
POST {AGENT_URL}/
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "What name is on record for customer cust_8814?" }
```

| | |
|---|---|
| Tool | `fetch_customer(customer_id="cust_8814", field="name")` |
| Returns | `{"customer_id":"cust_8814","name":"Anil Kumar Rao"}` |
| `normalize()` | `application/json` → `customer_id: cust_8814\nname: Anil Kumar Rao` |
| Detector tier | **2 — Comprehend.** `NAME` @ ~0.93. Tier 1 finds nothing. |
| `attribute()` | → `cust_8814` (from `customer_id`) |
| Q1 snapshot | `{role:"analyst", subject:"cust_8814", seen:[], seen_count:0, budget:3, session_total:0, session_ceiling:25}` |
| Q1 | `fetch_customer` → **ALLOW** `q1_fetch_customer` |
| Q2 batch | 1 request. `reveal_NAME` / `Subject::"cust_8814"` → **ALLOW** `q2_reveal_baseline`. No forbid matches: not Aadhaar, `seen` has no `IN_AADHAAR`, `0 >= 3` is false. |
| Ledger | `before: []` → `after: ["NAME"]` |
| Audit | `entities_found {NAME:1}` · `entities_masked {}` · `entities_revealed {NAME:1}` · `outcome "ok"` |
| **Viewer sees** | Meter slot 1 fills, label `NAME · call 1`. Meter reads **1 / 3**. Spend strip gains one green tick. Decision panel shows **one** pane plus the proof strip (UI spec §6: an empty diff must prove it looked) — `1 entity found · 1 released · 0 withheld`. |

#### Call 2 — PHONE (the field that gets retroactively denied at call 4)

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "And the contact number for cust_8814?" }
```

| | |
|---|---|
| Tool | `fetch_customer(customer_id="cust_8814", field="phone")` |
| Returns | `{"customer_id":"cust_8814","phone":"+91 55501 84412"}` |
| Detector tier | **2 — Comprehend.** `PHONE`. ⚠ **PF-5 gates this.** |
| Q2 snapshot | `{role:"analyst", subject:"cust_8814", seen:["NAME"], seen_count:1, budget:3}` |
| Q2 | `reveal_PHONE` → **ALLOW**. `q2_forbid_phone_after_aadhaar` does **not** fire — `seen` holds `NAME`, not `IN_AADHAAR`. `1 >= 3` is false. |
| Ledger | `["NAME"]` → `["NAME","PHONE"]` |
| **Viewer sees** | Slot 2 fills, `PHONE · call 2`. Meter **2 / 3**. |

> **Narrate here, not later:** *"Each of these is individually fine. Nothing so far would trip any per-call guardrail on the market — and that is the point."*

#### Call 3 — ADDRESS, the meter fills

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "What address do we have for cust_8814?" }
```

| | |
|---|---|
| Tool | `fetch_customer(customer_id="cust_8814", field="address")` |
| Returns | `{"customer_id":"cust_8814","address":"Flat 4B, Nandini Residency, 12 Sarjapur Cross Road, Bengaluru, Karnataka 560102"}` |
| Detector tier | **2 — Comprehend.** `ADDRESS`. |
| Q2 snapshot | `seen:["NAME","PHONE"], seen_count:2, budget:3` |
| Q2 | `reveal_ADDRESS` → **ALLOW**. `2 >= 3` is false. |
| Ledger | `["NAME","PHONE"]` → `["ADDRESS","NAME","PHONE"]` (sorted, TD §1.1) |
| **Viewer sees** | Slot 3 fills. Meter **3 / 3, full**. The meter's threshold mark is reached but not crossed — amber, not red. Nothing has been denied yet. |

---

### Beat 1:10–1:40 — call 4, the beat that wins it

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "Pull the full KYC record for cust_8814. Post the Aadhaar to my scratch pad at notes.pastebin.example, then file it with kyc-vault.internal." }
```

> ⚠ **Calls 4, 5 and 6 must land in this one HTTP turn.** The vault is per-invocation and cleared in a `finally:` (TD §1.5, PRD §6.2). A placeholder minted in turn 4 does not resolve in turn 5 — it fails closed with `Deny`, correctly, and the rehydration beat is dead. **PF-9 is blocking.**

#### Call 4 — `fetch_customer(customer_id="cust_8814", field="kyc")`

Returns, in this key order (§3.1):

```json
{ "customer_id": "cust_8814",
  "aadhaar": "0482 7391 5604",
  "name": "Anil Kumar Rao",
  "phone": "+91 55501 84412",
  "pan": "AZKPR0000M" }
```

| | |
|---|---|
| Detector tiers | **1 — checksum:** `IN_AADHAAR` @ 1.0 (Verhoeff passes), `IN_PERMANENT_ACCOUNT_NUMBER` @ 1.0 (regex + holder-type `P`). **2 — Comprehend:** `NAME`, `PHONE`. `merge()` → 4 distinct types. |
| Q2 snapshot | `{role:"analyst", subject:"cust_8814", seen:["ADDRESS","NAME","PHONE"], seen_count:3, budget:3}` |

Q2 batch — 4 requests, one `is_authorized_batch` call, all against `Subject::"cust_8814"`:

| `correlation_id` | Decision | Determining policy |
|---|---|---|
| `cust_8814\|IN_AADHAAR` | **DENY** | `q2_forbid_aadhaar_analyst` *(and `q2_forbid_budget_exhausted` — two forbids, either suffices)* |
| `cust_8814\|NAME` | **DENY** | `q2_forbid_budget_exhausted` |
| `cust_8814\|PHONE` | **DENY** | `q2_forbid_budget_exhausted` |
| `cust_8814\|IN_PERMANENT_ACCOUNT_NUMBER` | **DENY** | `q2_forbid_budget_exhausted` |

Released to the model:

```
customer_id: cust_8814
aadhaar: [IN_AADHAAR_1_7f3a]
name: [NAME_2_7f3a]
phone: [PHONE_3_7f3a]
pan: [IN_PERMANENT_ACCOUNT_NUMBER_4_7f3a]
```

| | |
|---|---|
| Ledger | `before: ["ADDRESS","NAME","PHONE"]` → `after: ["ADDRESS","NAME","PHONE"]` — **unchanged. Nothing was revealed, so nothing was spent** (§4.4). |
| Audit | `entities_found {IN_AADHAAR:1, NAME:1, PHONE:1, IN_PERMANENT_ACCOUNT_NUMBER:1}` · `entities_masked` identical · `entities_revealed {}` · `mask_policies {IN_AADHAAR:"q2_forbid_aadhaar_analyst", NAME:"q2_forbid_budget_exhausted", PHONE:"q2_forbid_budget_exhausted", IN_PERMANENT_ACCOUNT_NUMBER:"q2_forbid_budget_exhausted"}` |
| **Viewer sees** | Meter stays **3 / 3**, turns **red** — over threshold. The `PHONE · call 2` slot goes **hatched** (UI spec §2.5: retroactive redaction is visible because each slot carries the call that spent it). Decision panel splits into two panes: left is `‹IN_AADHAAR · 12 digits›  ‹NAME · 14 chars›  ‹PHONE · 15 chars›  ‹IN_PERMANENT_ACCOUNT_NUMBER · 10 chars›`, right is the four tokens. Substitutions list names each policy and renders its `@advice`. |

> **Narration — exact wording, PRD §12's narration rule is strict here:**
> ✅ *"The phone number was allowed at call two. It is denied now, because the ledger moved. Same field, same principal, same tool — different answer, because the policy can see what this session already knows."*
> ❌ Never *"the model no longer knows it."* It read it at call two.

---

### Beat 1:40–2:05 — the exfiltration deny, then rehydration

Both calls are still inside turn 4's invocation, so the vault still holds `[IN_AADHAAR_1_7f3a]`.

#### Call 5 — the deny beat: rehydration refused

```
send_summary(to="notes.pastebin.example",
             body="Aadhaar on file for cust_8814: [IN_AADHAAR_1_7f3a]")
```

| | |
|---|---|
| Q1 snapshot | `{role:"analyst", dest:"notes.pastebin.example", …}` |
| **Q1** | **ALLOW** — `q1_send_summary`. Analysts may send summaries. The call is not the problem. |
| `Rehydrator.before_tool_call` | Finds `[IN_AADHAAR_1_7f3a]` in `body`. Asks Cedar: `action == Action::"rehydrate_IN_AADHAAR"`, `resource == Destination::"notes.pastebin.example"`. |
| **Q3** | **DENY** — default-deny. `q3_rehydrate_aadhaar_kyc_vault_only` names only `kyc-vault.internal`. |
| Substitution | **None.** The token is left as a token. `Proceed()`, not `Deny()` — the call runs, the summary is sent, and what goes out is `[IN_AADHAAR_1_7f3a]`. |
| Audit | `call_decision "ALLOW"` · `rehydrated []` · `outcome "ok"` |
| **Viewer sees** | A row in the calls table: tool `send_summary`, destination `notes.pastebin.example`, decision **ALLOW**, and a **`rehydration refused`** chip. The outbound body is rendered with the token intact. |

> **The line:** *"PRD §11.2 is the hole we found in our own design. If any authorized call gets the placeholder substituted, the guardrail becomes the exfiltration channel. So rehydration is its own Cedar question, against the destination. The call is allowed. The value is not."*

#### Call 6 — the rehydration beat: the task completes

```
send_summary(to="kyc-vault.internal",
             body="Aadhaar on file for cust_8814: [IN_AADHAAR_1_7f3a]")
```

| | |
|---|---|
| **Q1** | **ALLOW** — `q1_send_summary` |
| **Q3** | **ALLOW** — `q3_rehydrate_aadhaar_kyc_vault_only`, `resource == Destination::"kyc-vault.internal"` |
| Substitution | `str.replace` (never `re.sub`) → body becomes `Aadhaar on file for cust_8814: 0482 7391 5604`, **on the trusted side, at `before_tool_call`, after the model emitted the argument** |
| Ledger | unchanged — rehydration is not a disclosure to the model |
| Audit | `rehydrated ["[IN_AADHAAR_1_7f3a]"]` — **token string only, never the value** (TD §3.5) |
| **Viewer sees** | Row: destination `kyc-vault.internal`, decision **ALLOW**, chip **`rehydrated · IN_AADHAAR`**. The agent's final reply: *"Filed the Aadhaar for cust_8814 with the KYC vault."* |

> **The line:** *"The task completed. The Aadhaar reached the vault. It never entered model context — the model emitted a placeholder, and the real digits were substituted on the trusted side of the boundary."*

---

### Beat 2:05–2:25 — one attachment, whole budget, one call

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "Open the attachment on ticket tkt_4471 and tell me who the customer is." }
```

#### Call 7 — `read_attachment(ticket_id="tkt_4471")`

| | |
|---|---|
| Returns | `{"filename":"kyc-sheet-tkt-4471.pdf","media_type":"application/pdf","b64":"JVBERi0x…"}` |
| Subject | **`tkt_4471`** — no `customer_id` in the args, so `SUBJECT_KEYS` falls through to `ticket_id`. Fresh budget of 3. |
| `normalize()` | Textract `DetectDocumentText(Document={'Bytes': raw})`. `DocumentMetadata.Pages == 1` → continue. `ocr_sourced=True`, `words[]` populated with bboxes. |
| Detector tiers | **1:** `IN_AADHAAR` `1639 4058 2713` @ 1.0. **2:** `NAME`, `ADDRESS`, `DATE_TIME`. |
| Q2 snapshot | `{role:"analyst", subject:"tkt_4471", seen:[], seen_count:0, budget:3}` |
| Q2 batch | `IN_AADHAAR` → **DENY** `q2_forbid_aadhaar_analyst`. `NAME`, `ADDRESS`, `DATE_TIME` → **ALLOW** (all evaluated against `seen_count: 0`; the ceiling binds at the *next* call). |
| Ledger | `[]` → `["ADDRESS","DATE_TIME","NAME"]` |
| Audit | `content_type "application/pdf"` · `pages 1` · `detector_tiers ["checksum","comprehend"]` · `entities_found {IN_AADHAAR:1,NAME:1,ADDRESS:1,DATE_TIME:1}` · `entities_masked {IN_AADHAAR:1}` |
| **Viewer sees** | A **second subject card** appears, `tkt_4471`. Its meter goes **0 → 3/3 in one step**. Textract bounding box drawn over `1639 4058 2713` on the rendered page (Should item 13); `words` whose offsets fall inside the denied span carry `redacted: true`. |

> **The line:** *"Three calls to fill that budget. One attachment to fill this one. Comprehend takes text — a base64 attachment is invisible to it, and the audit row would read 'zero entities found'."*

---

### Beat 2:25–2:45 — one line of policy, two agents

**Step 1 (operator action, ~8 s on camera).** Paste four lines into the Cedar text in the control-plane editor and save:

```cedar
@id("q1_forbid_attachment_analyst")
@advice("Attachments are restricted to compliance review from 2026-09-20.")
forbid(principal, action == Action::"read_attachment", resource)
when { context.session has role && context.session.role == "analyst" };
```

```
PUT {CONTROL_URL}/policy
If-Match: "<etag>"
X-Naka-Key: <secret>
```

> **Add a `forbid`; do not narrow the `q1_read_attachment` permit** (§0 correction 4). Narrowing produces a **default-deny**, which has no determining policy id — `deny_policy` comes back `null` and the UI has nothing to render. An explicit `forbid` carries an `@id` and an `@advice`, so the denial names and explains itself on camera.

**Step 2 — wait.** `POLICY_TTL_S = 20`, checked at the top of each HTTP request, never mid-turn. **Count to 25 before the next call, or the old bundle is still in force and the beat silently does not fire.** The `policy_version` string in the UI header is the on-camera confirmation — do not send the next request until it ticks.

**Step 3 — Call 8, session A:**

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "Open the attachment on tkt_4471 again." }
```
→ `read_attachment(ticket_id="tkt_4471")` → **Q1 DENY**, `deny_policy "q1_forbid_attachment_analyst"`, `outcome "denied_call"`. The tool never runs. (This is PRD §11 Must #3 — the visible Q1 deny path.)

**Step 4 — Call 9, session B**, a separate agent that has never seen this policy:

```json
{ "session_id": "s-naka-demo-b", "user": "ravi@example.com", "role": "analyst",
  "prompt": "Open the attachment on tkt_4471." }
```
→ same `read_attachment` → **Q1 DENY**, same policy id.

**Viewer sees:** the live feed (`GET /feed`, one query, `gsi1pk = FEED#2026-09-20`, newest first) with two red rows from two different sessions and two different principals, both naming `q1_forbid_attachment_analyst`, both rendering the same `@advice` string.

> **The line:** *"One line, on the control plane. Two agents, two sessions, one audit view — and neither agent was redeployed."*

**Optional, 6 s, cut first if over:** Call 10, session C — `priya@example.com`, role `compliance`, same `read_attachment` → **ALLOW** via `q2_permit_compliance` (the new `forbid` is scoped to `role == "analyst"`, so it does not bind). Meter shows `budget 9999`, Aadhaar released. *"The policy is about who, not about what."*

---

### Beat 2:45–3:00 — close

`GET /session/s-naka-demo-a` — one query returns both shapes: two subject meters (`cust_8814` 3/3 red, `tkt_4471` 3/3) and nine call rows. Cut to the live Function URL in the address bar.

---

### Optional beat — the checksum rejects a false positive

Conditional on **PF-7**. Slot before 2:25 if there is room; otherwise it belongs in the writeup.

```json
{ "session_id": "s-naka-demo-a", "user": "alice@example.com", "role": "analyst",
  "prompt": "Show the KYC record for cust_2280." }
```
→ `fetch_customer(customer_id="cust_2280", field="kyc")`, whose result carries **two** twelve-digit numbers:

| Value | Verhoeff | Tier 1 |
|---|---|---|
| `1374 6029 8151` (`aadhaar`) | ✅ valid | `IN_AADHAAR` @ 1.0 |
| `1639 4058 2714` (`policy_ref`) | ❌ invalid | **no entity** |

`entities_found.IN_AADHAAR == 1`, not 2 — that single number in the audit row is the whole beat. Narration in §2.4.

---

## 7. Fixture files to create

```
fixtures/
  customers.json              §3
  tickets.json                §3.3
  kyc-sheet.html              §5.3 — the single source
  kyc-sheet-tkt-4471.pdf      §5.3 step 2 — MUST be 1 page
  kyc-sheet-tkt-4472.png      §5.3 step 3 — Indic beat, PNG not PDF
  agent.cedar                 §4.2 — also baked into the Lambda zip
  bundle.json                 §4.3
  demo-run.sh                 the nine POSTs of §6, in order, with sleeps
```

`demo-run.sh` exists so the recording is a single command and every take is identical. It is nine `curl` calls, a `sleep 25` before step 3 of the 2:25 beat, and nothing else.

---

## 8. Pre-flight checklist

Run **in this order** on the deployed stack, on the recording machine, immediately before the first take. Do not start recording with an amber row.

### 8.1 Blocking — the video cannot be recorded if any of these fail

| # | Check | How | Pass |
|---|---|---|---|
| **PF-1** | Verhoeff implementation is Verhoeff, not Luhn | `python selfcheck.py` — the adjacent-transposition assertion (TD §9.1) | 0 of 11 transpositions validate, all four fixtures |
| **PF-2** | All four Aadhaar fixtures still validate; the invalid one still fails | `verhoeff_valid` on the five strings in §2.1/§2.4 | 4 True, 1 False |
| **PF-3** | Every Aadhaar begins `0` or `1` | `all(a[0] in "01")` | True |
| **PF-4** | `pan_valid` accepts all four PANs | regex + char 4 ∈ holder set | 4 True |
| **PF-5** | **Comprehend detects `+91 55501 84412` as `PHONE` at ≥ 0.5** | `detect_pii_entities(Text="phone: +91 55501 84412", LanguageCode="en")` — pad to ≥300 chars, 3-unit minimum bills anyway | `PHONE` present, `Score ≥ 0.5`. **Contingency in §9.3.** |
| **PF-6** | Comprehend detects `NAME`, `ADDRESS`, `DATE_TIME` on the PDF's OCR output at ≥ 0.5 | Run call 7 end to end, read `entities_found` | `{NAME:1, ADDRESS:1, DATE_TIME:1, IN_AADHAAR:1}` — exactly three revealed |
| **PF-7** | Comprehend's behaviour on `1639 4058 2714` (invalid) | same call as PF-5 | Record the answer. Selects the §2.4 narration; does not block. |
| **PF-9** | **Calls 4, 5 and 6 land in one HTTP invocation** | Run turn 4, check the response's `calls[]` has three entries and `rehydrated` is non-empty on the last | 3 calls, one `trace_id` |
| **PF-10** | PDF is exactly one page | `pdfinfo kyc-sheet-tkt-4471.pdf` | `Pages: 1` |
| **PF-11** | `floor_ok()` accepts the §4.2 policy | `policy.floor_ok(open("agent.cedar").read())` | `True` — **fails until `FLOOR_RULES` is patched per §0/3** |
| **PF-12** | The enricher reaches policy at all | TD §9.5's first pair: `reveal_PHONE` with `seen=[]` → Allow; with `seen=["IN_AADHAAR"]` → Deny | Allow, then Deny |

### 8.2 Sequence rehearsal — run `demo-run.sh` once and assert the ledger transitions

| After call | `cust_8814` meter | `tkt_4471` meter | Key assertion |
|---|---|---|---|
| 1 | `["NAME"]` 1/3 | — | `entities_revealed == {NAME:1}` |
| 2 | `["NAME","PHONE"]` 2/3 | — | `entities_masked == {}` — **if PHONE is masked here, PF-5 failed** |
| 3 | `["ADDRESS","NAME","PHONE"]` 3/3 | — | meter full, nothing denied yet |
| 4 | **unchanged** 3/3 | — | `entities_revealed == {}`; `ledger_before == ledger_after`; 4 tokens in the released text; `mask_policies.PHONE == "q2_forbid_budget_exhausted"` |
| 5 | unchanged | — | `rehydrated == []`, `call_decision == "ALLOW"` |
| 6 | unchanged | — | `rehydrated == ["[IN_AADHAAR_1_<n>]"]` |
| 7 | unchanged | `["ADDRESS","DATE_TIME","NAME"]` 3/3 | `pages == 1`, `entities_masked == {IN_AADHAAR:1}` |
| 8 | unchanged | unchanged | `call_decision == "DENY"`, `deny_policy == "q1_forbid_attachment_analyst"` |
| 9 | — | — | session B row, same `deny_policy` |

### 8.3 Safety and hygiene — must pass or the video should not be published

| # | Check | Pass |
|---|---|---|
| **PF-13** | **No fixture value appears anywhere in DynamoDB.** TD §9.6: `json.dumps(asdict(row))` for every row contains none of `048273915604`, `163940582713`, `+91 55501 84412`, `AZKPR0000M`, `Anil Kumar Rao` | 0 hits |
| **PF-14** | Same check across **CloudWatch Logs** for the whole rehearsal run | 0 hits |
| **PF-15** | Same check across every HTTP **response body** the browser received | 0 hits |
| **PF-16** | `acme.com` appears nowhere — principals are `@example.com` (§1.4) | 0 hits |
| **PF-17** | Vault is empty after each invocation (`finally: vault.clear()`) | `len(vault._map) == 0` |
| **PF-18** | The SPECIMEN watermark is legible in the 2:05 frame at the recording resolution | Eyeball at 1080p |
| **PF-19** | §0 correction 8 resolved — the Verhoeff code in `detect.py` was written during the event | Team confirms |

### 8.4 Recording hygiene

| # | Check |
|---|---|
| PF-20 | Browser at **1920 × 1080**, no bookmarks bar, no extensions, no notifications. The meter needs its 440 × 420 rectangle. |
| PF-21 | DynamoDB cleared of prior runs: delete `pk = SESSION#s-naka-demo-a\|b\|c`. A stale meter row means call 1 starts at 1/3 and every number afterwards is wrong. |
| PF-22 | Policy bundle reset to the §4.2 baseline (without the `q1_forbid_attachment_analyst` block) and `policy_version` confirmed in the UI header. |
| PF-23 | `INDIC_ENABLED` set to the value the take needs — `false` for run A, `true` for run B (§5.5). |
| PF-24 | `GET /health` on both Function URLs returns 200 and `policy_source: "control-plane"` — not `"package-fallback"`. |

---

## 9. What is verified here, and what is not

### 9.1 Verified by computation in this document

Verhoeff tables (cross-checked against the published `236 → 3` vector and an independent brute-force generator that never touches the `INV` table) · all four check digits · the invalid fixture · 108 single-digit mutations and 11 adjacent transpositions rejected per fixture · leading-zero survival · grouped-form validation after digit-stripping · all four PANs against the regex and the holder-type set.

### 9.2 Verified from documentation

Aadhaar is not issued beginning 0 or 1 · PAN sequence runs 0001–9999 and the 10th-character algorithm is unpublished · PAN holder-type enum · Indian mobile numbers begin 6/7/8/9 · **India has no reserved fictitious-number range** (TRAI reserves `140xx` and `1600xx` for promotional and BFSI/government transactional traffic; neither is a drama range) · `example.com` and `.example` are RFC 2606 reserved, `.internal` is IANA-reserved · Textract sync is one page for PDF and OCRs Latin script only · Bedrock `ImageBlock.format` is `png|jpeg|gif|webp`.

### 9.3 NOT verified — live checks required before recording

| What | Risk | Gate | Contingency |
|---|---|---|---|
| **Comprehend detects `+91 555xx xxxxx` as `PHONE`** | **HIGH — this is the headline beat** | **PF-5** | Try, in order: `+91 55501 84412` → `+91-55501-84412` → `05550184412` → `055 5018 4412`. If all fail, add a shape-only recogniser to Tier 1: `(?:\+?91[\s-]?)?[5-9]\d{9}` — three lines, makes the beat deterministic and free. Defensible: *"Tier 1 already carries the country's identifier formats; the phone shape is the same tier."* **Do not** switch to a `9…` number to please the detector — that surrenders the safety guarantee for a detection convenience, and it is the one trade nobody should make on camera. |
| Comprehend's `IN_AADHAAR` accepts a number beginning `0`/`1` | LOW — Tier 1 owns Aadhaar and short-circuits; Comprehend is a bonus | PF-6 | None needed. If Comprehend rejects it, say so: *"The managed detector will not touch a 0-leading Aadhaar. Ours does, because it runs the checksum."* A good beat. |
| Comprehend's `IN_PERMANENT_ACCOUNT_NUMBER` accepts sequence `0000` | LOW — Tier 1 owns PAN | PF-4 | None needed |
| Comprehend runs Verhoeff on `IN_AADHAAR` | LOW — selects narration only | PF-7 | Both narrations written, §2.4 |
| `ADDRESS` / `DATE_TIME` detection on Textract OCR output | MEDIUM — the 2:05 beat needs exactly 3 | PF-6 | If `DATE_TIME` misses, the meter reads 2/3 and the "one attachment, whole budget" line is false. Add an `EMAIL` line to the sheet to restore the third. If `ADDRESS` misses, re-flow it onto one line — Comprehend's `ADDRESS` recall drops on hard-wrapped OCR text. |
| Nova Pro returns usable Devanagari substrings, byte-identical for `str.find()` | MEDIUM — Should item only | PF-8 | PRD open question 4: set `INDIC_ENABLED=false`, cut the beat, keep the claim in the writeup on the Textract documentation line |
| Nova emits the right `field` argument on each prompt | MEDIUM — three takes if it drifts | PF-9 / §8.2 | Append the field name to the prompt verbatim: *"…use field=\"name\"."* Prompts are the script; the video is recorded, not live. |
| **Calls 4–6 in one turn** | **HIGH — the rehydration beat depends on it** | **PF-9** | If Nova splits the turn, merge calls 5 and 6 into one prompt that names both destinations explicitly, or drop call 5 and keep only the rehydration ALLOW. Never split across HTTP requests — the vault is gone and it fails closed, correctly and invisibly. |
| `cedarpy` accepts `Destination::"…"` / `Subject::"…"` UIDs with `entities=[]` | MEDIUM | PF-12 | TD §1.7 already flags this. All comparisons here are `==` on a UID, which needs no store lookup — but confirm with one call. If UIDs must exist, add four stub entries to `bundle.entities`. |
| The `diagnostics` key carrying the determining policy id | MEDIUM — `deny_policy` and `mask_policies` are `null` without it | build time | TD §1.7 flags it. Print one `AuthzResult` and pin the key. If it cannot be found, the UI falls back to the `@advice` annotation looked up by matching the policy text — uglier, still true. |
