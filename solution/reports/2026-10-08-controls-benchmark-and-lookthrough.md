# Repeated WF3 runs, reviewer measures and the first LookThrough answers

Date: 2026-10-08. Follows the [first run report](2026-10-06-wf3-two-arm-run.md), which describes the task, the dataset and the two arms. All data is synthetic and the rules are illustrative.

## 1. Summary

- Each arm of WF3 has now been run three times. The grounded agent produced the correct schedule in all three runs. The ungrounded agent produced it in two and, in the third, gave the investor in a circular holding the treaty rate, under-withholding by USD 45,000.
- Five measures of what a reviewer or auditor gets from a run were added beside the accuracy score. The ungrounded arm has no result on four of them, because it has no write checks, no recorded evidence and no links from terms to steps.
- The measures also showed two gaps on the grounded side. The write tool accepted four of ten faulty drafts, and it accepted a line with outcome `notApplicable` that cites no assessment. Both were closed afterwards, and a fourth grounded run passed the stricter checks (section 6).
- A read-only agent answered the six LookThrough questions and refused two unanswerable ones from the same bundle, scoring 29 of 29 points against the answer key. Each question was asked once. CQ4 to CQ6 were added on 2026-10-09.

Three runs per arm is a small number. One miss in three shows that the ungrounded arm can fail on this dataset; it does not measure how often.

## 2. Repeated runs of WF3

| Measure | Control | Grounded |
|---|---|---|
| Runs | RUN-c0837d95, RUN-3eaf6c9e, RUN-f1f55d26 | RUN-582dd980, RUN-067ce03d, RUN-083167fd |
| Lines of D-001-A correct | 15, 15, 14 of 15 | 15, 15, 15 of 15 |
| Difference from the answer key in tax | 0, 0, −45,000 | 0, 0, 0 |
| Recipients on which all runs agree | 14 of 15 | 15 of 15 |
| Scored points, as stored | 12, 13, 12 of 13 | 13, 13, 13 of 13 |
| Turns | 36 to 38 | 63 to 96 |
| Elapsed time | 120 to 130 seconds | 201 to 273 seconds |
| Estimated cost per run | USD 0.52 to 0.59 | USD 1.25 to 1.45 |

The first run of each arm is the one in the first report. The stored 12 for RUN-c0837d95 is the scorer word-list issue described there.

**The control's miss.** In RUN-f1f55d26 the agent found the circular holding between Meridian Holdings I and II and the open change case, and still entered I-006 as `cleared` at 15%, marked "provisional", with a note that 30% would apply if the clearance were withdrawn. The answer key requires the default rate or a hold. The other two control runs applied 30%. Nothing checked the line before it reached the reviewer.

The cost comparison is still not like for like: the grounded arm records an assessment for each rule it evaluates and passes its draft through the checks.

## 3. What a reviewer gets

The measures are computed by `python -m xbpei.measures` and shown on the Benchmark screen. The first is taken from the run log of each run. The next three need no agent run; their expected results are in `gold/answer-key.yaml`.

### Evidence behind the schedule

A line has evidence when it cites a recorded assessment and every fact that assessment cites resolves to an existing row.

| Run | Arm | Lines | Lines with evidence | Assessments | Facts cited | Facts that resolve |
|---|---|---|---|---|---|---|
| RUN-c0837d95 | control | 30 | 0 | 0 | 0 | 0 |
| RUN-3eaf6c9e | control | 30 | 0 | 0 | 0 | 0 |
| RUN-f1f55d26 | control | 30 | 0 | 0 | 0 | 0 |
| RUN-582dd980 | grounded | 30 | 30 | 43 | 207 | 207 |
| RUN-067ce03d | grounded | 30 | 15 | 19 | 109 | 109 |
| RUN-083167fd | grounded | 30 | 15 | 22 | 123 | 123 |

The control's basis for each line is free text, and nothing in it was checked against the data. In every grounded run all 15 dividend lines have evidence. Only the first grounded run recorded an assessment for the 15 return-of-capital lines; the other two gave those lines a text basis and no assessment, and the write tool accepted them.

### Faulty drafts put to the write tool

Ten drafts, each made by one change to an accepted draft. A draft the tool accepts would reach the reviewer.

| Id | Fault | Control | Result |
|---|---|---|---|
| F1 | The same recipient twice for one component | C3.1 | Refused |
| F2 | A recipient left off the schedule | C3.1 | Refused |
| F3 | Tax withheld does not follow from gross and rate | C3.4 | Refused |
| F4 | A cleared rate with no clearance or assessment behind it | C3.3 | Refused |
| F5 | A line citing an assessment that does not exist | C3.3 | Refused |
| F6 | A line for a party that is not an investor | C3.1 | Refused |
| F7 | The nominee paid as if the income were its own | C3.1 | Accepted |
| F8 | A treaty rate on an expired form and a lapsed clearance | C3.2 | Accepted |
| F9 | The 5% rate where the supporting assessment gives 15% | C3.3 | Accepted |
| F10 | A line supported by another party's assessment | C3.3 | Accepted |

The tool refuses faults of form and accepts faults of substance. It checks that a line's clearance and assessment exist, not that they are about that party, are in force on the payment date or give that rate. The control arm has no write checks at all: its miss in section 2 is a fault of the F8 kind.

### What a change to a term reaches

