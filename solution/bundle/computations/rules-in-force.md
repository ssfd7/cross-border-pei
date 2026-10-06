---
type: Attested Computation
title: Rule versions in force on a date
description: The rule versions that apply in a jurisdiction on a date, each with its rate, any holding threshold, its authority and the facts it requires.
status: draft
"@context": /context.jsonld
runtime: postgres
parameters:
  - { name: jurisdiction, type: string, required: true }
  - { name: on_date, type: date, required: true }
executor:
  resource: /references/executors/run-postgres.md
  receipt: [executed, parameters, computation_sha256, result_sha256, row_count]
attester:
  resource: /references/attesters/sanctioned_query.py
reads: [xbpei:RuleVersion, xbpei:appliesIn, xbpei:effectiveDuring, xbpei:versionLabel, xbpei:prescribedRate, xbpei:minimumVotingPercentage, xbpei:derivedFrom, xbpei:AuthoritySource, xbpei:citation, xbpei:requiresFact, xbpei:FactRequirement, xbpei:isMandatory]
supports: [WF3.3, WF3.6, C3.3, CQ4, CQ5]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

One rate per rule version. `minimum_voting_pct` is inclusive: a holding equal to it meets the threshold, and it is tested on voting percentage, not economic percentage. `treaty_country` is the residence the recipient must have; it has no ontology term yet. The rules are illustrative and have not been checked against the primary text.

# Computation

```sql
SELECT r.rule_id, r.version_label, r.rule_name, r.rate_pct AS prescribed_rate, r.min_vote_pct AS minimum_voting_pct,
       r.treaty_country, r.eff_from AS effective_from, r.eff_to AS effective_to,
       (SELECT string_agg(a.citation, '; ' ORDER BY a.authority_id)
        FROM rulebook.rule_authority ra JOIN rulebook.authority_source a ON a.authority_id = ra.authority_id
        WHERE ra.rule_id = r.rule_id AND ra.version_label = r.version_label) AS derived_from,
       (SELECT json_agg(json_build_object('requirement', q.req_id, 'description', q.description, 'mandatory', q.mandatory) ORDER BY q.req_id)
        FROM rulebook.fact_requirement q
        WHERE q.rule_id = r.rule_id AND q.version_label = r.version_label) AS requires_facts,
       'rulebook.rule_version:' || r.rule_id || '/' || r.version_label AS source_ref
FROM rulebook.rule_version r
WHERE r.applies_in = %(jurisdiction)s
  AND r.eff_from <= %(on_date)s::date AND (r.eff_to IS NULL OR r.eff_to >= %(on_date)s::date)
ORDER BY r.rule_id
```
