# AWS Services and Access — Naka

**Companion to:** `hackathon-agent-egress-guardrail-prd-2026-09-18.md` (§7 sets the stack; this document verifies it)
**All pages read:** 18 September 2026. Every price and limit below was pulled on that date and is cited. Anything not verified is written as **unverified** with the check to run.
**Region throughout:** `ap-south-1` (Asia Pacific, Mumbai).
**Price source:** where a number is marked *[Price List API]*, it came from the AWS Price List bulk API for `ap-south-1` — the same data behind the pricing pages, but region-exact (the HTML pricing pages render US rates by default). Endpoint: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<service>/current/region_index.json`.

---

# PART A — What can be used right now, without paying

## A.1 Builder ID vs Builder Center vs AWS account

These are three different things and conflating them will cost the team an evening.

| Thing | What it is | Does it run code or bill usage? |
|---|---|---|
| **AWS Builder ID** | A personal identity. "Your AWS Builder ID is separate from any AWS account or sign in credential." | **No.** The docs state it explicitly: an AWS Builder ID "Can't obtain AWS IAM credentials to access the AWS Management Console, AWS CLI, AWS SDKs, or AWS Toolkit." |
| **AWS Builder Center** (`builder.aws.com`) | A community/learning site you sign into with a Builder ID — articles, badges, Skill Builder, Student Rewards, a credit *redemption* page. | **No.** It has no compute and no service endpoints. It can *award* credit codes, which you then redeem **inside an AWS account**. |
| **AWS account** | "A resource container with contact and payment information. It establishes a security boundary in which to operate billed and metered AWS services, like S3, EC2, or Lambda." | **Yes.** This is the only one of the three that can run a Lambda. |

Source: [AWS Builder ID and other AWS credentials](https://docs.aws.amazon.com/signin/latest/userguide/differences-aws_builder_id.html) (read 18 Sep 2026).

**Direct answer to the common misunderstanding:** a verified Builder Center profile grants **zero** compute, **zero** service access and **no automatic credits**. It is an identity and community profile. The hackathon requires it because that is where SheerID student verification lives and where Student Rewards are issued — not because it provisions anything.

**One caveat worth knowing, not relying on.** The same AWS doc describes a "new AWS experience", currently rolling out "to a limited number of customers", in which a Builder ID *does* become a sign-in credential that "Can be used to obtain AWS IAM credentials". If the team sees a Builder-ID-based console, that is this preview. Do not plan around it; plan around a normal AWS account.

**What Builder Center Student Rewards actually gives.** Verify enrolment through SheerID and complete the profile → 12 months of premium AWS Skill Builder. Then badges convert to credits: **7 badges → $10 in AWS credits; 14 badges → $20; 21 badges → a Foundational certification exam voucher (~$100 value)**. Announced 24 August 2026. Source: [AWS Weekly Roundup, 24 Aug 2026](https://aws.amazon.com/blogs/aws/aws-weekly-roundup-student-rewards-on-aws-builder-center-local-zone-in-las-vegas-and-more-august-24-2026/).

$10–30 of credit earned by writing articles is not a build budget. Treat it as a nice-to-have.

## A.2 What the hackathon itself provides

From the [First Commit rules](https://www.wemakedevs.org/aws/first-commit/rules) and [event page](https://www.wemakedevs.org/aws/first-commit) (read 18 Sep 2026):

- **Required to compete:** a WeMakeDevs account **and** an AWS Builder Center profile with university enrolment verified. Student verification runs through SheerID.
- **Pending verification does not block you.** The rules say plainly: *"If your student verification is still being sorted out, enter anyway... an open case with them does not stop you submitting."* It blocks *claiming rewards* and the fast-track interview, not submission or judging.
- **Credits during the event:** the rules point entrants at the Free Tier's "up to $200 in credits plus always-free services" and add *"If you need more than that, you can request credits from the organisers."* **This is the fastest credit route that exists and it is the one to use.** Ask tonight.
- **Prize credits** ($3,000 Ship It / $2,000 Build It / $1,000 Best UI / $1,000 each to four runners-up) arrive **after** judging. They are irrelevant to building.
- **Your project has to use AWS, and your demo video has to show it.** *"Naming AWS in the writeup alone is not enough."* — this is a rule, not a suggestion, and it reinforces PRD §12: the Function URL and the AWS console have to be on camera.

## A.3 The AWS Free Tier as it exists for a new account in 2026

AWS replaced the old free tier on **15 July 2025** ([announcement posted 16 Jul 2025](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/)). Accounts created **before** 15 July 2025 are unaffected and keep the legacy program.

A new account today picks one of two plans at signup. Both get the credits; they differ in what they can reach.

| | **Free account plan** | **Paid account plan** |
|---|---|---|
| Credits | $100 on signup + up to $100 more from "Explore AWS" activities = **up to $200** | Same — $100 + up to $100 |
| Credit expiry | **12 months from account creation** (activities must be completed within 6 months) | Same |
| Duration | Ends at **6 months** or when credits are exhausted, whichever comes first | No expiry |
| At expiry | **"AWS closes your account, and you'll lose access to your resources and data."** 90-day content retention, upgradeable within that window | Account stays open |
| Free-tier offers active | **"Always free" only** | **"Always free" *and* short-term trials** |
| Service reach | *"Access to select AWS services and features"* — *"limited from accessing a subset of AWS services and offerings that would immediately consume the entire Free Tier credit amount or require hardware purchases"* | *"Access to all AWS services and features"* |
| Promotional credits | **"Not eligible for other promotional credits and discounts"** | **Eligible** |

Sources: [Choosing a plan (AWS Billing docs)](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html), [Explore AWS services with AWS Free Tier](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html), [AWS Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/), [AWS Free Tier Terms](https://aws.amazon.com/free/terms/). All read 18 Sep 2026.

Beyond the credits, both plans get **"over 30 always free services that offer monthly free usage limits"** — permanent monthly allowances, not a trial.

> ### ⚠️ Pick the **Paid account plan** at signup. Not the Free plan.
>
> Three reasons, in order of how badly each one bites:
>
> 1. **A Free-plan account cannot redeem promotional credits.** Verbatim from the billing docs: *"Free account plans are not eligible for other promotional credits and discounts."* If the team wins $3,000 in AWS credits, or the organisers hand out event credits, **a Free-plan account cannot take them.** You would have to upgrade first.
> 2. **Free-plan accounts get "Always free" offers only — no short-term trials.** Comprehend's and Textract's free allowances are both *time-limited trials* (§A.4). On a Free plan they are, by AWS's own taxonomy, not active. That is the difference between $0 and a few dollars — small, but it also means the free-tier numbers you planned around silently do not apply.
> 3. **The Free plan closes the account at 6 months** and takes the demo URL with it.
>
> The Paid plan carries the identical $100 + $100 credits. At the spend level in §A.7 those credits cover roughly two to eight years of this project. The only thing the Paid plan adds is *exposure* to a bill — which a zero-threshold AWS Budget alert and the §B.6 hygiene steps cap at effectively nothing.

## A.4 Per-service free allowance, for this exact stack

| Service | Free allowance | Type | Free at demo scale? |
|---|---|---|---|
| **AWS Lambda** | **1,000,000 requests/month + 400,000 GB-seconds/month** | Always free (encoded as a global `$0.00` tier in the Price List, i.e. not time-limited) | **Yes, by ~100×.** |
| **Lambda Function URLs** | No separate charge — you pay only the underlying Lambda requests + duration | n/a | **Yes.** No line item exists for function URLs in the Lambda price list. |
| **DynamoDB** | **25 GB storage** free per month. Also 25 provisioned WCU + 25 RCU and 2.5M Streams reads. | Always free | **Storage yes. Requests: see the trap in §A.5.** Cost still rounds to ~$0.00. |
| **Amazon S3** | 5 GB Standard, 20,000 GET, 2,000 PUT *(widely reported; see note)* | **Legacy 12-month tier** | Effectively yes — but assume $0 allowance and price it directly: it is still under $0.05/month. |
| **Amazon Comprehend** | **50,000 units (5,000,000 characters) per API per month, for 12 months** from your first request | **12-month trial** → Paid plan only | Yes on a Paid plan. On a Free plan, assume you pay — which is ~$1.50–2.50/month. |
| **Amazon Textract** | **1,000 pages/month of Detect Document Text, for three months** | **3-month trial** → Paid plan only | Yes (50 pages ≪ 1,000). Even unfree it is $0.08. |
| **Amazon Bedrock (Nova)** | **None.** | — | **No. Bedrock has no free tier at all.** See §A.5. |
| **CloudWatch** | **10 custom metrics · 10 alarms · 3 dashboards (≤50 metrics each) · 1,000,000 API requests · 5 GB Logs (ingestion + archive storage + Logs Insights scan, combined) · 1,800 min Live Tail** | Always free | **Yes, if you set log retention.** See §A.5. |
| **AWS X-Ray** | **100,000 traces stored/month + 1,000,000 traces retrieved or scanned/month** | Always free (`$0.00` tier in the ap-south-1 price list) | **Yes, by ~200×.** |

Sources: [Lambda pricing](https://aws.amazon.com/lambda/pricing/) · [DynamoDB on-demand pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/) · [Comprehend pricing](https://aws.amazon.com/comprehend/pricing/) · [Textract pricing](https://aws.amazon.com/textract/pricing/) · [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) · Price List API for `ap-south-1` (Lambda, DynamoDB, S3, Comprehend, Textract, X-Ray, Bedrock), all read 18 Sep 2026.

**Two honesty notes on this table.**

- *S3's 5 GB:* the [S3 pricing page](https://aws.amazon.com/s3/pricing/) now leads with the $200-credits language and no longer enumerates the 5 GB / 20,000 GET / 2,000 PUT allowance on the page itself. The `ap-south-1` S3 price list contains **no `$0.00` free-tier SKU** — unlike Lambda and X-Ray, which both carry explicit global `$0.00` tiers. That asymmetry is consistent with S3's allowance being the legacy 12-month offer rather than an always-free one. **Treat the exact S3 free allowance as unverified** and price S3 directly; at this workload it is pennies either way.
- *Trial vs always-free classification:* AWS names the durations (Comprehend 12 months, Textract 3 months) but does not publish a service-by-service Always-Free / Short-Term-Trial list in the docs — the FAQ redirects to the filterable widget on `aws.amazon.com/free`. **Mapping "12-month/3-month" → "short-term trial" → "Paid-plan only" is my inference from the verified rule** that Free-plan accounts get *"Access to Always free services"* while Paid-plan accounts get *"Always free services and short-term trial offers"*. It is a strong inference. It is not a quote.

## A.5 Every service here with no free tier, or a charge that will surprise you

**1. Amazon Bedrock — no free tier, at all.** There is no `$0.00` tier for any Nova SKU in the `ap-south-1` price list, and the Bedrock pricing page publishes no free allowance. The only "free" Bedrock is Free Tier *credits* being spent on it. This is the single largest line on the bill (§A.7).

`ap-south-1` on-demand rates *[Price List API, 18 Sep 2026]*:

| Model | Input / 1K tokens | Output / 1K tokens |
|---|---|---|
| `amazon.nova-pro-v1:0` | **$0.00094** ($0.94/M) | **$0.00376** ($3.76/M) |
| `amazon.nova-lite-v1:0` | **$0.000071** ($0.071/M) | **$0.000284** ($0.284/M) |
| `amazon.nova-micro-v1:0` | **$0.000041** | **$0.000164** |
| Nova Pro, `flex` service tier | $0.00047 | $0.00188 (half price, higher latency) |
| Nova Pro, cache read | $0.000235 | — |

> **Nova Lite is 13× cheaper than Nova Pro on input and 13× on output.** The agent reasoning loop — three tool calls, structured tool args, no vision — does not need Pro. Run the loop on `apac.amazon.nova-lite-v1:0` and reserve `apac.amazon.nova-pro-v1:0` for the Tier-3 Indic multimodal call only. That one change takes the model line from ~$7.50/month to ~$1/month. Both are multimodal, so Lite is a live fallback if Pro's Devanagari quality disappoints (PRD open question 4).

**2. Comprehend bills a 3-unit (300-character) minimum per request — confirmed.** Verbatim from the [Comprehend pricing page](https://aws.amazon.com/comprehend/pricing/): *"with a 3 unit (300 character) minimum charge per request"*, where *"1 unit = 100 characters"*. `ap-south-1` `DetectPiiEntities` is **$0.0001 per unit** for the first 10M units/month *[Price List API]*, i.e. **$0.0003 is the floor for any single call**, however short the string.

The PRD's warning is right and the arithmetic is worth stating: scanning five fields of ~30 characters each as five separate calls costs 5 × 3 = **15 units**. Batching the same 150 characters into one call costs **3 units** (the minimum). That is a **5× multiplier for free**, and it grows with field count. **One `DetectPiiEntities` call per hop. Never one per field.**

**3. DynamoDB on-demand has no free request allowance.** The always-free 25 read/write *capacity units* apply to **provisioned mode only**. The `ap-south-1` price list confirms it: `APS3-ReadCapacityUnit-Hrs` and `APS3-WriteCapacityUnit-Hrs` both carry a `$0.00` tier for the first 18,600 unit-hours; `APS3-ReadRequestUnits` and `APS3-WriteRequestUnits` carry **no `$0.00` tier**. On-demand rates: **$0.1425 per million read request units, $0.71 per million write request units** *[Price List API]*. The 25 GB storage allowance applies to both modes.

At 1,500 audit rows/month this is **$0.002**. It does not matter financially. It matters because "DynamoDB is free tier" is a sentence a judge might question, and the accurate answer is "storage is; on-demand requests are not; it costs two-tenths of a cent."

**4. Amazon Bedrock Data Automation — no free tier, confirmed, and it *is* priced in Mumbai.** `ap-south-1` *[Price List API]*: **Standard $0.01 per page processed**, Custom $0.04/page, Standard images $0.003, video $0.05/min. **No `$0.00` tier of any kind.** The PRD's $0.010/page and "no free tier" are both correct. But the PRD also rejects BDA partly for "a cross-region APAC hop" — and the existence of `APS3-DataAutomation-*` SKUs suggests BDA bills natively in Mumbai. The rejection still stands on cost and on Textract-sync being sufficient for single-page fixtures; just do not put the cross-region claim in the writeup without checking it (§B.7).

**5. CloudWatch Logs will be the sleeper bill if you log payloads.** `ap-south-1` ingestion is **$0.67/GB** for custom log data in the Standard log class *[Price List API]* — **34% more than us-east-1's $0.50**. Storage is $0.03/GB-month, Logs Insights scan $0.0067/GB. The 5 GB always-free allowance covers ingestion + archive + Insights scan *combined*. And: **CloudWatch Logs retention defaults to never expiring** — *"By default, log data is stored in CloudWatch Logs indefinitely"* ([docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)). A guardrail that prints every normalized document to stdout for debugging will eat 5 GB faster than you expect. Set retention to 3 days on both log groups at deploy time (§B.6).

**6. NAT Gateway, if anything ends up in a VPC.** Nothing in this stack needs a VPC. If one appears, a NAT Gateway bills hourly plus per-GB with no free tier. The commonly quoted *~$33/month* figure is **unverified for `ap-south-1`** (NAT is billed under the EC2 price list, which I did not pull) and is not in the PRD — do not attribute it there. The advice is identical regardless of the exact number: **do not attach these Lambdas to a VPC.**

**7. New accounts have reduced Lambda quotas.** From the [Lambda quotas page](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html): *"New AWS accounts have reduced concurrency and memory quotas for Lambda Functions and Lambda MicroVMs. AWS raises these quotas automatically based on your usage."* A brand-new account may not be able to allocate the memory you assume. Check Service Quotas before assuming 3,008 MB is available, and size the function accordingly — this is a step-1 discovery, not a Sunday-afternoon one.

## A.6 Credit programmes that could land within 48 hours

| Route | Verdict |
|---|---|
| **Ask the hackathon organisers** | **The only one that reliably works in time.** The rules explicitly invite it: *"If you need more than that, you can request credits from the organisers."* **Do this tonight.** |
| **AWS Free Tier $100 + $100** | Instant. $100 lands at account creation; the second $100 comes from completing "Explore AWS" activities in the console widget. Requires nothing but a signup. |
| **Builder Center Student Rewards** | $10 at 7 badges, $20 more at 14. Badges come from publishing articles and commenting. Possible inside 48 hours if someone writes, but it is $10–30 and the effort is better spent on the blog-prize post anyway. |
| **AWS Educate** | Still live as a learning platform (self-paced labs, badges, job board, "no credit card needed", registration from age 13 — [AWS Educate](https://aws.amazon.com/education/awseducate/), read 18 Sep 2026). **The current page does not advertise AWS credits or a sandbox account.** Third-party guides claiming "$100 AWS Educate credits, approved in 1–3 days" are **unverified against any AWS page I could read today.** Do not plan around it. |
| **AWS Academy** | Institution-gated: your college must be an approved AWS Academy member and enrol you. Not obtainable by an individual in 48 hours. |
| **AWS Activate (startup credits)** | Requires a company, usually an accelerator/VC referral for the larger tiers. Not a 48-hour path for a student team. |

**Plain answer:** apart from the organisers and the automatic Free Tier credits, **nothing arrives in time**. Build on the Free Tier's $200 and message the organisers now as a backstop.

## A.7 Bottom line

**Yes — this project can be built, demoed and left running on a new AWS account for effectively nothing, and $200 of free-tier credits covers it for years rather than weeks.**

Lambda, Function URLs, DynamoDB storage, CloudWatch and X-Ray are all comfortably inside always-free monthly allowances at demo scale — Lambda by about 100×, X-Ray by about 200×. The only services that will ever produce a non-zero line are Bedrock (no free tier), Comprehend and Textract (trial allowances that cover this workload but should be priced as if they don't).

Priced at full `ap-south-1` rates with **no free tier assumed at all**, at the PRD's demo scale of 500 invocations × 3 tool calls + 50 document pages per month:

| Line | Assumption | Monthly |
|---|---|---|
| Lambda (both functions, arm64) | 1,000 requests, ~5,000 GB-s | **$0.00** (inside 1M req / 400k GB-s) |
| Bedrock — **Nova Pro** for the whole loop | 5M input + 750K output tokens | **$7.52** |
| Bedrock — **Nova Lite** loop, Pro for Indic only | same token volume | **~$0.60** |
| Comprehend `DetectPiiEntities`, batched per hop | 1,500 calls ≈ 15,000 units | **$1.50** |
| Comprehend, naively per field (5 fields/hop) | 7,500 calls × 3-unit minimum = 22,500 units | **$2.25** — the 300-char floor, visible |
| Textract `DetectDocumentText` | 50 pages @ $0.0015/page | **$0.08** |
| DynamoDB on-demand | 3,000 WRU + reads, <1 GB stored | **~$0.01** |
| S3 (session objects) | a few hundred PUT/GET, <1 GB | **<$0.05** |
| CloudWatch Logs | <5 GB with 3-day retention | **$0.00** |
| **Total, Nova Pro throughout** | | **≈ $9.20 / month** |
| **Total, Nova Lite loop + Pro for Indic** | | **≈ $2.25 / month** |

**$200 in credits at $2.25/month is about 7 years. At $9.20/month it is about 21 months.** Either way the credits expire (12 months from account creation) long before the money runs out — which is the correct problem to have.

**Idle cost after the event is effectively $0.00.** Every service here is request-priced; with no traffic there is nothing to bill but a fraction of a gigabyte of S3 and DynamoDB storage, both inside always-free allowances. See §B.6 for the four settings that guarantee it.

The one thing that can kill the demo URL is **not cost — it is the Free plan closing the account at 6 months.** Choose the Paid plan.

---

# PART B — Service inventory for the build

## B.1 ap-south-1 availability

| Service / feature | Available in ap-south-1? | Evidence |
|---|---|---|
| Lambda, arm64, Python 3.12 | **Yes** | Region-wide GA; `ap-south-1` SKUs including `APS3-Lambda-GB-Second-ARM` in the price list |
| **Lambda Function URLs** | **Assume yes; verify in 60 seconds** | The docs say *"Function URLs are not supported in all AWS regions"* and point at a filterable capability explorer rather than a list. `ap-south-1` is a long-standing major region. **Check: §B.7** |
| DynamoDB | **Yes** | Full `ap-south-1` price list |
| S3 | **Yes** | Full `ap-south-1` price list |
| **Amazon Comprehend** | **Yes — named explicitly** | [Comprehend guidelines and quotas](https://docs.aws.amazon.com/comprehend/latest/dg/guidelines-and-limits.html) lists "Asia Pacific (Mumbai)" among supported regions |
| **Amazon Textract** | **Yes — named explicitly** | [Textract endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/textract.html): `textract.ap-south-1.amazonaws.com` |
| **Bedrock — Nova Pro, in-region** | **NO** | The [Nova Pro model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-pro.html) Regional-availability table marks `ap-south-1 (Mumbai)` as **In-Region ✗, Geo ✓, Global ✗** |
| **Bedrock — `apac.amazon.nova-pro-v1:0`** | **Yes** | Same model card: Geo inference IDs are `us.`, `eu.`, **`apac.amazon.nova-pro-v1:0`**; Geo is ✓ for `ap-south-1` |
| APAC profile's **destination regions** | **Not published** | The model card says: *"To retrieve current details for this inference profile, use the GetInferenceProfile operation."* **Check: §B.7** |
| CloudWatch / CloudWatch Logs | **Yes** | Full `ap-south-1` price list |
| X-Ray | **Yes** | `APS3-XRay-TracesStored` in the price list |

> ### The Bedrock finding that strengthens the PRD's argument
>
> The PRD chooses `apac.amazon.nova-*` over Claude because Claude in Mumbai is `global.*` only. True — and the model card adds a harder fact: **Nova Pro has no in-region option in `ap-south-1` either.** `amazon.nova-pro-v1:0` called directly against `bedrock-runtime.ap-south-1.amazonaws.com` is not an available path. The `apac.` profile is not a preference, it is **the only way to call Nova Pro from Mumbai.**
>
> The corresponding discipline: the APAC geo profile keeps requests *within the APAC geography*, not within India. AWS's own framing is *"Within geographic boundaries (such as US, EU, and APAC)"* ([cross-region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)). **Say "stays in APAC" in the video. Never say "stays in India."** A judge who runs `get-inference-profile` and sees Tokyo or Sydney in the destination list will puncture an over-claim in one sentence, and the accurate claim is already strong enough against Claude's global routing.
>
> Two more verified facts that belong in the writeup: *"There's no additional routing cost for using cross-Region inference. The price is calculated based on the Region from which you call an inference profile"* — so the `ap-south-1` rates in §A.5 are the correct ones. And *"All data transmitted during cross-Region operations remains on the AWS network and does not traverse the public internet. Data is encrypted in transit between AWS Regions."*

## B.2 Service-by-service

### AWS Lambda

**Operations called:** `CreateFunction`, `UpdateFunctionCode`, `UpdateFunctionConfiguration`, `CreateFunctionUrlConfig`, `AddPermission`, `GetFunctionUrlConfig`, `PutRetentionPolicy` (Logs). Runtime invocation arrives via the function URL, not an SDK call.

**Limits that matter** ([Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html), read 18 Sep 2026):

| Limit | Value |
|---|---|
| Max timeout | **900 s (15 min)** — the whole reason Function URLs beat API Gateway's 30 s |
| Memory | 128 MB – 10,240 MB, 1 MB steps; 1 vCPU-equivalent at 1,769 MB |
| **Invocation payload** | **6 MB request and 6 MB response (synchronous)**; 200 MB for a streamed response; **1 MB for request line + headers combined** |
| Deployment package | **50 MB zipped** via API/SDK/console; **250 MB unzipped including layers** |
| Layers | **5 per function** |
| `/tmp` | 512 MB – 10,240 MB |
| Env vars | 4 KB total |
| Resource-based policy | 20 KB |
| Control-plane API rate | **15 rps across all non-invoke APIs combined** — a rapid redeploy loop can throttle you |

`ap-south-1` pricing *[Price List API]*: **arm64 $0.0000133334 per GB-second**, x86 $0.0000166667 — arm64 is **20% cheaper**; requests $0.0000002 each on both architectures. Free tier is 1,000,000 requests + 400,000 GB-seconds per month, and the GB-second allowance is architecture-neutral.

**Easy to get wrong:**

- **The 250 MB unzipped ceiling is the real constraint**, not the 50 MB zip. `cedarpy` + `strands-agents` + `boto3` + the Strands layer must fit under it together. Measure `du -sh pkg/` before zipping, not after the upload fails.
- **The 6 MB response cap** bites if the UI ever returns a rendered page image or a base64 PDF through the same Function URL. Return a presigned S3 URL instead.
- **New-account quota reduction** (§A.5 #7) — check Service Quotas before assuming a memory size.
- `--architectures arm64` must be set at `create-function` time; changing it later means a full redeploy of the package built for the other platform.

### Lambda Function URLs

**Config:** `AuthType=NONE`, no qualifier (targets `$LATEST`), CORS configured on the URL rather than in handler code.

> ### ⚠️ The change that will produce a 403 on Sunday afternoon
>
> Verbatim from [Control access to Lambda function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html) (read 18 Sep 2026):
>
> > **"Starting in October 2025, new function URLs will require both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` permissions."**
>
> The console and AWS SAM add the resource-based policy for you. **The AWS CLI does not.** *"If you're using the AWS CLI, AWS CloudFormation, or the Lambda API directly, you must add the policy yourself"* — and *"Each statement must be added in a separate command."* The PRD's deploy snippet does `create-function-url-config` only, which leaves the URL returning **403 Forbidden even with `AuthType=NONE`**.
>
> The two commands the deploy script needs, immediately after `create-function-url-config`:
>
> ```
> aws lambda add-permission --function-name <fn> --statement-id UrlPolicyInvokeURL \
>   --action lambda:InvokeFunctionUrl --principal "*" --function-url-auth-type NONE --region ap-south-1
>
> aws lambda add-permission --function-name <fn> --statement-id UrlPolicyInvokeFunction \
>   --action lambda:InvokeFunction --principal "*" --invoked-via-function-url --region ap-south-1
> ```
>
> This is PRD §11.1 step 1 — "the single highest-risk step". Add both lines to the script before the first deploy.

