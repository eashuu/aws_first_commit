#!/usr/bin/env bash
# Full Naka deploy: build the zip, create the S3 session bucket and the
# DynamoDB table, create one shared IAM execution role, create both
# Lambdas, their Function URLs, and the permissions those URLs need to
# not 403. Plain zip + AWS CLI, no CDK (PRD §7: CDK costs 30-60 minutes of
# throwaway TypeScript and a `cdk bootstrap` IAM fight, for two functions).
#
# Both Lambdas share ONE IAM role/policy here rather than two narrower
# ones -- a deliberate hackathon simplification (least-privilege *within*
# the policy, not split *across* the two functions). Split them later if
# that matters more than the extra script complexity.
#
# Safe-ish to re-run: every step checks for what already exists before
# creating it, so fixing a typo in one step and re-running the whole
# script does not duplicate resources. The exception is the DynamoDB key
# schema / GSIs (see create-table.sh) -- those genuinely can't be patched
# in place.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration -- override any of these via environment before running,
# e.g. `AGENT_FN=my-agent STRANDS_LAYER_VERSION=3 ./deploy.sh`
#
# AWS_REGION is deliberately never passed via --environment to the
# Lambdas below: it's a Lambda-reserved environment variable name (the
# CLI rejects an attempt to set it), and the runtime already injects it
# to match the function's own configured region -- which is $REGION
# either way, since that's where these functions are being created.
# config.py's `_env("AWS_REGION", "ap-south-1")` picks that up for free.
# ---------------------------------------------------------------------------
# A public Function URL needs BOTH statements on the resource policy, or it
# answers an opaque 403 with no log line anywhere -- PRD §7 calls this the
# highest-risk step in the build, and it is. Verified against the live API,
# because the PRD's own version of this is subtly wrong:
#   - lambda:InvokeFunctionUrl MUST carry --function-url-auth-type NONE
#   - lambda:InvokeFunction MUST NOT. Passing it there is rejected outright
#     ("FunctionUrlAuthType is only supported for lambda:InvokeFunctionUrl"),
#     so a script that passes the flag to both -- and swallows errors, as
#     this one used to -- adds only the first statement and the URL 403s
#     forever, looking exactly like a code bug.
# add-permission has no upsert mode, so an already-present statement is
# success on a re-run; any OTHER error is surfaced, not hidden.
# The UI is served by the CONTROL plane but calls the DATA plane, which is
# a different origin. A Function URL sends no CORS headers unless told to,
# so without this the browser blocks every agent call -- the Run button
# fails with an opaque "TypeError: Failed to fetch" and the demo is dead,
# while curl against the same URL works perfectly and suggests nothing is
# wrong. Applied to both functions so the console also works when opened
# from somewhere other than the control-plane origin.
CORS_JSON='{"AllowOrigins":["*"],"AllowMethods":["GET","POST"],"AllowHeaders":["content-type","x-naka-key"],"MaxAge":86400}'

set_function_url() {
  local fn="$1" region="$2"
  if aws lambda get-function-url-config --function-name "$fn" --region "$region" >/dev/null 2>&1; then
    # Idempotent: re-applies CORS to a URL created before this existed.
    aws lambda update-function-url-config --function-name "$fn" --region "$region" \
      --auth-type NONE --cors "$CORS_JSON" >/dev/null
  else
    aws lambda create-function-url-config --function-name "$fn" --region "$region" \
      --auth-type NONE --cors "$CORS_JSON" >/dev/null
  fi
  aws lambda get-function-url-config --function-name "$fn" --region "$region" --query 'FunctionUrl' --output text
}

add_invoke_permissions() {
  local fn="$1" region="$2" out
  if ! out="$(aws lambda add-permission --function-name "$fn" --region "$region" \
      --action lambda:InvokeFunctionUrl --principal '*' \
      --function-url-auth-type NONE --statement-id url-invoke 2>&1)"; then
    case "$out" in
      *ResourceConflictException*) echo "    (url-invoke permission already present)" ;;
      *) echo "ERROR: add-permission url-invoke ($fn): $out" >&2; return 1 ;;
    esac
  fi
  if ! out="$(aws lambda add-permission --function-name "$fn" --region "$region" \
      --action lambda:InvokeFunction --principal '*' \
      --statement-id fn-invoke 2>&1)"; then
    case "$out" in
      *ResourceConflictException*) echo "    (fn-invoke permission already present)" ;;
      *) echo "ERROR: add-permission fn-invoke ($fn): $out" >&2; return 1 ;;
    esac
  fi
}

