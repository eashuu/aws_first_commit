# Naka — implementation

A guardrail on an AI agent's tool boundary: Cedar authorizes each tool call
(Q1), the result is normalized and scanned for PII (checksum → Comprehend →
Indic multimodal, unioned), and each detected field is authorized
*separately* against a running per-subject disclosure ledger (Q2). Denied
fields become numbered placeholders, rehydrated only into a
Cedar-authorized destination (Q3). See the planning package one level up —
`../hackathon-agent-egress-guardrail-prd-2026-09-18.md` (source of truth)
and `../08-technical-design.md` (module design) — for the full rationale.

**This directory is the implementation.** It follows `08-technical-design.md`
for architecture, but the Cedar policy and the three tool signatures follow
`../10-demo-fixtures.md` §0/§4 instead — that document found and fixed real
bugs in 08's own draft (an unscoped budget-ceiling `forbid` that also denied
the tool call itself, a `FLOOR_RULES` value that would reject the corrected
policy, an `AuditHook` that only bound `AfterToolCallEvent` and so silently
dropped every Q1 denial from the audit trail). `agent.cedar` documents this
in its header comment.

## What's implemented

| Module | Does |
|---|---|
| `config.py` | Every tunable, one place. Env-var driven, sane defaults. |
| `detect.py` | Tier 1 (Verhoeff/PAN/GSTIN/IFSC/Voter ID, all written fresh from published formats — see below), Tier 2 (Comprehend), Tier 3 (Nova Pro multimodal, additive-only), and `merge()`. |
| `normalize.py` | bytes → markdown. Text/JSON/CSV/XLSX pass through; PDF/image go through Textract, always (never a text-layer-only extractor). Multi-page PDFs are withheld whole. |
| `ledger.py` | The disclosure ledger — a grow-only set per `(session, subject)`, authoritative in DynamoDB via atomic `ADD` on a String Set. |
| `attribute.py` | Entity → data subject, from the tool call's own arguments, never content-based clustering. |
| `rehydrate.py` | The `Vault` (process-local, invocation-scoped, plaintext) and the `Rehydrator` — rehydration is itself a Cedar question against the destination (Q3), not a blanket substitution. |
| `cedar_q2.py` | The only module touching `cedarpy` directly — Q2 and Q3. |
| `policy.py` | Control-plane client: fetch, TTL cache, policy-floor enforcement, fail-closed to the packaged `agent.cedar`. |
| `guard.py` | `DisclosureGuard` — the intervention that wires normalize → detect → attribute → Q2 → redact → spend together. Also **shadow mode** (`enforce=False`, requested as `"enforce": false` on the agent API **and requiring the `X-Naka-Key` operator header** — see below): the identical decision path runs and is fully audited, but nothing is substituted and the ledger is never persisted. It exists because nobody turns on a blocking control in front of live traffic without first measuring what it would have blocked — and because it makes the demo's guarded/unguarded comparison one codepath with a flag, not two codepaths filmed side by side. It never alters traffic, not even on a detector outage; see `_withhold`. |
| `audit.py` | `AuditHook` — binds **both** `BeforeToolCallEvent` and `AfterToolCallEvent` (registered at `HookOrder.SDK_LAST` on the before side — verified against the actual Strands intervention registry, which runs interventions at `order=90` on `before_tool_call`; a hook at the default order would fire *before* interventions decide anything and could never see a Q1 denial). |
| `tools.py` | The three demo tools (`fetch_customer`, `read_attachment`, `send_summary`), fixture-backed. |
| `app_agent.py` / `app_control.py` | The two Lambda entry points. |
| `agent.cedar` | The policy — Q1, Q2, Q3, the compliance exemption. Packaged as the fail-closed fallback. |
| `selfcheck.py` | `python selfcheck.py` — 40+ assertions on the logic that doesn't need AWS to get right (Verhoeff correctness incl. the Luhn-discriminating adjacent-pair-transposition test, offset-preserving redaction, rehydration round-trips, ledger accumulation, the exact Cedar decisions the demo beat sheet requires, audit-row leak safety). All pass. |
| `fixtures/` | The demo data from `10-demo-fixtures.md` — synthetic, provably non-issuable Aadhaar/PAN/phone numbers, plus a generated (not scraped) KYC-sheet PDF/PNG. |
| `web/` | The control-plane UI — live feed, per-subject disclosure meter, before/after diff (reconstructed from entity *counts and shapes*, never plaintext — the API has no field that could carry it). |

