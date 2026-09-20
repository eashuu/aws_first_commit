# Seven things in the AWS docs that will change how you build an agent guardrail

*Bedrock Guardrails, Comprehend, Textract and Lambda Function URLs — and one I had to settle from two documents that disagree. Written from a build in ap-south-1 over Indian personal data.*

---

## The problem

An AI agent does not leak a database. It leaks one field at a time.

Call one returns a customer's name, and the policy allows it, because a name is not sensitive. Call two returns a phone number, and that is allowed too. Call three returns a PIN code, call four a date of birth. Every single decision was correct in isolation. By call four the agent is holding a re-identifiable person, and no per-call check anywhere in the stack was ever in a position to notice — because each one only ever saw its own call.

That is the failure we set out to control: not a forbidden field, but an accumulating one. The control has to be a property of *the person the data is about*, carried across calls, and it has to sit where the data actually enters the model — on what the tool **returns**, not on what the agent asks for.

## The stack

Python 3.12 on Lambda, arm64, behind a Function URL, in `ap-south-1`. Strands Agents for the agent loop, with the guardrail installed as interventions on the tool boundary. Cedar — embedded via `cedarpy`, not the managed service — answers three separate authorization questions per call: may this call happen, may this principal learn this field about this person given what the session already gave away, and may a redacted value be restored into this outbound argument. DynamoDB holds the disclosure ledger, keyed per subject, with atomic `ADD` on a string set so concurrent Lambdas cannot lose a write. Detection is tiered and unions rather than defers: local checksum validators for Aadhaar, PAN, GSTIN and IFSC, then Amazon Comprehend, then a multimodal pass for Indic-script documents. Amazon Bedrock runs Nova Lite for the agent loop. Textract normalises PDFs and images. S3 versions the policy bundle so it hot-reloads.

Roughly a weekend. The list below is what that weekend cost, and most of it was documented before I started.

## What fought back

If you are about to put a PII control in front of an AI agent's tool calls on AWS, this is the list I wish someone had handed me before I opened an editor. Every item is documented. That is the problem: each one is documented on the page you read *after* you have already built the thing that needed it.

I found these across two research passes done before writing any code, and the rest during the build. Four of them changed the architecture. One of them I expected to settle with a single CLI call and could not, for a reason that turned out to be worth more than the answer.

Nothing below is a criticism of any service. Several of these are AWS being unusually explicit about a boundary, and the exclusion notes are better than most vendors publish. They are just easy to miss.

---

## 1. Bedrock Guardrails' sensitive-information filter does not evaluate tool-use fields

This is the one that decided the whole design, so it goes first.

**The assumption:** Bedrock Guardrails is the AWS answer to "stop PII leaking from my model", so an agent that calls tools through Bedrock is covered.

**What the documentation says**, from the [sensitive-information filters page](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html), unedited:

> "This filter evaluates text content only. In tool use (function calling) workloads, it does not evaluate the following, so PII in these fields is neither blocked nor masked: PII the model generates into tool call arguments (`toolUse.input` in Converse, `tool_use` parameters in InvokeModel) … PII in tool results your application returns to the model (`toolResult`) … PII in the tool definitions you supply (`toolSpec.description`, `toolSpec.inputSchema`)."

Read that list again. `toolUse.input`, `toolResult`, `toolSpec` — those three fields *are* the agent's data surface. A tool returning a customer record returns it in `toolResult`. An agent about to send a phone number to an external API puts it in `toolUse.input`. The filter covers prompts and model responses, which is exactly what it says it covers, and which is not where agent data lives.

**What changed:** the guardrail has to sit at the tool boundary, in the framework, not at the model boundary. In Strands that means an `after_tool_call` intervention; in AgentCore it means a [Gateway RESPONSE Lambda interceptor](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/). Either way you are writing the scan yourself.

Two more lines from the same page, worth knowing before you enable tracing: the Guardrails trace `match` field "contains the original PII value, not the masked output", and model invocation logs "always contain the original, unmodified request regardless of guardrail intervention." If your compliance story depends on plaintext never reaching a log, check both.

---

## 2. Bedrock Guardrails has no Indian entity types

**The assumption:** the entity taxonomy is broad; Aadhaar or PAN is in there somewhere under a national-identifier category.

**What the documentation says:** the taxonomy on that same page is General, Finance, IT, **USA specific**, **Canada specific**, **UK specific**, and custom regex. There is no India-specific type. Not Aadhaar, not PAN, not GSTIN, not voter ID.