REGION="${AWS_REGION:-ap-south-1}"                # PRD §7: all of it in Mumbai
AGENT_FN="${AGENT_FN:-naka-agent}"                 # data plane (app_agent.py)
CONTROL_FN="${CONTROL_FN:-naka-control}"           # control plane (app_control.py)
TABLE_NAME="${AUDIT_TABLE:-naka_audit}"
ROLE_NAME="${ROLE_NAME:-naka-lambda-role}"
POLICY_NAME="${POLICY_NAME:-naka-lambda-policy}"

# The PRD names the exact layer ARN prefix but explicitly leaves the
# version (`:<v>`) unpinned -- there was no single version known-current
# when it was written, and guessing one wrong fails as an opaque import
# error deep inside a cold start, not a clear "wrong version" message.
# Find the real number with:
#   aws lambda list-layer-versions --region ap-south-1 \
#     --layer-name strands-agents-py3_12-aarch64 \
#     --compatible-runtime python3.12 --compatible-architecture arm64
# then `STRANDS_LAYER_VERSION=<n> ./deploy.sh`.
: "${STRANDS_LAYER_VERSION:?Set STRANDS_LAYER_VERSION to the layer version number (see comment above) and re-run.}"
LAYER_ARN="arn:aws:lambda:${REGION}:856699698935:layer:strands-agents-py3_12-aarch64:${STRANDS_LAYER_VERSION}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# S3 bucket for S3SessionManager (config.py's SESSION_PREFIX default is
# "sessions/", matched by iam-policy.json's s3:prefix condition). Bucket
# names are globally unique across all of AWS, so default to something
# account-scoped rather than a name someone else already took.
SESSION_BUCKET="${SESSION_BUCKET:-naka-sessions-${ACCOUNT_ID}}"

# Shared secret for PUT /policy (app_control.py's _route_put_policy checks
# the X-Naka-Key header against CFG.naka_key). Generate one if the caller
# didn't supply it: config.py's default is "", and `if not CFG.naka_key`
# means an empty key permanently locks writes rather than opening them up,
# but handing back a real, usable key beats a control plane nobody can
# ever administer.
if [ -z "${NAKA_KEY:-}" ]; then
  NAKA_KEY="$(openssl rand -hex 20 2>/dev/null || head -c 20 /dev/urandom | xxd -p)"
  echo "==> generated NAKA_KEY: $NAKA_KEY"
  echo "    SAVE THIS -- it's the X-Naka-Key header required to PUT /policy,"
  echo "    and it is not retrievable from AWS after this run (Lambda env"
  echo "    vars are not stored anywhere else)."
fi

# Everything else in config.py's Config (POLICY_TTL_S, the detection
# thresholds, the timeout budgets, AUDIT_TTL_DAYS, ...) has a workable
# default baked into config.py itself and is intentionally left unset
# here. Add `,KEY=value` entries to the relevant --environment string
# below if a demo needs to override one.
echo "==> account $ACCOUNT_ID, region $REGION"

# ---------------------------------------------------------------------------
# 1. Build the zip
# ---------------------------------------------------------------------------
ZIP_PATH="$ROOT/dist/naka.zip"
if [ -n "${SKIP_BUILD:-}" ] && [ -f "$ZIP_PATH" ]; then
  # For retries after a network failure in a later step -- the pip install
  # is the slowest part of this script and nothing about it changes.
  echo "==> [1/7] build SKIPPED (SKIP_BUILD set, reusing $ZIP_PATH)"
else
  echo "==> [1/7] build"
  "$HERE/build.sh"
fi

# ---------------------------------------------------------------------------
# 2. S3 session bucket
# ---------------------------------------------------------------------------
echo "==> [2/7] session bucket ($SESSION_BUCKET)"
if aws s3api head-bucket --bucket "$SESSION_BUCKET" --region "$REGION" 2>/dev/null; then
  echo "    already exists"
else
  # ap-south-1 is not us-east-1, so create-bucket needs an explicit
  # LocationConstraint or the call fails outright (us-east-1 is the one
  # region where you must NOT pass this).
  #
  # head-bucket is a network call and can fail for reasons unrelated to the
  # bucket's existence, which then sends us down this branch for a bucket we
  # already own. Treat "already owned" as success rather than failing a
  # deploy that has nothing wrong with it.
  if ! mk_out="$(aws s3api create-bucket \
      --bucket "$SESSION_BUCKET" \
      --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" 2>&1)"; then
    case "$mk_out" in
      *BucketAlreadyOwnedByYou*) echo "    already exists (head-bucket check failed transiently)" ;;
      *) echo "ERROR: create-bucket failed: $mk_out" >&2; exit 1 ;;
    esac
  fi