**Other things worth knowing:**

- Endpoint shape `https://<url-id>.lambda-url.ap-south-1.on.aws`. **The URL never changes once created — but deleting and recreating gives a different one.** Never delete the URL after the video is recorded.
- Payload format is **API Gateway payload format version 2.0** — `event["body"]`, `event["requestContext"]["http"]["method"]`, `event["rawPath"]`, `isBase64Encoded`. Binary uploads arrive base64-encoded.
- **Deleting a `NONE`-auth function URL does not delete its resource-based policy.** Clean up manually if you ever recreate.
- **CORS:** configure on the URL. If you also emit `Access-Control-Allow-Origin` from the handler you get duplicate headers on non-preflight requests and a browser error — *"The 'Access-Control-Allow-Origin' header contains multiple values '*, *', but only one is allowed"*. Pick one place; the docs recommend the URL config.
- **The free kill switch:** setting reserved concurrency to `0` makes the URL return 429 for everything, and setting it back reactivates. Zero cost, fully reversible, no resource deleted.

### Amazon DynamoDB

**Operations:** `PutItem` (audit rows, one per tool call, written from the `AuditHook`), **`UpdateItem`** (the ledger spend — an atomic `ADD` on a String Set; DynamoDB is the ledger authority per PRD §11.2), `Query` (dashboard reads by `pk = SESSION#<session_id>`), optionally `BatchWriteItem`. `CreateTable` / `DescribeTable` at deploy.