You can write custom regex, and for PAN that is genuinely fine — it is `[A-Z]{5}[0-9]{4}[A-Z]`. For Aadhaar a bare regex is a false-positive machine, because "twelve digits" matches a great many things that are not Aadhaar numbers.

**Where the coverage actually is:** Amazon Comprehend's `DetectPiiEntities` carries `IN_AADHAAR`, `IN_NREGA`, `IN_PERMANENT_ACCOUNT_NUMBER` and `IN_VOTER_NUMBER` ([entity list](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html)). And outside AWS, Microsoft's [Presidio](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md) has shipped `IN_AADHAAR` *with Verhoeff checksum validation*, plus `IN_PAN`, `IN_VOTER`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION` and `IN_GSTIN`, free, for years — which is why anything embedding Presidio inherits all of it.

If you are building for Indian data, "does it detect Aadhaar" is not the interesting question. Several things do. Keep reading.

---

## 3. Claude on Bedrock in Mumbai is `global.*` only. Nova has an APAC profile.

This is the finding that cost us the model we wanted, and it is the one I would most want another Indian team to read.

**The assumption:** ap-south-1 is a mature Region; pick your model and go.

**What the documentation says:** Claude on Bedrock in India is reached [through a `global.*` cross-region inference profile](https://aws.amazon.com/blogs/machine-learning/access-anthropic-claude-models-in-india-on-amazon-bedrock-with-global-cross-region-inference), and AWS states explicitly that a global profile can route requests outside the source Region. There is no in-region option and no APAC geo profile for it. Amazon Nova, by contrast, has `apac.*` profiles — `apac.amazon.nova-lite-v1:0`, `apac.amazon.nova-pro-v1:0` — which stay within APAC.

**What changed:** we are building a control *about* Indian personal data. Shipping it on a model whose documented routing behaviour is "may leave the source Region" would contradict the premise of the project, so the more capable model was ruled out by its inference profile rather than by its capability. That is an unusual reason to pick a model and it is worth being explicit about.

Three cautions if you make the same call:

- **Say "stays in APAC", not "stays in India."** The destination Regions inside an APAC geo profile are not published. Run `get-inference-profile` and enumerate what is actually associated with it before you write a residency sentence into a contract.
- That same output also determines your IAM policy. AWS requires the foundation model to be specified in **each Region associated with the profile**, so your `Resource` list is longer than one ARN.
- Nova Pro has **no in-region option in ap-south-1 either** — `apac.` is the only path there too, not a preference. This is a property of how Bedrock distributes models, not a ranking of vendors.

---

## 4. A Lambda Function URL needs two permissions, and the CLI only makes you think about one

**The assumption:** create the function, create the function URL with `AuthType=NONE`, add the invoke permission, done.

**What actually happens:** you get a 403 on every request, from a URL that exists, on a function that works when you invoke it directly. It looks exactly like a routing bug or a handler bug, and you will go looking in your code.

**The cause:** for function URLs created since October 2025, the caller needs **both** `lambda:InvokeFunctionUrl` *and* `lambda:InvokeFunction`. The console and SAM add both for you. The CLI adds what you ask for. So the same steps that work in the console fail from a script ([function URL auth docs](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)).

```bash
# Both of these. Not one.
aws lambda add-permission --action lambda:InvokeFunctionUrl \
  --principal '*' --function-url-auth-type NONE --statement-id url-invoke ...
aws lambda add-permission --action lambda:InvokeFunction \
  --principal '*' --function-url-auth-type NONE --statement-id fn-invoke ...
```

We made deploying a hello-world function behind a working URL step one of the build, before any logic existed, specifically because of this. If your deadline is a submission deadline, discovering a packaging or permissions problem on the last afternoon is the failure that cannot be recovered from. Discovering it on hour one costs five minutes.

---

## 5. Comprehend's API accepts `hi`. The developer guide says English and Spanish. Only one of them is about this feature.

**The contradiction:** the `DetectPiiEntities` [API reference](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectPiiEntities.html) lists `hi` among the valid values for `LanguageCode`. The [PII developer guide](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html) says PII detection supports English and Spanish.

Both statements are on AWS's own documentation site. They cannot both be describing the same behaviour.

**I could not settle this by running it**, which is its own lesson and I will come back to that. Here is what the documents actually support.

The `LanguageCode` enum is shared across Comprehend's APIs — the same twelve values appear on operations that genuinely are multilingual. The PII developer guide is specific to this feature and it opens by naming two languages. A shared enum is a weaker signal than a feature-specific support statement, so the working conclusion is: **`--language-code hi` will be accepted and will not detect what you want.** An API that takes your parameter without complaint is not the same as an API that supports it.

One `detect-pii-entities` call settles it for you if your account can make one:

```bash
aws comprehend detect-pii-entities \
  --language-code hi --text "<a Hindi sentence containing a phone number>" \
  --region ap-south-1
