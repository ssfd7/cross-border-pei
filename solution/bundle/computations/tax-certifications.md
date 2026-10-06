---
type: Attested Computation
title: Tax certifications and their validity on a date
description: Every tax certification on file, with whether it is valid on the date given.
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
reads: [xbpei:TaxCertification, xbpei:certifiedBy, xbpei:hasCertificationType, xbpei:claimsTreatyBenefit, xbpei:isIntermediaryCertification, xbpei:validDuring, xbpei:documentDate]
supports: [WF3.4, WF3.5, C3.2, C3.3]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Validity is tested on the dates, not on the onboarding system's own status flag, which is not updated when a form ends. A superseded form is never valid. `treaty_country` and `limitation_on_benefits` have no ontology term yet.

# Computation

```sql
SELECT t.form_id AS certification, t.inv_no AS party_no, i.display_name AS name, t.form_type AS certification_type,
       t.signed_dt AS signed_on, t.valid_to, t.treaty_claim = 'Y' AS claims_treaty_benefit, t.treaty_country,
       t.lob_cd AS limitation_on_benefits, t.is_intermediary = 'Y' AS is_intermediary, t.form_status AS system_status,
       (t.form_status <> 'SUPERSEDED' AND t.signed_dt <= %(on_date)s::date
        AND (t.valid_to IS NULL OR t.valid_to >= %(on_date)s::date)) AS valid_on_date,
       'onboarding.tax_form:' || t.form_id AS source_ref
FROM onboarding.tax_form t
JOIN investor_register.investor i ON i.inv_no = t.inv_no
ORDER BY t.inv_no, t.signed_dt
```
