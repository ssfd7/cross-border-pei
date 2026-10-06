---
type: Attested Computation
title: Declared owners of investors on a date
description: Who owns each investor, as the investor declared it, on a date.
status: draft
"@context": /context.jsonld
runtime: postgres
parameters:
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:OwnershipInterest, xbpei:heldBy, xbpei:interestIn, xbpei:economicPercentage, xbpei:votingPercentage, xbpei:validDuring, xbpei:evidencedBy]
supports: [WF3.6, CQ1]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Needed where a treaty claim rests on who owns the claimant. Declarations can point at each other; use the ownership-cycles computation before walking them.

# Computation

```sql
SELECT o.owned_inv_no AS party_no, owned.display_name AS name, o.owner_inv_no AS owner_no, owner.display_name AS owner_name,
       owner.country_res AS owner_residence, o.pct_econ AS economic_pct, o.pct_vote AS voting_pct,
       o.from_dt AS valid_from, o.to_dt AS valid_to, o.doc_ref AS evidenced_by,
       'onboarding.declared_owner:' || o.decl_id AS source_ref
FROM onboarding.declared_owner o
JOIN investor_register.investor owned ON owned.inv_no = o.owned_inv_no
JOIN investor_register.investor owner ON owner.inv_no = o.owner_inv_no
WHERE o.alloc_basis = 'OWNERSHIP'
  AND o.from_dt <= %(on_date)s::date AND (o.to_dt IS NULL OR o.to_dt >= %(on_date)s::date)
ORDER BY o.owned_inv_no, o.owner_inv_no
```