## Extra Indian-identifier coverage beyond the Must list

`detect.py` also covers **GSTIN**, **IFSC** and **Voter ID (EPIC)** as
format-validated Tier 1 entities (GSTIN additionally checks its embedded PAN
and state-code range). None of these have a publicly documented check-digit
algorithm that could be verified during this session, so — same honesty
call the design already makes for PAN — they're format/range checks, not
claimed checksums. Wired into `agent.cedar`'s baseline permit, budget
ceiling and compliance exemption, and into `config.py`'s
`DEFAULT_IDENTIFYING_TYPES`, so they count toward the disclosure budget like
every other identifying field.

## Why nothing here was copied from `../prompt_optimizer/`

That project already has a working Presidio-based Aadhaar/PAN detector. It
was deliberately **not** reused: the PRD explicitly names copying the
Verhoeff implementation "elsewhere on this machine" as a disqualification
risk (the hackathon requires work created during the event), and
`prompt_optimizer`'s detector is architecturally a torch/spaCy/GLiNER
service that doesn't fit a Lambda zip regardless. Every detector in
`detect.py` is written fresh from published formats/tables (the D5
dihedral-group Verhoeff tables, PAN's holder-type character set, GSTIN's
structure) — verified independently against `prompt_optimizer`'s entity
coverage only to confirm nothing was missed, never against its code.

## Running the self-check

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install strands-agents cedarpy boto3 openpyxl reportlab pillow
python fixtures/build_kyc_sheet.py   # generates the two demo document fixtures
python selfcheck.py
```

`reportlab`/`pillow` are dev-time only (fixture generation), never bundled
into the Lambda zip.

## Deploying

`deploy/` has both bash and PowerShell versions of everything:

| Script | Does |
|---|---|
| `build.sh` / `build.ps1` | Installs deps for the arm64/Python-3.12 target into a build dir, copies in the `.py` files, `agent.cedar`, `fixtures/`, `web/`, zips to `dist/naka.zip`. Uses **uv** when present — see "Why uv, not pip" below; this is not a preference. |
| `create-table.sh` / `.ps1` | Creates `naka_audit` (on-demand, pk/sk, the `gsi1` GSI with an `INCLUDE` projection matching exactly what `app_control.py`'s feed query reads), enables TTL on `expires_at`. Idempotent. |
| `deploy.sh` / `.ps1` | The full sequence: build the zip, create the session S3 bucket, **stage the zip to S3**, run `create-table`, create one shared IAM role from `iam-policy.json` + `trust-policy.json`, create the control-plane Lambda first (captures its Function URL), create the agent Lambda with `CONTROL_PLANE_URL` set to it, then both `add-permission` calls for both functions. `SKIP_BUILD=1` reuses an existing zip on a retry. |

### Three things that will cost you an hour each if you skip them

All three were hit for real while deploying this, and all three fail in a way
that looks like a code bug and is not.

**1. Why uv, not pip.** `pip --platform` only filters which *wheel tags* it
accepts. It does **not** evaluate PEP 508 environment markers for the target
— those are always evaluated against the machine running pip. `mcp` (a
`strands-agents` dependency) declares `pywin32>=310; sys_platform == "win32"`,
so building on Windows makes pip believe it needs pywin32, for which no
`manylinux_aarch64` wheel exists. With `--only-binary=:all:` that is a
resolution failure — but pip does not report one. It **backtracks**, silently
landing on `strands-agents 1.1.0`, the last release whose `mcp` range predates
that marker. The zip builds, uploads, and deploys cleanly, and the Lambda
then dies at import with `No module named 'strands.vended_interventions'`.
`uv pip install --python-platform aarch64-manylinux2014` evaluates markers for
the target and resolves correctly. `build.*` now also hard-fails if
`strands/vended_interventions` is missing from the build.

**2. The Function URL needs two permission statements, with different flags.**
A public Function URL 403s — opaquely, with no CloudWatch log line — unless the
resource policy grants *both* `lambda:InvokeFunctionUrl` **and**
`lambda:InvokeFunction`. The PRD says this. What the PRD gets wrong is the
call: `--function-url-auth-type NONE` is **only valid on
`lambda:InvokeFunctionUrl`**. Passing it alongside `lambda:InvokeFunction` is
rejected outright (`FunctionUrlAuthType is only supported for
lambda:InvokeFunctionUrl`), so a script that passes it to both — and swallows
errors, as this one originally did — adds only the first statement and the URL
403s forever.

**3. Upload via S3, not `--zip-file`.** `create-function --zip-file` sends the
whole package as a single non-resumable HTTPS body. At ~33 MB that reliably
dies with `Connection was closed before we received a valid response` on any
connection that isn't fast and stable, and it dies *after* the build, so each
retry re-runs the install. `deploy.*` now stages to
`s3://$SESSION_BUCKET/deploy/naka.zip` and passes `--code S3Bucket=...`.

