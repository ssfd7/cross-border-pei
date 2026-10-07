---
type: Tool
title: Draft a withholding schedule
description: Record a draft withholding schedule for a distribution with one determination per recipient and component.
status: draft
performed_by: agent
writes: [xbpei:WithholdingSchedule, xbpei:scheduleFor, xbpei:scheduleStatus, xbpei:preparedBy, xbpei:includes, xbpei:WithholdingDetermination, xbpei:determinedFor, xbpei:forComponent, xbpei:determinationOutcome, xbpei:grossAmount, xbpei:withholdingRate, xbpei:taxWithheld, xbpei:netAmount, xbpei:rateBasis, xbpei:reliesOnClearance, xbpei:supportedBy]
supports: [WF3.9, C3.1, C3.3, C3.4]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
---

The draft is checked before anything is written, and refused with the reasons if it fails:

- the shapes generated from the ontology (allowed outcomes, rates between 0 and 100, one value where one is allowed);
- the control shapes: one outcome per party and component, a cleared rate cites its basis, tax and net follow from gross and rate;
- the gross amounts of each component sum to the component's gross amount in the distribution.

The schedule is written as `draft`. Only a person can sign it.

# Input

| Field | Meaning |
|---|---|
| `distribution_id` | The distribution the schedule is for |
| `determinations` | List of `{determined_for, for_component, determination_outcome, gross_amount, withholding_rate, tax_withheld, net_amount, rate_basis, relies_on_clearance, supported_by}` |
