# Full Naka deploy for Windows/PowerShell. Mirrors deploy.sh step for
# step -- see that file's header and inline comments for the fuller "why"
# behind each choice (Function URL over API Gateway, both add-permission
# calls, the shared-role simplification, why AWS_REGION is never passed
# via --environment, etc). This file repeats only what's specific to the
# PowerShell mechanics.
$ErrorActionPreference = "Stop"

function Test-LastExit([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

# A public Function URL needs BOTH statements on the resource policy, or it
# answers an opaque 403 with no log line anywhere. Verified against the
# live API:
#   - lambda:InvokeFunctionUrl MUST carry --function-url-auth-type NONE
#   - lambda:InvokeFunction MUST NOT -- passing it there is rejected with
#     "FunctionUrlAuthType is only supported for lambda:InvokeFunctionUrl",
#     so a script that passes the flag to both silently adds only the first
#     and the URL 403s forever.
# add-permission has no upsert mode, so an already-present statement
# (ResourceConflictException on a re-run) is not a failure; any OTHER error
# is, and is surfaced rather than swallowed.
# The UI is served by the CONTROL plane but calls the DATA plane, which is
# a different origin. A Function URL sends no CORS headers unless told to,
# so without this the browser blocks every agent call -- the Run button
# fails with an opaque "TypeError: Failed to fetch" and the demo is dead,
# while curl against the same URL works perfectly and suggests nothing is
# wrong. Applied to both functions so the console also works when opened
# from somewhere other than the control-plane origin.
$CorsJson = '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"],"AllowHeaders":["content-type","x-naka-key"],"MaxAge":86400}'

function Set-FunctionUrl([string]$FnName, [string]$Region) {
    aws lambda get-function-url-config --function-name $FnName --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        aws lambda create-function-url-config --function-name $FnName --region $Region `
            --auth-type NONE --cors $CorsJson | Out-Null
        Test-LastExit "create-function-url-config ($FnName) failed"
    } else {
        # Idempotent: re-applies CORS to a URL created before this existed.
        aws lambda update-function-url-config --function-name $FnName --region $Region `
            --auth-type NONE --cors $CorsJson | Out-Null
        Test-LastExit "update-function-url-config ($FnName) failed"
    }
    return (aws lambda get-function-url-config --function-name $FnName --region $Region --query 'FunctionUrl' --output text).Trim()
}

function Add-InvokePermissions([string]$FnName, [string]$Region) {
    $url = aws lambda add-permission --function-name $FnName --region $Region `
        --action lambda:InvokeFunctionUrl --principal '*' `
        --function-url-auth-type NONE --statement-id url-invoke 2>&1
    if ($LASTEXITCODE -ne 0 -and "$url" -notmatch "ResourceConflictException") { throw "add-permission url-invoke ($FnName) failed: $url" }

    $fn = aws lambda add-permission --function-name $FnName --region $Region `
        --action lambda:InvokeFunction --principal '*' `
        --statement-id fn-invoke 2>&1
    if ($LASTEXITCODE -ne 0 -and "$fn" -notmatch "ResourceConflictException") { throw "add-permission fn-invoke ($FnName) failed: $fn" }
}

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here

# ---------------------------------------------------------------------------
# Configuration -- override any of these via environment before running,
# e.g. `$env:AGENT_FN = "my-agent"; $env:STRANDS_LAYER_VERSION = "3"; .\deploy.ps1`
# ---------------------------------------------------------------------------
$Region     = if ($env:AWS_REGION)  { $env:AWS_REGION }  else { "ap-south-1" }
$AgentFn    = if ($env:AGENT_FN)    { $env:AGENT_FN }    else { "naka-agent" }
$ControlFn  = if ($env:CONTROL_FN)  { $env:CONTROL_FN }  else { "naka-control" }
$TableName  = if ($env:AUDIT_TABLE) { $env:AUDIT_TABLE } else { "naka_audit" }
$RoleName   = if ($env:ROLE_NAME)   { $env:ROLE_NAME }   else { "naka-lambda-role" }
$PolicyName = if ($env:POLICY_NAME) { $env:POLICY_NAME } else { "naka-lambda-policy" }

# See deploy.sh's comment: the PRD names the layer ARN prefix but not a
# version. Find it with:
#   aws lambda list-layer-versions --region ap-south-1 --layer-name strands-agents-py3_12-aarch64 --compatible-runtime python3.12 --compatible-architecture arm64
# Note: ListLayerVersions/GetLayerVersion are not publicly granted cross-account
# on this layer beyond whichever versions Strands has opted to expose --
# if list-layer-versions 403s, probe versions directly instead:
#   aws lambda get-layer-version --region ap-south-1 --layer-name strands-agents-py3_12-aarch64 --version-number 1
if (-not $env:STRANDS_LAYER_VERSION) {
    throw "Set `$env:STRANDS_LAYER_VERSION to the layer version number (see comment above) and re-run."
}
$LayerArn = "arn:aws:lambda:${Region}:856699698935:layer:strands-agents-py3_12-aarch64:$($env:STRANDS_LAYER_VERSION)"

$AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
Test-LastExit "aws sts get-caller-identity failed -- is the AWS CLI configured (aws configure)?"

$SessionBucket = if ($env:SESSION_BUCKET) { $env:SESSION_BUCKET } else { "naka-sessions-$AccountId" }

$NakaKey = $env:NAKA_KEY
if (-not $NakaKey) {
    $bytes = New-Object byte[] 20
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $NakaKey = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    Write-Host "==> generated NAKA_KEY: $NakaKey"
    Write-Host "    SAVE THIS -- it's the X-Naka-Key header required to PUT /policy,"
    Write-Host "    and it is not retrievable from AWS after this run."
}

Write-Host "==> account $AccountId, region $Region"

# ---------------------------------------------------------------------------
# 1. Build
# ---------------------------------------------------------------------------
$ZipPath = Join-Path $Root "dist\naka.zip"
if ($env:SKIP_BUILD -and (Test-Path $ZipPath)) {
    # For retries after a network failure in a later step -- the pip install
    # is the slowest part of this script and nothing about it changes.
    Write-Host "==> [1/7] build SKIPPED (SKIP_BUILD set, reusing $ZipPath)"
} else {
    Write-Host "==> [1/7] build"
    & "$Here\build.ps1"
}

# ---------------------------------------------------------------------------
# 2. S3 session bucket
# ---------------------------------------------------------------------------
Write-Host "==> [2/7] session bucket ($SessionBucket)"
aws s3api head-bucket --bucket $SessionBucket --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    already exists"
} else {
    # ap-south-1 is not us-east-1, so create-bucket needs an explicit
    # LocationConstraint or the call fails outright.
    #
    # head-bucket is a network call and can fail for reasons that have
    # nothing to do with the bucket's existence, which then sends us down
    # this branch for a bucket we already own. Treat "already owned" as
    # success rather than failing a deploy that has nothing wrong with it.
    $mk = aws s3api create-bucket --bucket $SessionBucket --region $Region `
        --create-bucket-configuration LocationConstraint=$Region 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ("$mk" -match "BucketAlreadyOwnedByYou") {
            Write-Host "    already exists (head-bucket check failed transiently)"
        } else {
            throw "create-bucket failed: $mk"
        }
    }
}

# Stage the zip in S3 rather than pushing it inline to the Lambda API.
# create-function/update-function-code with --zip-file sends the whole
# package as one non-resumable HTTPS request body; at ~26 MB that reliably
# dies ("Connection was closed before we received a valid response") on any
# connection that isn't fast and stable. `aws s3 cp` chunks and retries, and
# Lambda then fetches the object server-side. The Lambda execution role
# cannot read this prefix (iam-policy.json scopes it to sessions/*) -- the
# deploying user's own credentials are what Lambda checks at create time.
$CodeKey = "deploy/naka.zip"
Write-Host "==> staging $ZipPath -> s3://$SessionBucket/$CodeKey"
aws s3 cp $ZipPath "s3://$SessionBucket/$CodeKey" --region $Region --only-show-errors
Test-LastExit "staging the zip to S3 failed"

# ---------------------------------------------------------------------------
# 3. DynamoDB table
# ---------------------------------------------------------------------------
Write-Host "==> [3/7] audit table ($TableName)"
$env:AWS_REGION = $Region
$env:AUDIT_TABLE = $TableName
& "$Here\create-table.ps1"

# ---------------------------------------------------------------------------
# 4. IAM role
# ---------------------------------------------------------------------------
Write-Host "==> [4/7] IAM role ($RoleName)"
aws iam get-role --role-name $RoleName 2>$null | Out-Null
$roleExists = ($LASTEXITCODE -eq 0)
if (-not $roleExists) {
    aws iam create-role --role-name $RoleName `
        --assume-role-policy-document "file://$Here/trust-policy.json" | Out-Null
    Test-LastExit "create-role failed"
}
$RoleArn = (aws iam get-role --role-name $RoleName --query 'Role.Arn' --output text).Trim()

