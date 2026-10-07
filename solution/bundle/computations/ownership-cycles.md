---
type: Attested Computation
title: Circular holdings on a date
description: Pairs of parties each of which holds the other, directly or through others, on a date.
status: draft
runtime: ladybug
parameters:
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-ladybug.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:OwnershipInterest, xbpei:heldBy, xbpei:interestIn, xbpei:validDuring]
supports: [CQ1, WF3.6]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

A circular holding means ultimate ownership cannot be read by walking the chain. Report it and pass the case to a person; do not resolve it.

# Computation

```cypher
MATCH (a:Party)-[:HOLDS* 1..6 (r, n | WHERE r.validFrom <= date($on_date) AND (r.validTo IS NULL OR r.validTo >= date($on_date)))]->(b:Party),
      (b)-[:HOLDS* 1..6 (r, n | WHERE r.validFrom <= date($on_date) AND (r.validTo IS NULL OR r.validTo >= date($on_date)))]->(a)
WHERE a.id < b.id
RETURN DISTINCT a.id AS party, a.name AS name, a.sourceRefs AS source_refs,
       b.id AS other_party, b.name AS other_name, b.sourceRefs AS other_source_refs
ORDER BY party, other_party
```