fi

# Stage the zip in S3 rather than pushing it inline to the Lambda API.
# create-function/update-function-code with --zip-file sends the whole
# package as one non-resumable HTTPS request body; at ~26 MB that reliably
# dies ("Connection was closed before we received a valid response") on any
# connection that isn't fast and stable. `aws s3 cp` chunks and retries, and
# Lambda then fetches the object server-side. The Lambda execution role
# cannot read this prefix (iam-policy.json scopes it to sessions/*) -- the
# deploying user's own credentials are what Lambda checks at create time.
CODE_KEY="deploy/naka.zip"
echo "==> staging $ZIP_PATH -> s3://$SESSION_BUCKET/$CODE_KEY"
aws s3 cp "$ZIP_PATH" "s3://$SESSION_BUCKET/$CODE_KEY" --region "$REGION" --only-show-errors

# ---------------------------------------------------------------------------
# 3. DynamoDB table (+ gsi1 + TTL)
# ---------------------------------------------------------------------------
echo "==> [3/7] audit table ($TABLE_NAME)"
AWS_REGION="$REGION" AUDIT_TABLE="$TABLE_NAME" "$HERE/create-table.sh"

# ---------------------------------------------------------------------------
# 4. IAM execution role
# ---------------------------------------------------------------------------
echo "==> [4/7] IAM role ($ROLE_NAME)"
NEW_ROLE=0
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "    already exists"
else
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://$HERE/trust-policy.json" >/dev/null
  NEW_ROLE=1
fi
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"

# Fill in the account/region/table/bucket/function placeholders and attach
# as an inline policy -- put-role-policy is create-or-replace (an upsert),
# so re-running this after editing iam-policy.json just updates it in
# place rather than erroring on "already exists".
TMP_POLICY="$(mktemp)"
sed \
  -e "s/__REGION__/${REGION}/g" \
  -e "s/__ACCOUNT_ID__/${ACCOUNT_ID}/g" \
  -e "s/__TABLE_NAME__/${TABLE_NAME}/g" \
  -e "s/__SESSION_BUCKET__/${SESSION_BUCKET}/g" \
  -e "s/__AGENT_FN__/${AGENT_FN}/g" \
  -e "s/__CONTROL_FN__/${CONTROL_FN}/g" \
  "$HERE/iam-policy.json" > "$TMP_POLICY"
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document "file://$TMP_POLICY"
rm -f "$TMP_POLICY"

if [ "$NEW_ROLE" = "1" ]; then
  echo "    waiting ~10s for IAM's eventual consistency (a brand-new role's"
  echo "    trust policy and permissions don't reliably show up read-your-"
  echo "    writes on the very next create-function call)"
  sleep 10
fi

# ---------------------------------------------------------------------------
# 5. Control-plane Lambda (created first: the agent's CONTROL_PLANE_URL
#    env var needs this one's Function URL, captured below)
# ---------------------------------------------------------------------------
echo "==> [5/7] control-plane Lambda ($CONTROL_FN)"
CONTROL_ENV="Variables={AUDIT_TABLE=${TABLE_NAME},NAKA_KEY=${NAKA_KEY}}"
if aws lambda get-function --function-name "$CONTROL_FN" --region "$REGION" >/dev/null 2>&1; then
  echo "    exists -- updating code and configuration"
  aws lambda update-function-code --function-name "$CONTROL_FN" --region "$REGION" \
    --s3-bucket "$SESSION_BUCKET" --s3-key "$CODE_KEY" >/dev/null
  aws lambda wait function-updated --function-name "$CONTROL_FN" --region "$REGION"
  aws lambda update-function-configuration --function-name "$CONTROL_FN" --region "$REGION" \
    --environment "$CONTROL_ENV" >/dev/null
else
  aws lambda create-function \
    --function-name "$CONTROL_FN" \
    --region "$REGION" \
    --architectures arm64 \
    --runtime python3.12 \
    --handler app_control.lambda_handler \
    --role "$ROLE_ARN" \
    --layers "$LAYER_ARN" \
    --timeout 30 \
    --memory-size 1024 \
    --code "S3Bucket=${SESSION_BUCKET},S3Key=${CODE_KEY}" \
    --environment "$CONTROL_ENV" >/dev/null
