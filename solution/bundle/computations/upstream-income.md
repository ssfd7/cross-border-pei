---
type: Attested Computation
title: Income received before a distribution
description: Dividend and interest payments received by the distributing fund and the entities it holds in the 60 days before the record date.
status: draft
runtime: postgres
parameters:
  - { name: distribution_id, type: string, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:PaymentEvent, xbpei:payer, xbpei:payee, xbpei:hasPaymentType, xbpei:amount, xbpei:currencyCode, xbpei:occurredOn]
supports: [WF3.2, CQ3]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Shows which company paid the income a component passes on, so that the holding threshold is tested against the right company. Payers and payees are matched to entity management on LEI; a payer with no entity is known to treasury only.

# Computation

```sql
SELECT p.pay_id AS payment, p.value_dt AS occurred_on, p.pay_type_cd AS payment_code, p.amt AS amount, p.ccy AS currency,
       payer.cp_name AS payer_name, payer_entity.entity_id AS payer_entity,
       payee.cp_name AS payee_name, payee_entity.entity_id AS payee_entity,
       'treasury.payment:' || p.pay_id AS source_ref
FROM treasury.distribution d
JOIN treasury.payment p ON p.pay_type_cd IN ('DIV', 'INT') AND p.value_dt BETWEEN d.record_dt - 60 AND d.record_dt
JOIN treasury.counterparty payer ON payer.cp_id = p.payer_cp
JOIN treasury.counterparty payee ON payee.cp_id = p.payee_cp
LEFT JOIN entity_mgmt.legal_entity payer_entity ON payer_entity.lei = payer.lei
LEFT JOIN entity_mgmt.legal_entity payee_entity ON payee_entity.lei = payee.lei
WHERE d.dist_id = %(distribution_id)s
ORDER BY p.value_dt, p.pay_id
```
