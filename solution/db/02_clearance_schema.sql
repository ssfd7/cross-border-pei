-- The Clearance schema: the only place agents write. Tables and columns follow the ontology
-- (xb-pei-model.ttl, pages 03 to 05) in snake_case. Records are added, never changed: a renewed
-- or withdrawn clearance and a corrected schedule are new rows.
-- Parties are identified by investor number; other source records by a reference of the form
-- schema.table:key.

CREATE SCHEMA clearance;

CREATE TABLE clearance.change_event (
    change_id    text PRIMARY KEY,
    changes_ref  text NOT NULL,
    description  text NOT NULL,
    occurred_on  date,
    learned_on   date NOT NULL,
    recorded_on  date NOT NULL
);

CREATE TABLE clearance.case (
    case_id                text PRIMARY KEY,
    case_kind              text NOT NULL CHECK (case_kind IN ('onboarding', 'renewal', 'change', 'distribution')),
    concerns_party         text,
    concerns_distribution  text,
    triggered_by           text REFERENCES clearance.change_event,
    opened_on              date NOT NULL,
    closed_on              date,
    case_outcome           text
);

CREATE TABLE clearance.clearance (
    clearance_id       text PRIMARY KEY,
    case_id            text REFERENCES clearance.case,
    clearance_of       text NOT NULL,
    in_context_of      text NOT NULL,
    clearance_status   text NOT NULL CHECK (clearance_status IN ('cleared', 'admittedWithOpenItems', 'notCleared', 'withdrawn')),
    decided_on         date NOT NULL,
    valid_from         date NOT NULL,
    valid_to           date,
    default_treatment  text,
    reviewed_by        text NOT NULL
);

-- reliance_kind: certification = reliesOnCertification, fact = reliesOnFact
CREATE TABLE clearance.clearance_reliance (
    clearance_id   text NOT NULL REFERENCES clearance.clearance,
    reliance_kind  text NOT NULL CHECK (reliance_kind IN ('certification', 'fact')),
    source_ref     text NOT NULL,
    PRIMARY KEY (clearance_id, source_ref)
);

CREATE TABLE clearance.obligation_assessment (
    assessment_id      text PRIMARY KEY,
    evaluates_rule     text NOT NULL,
    evaluates_version  text NOT NULL,
    subject_party      text,
    subject_event      text,
    assessed_on        date NOT NULL,
    assessment_result  text NOT NULL CHECK (assessment_result IN ('applicable', 'notApplicable', 'undetermined')),
    reasoning          text NOT NULL
);

CREATE TABLE clearance.assessment_fact (
    assessment_id  text NOT NULL REFERENCES clearance.obligation_assessment,
    source_ref     text NOT NULL,
    PRIMARY KEY (assessment_id, source_ref)
);

-- an open item of a clearance (hasOpenItem) or a gap of an assessment (identifiesGap)
CREATE TABLE clearance.missing_fact_finding (
    finding_id         text PRIMARY KEY,
    clearance_id       text REFERENCES clearance.clearance,
    assessment_id      text REFERENCES clearance.obligation_assessment,
    unmet_requirement  text NOT NULL,
    about_party        text,
    description        text NOT NULL,
    recorded_on        date NOT NULL,
    CHECK (clearance_id IS NOT NULL OR assessment_id IS NOT NULL)
);

CREATE TABLE clearance.obligation (
    obligation_id     text PRIMARY KEY,
    assessment_id     text NOT NULL REFERENCES clearance.obligation_assessment,
    obligated_party   text NOT NULL,
    based_on_rule     text NOT NULL,
    based_on_version  text NOT NULL,
    obligation_kind   text NOT NULL CHECK (obligation_kind IN ('reporting', 'withholding')),
    due_date          date
);

-- a schedule is signed only by a named reviewer who did not prepare it (control C3.5)
CREATE TABLE clearance.withholding_schedule (
    schedule_id      text PRIMARY KEY,
    schedule_for     text NOT NULL,
    schedule_status  text NOT NULL CHECK (schedule_status IN ('draft', 'signed', 'superseded')),
    prepared_by      text NOT NULL,
    signed_off_by    text,
    signed_off_on    date,
    CHECK (signed_off_by IS DISTINCT FROM prepared_by),
    CHECK (schedule_status <> 'signed' OR (signed_off_by IS NOT NULL AND signed_off_on IS NOT NULL))
);

CREATE TABLE clearance.withholding_determination (
    determination_id      text PRIMARY KEY,
    schedule_id           text NOT NULL REFERENCES clearance.withholding_schedule,
    determined_for        text NOT NULL,
    for_component         text NOT NULL,
    determination_outcome text NOT NULL CHECK (determination_outcome IN ('cleared', 'defaultRate', 'held', 'notApplicable')),
    gross_amount          numeric(18, 2) NOT NULL,
    withholding_rate      numeric(5, 2) CHECK (withholding_rate BETWEEN 0 AND 100),
    tax_withheld          numeric(18, 2),
    net_amount            numeric(18, 2),
    rate_basis            text NOT NULL,
    relies_on_clearance   text REFERENCES clearance.clearance,
    supported_by          text REFERENCES clearance.obligation_assessment,
    decided_on            date NOT NULL
);
