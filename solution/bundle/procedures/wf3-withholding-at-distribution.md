---
type: Procedure
title: WF3 Withholding determination at distribution
description: Decide the withholding for every recipient of a distribution before it is paid, and have the schedule signed off.
status: draft
tags: [clearance, withholding]
supports: [WF3]
sources:
  - id: wf3
    resource: ../../../business/clearance-product/wf3-withholding-at-distribution.md
    title: WF3 Withholding determination at distribution, operating procedure
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T16:57:20Z }
steps:
  - id: 1
    title: Open a distribution case and freeze the investor list as at the record date
    performed_by: agent
    uses: [/tools/open-case.md, /computations/distribution.md, /computations/frozen-investor-list.md, /computations/record-conflicts.md]
    supports: [C3.1]
  - id: 2
    title: Break the distribution into components by income type and source, and find which company paid the income
    performed_by: agent
    uses: [/computations/distribution.md, /computations/upstream-income.md, /tools/read-document.md]
  - id: 3
    title: For each component, find whether a withholding rule applies and which rule versions are in force
    performed_by: agent
    uses: [/computations/rules-in-force.md]
  - id: 4
    title: Read each investor's clearance and find the recipients behind each investor of record
    performed_by: agent
    uses: [/computations/clearance-in-force.md, /computations/beneficial-recipients.md]
  - id: 5
    title: Test that each clearance and certification is valid on the payment date, not only today
    performed_by: agent
    uses: [/computations/clearance-in-force.md, /computations/tax-certifications.md]
    supports: [C3.2]
  - id: 6
    title: Determine the rate for each recipient and component, and record the assessment behind it
    performed_by: agent
    uses: [/computations/tax-residence.md, /computations/effective-holding.md, /computations/declared-owners.md, /computations/ownership-cycles.md, /tools/record-assessment.md]
    supports: [C3.3]
  - id: 7
    title: For each recipient without a valid clearance, record the fact that is missing and what would cure it
    performed_by: agent
    uses: [/tools/record-assessment.md]
  - id: 8
    title: Where it cannot be cured, apply the default rate or hold the payment, and record which and why
    performed_by: agent
    uses: [/tools/record-assessment.md]
  - id: 9
    title: Compile the withholding schedule
    performed_by: agent
    uses: [/tools/draft-schedule.md]
    supports: [C3.1, C3.3, C3.4]
  - id: 10
    title: Second review and sign-off
    performed_by: human
    role: Tax reviewer
    uses: [/tools/sign-off-schedule.md]
    supports: [C3.5]
  - id: 11
    title: Release payments only against the signed schedule
    performed_by: human
    role: Treasury
    supports: [C3.6]
  - id: 12
    title: Record amounts withheld for deposit and annual statements
    performed_by: human
    role: Fund tax team
---

# Policy

No distribution is released until every recipient's payment is cleared at a documented rate, put on a recorded default rate, or held. Each decision names the certification, the rule version and the reviewer behind it.[^wf3]

The agent prepares the schedule. A person decides: the run stops at step 10.

# Decision rules

Rates, thresholds and required facts come from [the rule versions in force](/computations/rules-in-force.md). They are never taken from memory.

1. **One determination per recipient and component.** The recipient is the party whose income it is, from [beneficial recipients](/computations/beneficial-recipients.md), not always the investor of record. Its gross amount is its share of the investor's line.
2. **Component not subject to withholding.** A return of capital, or income with no rule in force for its source: outcome `notApplicable`, rate 0, with the reason.
3. **Recipient certified as a US person.** The statutory rule is assessed `notApplicable`; outcome `notApplicable`, paid gross.
4. **No clearance in force on the payment date,** or no certification valid on that date: outcome `defaultRate` at the statutory rate, with the missing fact recorded.
5. **Clearance with an open change case.** A fact it relied on has changed. It is not relied on for a reduced rate: the treaty rule is assessed `undetermined`, the default rate is applied, and the line is left for the reviewer.
6. **Treaty rate.** Needs every mandatory fact of the treaty rule: a valid certification claiming the treaty with a limitation-on-benefits statement, and tax residence in the treaty jurisdiction on the payment date. Where the limitation-on-benefits claim rests on ownership, the owners must be known up to the ultimate owners; a circular holding makes that `undetermined`.
7. **Qualifying-holding rate.** Needs the treaty rate's facts and an [effective voting percentage](/computations/effective-holding.md) in the company that paid the income at or above the rule's threshold.
8. **Undocumented recipient behind an intermediary.** Default rate on its share; the documented recipients keep their own rates.
9. **Sources disagree on a holding.** Use the system of record, and say in the reasoning what the other source holds.
10. **Default rate or hold.** A payment is held only where the fund's terms allow it. Where the terms cannot be read, apply the default rate.

Every reduced rate cites the rule version, the certification and the clearance relied on. An investor with no determination, or two, fails the schedule.

# Outcomes

| Outcome | Meaning |
|---|---|
| `cleared` | Paid net of tax at a documented rate |
| `defaultRate` | Paid net of the default rate because a required fact is missing |
| `held` | Payment withheld in full pending documentation, where the fund's terms allow |
| `notApplicable` | The component is not subject to withholding for this recipient; recorded with the reason |

[^wf3]: WF3 Withholding determination at distribution, operating procedure
