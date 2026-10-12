# Roadmap

What comes next for the prototype, ordered by how much each phase strengthens its claim: that one ontology and one semantic layer ground AI agents across two products, with results that can be measured. Dates are not set. The product roadmaps, which run beyond the prototype, are in the [LookThrough](business/lookthrough-product/lookthrough-business-product.md) and [Clearance](business/clearance-product/clearance-business-product.md) requirements.

Where the prototype stands today, and what has not been checked, is in the [README](README.md) under Limits.

## Phases

| Phase | Outcome | Why it matters | Exit criterion |
|---|---|---|---|
| 1 | Realistic synthetic data: a generated dataset that an agent without the semantic layer cannot read its way through | The ungrounded agent produced a correct schedule in 2 of 3 runs, so the benchmark barely separates the two arms | The ungrounded arm fails for stated reasons on the new data, and the answer key is generated with it |
| 2 | A benchmark that can be quoted: enough runs in each arm to report rates, with cost and time per run | The current figures are counts from three or four runs, not rates | Each arm run often enough to report a rate with its spread |
| 3 | Reuse shown: WF1 investor tax onboarding on the same ontology, mappings and computations | Reuse is claimed today and evidenced only between WF3 and LookThrough | WF1 runs end to end, with a count of what it reused and what was new |
| 4 | Governance in motion: a term moves from proposed to reviewed to released, and a change shows what it reaches | Most terms are still proposed, so the lifecycle exists and has not been exercised | One term taken through the lifecycle, with the affected computations and steps re-checked |
| 5 | A second obligation and jurisdiction pair, added as rule versions and data | Tests the claim that the ontology holds no jurisdiction-specific rule | The second pair runs with no change to the ontology's classes |
| 6 | Practitioner review of the procedures and rules, with an effort baseline | Until a baseline exists, every ROI goal is a hypothesis | Procedures reviewed and baseline hours recorded per workflow |

Phases 1 and 2 belong together and come first. Phase 6 depends on finding a practitioner and can run alongside any other phase.

## Phase 1: realistic synthetic data

The present dataset is small and legible: a model can read every row, and some answers are written out in plain words. A benchmark on it measures little. The replacement should have the properties that make the real problem hard.

| Property | What changes | What it tests |
|---|---|---|
| Scale | Several funds, hundreds of investors, several distributions | The answer cannot be held in one prompt; the agent must use the computations |
| Legacy legibility | Cryptic column names and coded values, with no plain-word descriptions | Whether the mappings carry the meaning, not the data |
| Conflict and dirt | More disagreement between source systems, duplicates, missing values and stale records | Whether the system of record and the conflict computations are used |
| History | Dated changes of residence, status and ownership | Whether "as at the payment date" is applied |
| Structure depth | Longer chains, nested intermediaries, more circular holdings | The look-through and effective-holding computations |
| Generated answer key | A seeded generator writes the data and the expected answers together | The key is independent of any agent, and the dataset can be rebuilt at any size |

Two further steps widen the gap between the arms at little cost:

- Run a smaller model in both arms. If grounding lets a cheaper model do the work, that is a cost result as well as a quality one.
- Record cost, turns and elapsed time per run beside correctness, so the benchmark reports what a correct answer costs.

## Smaller items

- Test the 10 percent voting threshold against a direct holding, if the open question below is settled that way.
- Run the Turtle through a reasoner and a profile check. It parses with rdflib only.
- Run `bundle check` and `check_mappings` on every push.

## Deferred

- WF2 documentation upkeep. It follows WF1 and shows nothing that WF1 does not.
- An OSSIE export of the LookThrough metrics, described in [`solution/okf-and-ossie-agentic-project-note.md`](solution/okf-and-ossie-agentic-project-note.md).

## Open questions

- Whether Ownership Interest and Tax Certification are also kinds of Fact Assertion. Jurisdiction Fact and Tax Status Assertion were made so in v0.11.
- Whether to source more definitions. Fourteen terms now name a source that was read before it was recorded (the 1996 convention, the withholding regulation and statute, ISO 17442 and the OMG Commons ontology); the OECD Model Tax Convention, FATF, the other ISO standards and ILPA could not be reached to check and are not cited. See [`model/README.md`](model/README.md).
- Whether the 5 percent rule should test a direct holding. The convention says "owns directly at least 10 percent of the voting stock"; the prototype tests the holding multiplied through the tiers.
- How large the phase 1 dataset should be, given that each agent run costs more as the data grows.