# put-role-policy is create-or-replace (an upsert), so re-running this
# after editing iam-policy.json just updates it in place.
$policyText = Get-Content -Raw "$Here\iam-policy.json"
$policyText = $policyText -replace "__REGION__", $Region
$policyText = $policyText -replace "__ACCOUNT_ID__", $AccountId
$policyText = $policyText -replace "__TABLE_NAME__", $TableName
$policyText = $policyText -replace "__SESSION_BUCKET__", $SessionBucket
$policyText = $policyText -replace "__AGENT_FN__", $AgentFn
$policyText = $policyText -replace "__CONTROL_FN__", $ControlFn
$tmpPolicy = New-TemporaryFile
Set-Content -Path $tmpPolicy -Value $policyText -Encoding utf8NoBOM
aws iam put-role-policy --role-name $RoleName --policy-name $PolicyName `
    --policy-document "file://$tmpPolicy"
$rc = $LASTEXITCODE
Remove-Item $tmpPolicy -ErrorAction SilentlyContinue
if ($rc -ne 0) { throw "put-role-policy failed" }

if (-not $roleExists) {
    Write-Host "    waiting ~10s for IAM's eventual consistency"
    Start-Sleep -Seconds 10
}

# ---------------------------------------------------------------------------
# 5. Control-plane Lambda (created first: the agent's CONTROL_PLANE_URL
#    env var needs this one's Function URL, captured below)
# ---------------------------------------------------------------------------
Write-Host "==> [5/7] control-plane Lambda ($ControlFn)"
$controlEnv = "Variables={AUDIT_TABLE=$TableName,NAKA_KEY=$NakaKey}"
aws lambda get-function --function-name $ControlFn --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    exists -- updating code and configuration"
    aws lambda update-function-code --function-name $ControlFn --region $Region `
        --s3-bucket $SessionBucket --s3-key $CodeKey | Out-Null
    aws lambda wait function-updated --function-name $ControlFn --region $Region
    aws lambda update-function-configuration --function-name $ControlFn --region $Region `
        --environment $controlEnv | Out-Null
} else {
    aws lambda create-function --function-name $ControlFn --region $Region `
        --architectures arm64 --runtime python3.12 `
        --handler app_control.lambda_handler --role $RoleArn `
        --layers $LayerArn --timeout 30 --memory-size 1024 `
        --code "S3Bucket=$SessionBucket,S3Key=$CodeKey" --environment $controlEnv | Out-Null
    Test-LastExit "create-function ($ControlFn) failed"
}
aws lambda wait function-active --function-name $ControlFn --region $Region

# Function URL, not API Gateway -- see deploy.sh's comment (30s API
# Gateway cap vs a 15-minute Function URL ceiling the agent loop can need).
$ControlUrl = Set-FunctionUrl $ControlFn $Region

# BOTH add-permission calls, or the URL 403s -- see deploy.sh's comment
# for the full October-2025 story. No idempotent "or update" mode exists
# for add-permission, so an already-present statement is swallowed here,
# not treated as failure.
Add-InvokePermissions $ControlFn $Region

Write-Host "    control-plane URL: $ControlUrl"

# ---------------------------------------------------------------------------
# 6. Data-plane (agent) Lambda -- gets CONTROL_PLANE_URL from step 5
# ---------------------------------------------------------------------------
Write-Host "==> [6/7] data-plane Lambda ($AgentFn)"
$agentEnv = "Variables={AUDIT_TABLE=$TableName,SESSION_BUCKET=$SessionBucket,SESSION_PREFIX=sessions/,MODEL_ID=apac.amazon.nova-lite-v1:0,INDIC_MODEL_ID=apac.amazon.nova-pro-v1:0,CONTROL_PLANE_URL=$ControlUrl}"
aws lambda get-function --function-name $AgentFn --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    exists -- updating code and configuration"
    aws lambda update-function-code --function-name $AgentFn --region $Region `
        --s3-bucket $SessionBucket --s3-key $CodeKey | Out-Null
    aws lambda wait function-updated --function-name $AgentFn --region $Region
    aws lambda update-function-configuration --function-name $AgentFn --region $Region `
        --environment $agentEnv | Out-Null
} else {
    # timeout 900 (the Lambda maximum, = Function URL's 15-minute ceiling):
    # the agent loop calls Bedrock/Textract/Comprehend multiple times per
    # turn, so there's no reason to cap it below what the URL itself allows.
    aws lambda create-function --function-name $AgentFn --region $Region `
        --architectures arm64 --runtime python3.12 `
        --handler app_agent.lambda_handler --role $RoleArn `
        --layers $LayerArn --timeout 900 --memory-size 1024 `
        --code "S3Bucket=$SessionBucket,S3Key=$CodeKey" --environment $agentEnv | Out-Null
    Test-LastExit "create-function ($AgentFn) failed"
}
aws lambda wait function-active --function-name $AgentFn --region $Region

$AgentUrl = Set-FunctionUrl $AgentFn $Region

Add-InvokePermissions $AgentFn $Region

# Tell the control plane where the data plane lives, now that both URLs
# exist. The UI the control plane serves prefills its "agent Function URL"
# field from this, so a first-time visitor (who has no localStorage) gets a
# working console instead of "Set the agent Function URL first". This is a
# second update-function-configuration rather than part of step 5 because
# $AgentUrl does not exist yet at that point.
Write-Host "    wiring AGENT_URL into $ControlFn"
aws lambda wait function-updated --function-name $ControlFn --region $Region
aws lambda update-function-configuration --function-name $ControlFn --region $Region `
    --environment "Variables={AUDIT_TABLE=$TableName,NAKA_KEY=$NakaKey,AGENT_URL=$AgentUrl}" | Out-Null
Test-LastExit "wiring AGENT_URL into $ControlFn failed"

# ---------------------------------------------------------------------------
# 7. Done
# ---------------------------------------------------------------------------
Write-Host "==> [7/7] deployed"
Write-Host "    control plane : $ControlUrl"
Write-Host "    data plane    : $AgentUrl"
Write-Host "    NAKA_KEY      : $NakaKey   (X-Naka-Key header for PUT ${ControlUrl}policy)"
Write-Host "    audit table   : $TableName"
Write-Host "    session bucket: $SessionBucket"
Write-Host ""
Write-Host "    Smoke test:"
Write-Host "      curl.exe -s ${AgentUrl}health"
Write-Host "      curl.exe -s ${ControlUrl}health"

# Without this the script's exit code is whatever the LAST native command
# happened to return -- which, on a successful re-run, is a non-zero
# "already exists" from add-permission or update-time-to-live. A deploy
# that worked must not report failure.
exit 0
