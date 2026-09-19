# Creates the naka_audit DynamoDB table. Windows/PowerShell twin of
# create-table.sh -- see that file's comments for the full rationale
# (why gsi1's projection is INCLUDE and not KEYS_ONLY, why TTL is on
# 'expires_at'). This file repeats only what differs mechanically here.
$ErrorActionPreference = "Stop"

$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }
$TableName = if ($env:AUDIT_TABLE) { $env:AUDIT_TABLE } else { "naka_audit" }

aws dynamodb describe-table --table-name $TableName --region $Region 2>$null | Out-Null
$exists = ($LASTEXITCODE -eq 0)

if ($exists) {
    Write-Host "==> table '$TableName' already exists in $Region, skipping create"
} else {
    Write-Host "==> creating table '$TableName' in $Region"

    $gsiJson = @'
[{
  "IndexName": "gsi1",
  "KeySchema": [
    {"AttributeName": "gsi1pk", "KeyType": "HASH"},
    {"AttributeName": "gsi1sk", "KeyType": "RANGE"}
  ],
  "Projection": {
    "ProjectionType": "INCLUDE",
    "NonKeyAttributes": [
      "ts", "seq", "principal", "role", "subject", "tool",
      "call_decision", "deny_policy", "content_type",
      "detector_tiers", "entities_found", "entities_masked",
      "entities_revealed", "mask_policies", "ledger_after",
      "budget", "outcome", "latency_ms", "policy_version"
    ]
  }
}]
'@
    $gsiJsonPath = New-TemporaryFile
    Set-Content -Path $gsiJsonPath -Value $gsiJson -Encoding utf8NoBOM

    aws dynamodb create-table `
        --table-name $TableName `
        --region $Region `
        --billing-mode PAY_PER_REQUEST `
        --attribute-definitions `
            AttributeName=pk,AttributeType=S `
            AttributeName=sk,AttributeType=S `
            AttributeName=gsi1pk,AttributeType=S `
            AttributeName=gsi1sk,AttributeType=S `
        --key-schema `
            AttributeName=pk,KeyType=HASH `
            AttributeName=sk,KeyType=RANGE `
        --global-secondary-indexes "file://$gsiJsonPath"
    $rc = $LASTEXITCODE

    Remove-Item $gsiJsonPath -ErrorAction SilentlyContinue
    if ($rc -ne 0) { throw "create-table failed" }

    Write-Host "==> waiting for table to become ACTIVE"
    aws dynamodb wait table-exists --table-name $TableName --region $Region
}

# Why INCLUDE, not KEYS_ONLY: see create-table.sh's comment -- app_control.py's
# _route_feed reads display fields straight off the gsi1 query results and
# never re-fetches the base table row, so those fields must be projected
# onto the index itself or the live feed renders empty columns.
Write-Host "==> gsi1 projection: INCLUDE (see create-table.sh comment for why, not KEYS_ONLY)"

Write-Host "==> enabling TTL on 'expires_at' (audit.py's put_row() and ledger.py's spend() both set this to now + AUDIT_TTL_DAYS on every write)"
aws dynamodb update-time-to-live `
    --table-name $TableName `
    --region $Region `
    --time-to-live-specification "Enabled=true,AttributeName=expires_at"
if ($LASTEXITCODE -ne 0) {
    Write-Host "    (update-time-to-live errored -- almost always means TTL is already ON from a previous run, which is fine; re-check with 'aws dynamodb describe-time-to-live' if unsure)"
}

Write-Host "==> done: $TableName"