Before running `deploy.sh`/`deploy.ps1`:

1. **AWS account on the Paid plan** — a Free-plan account cannot redeem
   promotional credits and auto-closes at six months (README.md at the repo
   root, §"Before you write a line of code").
2. Find and set `STRANDS_LAYER_VERSION` — the PRD names the layer ARN
   prefix but not a version number (and its ARN has two typos: the segment
   is `py3_12` with an underscore, not `py3.12`, and `aarch64`, not `arm64`
   — `arm64` is only the `CompatibleArchitectures` API value, not part of
   the layer name string; confirmed against strandsagents.com and by
   probing the real API). The script refuses to guess and tells you to run:
   ```bash
   aws lambda list-layer-versions --region ap-south-1 \
     --layer-name strands-agents-py3_12-aarch64 \
     --compatible-runtime python3.12 --compatible-architecture arm64
   ```
   If that 403s (this layer doesn't grant public `ListLayerVersions`, only
   `GetLayerVersion` on specific versions), probe directly instead:
   ```bash
   aws lambda get-layer-version --region ap-south-1 \
     --layer-name strands-agents-py3_12-aarch64 --version-number 1
   ```
   incrementing until it 403s — the last one that succeeds is the latest.
   As of this session, version 2 (2026-05-21) is the latest accessible.
3. `NAKA_KEY` (the `PUT /policy` shared secret) is auto-generated and
   printed once if you don't supply one — save it, it gates the only
   mutating route on either Lambda.
4. `SESSION_BUCKET` defaults to `naka-sessions-<account-id>` and is
   created for you if missing.

`deploy.*` sets `AGENT_URL` on the **control** plane in a second pass, after
both Function URLs exist, so the UI can prefill its agent-endpoint field from
`GET /health`. Without it the field is only ever populated from the viewer's
own `localStorage`, which a first-time visitor (a judge opening the link)
does not have — they would land on a console that refuses to run anything.

The IAM policy scopes Bedrock to the two inference profiles actually used
(`apac.amazon.nova-lite-v1:0`, `apac.amazon.nova-pro-v1:0`) plus their
underlying foundation-model ARNs across regions, since — per the PRD — an
APAC geo profile's actual destination regions are undisclosed; narrow this
with `aws bedrock get-inference-profile` if tighter least-privilege matters
more than the extra setup step.

## Testing

Two suites, deliberately split by what they need:

| Suite | Needs AWS | Covers |
|---|---|---|
| `python selfcheck.py` | no | Pure logic: Verhoeff (incl. the adjacent-transposition case that discriminates it from Luhn), offset-preserving redaction, merge/containment ranking, chunk-offset arithmetic, subject canonicalisation, rehydration round-trips, and the exact Cedar decisions the demo beat sheet requires. |
| `python livecheck.py` | yes | The wiring: real DynamoDB ledger round-trips and atomic set-union, real audit-row shapes read back through the control plane, the full guard pipeline (tool → normalize → detect → Q2 → redact → spend), both fail-closed paths, and every control-plane route. |

`livecheck.py` reports **SKIP, not FAIL**, for any check whose AWS service is
unreachable, so it stays useful on a half-provisioned account — the summary
tells you which half. Everything it writes goes under a
`SESSION#livecheck-<uuid>` partition and is deleted on the way out.

It also stubs Comprehend (with strings copied verbatim from
`fixtures/customers.json`) so the pipeline checks still run when the real
service is gated. That stub is a wiring test and says so; it is never a
substitute for the real-Comprehend check, which is a separate, skippable case.

## Why shadow mode needs the operator key