For three terms, `bundle affected` returned the computations, tools and WF3 steps that a hand check of the bundle's frontmatter gives: `xbpei:votingPercentage` reaches four computations and steps 1 and 6; `xbpei:TaxCertification` reaches two computations and steps 4 and 5; `xbpei:withholdingRate` reaches one tool and step 9. The control arm has nothing that links a term to a step.

### Terms that cannot be answered

Six lookups returned what was expected: two mapped terms were answered, two terms of the ontology that no source holds (`xbpei:vintageYear`, carried interest) were reported as unmapped, and two phrases outside the ontology (politically exposed person, net asset value) were reported as unknown.

## 4. LookThrough questions

`python -m xbpei.ask` runs an agent with the same bundle as the Clearance agent and without the write tools. It looks terms up and runs attested computations; it writes no queries. Three computations were added for it: the entities of the fund structure, the jurisdictions on the chain to a company, and the payments that cross a border.

| Question | Run | Result | Points | Turns | Estimated cost |
|---|---|---|---|---|---|
| CQ1 Which investors have indirect exposure to Orion Manufacturing, and how much? | RUN-9eb95edb | Answered | 3 of 3 | 10 | USD 0.16 |
| CQ2 Which jurisdictions are on the chain from the fund to each portfolio company? | RUN-bee92a47 | Answered | 7 of 7 | 9 | USD 0.15 |
| CQ3 Which payments cross a jurisdictional boundary? | RUN-c315ee6b | Answered | 3 of 3 | 7 | USD 0.12 |
| CQ4 What facts and rules support the withholding on Harbor Pension Trust's share of the dividend? | RUN-126585e2 | Answered | 4 of 4 | 9 | USD 0.19 |
| CQ5 Which required facts are missing, and for which parties? | RUN-f14afc82 | Answered | 2 of 2 | 5 | USD 0.07 |
| CQ6 What would have to be revisited if the status or ownership of Meridian Holdings I changed? | RUN-8ee6fded | Answered | 4 of 4 | 10 | USD 0.15 |
| What is the vintage year of Atlas Growth Fund I? | RUN-635befc4 | Refused: no source holds the term | 3 of 3 | 8 | USD 0.05 |
| Which investors are politically exposed persons? | RUN-2bf03b90 | Refused: not a term of the ontology | 3 of 3 | 9 | USD 0.03 |

The answers reported what the sources leave open without being asked for it: the difference between the investor register and entity management on one holding (3.0% against 3.5%), the unrecorded tax residence of the Luxembourg feeder, and the two payments whose crossing cannot be determined.

CQ4 to CQ6 were added the next day with three more computations: the support for a withholding determination, the missing-fact findings, and the records that rest on a party's facts. They read the assessments, findings and schedule that the last run of WF3 recorded (RUN-305c4912), so the second product reuses what the first one wrote. Their answer key names only what any correct run leaves, which makes these three the most lightly scored. For CQ6 the answer lists the records to look at again; whether a treatment would change depends on the new fact, and the answer says so.

## 5. Limits

- Three runs per arm and one run per question. The figures show what happened, not rates.
- There is no ungrounded arm for the LookThrough questions, so they show that the bundle supports a second product, not that grounding improves the answers.
- The evidence, term-impact and lookup measures favour the grounded arm by construction. They describe what the semantic layer leaves on record; they are not a contest between two agents.
- The faulty drafts were written by the same hand as the checks they test. A practitioner would add others.
- The dataset is unchanged: small, and legible to a model without help. The limits in section 9 of the first report still apply.

## 6. Checks added after these runs

The results in sections 2 and 3 are as found. Afterwards the write tool was given four more checks, and an eleventh faulty draft was added (F11, a line with no assessment behind it):

- each component has one line for every beneficial recipient of the distribution and for no other party (F7);
- every line cites an assessment, and the assessment is about that party and that component (F10, F11);
- the outcome follows from the assessment, and where the assessment found a rule version applicable the rate is that rule version's (F9);
- a clearance relied on is in force on the payment date (F8).

With these, the tool refuses 11 of 11 faulty drafts. One more grounded run, RUN-305c4912, was made against them: its first draft was accepted, with 15 of 15 lines correct, 13 of 13 points and evidence behind 30 of 30 lines (34 assessments, 179 of 179 cited facts resolve), in 78 turns for an estimated USD 1.52. The drafts of RUN-067ce03d and RUN-083167fd would now be refused for their return-of-capital lines.

One run shows the agent can still complete the procedure under the stricter checks; it says nothing more. The checks are written against the same ten faults they were built to catch, so 11 of 11 is a regression test, not evidence that no faulty draft can pass.

## 7. Options from here

1. **Have a practitioner add faulty drafts** the present checks were not written for.
2. **A harder dataset or a smaller model**, as set out in the first report. Neither has been tried.

## 8. Files

- `xbpei/measures.py`, `xbpei/ask.py`, and `score_answer` in `xbpei/score.py`
- `gold/answer-key.yaml`: sections `lookthrough_questions`, `term_impact`, `term_lookup` and `faulty_drafts`
- `bundle/computations/structure-entities.md`, `chain-jurisdictions.md`, `cross-border-payments.md`, `determination-support.md`, `missing-facts.md`, `records-resting-on-party.md`
- `reports/runs/`: every run named above, with its steps