fi
aws lambda wait function-active --function-name "$CONTROL_FN" --region "$REGION"

# Function URL, not API Gateway (PRD §7): an API Gateway HTTP API hard-caps
# a request at 30s and the agent loop can legitimately run longer than
# that; Function URLs allow up to 15 minutes. The control plane doesn't
# need that headroom itself, but both Lambdas use the same mechanism for
# consistency, and it's genuinely simpler than standing up API Gateway for
# just one of the two.
CONTROL_URL="$(set_function_url "$CONTROL_FN" "$REGION")"

add_invoke_permissions "$CONTROL_FN" "$REGION"

echo "    control-plane URL: $CONTROL_URL"

# ---------------------------------------------------------------------------
# 6. Data-plane (agent) Lambda -- gets CONTROL_PLANE_URL from step 5
# ---------------------------------------------------------------------------
echo "==> [6/7] data-plane Lambda ($AGENT_FN)"
AGENT_ENV="Variables={AUDIT_TABLE=${TABLE_NAME},SESSION_BUCKET=${SESSION_BUCKET},SESSION_PREFIX=sessions/,MODEL_ID=apac.amazon.nova-lite-v1:0,INDIC_MODEL_ID=apac.amazon.nova-pro-v1:0,CONTROL_PLANE_URL=${CONTROL_URL}}"
if aws lambda get-function --function-name "$AGENT_FN" --region "$REGION" >/dev/null 2>&1; then
  echo "    exists -- updating code and configuration"
  aws lambda update-function-code --function-name "$AGENT_FN" --region "$REGION" \
    --s3-bucket "$SESSION_BUCKET" --s3-key "$CODE_KEY" >/dev/null
  aws lambda wait function-updated --function-name "$AGENT_FN" --region "$REGION"
  aws lambda update-function-configuration --function-name "$AGENT_FN" --region "$REGION" \
    --environment "$AGENT_ENV" >/dev/null
else
  # timeout 900 (the Lambda maximum, = Function URL's 15-minute ceiling)
  # deliberately uses the headroom the PRD chose Function URL over API
  # Gateway to get -- the agent loop calls Bedrock/Textract/Comprehend
  # multiple times per turn and there's no reason to cap it below what
  # the URL itself allows.
  aws lambda create-function \
    --function-name "$AGENT_FN" \
    --region "$REGION" \
    --architectures arm64 \
    --runtime python3.12 \
    --handler app_agent.lambda_handler \
    --role "$ROLE_ARN" \
    --layers "$LAYER_ARN" \
    --timeout 900 \
    --memory-size 1024 \
    --code "S3Bucket=${SESSION_BUCKET},S3Key=${CODE_KEY}" \
    --environment "$AGENT_ENV" >/dev/null
fi
aws lambda wait function-active --function-name "$AGENT_FN" --region "$REGION"

AGENT_URL="$(set_function_url "$AGENT_FN" "$REGION")"

add_invoke_permissions "$AGENT_FN" "$REGION"

# Tell the control plane where the data plane lives, now that both URLs
# exist. The UI the control plane serves prefills its "agent Function URL"
# field from this, so a first-time visitor (who has no localStorage) gets a
# working console instead of "Set the agent Function URL first". This is a
# second update-function-configuration rather than part of step 5 because
# $AGENT_URL does not exist yet at that point.
echo "    wiring AGENT_URL into $CONTROL_FN"
aws lambda wait function-updated --function-name "$CONTROL_FN" --region "$REGION"
aws lambda update-function-configuration --function-name "$CONTROL_FN" --region "$REGION" \
  --environment "Variables={AUDIT_TABLE=${TABLE_NAME},NAKA_KEY=${NAKA_KEY},AGENT_URL=${AGENT_URL}}" >/dev/null

# ---------------------------------------------------------------------------
# 7. Done
# ---------------------------------------------------------------------------
echo "==> [7/7] deployed"
echo "    control plane : $CONTROL_URL"
echo "    data plane    : $AGENT_URL"
echo "    NAKA_KEY      : $NAKA_KEY   (X-Naka-Key header for PUT ${CONTROL_URL}policy)"
echo "    audit table   : $TABLE_NAME"
echo "    session bucket: $SESSION_BUCKET"
echo
echo "    Smoke test:"
echo "      curl -s ${AGENT_URL}health"
echo "      curl -s ${CONTROL_URL}health"
