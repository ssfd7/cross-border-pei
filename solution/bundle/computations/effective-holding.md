---
type: Attested Computation
title: Effective holding in a company
description: The effective economic and voting percentage each investor holds in a company on a date, multiplied through every tier of the chain.
status: draft
"@context": /context.jsonld
runtime: ladybug
parameters:
  - { name: company_id, type: string, required: true }
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-ladybug.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:OwnershipInterest, xbpei:heldBy, xbpei:interestIn, xbpei:economicPercentage, xbpei:votingPercentage, xbpei:holdingCapacity, xbpei:validDuring, xbpei:FundVehicle, xbpei:SPV, xbpei:BeneficialOwner]
supports: [CQ1, WF3.6, C3.3]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Walks beneficial interests from the system of record that are valid on the date, through fund vehicles and SPVs only, so it stops at the investor and does not continue into the investor's own owners. Nominee interests are skipped: the owners behind a nominee appear in their own right. `source_refs` lists the same party in each system; an investor number is the part after `investor_register.investor:`.

# Computation

```cypher
MATCH p = (h:Party)-[e:HOLDS* ACYCLIC 1..8 (r, n | WHERE r.systemOfRecord AND r.holdingCapacity = 'beneficial'
        AND r.validFrom <= date($on_date) AND (r.validTo IS NULL OR r.validTo >= date($on_date)) AND (n.isFundVehicle OR n.isSPV))]->(c:Party {id: $company_id})
WHERE NOT h.isSPV AND NOT (h.isFundVehicle AND EXISTS {
        MATCH (:Party)-[r:HOLDS]->(h) WHERE r.systemOfRecord AND r.validFrom <= date($on_date) AND (r.validTo IS NULL OR r.validTo >= date($on_date)) })
WITH h, list_product(properties(rels(p), 'economicPercentage')) / pow(100, size(rels(p)) - 1) AS economic,
     list_product(properties(rels(p), 'votingPercentage')) / pow(100, size(rels(p)) - 1) AS voting
RETURN h.id AS holder, h.name AS name, h.sourceRefs AS source_refs,
       round(sum(economic), 4) AS effective_economic_pct, round(sum(voting), 4) AS effective_voting_pct
ORDER BY holder
```
