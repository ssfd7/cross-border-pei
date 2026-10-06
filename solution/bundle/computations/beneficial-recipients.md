---
type: Attested Computation
title: Beneficial recipients of a distribution
description: For each investor of record, the parties whose income its share is, with each party's share of that investor's line.
status: draft
"@context": /context.jsonld
runtime: postgres
parameters:
  - { name: distribution_id, type: string, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:BeneficialOwner, xbpei:OwnershipInterest, xbpei:holdingCapacity, xbpei:heldThrough, xbpei:heldBy, xbpei:economicPercentage, xbpei:isIntermediaryCertification, xbpei:TaxCertification]
supports: [WF3.4, WF3.6, C3.1]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

An investor of record is looked through when its certification valid on the payment date is an intermediary certification. A flow-through fund vehicle is looked through to its own investors; a nominee to the owners in its allocation. One level is looked through: a recipient that is itself an intermediary is flagged, and its shares must then be resolved before a rate is decided. Shares of one investor of record must sum to 100.

# Computation

```sql
WITH dist AS (
    SELECT d.record_dt, d.pay_dt, f.fund_code
    FROM treasury.distribution d
    JOIN treasury.counterparty cp ON cp.cp_id = d.fund_cp
    JOIN investor_register.fund f ON f.lei = cp.lei
    WHERE d.dist_id = %(distribution_id)s
), intermediary AS (
    SELECT DISTINCT t.inv_no
    FROM onboarding.tax_form t, dist
    WHERE t.is_intermediary = 'Y' AND t.form_status <> 'SUPERSEDED'
      AND t.signed_dt <= dist.pay_dt AND (t.valid_to IS NULL OR t.valid_to >= dist.pay_dt)
), payee AS (
    SELECT c.inv_no, c.commit_id, i.lei, c.inv_no IN (SELECT inv_no FROM intermediary) AS looked_through
    FROM dist
    JOIN investor_register.commitment c ON c.fund_code = dist.fund_code
         AND c.from_dt <= dist.record_dt AND (c.to_dt IS NULL OR c.to_dt >= dist.record_dt)
    JOIN investor_register.investor i ON i.inv_no = c.inv_no
), recipient AS (
    SELECT p.inv_no AS investor_no, p.inv_no AS recipient_no, 100::numeric AS share_pct, 'own account' AS basis,
           'investor_register.commitment:' || p.commit_id AS source_ref
    FROM payee p WHERE NOT p.looked_through
    UNION ALL
    SELECT p.inv_no, c.inv_no, c.unit_pct, 'investor in a flow-through fund vehicle',
           'investor_register.commitment:' || c.commit_id
    FROM payee p
    JOIN investor_register.fund f ON f.lei = p.lei
    JOIN investor_register.commitment c ON c.fund_code = f.fund_code
    CROSS JOIN dist
    WHERE p.looked_through AND c.from_dt <= dist.record_dt AND (c.to_dt IS NULL OR c.to_dt >= dist.record_dt)
    UNION ALL
    SELECT p.inv_no, o.owner_inv_no, o.pct_econ, 'beneficial owner behind a nominee',
           'onboarding.declared_owner:' || o.decl_id
    FROM payee p
    JOIN onboarding.declared_owner o ON o.owned_inv_no = p.inv_no AND o.alloc_basis = 'NOMINEE_ALLOC'
    CROSS JOIN dist
    WHERE p.looked_through AND o.from_dt <= dist.record_dt AND (o.to_dt IS NULL OR o.to_dt >= dist.record_dt)
)
SELECT r.investor_no, r.recipient_no, i.display_name AS recipient_name, r.share_pct, r.basis,
       r.recipient_no IN (SELECT inv_no FROM intermediary) AS recipient_is_intermediary, r.source_ref
FROM recipient r JOIN investor_register.investor i ON i.inv_no = r.recipient_no
ORDER BY r.investor_no, r.recipient_no
```
