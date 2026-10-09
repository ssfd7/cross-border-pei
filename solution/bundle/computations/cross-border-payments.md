---
type: Attested Computation
title: Payments that cross a border
description: Each payment in a period with the tax residence of its payer and payee on the payment date, and whether it crosses a border.
status: draft
runtime: postgres
parameters:
  - { name: from_date, type: date, required: true }
  - { name: to_date, type: date, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:PaymentEvent, xbpei:payer, xbpei:payee, xbpei:hasPaymentType, xbpei:amount, xbpei:currencyCode, xbpei:occurredOn, xbpei:Party, xbpei:leiCode, xbpei:JurisdictionFact, xbpei:aboutEntity, xbpei:hasJurisdiction, xbpei:hasFactType, xbpei:TaxResidence, xbpei:Incorporation, xbpei:validDuring]
supports: [CQ3]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-08T15:10:00Z }
---

A payment crosses a border when the tax residence of the payer and of the payee on the payment date differ. Treasury's counterparties are matched on LEI to the entities of the structure and to the investors, and the tax residence is read from the system of record for each: entity management for structure entities, the onboarding record for investors. The country treasury holds for a counterparty has no stated capacity and is not used.

`crossing` is `undetermined` where a tax residence is not recorded, where the counterparty matches no entity or investor, or where the sources give more than one. `reason` says which. That is a result to report, not a gap to fill: the incorporation columns are given so the answer can say what is known, and they do not decide the crossing.

# Computation

```sql
WITH fact (cp_id, capacity, country, from_dt, to_dt, source_ref) AS (
    SELECT c.cp_id, j.capacity_cd, j.country, j.from_dt, j.to_dt,
           'entity_mgmt.entity_jurisdiction:' || j.entity_id || '/' || j.capacity_cd || '/' || j.country || '/' || j.from_dt
    FROM treasury.counterparty c
    JOIN entity_mgmt.legal_entity e ON e.lei = c.lei
    JOIN entity_mgmt.entity_jurisdiction j ON j.entity_id = e.entity_id AND j.capacity_cd IN ('TAXRES', 'INC')
    UNION ALL
    SELECT c.cp_id, 'TAXRES', r.country, r.from_dt, r.to_dt, 'onboarding.residence_record:' || r.inv_no || '/' || r.country || '/' || r.from_dt
    FROM treasury.counterparty c
    JOIN investor_register.investor i ON i.lei = c.lei
    JOIN onboarding.residence_record r ON r.inv_no = i.inv_no
), matched (cp_id) AS (
    SELECT c.cp_id FROM treasury.counterparty c
    WHERE EXISTS (SELECT 1 FROM entity_mgmt.legal_entity e WHERE e.lei = c.lei)
       OR EXISTS (SELECT 1 FROM investor_register.investor i WHERE i.lei = c.lei)
), side AS (
    SELECT p.pay_id, s.role, cp.cp_id, cp.cp_name, m.cp_id IS NOT NULL AS matched,
           array_agg(DISTINCT f.country ORDER BY f.country) FILTER (WHERE f.capacity = 'TAXRES') AS residence,
           array_agg(DISTINCT f.country ORDER BY f.country) FILTER (WHERE f.capacity = 'INC') AS incorporation,
           array_agg(DISTINCT f.source_ref ORDER BY f.source_ref) FILTER (WHERE f.capacity = 'TAXRES') AS source_refs
    FROM treasury.payment p
    CROSS JOIN (VALUES ('payer'), ('payee')) AS s (role)
    JOIN treasury.counterparty cp ON cp.cp_id = CASE s.role WHEN 'payer' THEN p.payer_cp ELSE p.payee_cp END
    LEFT JOIN matched m ON m.cp_id = cp.cp_id
    LEFT JOIN fact f ON f.cp_id = cp.cp_id AND f.from_dt <= p.value_dt AND (f.to_dt IS NULL OR f.to_dt >= p.value_dt)
    GROUP BY p.pay_id, s.role, cp.cp_id, cp.cp_name, m.cp_id
)
SELECT p.pay_id AS payment, p.value_dt AS occurred_on, p.pay_type_cd AS payment_code, p.amt AS amount, p.ccy AS currency,
       a.cp_name AS payer_name, array_to_string(a.residence, ',') AS payer_tax_residence, array_to_string(a.incorporation, ',') AS payer_incorporation,
       b.cp_name AS payee_name, array_to_string(b.residence, ',') AS payee_tax_residence, array_to_string(b.incorporation, ',') AS payee_incorporation,
       CASE WHEN cardinality(a.residence) = 1 AND cardinality(b.residence) = 1
            THEN CASE WHEN a.residence = b.residence THEN 'notCrossBorder' ELSE 'crossBorder' END
            ELSE 'undetermined' END AS crossing,
       NULLIF(concat_ws('; ',
           CASE WHEN NOT a.matched THEN 'the payer matches no entity or investor'
                WHEN a.residence IS NULL THEN 'the tax residence of the payer is not recorded'
                WHEN cardinality(a.residence) > 1 THEN 'the sources give the payer more than one tax residence' END,
           CASE WHEN NOT b.matched THEN 'the payee matches no entity or investor'
                WHEN b.residence IS NULL THEN 'the tax residence of the payee is not recorded'
                WHEN cardinality(b.residence) > 1 THEN 'the sources give the payee more than one tax residence' END), '') AS reason,
       'treasury.payment:' || p.pay_id AS source_ref, a.source_refs || b.source_refs AS residence_refs
FROM treasury.payment p
JOIN side a ON a.pay_id = p.pay_id AND a.role = 'payer'
JOIN side b ON b.pay_id = p.pay_id AND b.role = 'payee'
WHERE p.value_dt BETWEEN %(from_date)s::date AND %(to_date)s::date
ORDER BY p.value_dt, p.pay_id
```

