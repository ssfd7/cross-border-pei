---
type: Attested Computation
title: Holdings on which sources disagree
description: Holdings where a secondary source gives a different percentage from the system of record on a date.
status: draft
"@context": /context.jsonld
runtime: ladybug
parameters:
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-ladybug.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:OwnershipInterest, xbpei:economicPercentage, xbpei:votingPercentage, xbpei:evidencedBy]
supports: [CQ1, WF3.1, C3.4]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

The investor register is the system of record for an investor's interest in a fund vehicle. A difference is reported with both rows; neither figure is dropped.

# Computation

```cypher
MATCH (a:Party)-[r:HOLDS]->(b:Party), (a)-[s:HOLDS]->(b)
WHERE r.systemOfRecord AND NOT s.systemOfRecord AND r.validFrom <= date($on_date) AND (r.validTo IS NULL OR r.validTo >= date($on_date))
  AND s.validFrom <= date($on_date) AND (s.validTo IS NULL OR s.validTo >= date($on_date))
  AND (r.economicPercentage <> s.economicPercentage OR r.votingPercentage <> s.votingPercentage)
RETURN a.id AS holder, a.name AS name, a.sourceRefs AS source_refs, b.id AS held_entity,
       r.sourceRef AS record_ref, r.economicPercentage AS record_economic_pct, r.votingPercentage AS record_voting_pct,
       s.sourceRef AS other_ref, s.economicPercentage AS other_economic_pct, s.votingPercentage AS other_voting_pct
ORDER BY holder
```
