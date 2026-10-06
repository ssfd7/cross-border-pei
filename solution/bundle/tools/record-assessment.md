---
type: Tool
title: Record an obligation assessment
description: Record the evaluation of one rule version for one party and event, with the facts used and any facts missing.
status: draft
"@context": /context.jsonld
performed_by: agent
writes: [xbpei:ObligationAssessment, xbpei:evaluates, xbpei:hasSubjectParty, xbpei:hasSubjectEvent, xbpei:assessmentResult, xbpei:reasoning, xbpei:usesFact, xbpei:identifiesGap, xbpei:MissingFactFinding, xbpei:unmetRequirement]
supports: [WF3.3, WF3.6, C3.3, CQ4, CQ5]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

Adds the assessment, one row per fact used and one finding per missing fact. Every fact must be a `source_ref` returned by a computation; a reference that does not resolve to a row is refused. `undetermined` is a recorded result and needs at least one missing fact.

# Input

| Field | Meaning |
|---|---|
| `rule_id`, `version_label` | The rule version evaluated |
| `subject_party` | Investor number of the party assessed |
| `subject_event` | The distribution component, for example `D-001-A` |
| `assessment_result` | `applicable`, `notApplicable` or `undetermined` |
| `reasoning` | How the result follows from the rule and the facts |
| `facts` | List of `source_ref` values relied on |
| `gaps` | List of `{unmet_requirement, about_party, description}` |
