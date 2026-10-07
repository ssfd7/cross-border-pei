---
type: Attested Computation
title: Clearance in force on a date
description: For each party, the latest clearance decision for a fund as at a date, whether it is in force then, its open items and any open change case.
status: draft
runtime: postgres
parameters:
  - { name: fund_code, type: string, required: true }
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:Clearance, xbpei:clearanceOf, xbpei:inContextOf, xbpei:clearanceStatus, xbpei:decidedOn, xbpei:validDuring, xbpei:defaultTreatment, xbpei:hasOpenItem, xbpei:reliesOnCertification, xbpei:reliesOnFact, xbpei:Case, xbpei:ChangeEvent, xbpei:triggeredBy]
supports: [WF3.4, WF3.5, C3.2]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

A renewal or withdrawal is a new record, so the decision that counts is the latest one decided on or before the date. An open change case means a fact the clearance relied on has changed and the clearance is under review: it must not be relied on for a reduced rate until the case is closed. An underlying owner of an intermediary has no clearance of its own; the intermediary's clearance covers it.

# Computation

```sql
WITH latest AS (
    SELECT c.*, row_number() OVER (PARTITION BY c.clearance_of ORDER BY c.decided_on DESC, c.valid_from DESC) AS position
    FROM clearance.clearance c
    WHERE c.in_context_of = %(fund_code)s AND c.decided_on <= %(on_date)s::date AND c.valid_from <= %(on_date)s::date
)
SELECT l.clearance_id AS clearance, l.clearance_of AS party_no, l.clearance_status, l.decided_on, l.valid_from, l.valid_to,
       (l.clearance_status IN ('cleared', 'admittedWithOpenItems')
        AND (l.valid_to IS NULL OR l.valid_to >= %(on_date)s::date)) AS in_force_on_date,
       l.default_treatment,
       (SELECT array_agg(m.finding_id || ' (' || m.unmet_requirement || '): ' || m.description ORDER BY m.finding_id)
        FROM clearance.missing_fact_finding m WHERE m.clearance_id = l.clearance_id) AS open_items,
       (SELECT array_agg(k.case_id || ': ' || e.description ORDER BY k.case_id)
        FROM clearance.case k LEFT JOIN clearance.change_event e ON e.change_id = k.triggered_by
        WHERE k.concerns_party = l.clearance_of AND k.case_kind = 'change'
          AND k.opened_on <= %(on_date)s::date AND (k.closed_on IS NULL OR k.closed_on > %(on_date)s::date)) AS open_change_cases,
       (SELECT array_agg(r.source_ref ORDER BY r.source_ref) FROM clearance.clearance_reliance r
        WHERE r.clearance_id = l.clearance_id) AS relies_on,
       'clearance.clearance:' || l.clearance_id AS source_ref
FROM latest l
WHERE l.position = 1
ORDER BY l.clearance_of
```
