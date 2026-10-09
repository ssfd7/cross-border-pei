---
type: Attested Computation
title: Records that rest on a party's facts
description: The clearances, assessments, determinations and open cases that rely on a recorded fact about a party, and so would have to be revisited if its status or ownership changed.
status: draft
runtime: postgres
parameters: 
  - { name: party_no, type: string, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:Clearance, xbpei:clearanceOf, xbpei:clearanceStatus, xbpei:reliesOnCertification, xbpei:reliesOnFact, xbpei:ObligationAssessment, xbpei:usesFact, xbpei:assessmentResult, xbpei:WithholdingDetermination, xbpei:supportedBy, xbpei:reliesOnClearance, xbpei:determinationOutcome, xbpei:Case, xbpei:concernsParty, xbpei:triggeredBy, xbpei:ChangeEvent, xbpei:changes, xbpei:TaxCertification, xbpei:OwnershipInterest, xbpei:JurisdictionFact, xbpei:TaxStatusAssertion]
supports: [CQ6]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-09T09:00:00Z }
---

The facts about a party are its tax certifications, its tax status and tax residence records, its commitments, and every ownership declaration in which it is the owner or the owned party. A record rests on the party when it cites one of those facts: a clearance through what it relies on, an assessment through the facts it used. A determination of the latest schedule rests on the party when its assessment or its clearance does. An open case is listed when it concerns the party or was triggered by a change to one of its facts.

`rests_on` lists the facts cited. The list is of records that would have to be looked at again, not of records that would change: whether a treatment changes depends on the new fact. A party whose facts nothing cites returns no rows. Assessments and determinations are what the last run of WF3 recorded.

# Computation

```sql
WITH fact (source_ref) AS (
    SELECT 'onboarding.tax_form:' || form_id FROM onboarding.tax_form WHERE inv_no = %(party_no)s
    UNION ALL SELECT 'onboarding.tax_status:' || status_id FROM onboarding.tax_status WHERE inv_no = %(party_no)s
    UNION ALL SELECT 'onboarding.residence_record:' || inv_no || '/' || country || '/' || from_dt FROM onboarding.residence_record WHERE inv_no = %(party_no)s
    UNION ALL SELECT 'investor_register.commitment:' || commit_id FROM investor_register.commitment WHERE inv_no = %(party_no)s
    UNION ALL SELECT 'onboarding.declared_owner:' || decl_id FROM onboarding.declared_owner WHERE %(party_no)s IN (owned_inv_no, owner_inv_no)
), cleared AS (
    SELECT c.clearance_id, c.clearance_of, c.clearance_status, array_agg(r.source_ref ORDER BY r.source_ref) AS rests_on
    FROM clearance.clearance c JOIN clearance.clearance_reliance r USING (clearance_id) JOIN fact USING (source_ref)
    GROUP BY c.clearance_id, c.clearance_of, c.clearance_status
), assessed AS (
    SELECT a.assessment_id, a.subject_party, a.subject_event, a.assessment_result, array_agg(f.source_ref ORDER BY f.source_ref) AS rests_on
    FROM clearance.obligation_assessment a JOIN clearance.assessment_fact f USING (assessment_id) JOIN fact USING (source_ref)
    GROUP BY a.assessment_id, a.subject_party, a.subject_event, a.assessment_result
)
SELECT 'clearance' AS kind, clearance_id AS record, clearance_of AS party, NULL AS component, clearance_status AS state, rests_on,
       'clearance.clearance:' || clearance_id AS source_ref
FROM cleared
UNION ALL
SELECT 'assessment', assessment_id, subject_party, subject_event, assessment_result, rests_on, 'clearance.obligation_assessment:' || assessment_id
FROM assessed
UNION ALL
SELECT 'determination', d.determination_id, d.determined_for, d.for_component, d.determination_outcome,
       array_remove(ARRAY[(SELECT 'clearance.obligation_assessment:' || assessment_id FROM assessed WHERE assessment_id = d.supported_by),
                          (SELECT 'clearance.clearance:' || clearance_id FROM cleared WHERE clearance_id = d.relies_on_clearance)], NULL),
       'clearance.withholding_determination:' || d.determination_id
FROM clearance.withholding_determination d
WHERE d.schedule_id = (SELECT max(schedule_id) FROM clearance.withholding_schedule)
  AND (d.supported_by IN (SELECT assessment_id FROM assessed) OR d.relies_on_clearance IN (SELECT clearance_id FROM cleared))
UNION ALL
SELECT 'case', k.case_id, k.concerns_party, NULL, k.case_kind || ', open', array_remove(ARRAY[e.changes_ref], NULL), 'clearance.case:' || k.case_id
FROM clearance.case k LEFT JOIN clearance.change_event e ON e.change_id = k.triggered_by
WHERE k.closed_on IS NULL AND (k.concerns_party = %(party_no)s OR e.changes_ref IN (SELECT source_ref FROM fact))
ORDER BY 1, 2
```