Both Function URLs are `AuthType=NONE` — public and unauthenticated, on
purpose, so a judge can open the link. That makes any request field which
weakens the guardrail an internet-facing switch. `"enforce": false` is
exactly such a field: honouring it from an unauthenticated body would let
any caller turn the whole control off, which is the one outcome this system
exists to prevent, and it would be a strange thing to ship in a tool whose
entire claim is that it fails closed.

So `enforce: false` requires the same `X-Naka-Key` header that gates
`PUT /policy`. Deciding to measure rather than block is an operator's call,
not a caller's. Enforcing — the default, and the protective path — requires
no key and never will: a protection that only works when a secret is present
is not a protection.

```bash
# blocked: 401, no key
curl -s -X POST "$AGENT_URL" -d '{"prompt":"...","enforce":false}'

# allowed: operator measurement run
curl -s -X POST "$AGENT_URL" -H "X-Naka-Key: $NAKA_KEY" \
  -d '{"prompt":"...","enforce":false}'
```

`livecheck.py` asserts all of this, including that the default enforcing
path never demands a key.

## The console

Served by the control-plane Lambda at its Function URL root. Four one-click
scenarios sit above the prompt box, each carrying a complete payload and the
role it needs, so a decision is reachable in one click rather than four
configured fields:

| Scenario | Proves |
|---|---|
| Benign lookup | Aadhaar and PAN masked, name released, ledger spent |
| Budget bites | The fourth distinct field for one subject is refused |
| Exfiltration attempt | Q3 denies rehydrating a value into an unauthorized destination |
| Compliance role | The same call under a principal the policy exempts |

**Each scenario mints a fresh `session_id`.** That is deliberate and
load-bearing, not cosmetic: the ledger is cumulative per `(session,
subject)`, so replaying scenarios in one session would leave "budget bites"
already exhausted before it ran, and the demo would appear to block a call
it had not yet earned the right to block. A judge replaying them in any
order gets the same result each time.

`GET /diag` probes Comprehend, Textract and Bedrock **server-side, live**
(60s cache) and the console renders every detector tier including the quiet
ones. A gated service reports `NOT_RUN` in neutral grey, never `FAIL` in
red — being unavailable on this account is a provisioning state, not a
defect, and the distinction between "found nothing" and "never looked" is
the same one the product exists to enforce (PRD §6.3).

## Deployment status

Deployed and verified live in `ap-south-1`:

- both Lambdas healthy behind their Function URLs (`GET /health` → 200 on each)
- DynamoDB `naka_audit` + `gsi1` + TTL, S3 session bucket, shared IAM role
- `selfcheck.py` all green; `livecheck.py` 23 passed / 0 failed / 6 skipped

The 6 skips are **Comprehend, Textract and Bedrock**, which are all refusing
calls on this account (`SubscriptionRequiredException` /
"account is currently being verified"). That is an AWS account-activation
state, not a code or IAM problem — confirmed by the fact that it reproduces
in `us-east-1` as well, while DynamoDB/S3/Lambda/IAM work fine in the same
credentials. Nothing needs redeploying when it clears.

## What's not done

- **Tier 1, 2 and 3 detection has never run against the real services** —
  see "Deployment status". This is the one genuinely unvalidated area, and
  it is the entire detection path. `livecheck.py` has the checks written and
  waiting; they flip from SKIP to PASS/FAIL the moment the account activates.
- **Shadow mode (`DisclosureGuard(enforce=False)`) has no activation path.**
  The implementation is complete and safe-by-default, but nothing constructs
  a guard with `enforce=False`, so it is currently unreachable code. Wiring
  it to a *request* field would be a vulnerability — the data-plane Function
  URL is unauthenticated, so any caller could switch the guardrail off. If it
  is needed for the demo's guarded/unguarded comparison, gate it behind a
  deploy-time env var or the `NAKA_KEY`, never the request body.
- The **UI** covers the Must-list item (live feed, meter, diff, policy
  editor) but not the full visual design pass in `../03-ui-ux-design-spec.md`
  — that document targets the separate Best UI prize criterion and is a
  larger, design-focused follow-up.
- **Async multi-page Textract, OpenSearch, streaming, auth, multi-tenancy,
  signed audit rows** — all explicitly Will-Not per the PRD's scope section,
  not gaps.
- Tier 3 (Indic multimodal) quality against real Nova Pro output is
  **unverified** — PRD open question 4. `INDIC_ENABLED=false` demotes it
  cleanly; the rest of the system does not depend on it.