# Glossary

Meanings from ontology version 0.10, [xb-pei-model.ttl](../../../model/xb-pei-model.ttl). Locations from the mapping files, [mappings](../references/mappings). For the terms in `reads` and `writes`. Generated by `xbpei/bundle.py`; do not edit.

- **`xbpei:PaymentEvent`** (class; reviewed; steward: Fund finance and treasury)
  - Meaning: A transfer of cash from a payer to a payee. An allocation of taxable income is not a payment event. Kind of `xbpei:Event`.
  - In Postgres: `treasury.payment`.
- **`xbpei:payer`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The party that makes the payment. Of `xbpei:PaymentEvent`. Value: `xbpei:Party`.
  - In Postgres: `treasury.payment.payer_cp`.
- **`xbpei:payee`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The party that receives the payment. Of `xbpei:PaymentEvent`. Value: `xbpei:Party`.
  - In Postgres: `treasury.payment.payee_cp`.
- **`xbpei:hasPaymentType`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The kind of payment. Of `xbpei:PaymentEvent`. Value: `xbpei:PaymentType`.
  - In Postgres: `treasury.payment.pay_type_cd`.
- **`xbpei:amount`** (attribute; reviewed; steward: Fund finance and treasury)
  - Meaning: Gross amount paid, in the payment currency. Of `xbpei:PaymentEvent`. Value: `xsd:decimal`.
  - In Postgres: `treasury.payment.amt`.
- **`xbpei:currencyCode`** (attribute; reviewed; steward: Fund finance and treasury)
  - Meaning: ISO 4217 currency of a payment or of a fund vehicle's commitments. Of `xbpei:PaymentEvent`, `xbpei:FundVehicle`, `xbpei:DistributionEvent`. Value: `xbpei:CurrencyCode`.
  - In Postgres: `treasury.payment.ccy`.
- **`xbpei:occurredOn`** (attribute; reviewed; steward: Fund finance and treasury)
  - Meaning: Date on which the event took place. Of `xbpei:Event`, `xbpei:ChangeEvent`. Value: `xsd:date`.
  - In Postgres: `treasury.payment.value_dt`.
