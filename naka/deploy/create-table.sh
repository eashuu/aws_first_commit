#!/usr/bin/env bash
# Creates the naka_audit DynamoDB table: on-demand billing, the base
# pk/sk key schema ledger.py and audit.py write to, the gsi1 GSI
# app_control.py's _route_feed queries directly (IndexName: "gsi1"), and
# a TTL attribute so old audit rows age out instead of growing the table
# (and the bill) forever.
#
# Idempotent: if the table already exists this is a no-op. Key schema and
# GSIs can't be changed after create without standing up a whole new
# table, so re-running this after a typo in some OTHER deploy step is
# safe -- a typo in the schema itself means delete-and-recreate, there's
# no in-place fix for that and this script doesn't attempt one.
set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"
TABLE_NAME="${AUDIT_TABLE:-naka_audit}"

if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "==> table '$TABLE_NAME' already exists in $REGION, skipping create"
else
  echo "==> creating table '$TABLE_NAME' in $REGION"
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --region "$REGION" \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
        AttributeName=gsi1pk,AttributeType=S \
        AttributeName=gsi1sk,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --global-secondary-indexes \
      '[{
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
      }]'

  echo "==> waiting for table to become ACTIVE"
  aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"
fi

# Why INCLUDE, not KEYS_ONLY (either is fine functionally, but only one of
# them is correct for how this table is actually read): app_control.py's
# _route_feed queries gsi1 directly and hands the returned items straight
# to _item_to_row() for the live dashboard feed -- it never does a second
# GetItem back to the base table to fetch display fields. A GSI always
# projects the base table's key attributes (pk, sk) automatically
# regardless of projection type, but KEYS_ONLY would project nothing else
# -- every column _item_to_row reads beyond pk/sk (ts, seq, tool,
# principal, role, subject, call_decision, entities_found, ...) would come
# back missing, and the feed would render mostly-empty rows. ALL would
# also work, and is simpler to keep in sync as the schema evolves, at the
# cost of storing (and paying gsi1's own write-capacity for) a second full
# copy of every item attribute, including several the feed never reads
# (pages, truncated, rehydrated, invocation_id, session_total,
# ledger_before, expires_at). INCLUDE with the exact field list
# _item_to_row uses is the tightest projection that is still correct.
echo "==> gsi1 projection: INCLUDE (see comment in this script for why, not KEYS_ONLY)"

echo "==> enabling TTL on 'expires_at' (audit.py's put_row() and"
echo "    ledger.py's spend() both set this to now + AUDIT_TTL_DAYS on"
echo "    every write)"
aws dynamodb update-time-to-live \
  --table-name "$TABLE_NAME" \
  --region "$REGION" \
  --time-to-live-specification "Enabled=true,AttributeName=expires_at" \
  || echo "    (update-time-to-live errored -- almost always means TTL is already ON from a previous run, which is fine; re-check with 'aws dynamodb describe-time-to-live' if unsure)"

echo "==> done: $TABLE_NAME"
