---
okf_version: "0.2"
ontology: { prefix: xbpei, namespace: "https://w3id.org/xb-pei/ontology#", resource: ../../model/xb-pei-model.ttl }
---

# Procedures

* [WF3 Withholding determination at distribution](procedures/wf3-withholding-at-distribution.md) - Decide the withholding for every recipient of a distribution before it is paid, and have the schedule signed off.

# Computations

* [Distribution and its components](computations/distribution.md) - A distribution with its dates, fund and components.
* [Frozen investor list](computations/frozen-investor-list.md) - Investors of record at the record date, with gross amount per component.
* [Beneficial recipients of a distribution](computations/beneficial-recipients.md) - The parties whose income each investor's share is.
* [Tax certifications and their validity on a date](computations/tax-certifications.md) - Every certification on file, tested on a date.
* [Clearance in force on a date](computations/clearance-in-force.md) - The latest clearance decision per party, its open items and open change cases.
* [Tax residence on a date](computations/tax-residence.md) - Recorded tax residence of investors and underlying owners.
* [Declared owners of investors on a date](computations/declared-owners.md) - Who owns each investor, as declared.
* [Rule versions in force on a date](computations/rules-in-force.md) - Rates, thresholds, authorities and required facts.
* [Income received before a distribution](computations/upstream-income.md) - Which company paid the income a component passes on.
* [Effective holding in a company](computations/effective-holding.md) - Economic and voting percentage per investor, multiplied through the chain.
* [Circular holdings on a date](computations/ownership-cycles.md) - Parties that hold each other.
* [Holdings on which sources disagree](computations/record-conflicts.md) - Differences between a secondary source and the system of record.

# Tools

* [Read a document](tools/read-document.md) - Return the text of a document by its reference.
* [Open a case](tools/open-case.md) - Open a unit of clearance work.
* [Record an obligation assessment](tools/record-assessment.md) - Record a rule evaluation with the facts used and missing.
* [Draft a withholding schedule](tools/draft-schedule.md) - Record a draft schedule after it passes the checks.
* [Sign off a withholding schedule](tools/sign-off-schedule.md) - Second review by a person.

# References

* [Mappings](references/mappings/) - Where instances of ontology terms live in each source system.
* [Graph mapping](references/mappings/graph/ladybug.yaml) - Where instances of ontology terms live in the graph.
* [Executors](references/executors/) - How computations are run on Postgres and on the graph.
* [Attesters](references/attesters/) - The check that a run used the sanctioned computation.
