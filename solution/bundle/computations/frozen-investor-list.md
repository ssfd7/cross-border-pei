---
type: Attested Computation
title: Frozen investor list
description: The investors of record of the distributing fund at the record date, with their interest and gross amount per component.
status: draft
runtime: postgres
parameters:
  - { name: distribution_id, type: string, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:OwnershipInterest, xbpei:heldBy, xbpei:interestIn, xbpei:economicPercentage, xbpei:votingPercentage, xbpei:validDuring, xbpei:Party, xbpei:recordDate, xbpei:grossAmount]
supports: [WF3.1, C3.1, C3.4]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Treasury payees are matched to investors on LEI, never on name: two investors share a name. Only interests valid on the record date are used; ended interests are history.

# Computation

```sql
SELECT i.inv_no AS investor_no, i.display_name AS name, i.reg_no AS registration_no, c.commit_id AS interest,
       c.unit_pct AS economic_pct, c.vote_pct AS voting_pct, l.comp_id AS component, l.gross_amt AS gross_amount,
       'investor_register.commitment:' || c.commit_id AS source_ref
FROM treasury.distribution d
JOIN treasury.counterparty fund_cp ON fund_cp.cp_id = d.fund_cp
JOIN investor_register.fund f ON f.lei = fund_cp.lei
JOIN treasury.distribution_component dc ON dc.dist_id = d.dist_id
JOIN treasury.distribution_line l ON l.comp_id = dc.comp_id
JOIN treasury.counterparty cp ON cp.cp_id = l.payee_cp
JOIN investor_register.investor i ON i.lei = cp.lei
JOIN investor_register.commitment c ON c.inv_no = i.inv_no AND c.fund_code = f.fund_code
     AND c.from_dt <= d.record_dt AND (c.to_dt IS NULL OR c.to_dt >= d.record_dt)
WHERE d.dist_id = %(distribution_id)s
ORDER BY i.inv_no, l.comp_id
```
