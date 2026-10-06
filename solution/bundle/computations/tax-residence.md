---
type: Attested Computation
title: Tax residence on a date
description: The recorded tax residence of each investor and underlying owner on a date.
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
reads: [xbpei:JurisdictionFact, xbpei:aboutEntity, xbpei:hasJurisdiction, xbpei:hasFactType, xbpei:TaxResidence, xbpei:validDuring]
supports: [WF3.6, C3.3, CQ2]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Read from the onboarding record, which is the system of record for an investor's tax residence. A party with no row has no recorded tax residence: that is unknown, not "none".

# Computation

```sql
SELECT r.inv_no AS party_no, i.display_name AS name, r.country, r.from_dt AS valid_from, r.to_dt AS valid_to,
       'onboarding.residence_record:' || r.inv_no || '/' || r.country || '/' || r.from_dt AS source_ref
FROM onboarding.residence_record r
JOIN investor_register.investor i ON i.inv_no = r.inv_no
WHERE r.from_dt <= %(on_date)s::date AND (r.to_dt IS NULL OR r.to_dt >= %(on_date)s::date)
ORDER BY r.inv_no
```
