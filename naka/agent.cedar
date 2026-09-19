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
// role == "analyst", or the compliance exemption cannot work (TD s9.5).
//
// This is the corrected policy (10-demo-fixtures.md s0/s4) — it differs from
// the PRD s6.1 and 08-technical-design.md s3.4 drafts in two load-bearing
// ways: the phone forbid is keyed on IN_AADHAAR only (not containsAll/
// containsAny NAME/ADDRESS, which denies the phone at call 2 and breaks the
// PRD s12 beat sheet), and the budget-ceiling forbid is scoped to reveal_*
// actions only (an unscoped ceiling also denies the tool CALL itself once
// spent, which kills the rehydration beat and the compliance exemption).
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
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER", Action::"reveal_IN_GSTIN",
                  Action::"reveal_IN_IFSC", Action::"reveal_IN_VOTER_NUMBER",
                  Action::"reveal_IN_NREGA", Action::"reveal_CREDIT_DEBIT_NUMBER",
                  Action::"reveal_AGE"],
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
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER", Action::"reveal_IN_GSTIN",
                  Action::"reveal_IN_IFSC", Action::"reveal_IN_VOTER_NUMBER",
                  Action::"reveal_IN_NREGA", Action::"reveal_CREDIT_DEBIT_NUMBER",
                  Action::"reveal_AGE"],
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
// Scoped to Q1 + Q2 only. Writing this unscoped would also exempt compliance
// from the destination rule and re-open the exfiltration hole for the one
// role that handles the most sensitive data.

@id("q2_permit_compliance")
@advice("Compliance review is exempt from the per-subject disclosure budget. Rehydration destinations still apply.")
permit(principal,
       action in [Action::"fetch_customer", Action::"read_attachment",
                  Action::"send_summary",
                  Action::"reveal_NAME", Action::"reveal_PHONE",
                  Action::"reveal_EMAIL", Action::"reveal_ADDRESS",
                  Action::"reveal_DATE_TIME", Action::"reveal_IN_AADHAAR",
                  Action::"reveal_IN_PERMANENT_ACCOUNT_NUMBER", Action::"reveal_IN_GSTIN",
                  Action::"reveal_IN_IFSC", Action::"reveal_IN_VOTER_NUMBER",
                  Action::"reveal_IN_NREGA", Action::"reveal_CREDIT_DEBIT_NUMBER",
                  Action::"reveal_AGE"],
       resource)
when { context.session has role && context.session.role == "compliance" };