- **`xbpei:Party`** (class; reviewed; steward: Fund administration)
  - Meaning: A person or legal entity that can hold interests, play roles, pay or receive payments, and bear obligations. Identity is separate from the roles a party plays.
  - In Postgres: `investor_register.investor`; `treasury.counterparty`.
- **`xbpei:leiCode`** (attribute; reviewed; steward: Fund administration)
  - Meaning: ISO 17442 Legal Entity Identifier, where one exists. Of `xbpei:LegalEntity`.
  - In Postgres: `entity_mgmt.legal_entity.lei`; `investor_register.investor.lei`; `treasury.counterparty.lei`.
- **`xbpei:JurisdictionFact`** (class; reviewed; steward: Fund tax team)
  - Meaning: A dated statement linking a legal entity to a jurisdiction in a stated capacity, such as incorporation, tax residence or operating location.
  - In Postgres: `entity_mgmt.entity_jurisdiction`; `investor_register.investor`; `onboarding.residence_record`.
- **`xbpei:aboutEntity`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The legal entity the jurisdiction fact is about. Of `xbpei:JurisdictionFact`. Value: `xbpei:LegalEntity`.
  - In Postgres: `entity_mgmt.entity_jurisdiction.entity_id`; `investor_register.investor.inv_no`; `onboarding.residence_record.inv_no`.
- **`xbpei:hasJurisdiction`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The jurisdiction the fact links the entity to. Of `xbpei:JurisdictionFact`. Value: `xbpei:Jurisdiction`.
  - In Postgres: `entity_mgmt.entity_jurisdiction.country`; `entity_mgmt.entity_jurisdiction.subdivision`; `investor_register.investor.country_inc`; `investor_register.investor.country_res`; `onboarding.residence_record.country`.
- **`xbpei:hasFactType`** (relationship; reviewed; steward: Fund finance and treasury)
  - Meaning: The capacity in which the fact links the entity to the jurisdiction: incorporation, tax residence or operating location. Of `xbpei:JurisdictionFact`. Value: `xbpei:JurisdictionFactType`.
  - In Postgres: `entity_mgmt.entity_jurisdiction.capacity_cd`; `xbpei:Incorporation` for every row of `investor_register.investor`; `xbpei:TaxResidence` for every row of `investor_register.investor`; `xbpei:TaxResidence` for every row of `onboarding.residence_record`.
- **`xbpei:TaxResidence`** (code; reviewed; steward: Knowledge engineering)
  - Meaning: The jurisdiction that treats the entity as resident for tax purposes under its own law.
  - In Postgres: `entity_mgmt.entity_jurisdiction.capacity_cd` = 'TAXRES'; the `xbpei:hasFactType` of every `xbpei:JurisdictionFact` in `investor_register.investor`; the `xbpei:hasFactType` of every `xbpei:JurisdictionFact` in `onboarding.residence_record`.
- **`xbpei:Incorporation`** (code; reviewed; steward: Knowledge engineering)
  - Meaning: The jurisdiction under whose law the entity is formed and registered.
  - In Postgres: `entity_mgmt.entity_jurisdiction.capacity_cd` = 'INC'; the `xbpei:hasFactType` of every `xbpei:JurisdictionFact` in `investor_register.investor`.
- **`xbpei:validDuring`** (relationship; reviewed; steward: Fund administration)
  - Meaning: The period during which the interest, statement, certification or clearance holds. Of `xbpei:OwnershipInterest`, `xbpei:JurisdictionFact`, `xbpei:TaxStatusAssertion`, `xbpei:TaxCertification`, `xbpei:Clearance`. Value: `xbpei:TimeInterval`.
  - In Postgres: `entity_mgmt.entity_jurisdiction.from_dt` to `entity_mgmt.entity_jurisdiction.to_dt`; `onboarding.residence_record.from_dt` to `onboarding.residence_record.to_dt`.
