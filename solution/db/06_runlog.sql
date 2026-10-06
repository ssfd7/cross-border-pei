-- Record of every agent run and every step in it: which bundle concept was used, which ontology
-- terms it concerned, what was executed and what came back. Feeds replay, provenance and the benchmark.

CREATE SCHEMA runlog;

CREATE TABLE runlog.run (
    run_id       text PRIMARY KEY,
    arm          text NOT NULL,
    procedure    text,
    subject      text,
    model        text,
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    outcome      text,
    turns        integer,
    duration_ms  integer,
    cost_usd     numeric(10, 4),
    usage        jsonb,
    final_text   text,
    score        jsonb
);

-- kind: computation, tool, lookup, message, or sql for a query the agent wrote itself.
-- attested is null where no attestation applies.
CREATE TABLE runlog.step (
    run_id      text NOT NULL REFERENCES runlog.run,
    seq         integer NOT NULL,
    at          timestamptz NOT NULL DEFAULT now(),
    kind        text NOT NULL CHECK (kind IN ('computation', 'tool', 'lookup', 'message', 'sql')),
    concept     text,
    terms       text[],
    parameters  jsonb,
    executed    text,
    result      jsonb,
    row_count   integer,
    attested    boolean,
    verdict     text,
    PRIMARY KEY (run_id, seq)
);

GRANT USAGE ON SCHEMA runlog TO xbpei_agent;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA runlog TO xbpei_agent;
GRANT UPDATE (finished_at, outcome, turns, duration_ms, cost_usd, usage, final_text, score) ON runlog.run TO xbpei_agent;

-- The role a reviewer signs off as. Only a person can turn a draft schedule into a signed one.
CREATE ROLE xbpei_reviewer LOGIN PASSWORD 'xbpei_reviewer';
GRANT USAGE ON SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance, runlog TO xbpei_reviewer;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance, runlog TO xbpei_reviewer;
GRANT UPDATE (schedule_status, signed_off_by, signed_off_on) ON clearance.withholding_schedule TO xbpei_reviewer;

-- The role the ungrounded control agent queries as: it can read the source systems and the
-- Clearance schema, and nothing else. It cannot see the run log, which holds other runs' answers.
CREATE ROLE xbpei_control LOGIN PASSWORD 'xbpei_control';
GRANT USAGE ON SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance TO xbpei_control;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance TO xbpei_control;