# Glossary

Meanings from ontology version 0.11, [xb-pei-model.ttl](../../../model/xb-pei-model.ttl). Locations from the mapping files, [mappings](../references/mappings). For the terms in `reads` and `writes`. Generated by `xbpei/bundle.py`; do not edit.

- **`xbpei:Clearance`** (class; proposed; steward: Fund tax team)
  - Meaning: A dated decision on whether a party's tax documentation supports its treatment as an investor in a fund vehicle, with the certifications and facts relied on and any open items. A renewed or withdrawn clearance is a new record; earlier records are kept.
  - In Postgres: `clearance.clearance`.
- **`xbpei:clearanceOf`** (relationship; proposed; steward: Fund tax team)
  - Meaning: The party the clearance is about. Of `xbpei:Clearance`. Value: `xbpei:Party`.
  - In Postgres: `clearance.clearance.clearance_of`.
- **`xbpei:clearanceStatus`** (attribute; proposed; steward: Fund tax team)
  - Meaning: Outcome recorded by the clearance. Of `xbpei:Clearance`. Allowed: cleared, admittedWithOpenItems, notCleared, withdrawn.
  - In Postgres: `clearance.clearance.clearance_status`.
- **`xbpei:reliesOnCertification`** (relationship; proposed; steward: Fund tax team)
  - Meaning: A certification the clearance decision relied on, including those of underlying owners of an intermediary. Of `xbpei:Clearance`. Value: `xbpei:TaxCertification`.
  - In Postgres: `clearance.clearance_reliance`.
- **`xbpei:reliesOnFact`** (relationship; proposed; steward: Fund tax team)
  - Meaning: A recorded fact the clearance decision relied on. A change to that fact puts the clearance up for review. Of `xbpei:Clearance`. Value: `xbpei:FactAssertion`.
  - In Postgres: `clearance.clearance_reliance`.
- **`xbpei:ObligationAssessment`** (class; proposed; steward: Fund tax team)
  - Meaning: A dated evaluation of a rule version against the facts available about a party or event, with a result of applicable, not applicable or undetermined.
  - In Postgres: `clearance.obligation_assessment`.
- **`xbpei:usesFact`** (relationship; proposed; steward: Fund tax team)
  - Meaning: A fact assertion the assessment relied on. Of `xbpei:ObligationAssessment`. Value: `xbpei:FactAssertion`.
  - In Postgres: `clearance.assessment_fact`.
- **`xbpei:assessmentResult`** (attribute; proposed; steward: Fund tax team)
  - Meaning: Outcome of the assessment. Undetermined is a recorded outcome, not a missing value. Of `xbpei:ObligationAssessment`. Allowed: applicable, notApplicable, undetermined.
  - In Postgres: `clearance.obligation_assessment.assessment_result`.