```

**Here is the part I did not expect, and it changed the design.** Bedrock Guardrails' sensitive-information filter *does* support Hindi — one of seventeen languages, all listed as optimised and supported. And as §2 covers, Guardrails has **no Indian entity types at all.** So the service with `IN_AADHAAR` and `IN_PERMANENT_ACCOUNT_NUMBER` cannot read Hindi, and the service that reads Hindi does not know what an Aadhaar number is. Each has precisely what the other lacks, and neither closes the case alone.

That is why our detector tiers **union** instead of deferring: local checksum validators catch the Indian identifiers by structure regardless of surrounding script, Comprehend handles English free text, and a multimodal pass covers Indic-script documents. No tier is allowed to clear another tier's findings, because a document can contain text instructing a detector to report nothing. If you do route through a generative model, discard any returned substring not literally present in the source via `str.find()` — never trust a model's character offsets.

**Why I could not just run the command, and still cannot.** On a new AWS account, `comprehend:DetectPiiEntities` returned `SubscriptionRequiredException`. So did `textract:DetectDocumentText`. Bedrock returned `AccessDeniedException` — "your account is currently being verified" — in one region and `ValidationException` in another, and the Lambda concurrency limit sat at 10 instead of 1000. Same credentials, and DynamoDB, S3, Lambda and IAM all worked fine, so it was neither IAM nor region: the AI services are gated together while an account is verified, and they announce it three different ways. If you are starting an account for a deadline, make that the first call you make, not the last.

This did not clear. It held for the entire build, through a support case, and the project shipped with tiers 2 and 3 wired, probed live and reported as `NOT_RUN` rather than green — which turned out to be the more interesting product decision anyway. A detector that could not run must never be reported as a clean scan, and having the constraint forced on us is how that rule got built in properly instead of being asserted in a README.

One related detail: there is no `en-IN` parameter value, though Comprehend's AI Service Card lists en-IN among the locales it was trained on.

---

## 6. Textract is one page for PDFs, and Latin script only

Two separate limits that people conflate.

**The page limit.** `DetectDocumentText` in synchronous mode handles **one page** for PDF and TIFF ([document quotas](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)). Two pages forces you onto the asynchronous API, which means S3, a job id, and polling — a different program, not a flag. The inline `Bytes` path is 10 MB and single-page.

If you are demoing document handling, this is survivable and even convenient: an Aadhaar card, a PAN card and a payslip are each one page. If you are building for real invoice or contract ingestion, budget for the async path from the start.

**The script limit, which is the bigger one.** Textract's OCR is **Latin-script only**. It will not read Devanagari or Tamil.

Put that together with finding 2 and Comprehend's English/Spanish support and you get a specific, checkable result: **an Indian identity document prints the holder's name twice, once in English and once in a regional script, and the entire mainstream PII stack can only see one of them.** Textract will not OCR the regional-script half; Comprehend would not process it if it did. Every "we support Indian identifiers" claim in this category, including ones that are true about the numbers, is silent about the name.

That is not a small edge case. On an Aadhaar card it is half the identifying text on the document.

**One more, from experience rather than docs:** a checksum is robust against false positives and fragile against OCR errors. A real Aadhaar number with one misread digit fails the Verhoeff check and gets silently dropped. On OCR-sourced text, keep 12-digit sequences that *fail* the checksum too, at lower confidence and tagged as OCR-derived. Checksum as a confidence signal, not a gate.

Also worth checking before you load-test: synchronous Textract is **5 TPS in Mumbai** against 25 in us-east-1. Regional quotas are not uniform.

---

## 7. Comprehend's 300-character minimum makes per-field scanning about five times the cost of the same bytes

**The assumption:** Comprehend bills per character, so scanning ten small fields costs the same as scanning them concatenated. Scan per field — it is cleaner and you get precise attribution for free.

**What the [pricing page](https://aws.amazon.com/comprehend/pricing/) says:** billing is in units of 100 characters, with a **minimum of 3 units (300 characters) per request.**

So the arithmetic:

| | Requests | Billed units |
|---|---|---|
| Five 60-character fields, scanned one at a time | 5 | 5 × 3 (minimum) = **15** |
| The same five fields in one 300-character request | 1 | 3 = **3** |

Identical bytes, five times the cost. And the ratio gets worse as the fields get smaller: fifteen 20-character fields scanned individually bill 45 units against 3 for the batch.

**What changed:** batch every tool result into one Comprehend call per hop, never one per field, and get attribution from the returned character offsets instead of from request boundaries. That is a slightly more annoying piece of code and it is the difference between a bill that tracks your data volume and one that tracks your field count.

While you are there: the per-request limit is 100 KB, so a spreadsheet column of five thousand identifiers is still plain text but is now a chunking loop.

---

## Six smaller ones, in one block

- **API Gateway HTTP API has a hard 30-second integration timeout.** An agent loop with three tool calls plus document extraction will exceed it. A Lambda Function URL has a 15-minute ceiling and built-in HTTPS, which is why the URL in this build is a Function URL.
- **AgentCore Runtime has no public URL.** `InvokeAgentRuntime` is SigV4 or JWT only ([FAQs](https://aws.amazon.com/bedrock/agentcore/faqs/)). If your deliverable is a link someone can click, that rules it out regardless of how good a fit it otherwise is.
- **Bedrock has no free tier at all.** Not reduced, not time-limited — none. Neither does Bedrock Data Automation.
- **DynamoDB on-demand request units have no free allowance.** The 25 RCU/25 WCU free tier is provisioned-mode only. The 25 GB of storage is free in both modes, which is where the confusion comes from.
- **CloudWatch Logs retention defaults to never expire**, and Logs in Mumbai is $0.67/GB, roughly 34% above us-east-1. Set retention when you create the log group, not after the bill.
- **A Function URL is reported with a trailing slash, and that is a trap if you put it in an environment variable.** `aws lambda create-function-url-config` returns `https://<id>.lambda-url.<region>.on.aws/`. Concatenate `/policy` onto it and you get `//policy`, which a path-equality router does not match. In our case the data plane fetched its policy bundle from `//policy`, got a 404, swallowed it as a transient failure, and silently fell back to the policy baked into the deployment package — on every request, from first deploy. Nothing surfaced it, because falling back to a known-good policy is exactly the correct behaviour when a fetch fails; there was simply no signal that the fetch was failing *every single time*. The tell was on every audit row: a `policy_version` that never changed. `rstrip("/")` the base URL, and make "which policy version actually decided this" a field you can see.
- **Cedar has no set cardinality operator** — no `.size()`, no `.count()`, and sets are not comparable with `<` or `>` ([operators](https://docs.cedarpolicy.com/policies/syntax-operators.html)). If your policy needs to compare a count against a threshold, compute the count outside the policy and pass it in as a long. This one is not AWS's, but if you are writing Cedar for agent authorization you will hit it in the first hour.

---

## The hour that pays for itself

If you are starting a build like this on Monday, do these before you write anything:

1. `aws comprehend detect-pii-entities --language-code hi --text "…"` — settles finding 5 outright.
2. `aws bedrock get-inference-profile --inference-profile-identifier apac.amazon.nova-lite-v1:0 --region ap-south-1` — gives you the actual Region list behind your residency claim, and the ARNs for your IAM policy.
3. Call `DetectDocumentText` synchronously on a two-page PDF and watch it fail, so the failure is a known quantity rather than a surprise at midnight.
4. Deploy an empty function behind a Function URL with both `add-permission` calls and curl it. You now know your packaging and your permissions work.
5. Send the same text to Comprehend once as one request and once as five, and look at the billed units.
6. Time a `detect-pii-entities` call from your Region. AWS publishes no latency figure for it; the number you measure is better than any number you will find.

That is under an hour, and it removes four architecture decisions from the guess pile.

---

## The pattern underneath

Three shapes recur, and once you can see them you find these faster:

**The API reference and the developer guide disagree, and the developer guide holds the caveat.** The enum is generated from the service model. The prose is written by someone who knows what was actually tested.

**The limit that bites is a billing limit, not a technical one.** Nothing fails when you scan per field. The request succeeds, the entities come back, the tests pass, and you find out at the end of the month.

**A routing fact can be an architecture fact.** "This inference profile may route outside the source Region" is one sentence in a blog post, and for anyone with a residency requirement it decides which model you ship.

And the one that produced this whole list: **the exclusion is always on the page you read after you have built the thing.** The Guardrails page tells you plainly that it does not evaluate `toolResult`. It is just three paragraphs below where you stopped reading when you were satisfied the service did PII.

---

These came out of building **Naka**, a disclosure-budget guardrail that tracks what an agent session has cumulatively learned about one person across tool calls, running on Lambda in ap-south-1 — repo at https://github.com/eashuu/aws_first_commit. But none of the seven is about that project. They are properties of the AWS surface, and they will apply to whatever you put on it.

If you resolve finding 5 before I do, I would like to know.