**Limits:** max item **400 KB** including attribute names ([Constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html)); Query/Scan return at most **1 MB per page**; on-demand table default ceiling **40,000 read request units and 40,000 write request units per table** ([Quotas](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html)); no account-level throughput quota applies to on-demand tables.

`ap-south-1` on-demand *[Price List API]*: **$0.1425/M read request units, $0.71/M write request units, $0.285/GB-month storage beyond the free 25 GB.**

**Easy to get wrong:**

- On-demand request units have no free allowance (§A.5 #3). Cost is still ~$0.002/month.
- The PRD's key design (`pk = SESSION#<session_id>`, `sk = CALL#<ts>#<seq>` or `METER#<subject>`) supports "show me one session, all its calls and meters" in a single Query, but **not** "show me the last 50 decisions across all sessions" — a Query needs a partition key. The dashboard's cross-session live feed either needs a GSI (e.g. `pk = "FEED"`, `sk = <timestamp>#<session_id>`) or a Scan. **A Scan over a few thousand small items is fine at hackathon scale and costs nothing.** Take the Scan; a GSI is 20 minutes of schema work you do not have.
- Leave point-in-time recovery and backups **off** — both bill on stored bytes, neither is in the free tier.
- Audit items are tiny (~1–2 KB), so the 400 KB ceiling is irrelevant — unless someone is tempted to put the normalized document text in the row. **Don't. PRD §10 already forbids raw values.**

### Amazon S3

**Operations (via `S3SessionManager`):** `PutObject`, `GetObject`, `ListObjectsV2`, `DeleteObject`. Key layout from the [Strands session-management docs](https://strandsagents.com/docs/user-guide/concepts/agents/session-management/):

```
<prefix>/session_<session_id>/
  session.json
  agents/agent_<agent_id>/
    agent.json
    messages/
```

`ap-south-1` *[Price List API]*: **$0.025/GB-month** (first 50 TB), **$0.005 per 1,000 PUT/COPY/POST/LIST**, **$0.004 per 10,000 GET**.

> ### ⚠️ Correction to PRD §5: `S3SessionManager` does not lock either
>
> An earlier draft justified S3 over `FileSessionManager` because *"FileSessionManager has no locking and corrupts on concurrent writes"*. The Strands docs are blunter, and the warning is **not** file-backend-specific:
>
> > **"Session managers are not thread-safe and take no distributed lock."**
>
> The named failure modes are *"overlapping writers using identical session/agent IDs"* and *"simultaneous cold starts both succeeding with the later write winning."* Both are exactly what two Lambda execution environments handling the same `session_id` will do.
>
> S3 is still the right choice — it is durable, survives cold starts, needs no code, and restores on `session_id`, none of which a Lambda's local `/tmp` does. But the reason is **durability across invocations, not locking.** Say that in the writeup.
>
> **The PRD's answer (§11.2) is the right one and it is cheap:** keep `S3SessionManager` as the *cache* and put the authoritative counter in DynamoDB, where `UpdateItem … ADD seen :types` on a String Set is a server-side atomic set-union that cannot lose a spend, and `ReturnValues=ALL_OLD` hands back `ledger_before` in the same round trip. The last-write-wins ceiling then only costs conversation history, never budget. What remains honest to state in the writeup: two *separate invocations* on one session can still each authorize against a pre-spend snapshot, so the budget can be exceeded by one hop's worth per concurrent invocation — a `ConditionExpression` on the meter row is the production fix.
>
> Also worth a look if the clock allows: the docs now recommend **`SnapshotSessionManager`** for new single-agent sessions, with `FileSessionManager` merely "still supported". Whether a snapshot manager has an S3 backend is **unverified** — a 5-minute read of the session-management page during step 7 will settle it.

**Easy to get wrong:** bucket names are globally unique (prefix with the account ID); Block Public Access is on by default and should stay on — the Lambda reads via its execution role, not public URLs.

### Amazon Comprehend — `DetectPiiEntities`

**Operation:** `DetectPiiEntities(Text, LanguageCode)` → `Entities[{Score, Type, BeginOffset, EndOffset}]`.

**Limits** ([API reference](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectPiiEntities.html), [quotas](https://docs.aws.amazon.com/comprehend/latest/dg/guidelines-and-limits.html)):

- **`Text` max 100 KB UTF-8.** Exceeding it raises `TextSizeLimitExceededException` (HTTP 400) — *"The size of the input text exceeds the limit. Use a smaller document."* This is PRD §9's "volume, not format" hole; chunk before you call.
- `LanguageCode` is **required**.
- **No published TPS.** *"Amazon Comprehend applies dynamic throttling to synchronous requests... we recommend that you turn on billing alerts or implement rate-limiting in your application."* Retry `ThrottlingException` with backoff — boto3's default `standard` retry mode does this, but only for 3 attempts.
- Batch alternative `BatchDetectPiiEntities` does not exist; the batch APIs cap at **25 documents × 5 KB each** and do not cover PII.

**Indian entity types confirmed** ([Detecting PII entities](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html)): `IN_AADHAAR` (*"a 12-digit unique identification number... The Aadhaar format has a space or hyphen after the fourth and eighth digit"*), `IN_PERMANENT_ACCOUNT_NUMBER`, `IN_VOTER_NUMBER`, `IN_NREGA`. Universal types include `NAME`, `PHONE`, `ADDRESS`, `EMAIL`, `AGE`, `DATE_TIME`, `CREDIT_DEBIT_NUMBER`, `DRIVER_ID`, `PASSWORD`, `USERNAME`, `IP_ADDRESS` — the full list is on that page and is the right source for the demo's `reveal_*` Cedar action names.

> ### 🔎 A 10-minute experiment that could save the Tier-3 build
>
> The developer guide says: *"You can use Amazon Comprehend to detect PII entities in **English or Spanish** text documents."* The PRD builds Tier 3 (Nova multimodal on the image) on that constraint.
>
> But the **API reference** lists `LanguageCode` valid values as:
>
> > `en | es | fr | de | it | pt | ar | hi | ja | ko | zh | zh-TW`
>
> — **including `hi` (Hindi).** That enum is probably shared across Comprehend's language codes rather than specific to PII, and the prose is the authoritative statement of support. **But the cost of finding out is one API call.**
>
> Run `DetectPiiEntities(Text=<Devanagari name + Aadhaar>, LanguageCode="hi")` in the first hour. Three outcomes: `UnsupportedLanguageException` → the PRD stands unchanged, Tier 3 goes to Nova. Accepted but garbage → same. Accepted and it finds the name → **the Indic tier gets offsets and confidence scores from a real PII model instead of substring-matching an LLM's output**, which is a materially better demo and a better line in the writeup. Test it before building Tier 3 either way.

### Amazon Textract — `DetectDocumentText`

**Operation:** `DetectDocumentText(Document={Bytes | S3Object})` → `Blocks[]` of `PAGE` / `LINE` / `WORD` with `Confidence` and `Geometry.BoundingBox`.

**Limits** ([Set quotas in Amazon Textract](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html), read 18 Sep 2026) — verbatim where it matters:

- *"For synchronous operations, JPEG, PNG, PDF, and TIFF files have a limit of **10 MB in memory**. PDF and TIFF files also have a limit of **1 page**."* — the PRD's central Textract constraint, confirmed.
- Async: PDF/TIFF up to 500 MB and 3,000 pages, **S3-only**. Out of scope per PRD §11.
- *"Amazon Textract supports **English, French, German, Italian, Portuguese, and Spanish** text detection."* — **Latin scripts only, confirmed.** No Devanagari, no Tamil. Handwriting is English-only.
- *"Amazon Textract does not support vertical text."* Images ≤ **10,000 pixels** on all sides. Minimum detectable text height **15 pixels** (≈8 pt at 150 DPI) — **scan the Aadhaar fixture at 200–300 DPI**, because the 12-digit number in small print is exactly what falls under 15 px on a low-res phone photo.
- PDFs cannot be password-protected; **XFA-based PDFs are not supported.**
- Character set explicitly includes **`₹`** — useful for the payslip fixture.

**`ap-south-1` quota that will bite a load test** ([Textract endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/textract.html)): synchronous `DetectDocumentText` is **5 transactions per second per account in Mumbai** — versus 25 in us-east-1 and us-west-2. Fine for a demo, instantly throttling under any burst.

`ap-south-1` price *[Price List API]*: **USD 1.50 per 1,000 pages** for sync `DetectDocumentText` (0–1M pages tier) = **$0.0015/page**. 50 pages = **$0.075**. The PRD's $0.08 is right.

**Easy to get wrong:**

- **`Document.Bytes` takes raw bytes.** boto3 base64-encodes for you. Base64 it yourself first and you send a double-encoded blob that Textract rejects with an unhelpful error. This is the single most common Textract bug.
- **`Geometry.BoundingBox` is normalized 0–1**, as ratios of page width and height — not pixels. Multiply by the rendered image dimensions before drawing PRD §11 item 13's redaction boxes.
- The 10 MB limit is *in memory* after decoding, not the file size on disk.

### Amazon Bedrock — Nova via `apac.*`

**Operations:** `Converse` / `ConverseStream` (what Strands' `BedrockModel` uses), or `InvokeModel`. `GetInferenceProfile` once, for the §B.7 check.

**Model IDs:** `apac.amazon.nova-pro-v1:0`, `apac.amazon.nova-lite-v1:0`. Nova Pro: **300K-token context, 5K max output**, input modalities text + image + video, output text only. Supports Converse, Guardrails, prompt caching (min 1K tokens/checkpoint, 4 checkpoints, 5-minute TTL). **Does not support** structured outputs or `CountTokens` — relevant if the audit row wants exact token counts.

**Model access:** *"Access to all Amazon Bedrock foundation models is enabled by default with the correct AWS Marketplace permissions in all commercial AWS Regions"* ([Request access to models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)). **Amazon's own models are not sold through AWS Marketplace and have no product ID**, so Nova should need no subscription step at all. Third-party models auto-subscribe on first invoke and can return `AccessDeniedException` for up to ~2 minutes while that settles — one more reason Nova is the low-risk choice on a deadline. Verify with `get-foundation-model-availability` (§B.7) rather than discovering it on camera.

> ### ⚠️ The IAM shape that breaks cross-region inference
>
> From [Prerequisites for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html), emphasis theirs:
>
> > **"When you specify an inference profile in the `Resource` field in the first statement, you must also specify the foundation model in each Region associated with it."**
>
> A policy that grants `bedrock:InvokeModel*` on only `arn:aws:bedrock:ap-south-1:<acct>:inference-profile/apac.amazon.nova-pro-v1:0` **will fail** when the profile routes to Tokyo or Sydney. You need the profile ARN **and** `arn:aws:bedrock:<each-destination-region>::foundation-model/amazon.nova-pro-v1:0`.
>
> For a two-day build, use the documented wildcard form and note the tightening as future work:
>
> ```
> "Action":   ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
> "Resource": ["arn:aws:bedrock:*::foundation-model/amazon.nova-*",
>              "arn:aws:bedrock:*:*:inference-profile/apac.amazon.nova-*"]
> ```
>
> Scoping to an enumerated destination list is a five-minute edit **once `GetInferenceProfile` tells you what the list is** (§B.7) — worth doing before submission, because "least privilege across the exact geo boundary" is a good line in a governance project's writeup.

### CloudWatch and CloudWatch Logs

**Operations:** `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` (the Lambda runtime does all three); `logs:PutRetentionPolicy` at deploy.

**Free, always:** 10 custom metrics · 10 alarms (standard resolution) · 3 dashboards of ≤50 metrics · 1,000,000 API requests · **5 GB of Logs covering ingestion + archive storage + Logs Insights scan combined** · 1,800 minutes of Live Tail ([CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)).

**`ap-south-1` rates beyond that** *[Price List API]*: ingestion $0.67/GB Standard class ($0.335 Infrequent Access), storage $0.03/GB-month, Logs Insights scan $0.0067/GB, standard alarm $0.10/alarm-month, custom metrics $0.30/metric-month for the first 10,000, Live Tail $0.01/minute.

**Easy to get wrong:** retention defaults to never expiring (§A.5 #5). And **Lambda's built-in metrics — `Invocations`, `Errors`, `Duration`, `Throttles`, `ConcurrentExecutions` — are vended metrics, not custom metrics, so they are free and unlimited.** Only metrics you publish yourself (`PutMetricData`, or Embedded Metric Format inside a log line) count against the 10. If the disclosure meter ever wants a CloudWatch-backed metric, keep the cardinality at ten or fewer distinct metric names — one metric per *subject* would blow past it immediately.

### AWS X-Ray — worth enabling?

**Free:** 100,000 traces stored/month and 1,000,000 traces retrieved or scanned/month *[Price List API: `Global-XRay-TracesStored` and `Global-XRay-TracesAccessed` at `$0.00`]*. Beyond: `ap-south-1` **$5.00 per million traces stored** and **$0.50 per million retrieved or scanned**. At 500 invocations/month you are two orders of magnitude inside free.

**Verdict: enable active tracing, do not instrument.**

`aws lambda update-function-configuration --tracing-config Mode=Active` costs one CLI flag and five IAM actions, and gives a service map plus per-invocation duration in the console — a real screenshot for the video at zero cost and zero code.

What it does **not** give without adding `aws-xray-sdk` and patching boto3 is per-downstream-call subsegments (the Comprehend / Textract / Bedrock breakdown). That instrumentation adds an import to the cold start, more package weight against the 250 MB ceiling, and code to the critical path — on a two-day clock, against Must-list items.

**And the project already has a better observability story than X-Ray.** PRD §10's audit row carries `latency_ms { normalize, detect, cedar, total }` **per tool call, joined to the policy decision** — which is exactly the thing X-Ray cannot show you, because X-Ray has no idea what a disclosure budget is. A dashboard panel reading those numbers out of DynamoDB is on-theme, on-brand for a governance product, and is being built anyway. **That is the observability story. X-Ray is a free screenshot on top of it.**

## B.3 IAM action list

Four policies. Every action below is one I verified in service documentation or used in a verified example.

**1. Data-plane Lambda execution role** — the agent

```
logs:CreateLogGroup
logs:CreateLogStream
logs:PutLogEvents

comprehend:DetectPiiEntities
comprehend:ContainsPiiEntities          # only if you add the cheap pre-filter

textract:DetectDocumentText

bedrock:InvokeModel
bedrock:InvokeModelWithResponseStream

s3:GetObject
s3:PutObject
s3:DeleteObject
s3:ListBucket

dynamodb:PutItem
dynamodb:UpdateItem                     # the atomic ledger spend — ADD on a String Set
dynamodb:BatchWriteItem
dynamodb:Query
dynamodb:GetItem
```

Resource scoping: `comprehend:*` and `textract:*` take `"Resource": "*"` (neither has ARN-addressable resources for these calls). `s3:ListBucket` scopes to the bucket ARN; the three object actions scope to `<bucket-arn>/*`. DynamoDB scopes to the table ARN. Bedrock scopes per the block in §B.2 — **profile ARN plus foundation-model ARNs in every destination region.**

**2. Control-plane Lambda execution role** — policy serving, audit reads, UI

```
logs:CreateLogGroup
logs:CreateLogStream
logs:PutLogEvents

dynamodb:Query
dynamodb:GetItem
dynamodb:Scan                           # cross-session live feed; see §B.2 DynamoDB
                                        # no write actions: there is no POST /decisions —
                                        # the data plane writes DynamoDB directly (PRD §5)

s3:GetObject                            # only if agent.cedar lives in S3
```

**3. Add to either role if active tracing is on**

```
xray:PutTraceSegments
xray:PutTelemetryRecords
xray:GetSamplingRules
xray:GetSamplingTargets
xray:GetSamplingStatisticSummaries
```

(All five are the standard set; the AWS-managed `AWSXRayDaemonWriteAccess` policy is the lazier equivalent.)

**4. Deployment identity** — the human or CI doing the zip-and-push

```
iam:CreateRole
iam:GetRole
iam:PutRolePolicy
iam:AttachRolePolicy
iam:PassRole

lambda:CreateFunction
lambda:GetFunction
lambda:UpdateFunctionCode
lambda:UpdateFunctionConfiguration
lambda:CreateFunctionUrlConfig
lambda:GetFunctionUrlConfig
lambda:UpdateFunctionUrlConfig
lambda:AddPermission
lambda:GetLayerVersion                  # required to attach the public Strands layer

dynamodb:CreateTable
dynamodb:DescribeTable

s3:CreateBucket
s3:PutBucketPolicy

logs:PutRetentionPolicy

bedrock:GetInferenceProfile             # the §B.7 destination-region check
bedrock:GetFoundationModelAvailability  # the §B.7 model-access check
```

**Three scoping notes.** `iam:PassRole` should be conditioned on `"iam:PassedToService": "lambda.amazonaws.com"` — it is the one action here that is genuinely dangerous unscoped. `lambda:GetLayerVersion` must cover the cross-account Strands layer ARN from PRD §7. And `bedrock:InvokeModel*` in the AWS example policies is a wildcard covering both `InvokeModel` and `InvokeModelWithResponseStream`; spelled out above so the enumeration is unambiguous.

## B.4 Keeping the demo URL alive for judging, at no cost

Everything in this stack is request-priced. With no traffic, Lambda, Function URLs, Bedrock, Comprehend, Textract and DynamoDB on-demand requests all bill **$0.00**. The only residue is stored bytes, and at this scale all of it is inside always-free allowances. **The idle steady state is genuinely zero.**

Four settings make that guaranteed rather than probable. All are one command each.

1. **`aws logs put-retention-policy --retention-in-days 3`** on both `/aws/lambda/*` log groups. Without it, retention is *never expire* and log storage grows forever. This is the only line item with a non-zero slope at idle.
2. **Keep DynamoDB in on-demand mode.** Provisioned mode bills capacity-hours whether or not anything reads. On-demand at zero traffic is zero.
3. **An AWS Budget with a near-zero threshold and an email action.** Budget pricing is **unverified** — a small number of budgets per account are commonly free; check the Billing console before creating several.
4. **Do not delete the function URL.** Confirmed in the docs: *"When you delete a function URL, you can't recover it. Creating a new function URL results in a different URL address."* A dead link in a submitted video is unrecoverable. If you need traffic stopped, set reserved concurrency to `0` — the URL survives, returns 429, and reverses instantly.

Optional, if S3 session objects accumulate: a lifecycle rule expiring `session_*` prefixes after 7 days. Under a gigabyte it is worth less than the two minutes it takes.

**The one real threat is not cost.** A **Free-plan** account closes 6 months after signup and *"you'll lose access to your resources and data"*, with 90 days of retention. Submissions close 20 September 2026; judging is days later, so the link survives judging either way — but it dies around March 2027 unless the account is on the Paid plan. §A.3 already recommends the Paid plan for a different reason. This is the second one.

## B.5 Corrections and additions to the PRD

Ordered by how much each one costs if missed. **The "PRD says" column quotes the pre-correction draft; PRD v2 has since absorbed rows 1–9.** It is kept as a correction log, not as a live description of the PRD.

| # | PRD said | Verified reality | Do |
|---|---|---|---|
| 1 | Deploy = `create-function-url-config --auth-type NONE` | Since **Oct 2025** function URLs need **both** `lambda:InvokeFunctionUrl` **and** `lambda:InvokeFunction` in the resource policy, added as **two separate `add-permission` calls** by the CLI | Add both lines to the deploy script **before** step 1 of §11.1 |
| 2 | Free Tier gives $200 in credits | True — but a **Free-plan** account **cannot redeem promotional credits** and **auto-closes at 6 months** | **Choose the Paid plan at signup.** Same credits, no cliff, can accept the prize credits |
| 3 | `S3SessionManager` chosen because *"FileSessionManager has no locking"* | *"Session managers are **not thread-safe and take no distributed lock**"* — applies to S3 too | Keep S3 as the **cache** (durability across invocations is the real reason) and make **DynamoDB the ledger authority** with an atomic `ADD` on a String Set — PRD §11.2 |
| 4 | Use `apac.*` because Claude in Mumbai is `global.*` only | **Nova Pro has no in-region option in `ap-south-1` either** — `apac.` is the only path, not a preference | Strengthen the claim. And say **"stays in APAC"**, never "stays in India" |
| 5 | Comprehend does English and Spanish only | The **API enum** accepts `hi`; the **developer guide** says English or Spanish | **One test call in the first hour.** If `hi` works, Tier 3 gets real offsets and scores |
| 6 | Model = `apac.amazon.nova-pro-v1:0` throughout | Nova **Lite** is **13× cheaper** on both input and output, equally multimodal | Lite for the agent loop, Pro for the Indic image call only. ~$7.50/mo → ~$1/mo |
| 7 | DynamoDB on-demand, free tier | Free tier covers **25 GB storage** and **provisioned** capacity units. On-demand request units have **no free allowance** | Nothing to change (~$0.002/mo). Just don't say "free tier" about it on camera |
| 8 | Comprehend under the 50,000-unit free tier at ~$0 | 50,000 units per API per month **for 12 months from first request** — a trial, not always-free | Price it as if unfree: **$1.50/month batched** |
| 9 | Textract 1,000 free pages/month for three months | Confirmed. `ap-south-1` **$1.50/1,000 pages**; 50 pages = **$0.075** | PRD's $0.08 stands |
| 10 | BDA rejected partly for *"a cross-region APAC hop"* | `APS3-DataAutomation-*` SKUs exist at **$0.01/page Standard**, suggesting native Mumbai billing | Rejection stands on cost + no free tier. **Drop the cross-region claim** unless §B.7 confirms it |
| 11 | — | **`ap-south-1` sync `DetectDocumentText` is 5 TPS**, vs 25 in us-east-1 | Do not batch-fire the fixture set |
| 12 | — | **New accounts get reduced Lambda concurrency and memory quotas** | Check Service Quotas at step 1, not Sunday |
| 13 | — | CloudWatch Logs ingest is **$0.67/GB in Mumbai**, 34% above us-east-1, and retention defaults to **never expire** | `put-retention-policy 3` at deploy |

## B.6 Five checks to run yourself, first hour, before anything is built

These are the claims I could not close from documentation, plus the two cheapest experiments with the biggest downstream effect. Each is one command.

```bash
# 1. Function URL support in ap-south-1. The docs decline to publish a region list.
#    This creates and immediately deletes a throwaway URL. If it errors, the whole
#    "Ship It needs a public URL" plan needs a different front door — know now.
aws lambda create-function-url-config --function-name <hello-world> \
    --auth-type NONE --region ap-south-1

# 2. APAC geo profile destination regions. The model card explicitly tells you to ask.
#    The answer decides both the IAM Resource list AND what you may claim in the video.
aws bedrock get-inference-profile \
    --inference-profile-identifier apac.amazon.nova-pro-v1:0 --region ap-south-1

# 3. Nova model access. Expect agreementAvailability AVAILABLE with no action needed.
aws bedrock get-foundation-model-availability \
    --model-id amazon.nova-pro-v1:0 --region ap-south-1

# 4. Does Comprehend accept Hindi for PII? UnsupportedLanguageException => PRD stands.
#    Anything else => Tier 3 may get real offsets instead of LLM substring matching.
aws comprehend detect-pii-entities --language-code hi --region ap-south-1 \
    --text "<Devanagari name + a seeded 12-digit Aadhaar>"

# 5. New-account Lambda quotas, before assuming a memory size.
aws service-quotas list-service-quotas --service-code lambda --region ap-south-1 \
    --query "Quotas[?contains(QuotaName,'oncurrent')||contains(QuotaName,'emory')]"
```

Optional, only if multi-page PDFs get promoted from Will-Not to Should:
`aws bedrock-data-automation list-blueprints --region ap-south-1` — settles PRD §7's cross-region claim about BDA.

---

## Sources

All read **18 September 2026**.

**Identity and the hackathon** — [AWS Builder ID and other AWS credentials](https://docs.aws.amazon.com/signin/latest/userguide/differences-aws_builder_id.html) · [AWS Builder Center](https://builder.aws.com/) · [Student Rewards on AWS Builder Center (AWS Weekly Roundup, 24 Aug 2026)](https://aws.amazon.com/blogs/aws/aws-weekly-roundup-student-rewards-on-aws-builder-center-local-zone-in-las-vegas-and-more-august-24-2026/) · [First Commit — rules](https://www.wemakedevs.org/aws/first-commit/rules) · [First Commit — event page](https://www.wemakedevs.org/aws/first-commit)

**Free tier** — [AWS Free Tier](https://aws.amazon.com/free/) · [Free tier restructure announcement, posted 16 Jul 2025](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/) · [AWS Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) · [AWS Free Tier Terms](https://aws.amazon.com/free/terms/) · [Explore AWS services with AWS Free Tier (Billing docs)](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html) · [Choosing a plan (Billing docs)](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html) · [AWS Educate](https://aws.amazon.com/education/awseducate/)

**Pricing** — [Lambda](https://aws.amazon.com/lambda/pricing/) · [DynamoDB on-demand](https://aws.amazon.com/dynamodb/pricing/on-demand/) · [S3](https://aws.amazon.com/s3/pricing/) · [Comprehend](https://aws.amazon.com/comprehend/pricing/) · [Textract](https://aws.amazon.com/textract/pricing/) · [Bedrock](https://aws.amazon.com/bedrock/pricing/) · [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/) · **AWS Price List bulk API, `ap-south-1`** for `AWSLambda`, `AmazonDynamoDB`, `AmazonS3`, `comprehend`, `AmazonTextract`, `AmazonBedrock`, `AmazonCloudWatch`, `AWSXRay` — `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json`

**Limits and APIs** — [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html) · [Creating and managing Lambda function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html) · [Invoking Lambda function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html) · [Control access to Lambda function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html) · [DynamoDB quotas](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html) · [DynamoDB constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html) · [Comprehend guidelines and quotas](https://docs.aws.amazon.com/comprehend/latest/dg/guidelines-and-limits.html) · [DetectPiiEntities API reference](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectPiiEntities.html) · [Detecting PII entities](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html) · [Textract set quotas](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html) · [Textract endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/textract.html) · [CloudWatch log groups and retention](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)

**Bedrock** — [Nova Pro model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-pro.html) · [Cross-region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) · [Supported regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html) · [Prerequisites for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html) · [Request access to models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)

**Strands** — [Session management](https://strandsagents.com/docs/user-guide/concepts/agents/session-management/)