- **`xbpei:WithholdingDetermination`** (class; proposed; steward: Fund tax team)
  - Meaning: The treatment decided for one party and one distribution component: the outcome, the rate and its basis, the clearance relied on and the assessment that supports it.
  - In Postgres: `clearance.withholding_determination`.
- **`xbpei:supportedBy`** (relationship; proposed; steward: Fund tax team)
  - Meaning: An assessment giving the rule version and facts behind the determination. Of `xbpei:WithholdingDetermination`. Value: `xbpei:ObligationAssessment`.
  - In Postgres: `clearance.withholding_determination.supported_by`.
- **`xbpei:reliesOnClearance`** (relationship; proposed; steward: Fund tax team)
  - Meaning: The clearance whose validity on the payment date the determination relied on. Of `xbpei:WithholdingDetermination`. Value: `xbpei:Clearance`.
  - In Postgres: `clearance.withholding_determination.relies_on_clearance`.
- **`xbpei:determinationOutcome`** (attribute; proposed; steward: Fund tax team)
  - Meaning: Outcome for the party and component. Of `xbpei:WithholdingDetermination`. Allowed: cleared, defaultRate, held, notApplicable.
  - In Postgres: `clearance.withholding_determination.determination_outcome`.
- **`xbpei:Case`** (class; proposed; steward: Fund tax team)
  - Meaning: A unit of clearance work with an opening trigger and an outcome: onboarding, renewal, change in circumstances, or distribution.
  - In Postgres: `clearance.case`.
- **`xbpei:concernsParty`** (relationship; proposed; steward: Fund tax team)
  - Meaning: The party the case or the missing fact is about. Of `xbpei:Case`, `xbpei:MissingFactFinding`. Value: `xbpei:Party`.
  - In Postgres: `clearance.case.concerns_party`.
- **`xbpei:triggeredBy`** (relationship; proposed; steward: Fund tax team)
  - Meaning: The change that opened the case. Of `xbpei:Case`. Value: `xbpei:ChangeEvent`.
  - In Postgres: `clearance.case.triggered_by`.
- **`xbpei:ChangeEvent`** (class; proposed; steward: Fund finance and treasury)
  - Meaning: A recorded change to a fact that triggers review of assessments relying on it. A change triggers review; it does not itself prove that an obligation changed.
  - In Postgres: `clearance.change_event`.
- **`xbpei:changes`** (relationship; proposed; steward: Fund tax team)
  - Meaning: The fact assertion the change event alters or supersedes. Of `xbpei:ChangeEvent`. Value: `xbpei:FactAssertion`.
  - In Postgres: `clearance.change_event.changes_ref`.
- **`xbpei:TaxCertification`** (class; proposed; steward: Fund tax team)
  - Meaning: A signed self-certification of tax status supplied by a party, valid for a stated period. Which form applies is jurisdiction-specific and is given by its certification type. Kind of `xbpei:SourceDocument`.
  - In Postgres: `onboarding.tax_form`.
  - Source: 26 CFR 1.1441-1(c)(16).
- **`xbpei:OwnershipInterest`** (class; reviewed; steward: Fund tax team)
  - Meaning: A holding by one party in one legal entity, with its own percentages, share class, validity period, governing agreement and evidence.
  - In Postgres: `investor_register.commitment`; `onboarding.declared_owner` where `alloc_basis = 'OWNERSHIP'`; `onboarding.declared_owner` where `alloc_basis = 'NOMINEE_ALLOC'`.
- **`xbpei:JurisdictionFact`** (class; reviewed; steward: Fund tax team)
  - Meaning: A dated statement linking a legal entity to a jurisdiction in a stated capacity, such as incorporation, tax residence or operating location. Kind of `xbpei:FactAssertion`.
  - In Postgres: `onboarding.residence_record`.
- **`xbpei:TaxStatusAssertion`** (class; reviewed; steward: Fund tax team)
  - Meaning: A dated statement of a party's tax classification or status as assessed under one jurisdiction. Kind of `xbpei:FactAssertion`.
  - In Postgres: `onboarding.tax_status`.
