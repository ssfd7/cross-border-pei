---
type: Attested Computation
title: Distribution and its components
description: A distribution with its record and payment dates, the fund making it and its components by income type and source.
status: draft
runtime: postgres
parameters:
  - { name: distribution_id, type: string, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:DistributionEvent, xbpei:DistributionComponent, xbpei:distributedBy, xbpei:hasComponent, xbpei:hasIncomeType, xbpei:sourcedIn, xbpei:recordDate, xbpei:paymentDate, xbpei:grossAmount, xbpei:currencyCode]
supports: [WF3.1, WF3.2]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

The fund is matched from treasury to the investor register and to entity management on LEI. Income codes are DIV dividend, INT interest, GAIN gain on disposal and ROC return of capital.

# Computation

```sql
SELECT d.dist_id AS distribution, f.fund_code, e.entity_id AS fund_entity, f.fund_name, d.record_dt AS record_date,
       d.pay_dt AS payment_date, d.ccy AS currency, d.gross_amt AS distribution_gross, dc.comp_id AS component,
       dc.income_cd AS income_code, dc.source_country, dc.gross_amt AS component_gross,
       'treasury.distribution_component:' || dc.comp_id AS source_ref
FROM treasury.distribution d
JOIN treasury.counterparty cp ON cp.cp_id = d.fund_cp
JOIN investor_register.fund f ON f.lei = cp.lei
LEFT JOIN entity_mgmt.legal_entity e ON e.lei = cp.lei
JOIN treasury.distribution_component dc ON dc.dist_id = d.dist_id
WHERE d.dist_id = %(distribution_id)s
ORDER BY dc.comp_id
```
