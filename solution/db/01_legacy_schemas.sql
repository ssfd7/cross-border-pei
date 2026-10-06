-- Emulated legacy systems: one schema per system. Agents read these and never write to them.
-- Table and column names are each system's own, not the ontology's. The mapping layer bridges them.
-- There are no keys across schemas: systems are joined on registration number or LEI, never on name.

CREATE SCHEMA entity_mgmt;        -- the fund's own legal structure
CREATE SCHEMA investor_register;  -- investors and their commitments
CREATE SCHEMA onboarding;         -- tax forms and ownership declarations supplied by investors
CREATE SCHEMA treasury;           -- payments and proposed distributions
CREATE SCHEMA documents;          -- index of the document folder
CREATE SCHEMA rulebook;           -- the tax team's rule library (illustrative rules)

-- entity_mgmt ---------------------------------------------------------------

CREATE TABLE entity_mgmt.legal_entity (
    entity_id     text PRIMARY KEY,
    legal_name    text NOT NULL,
    reg_no        text,
    lei           char(20),
    legal_form    text,
    is_fund       char(1) NOT NULL DEFAULT 'N' CHECK (is_fund IN ('Y', 'N')),
    is_spv        char(1) NOT NULL DEFAULT 'N' CHECK (is_spv IN ('Y', 'N')),
    is_portco     char(1) NOT NULL DEFAULT 'N' CHECK (is_portco IN ('Y', 'N')),
    tax_class_us  text
);

CREATE TABLE entity_mgmt.entity_jurisdiction (
    entity_id    text NOT NULL REFERENCES entity_mgmt.legal_entity,
    country      char(2) NOT NULL,
    subdivision  text,
    capacity_cd  text NOT NULL CHECK (capacity_cd IN ('INC', 'TAXRES', 'OPS')),
    from_dt      date NOT NULL,
    to_dt        date,
    recorded_dt  date NOT NULL,
    doc_ref      text
);

CREATE TABLE entity_mgmt.shareholding (
    holding_id       text PRIMARY KEY,
    owner_entity_id  text NOT NULL REFERENCES entity_mgmt.legal_entity,
    owned_entity_id  text NOT NULL REFERENCES entity_mgmt.legal_entity,
    pct_econ         numeric(7, 4) NOT NULL,
    pct_vote         numeric(7, 4) NOT NULL,
    share_class      text,
    eff_from         date NOT NULL,
    eff_to           date,
    doc_ref          text
);

-- investor_register ---------------------------------------------------------

CREATE TABLE investor_register.fund (
    fund_code  text PRIMARY KEY,
    fund_name  text NOT NULL,
    lei        char(20),
    base_ccy   char(3) NOT NULL
);

-- rec_type: INV = investor of record, UO = underlying owner known only from a declaration
CREATE TABLE investor_register.investor (
    inv_no        text PRIMARY KEY,
    display_name  text NOT NULL,
    inv_type      char(3) NOT NULL CHECK (inv_type IN ('ENT', 'IND')),
    rec_type      char(3) NOT NULL CHECK (rec_type IN ('INV', 'UO')),
    reg_no        text,
    lei           char(20),
    legal_form    text,
    country_inc   char(2),
    country_res   char(2)
);

CREATE TABLE investor_register.commitment (
    commit_id   text PRIMARY KEY,
    inv_no      text NOT NULL REFERENCES investor_register.investor,
    fund_code   text NOT NULL REFERENCES investor_register.fund,
    commit_amt  numeric(18, 2) NOT NULL,
    unit_pct    numeric(7, 4) NOT NULL,
    vote_pct    numeric(7, 4) NOT NULL,
    unit_class  text,
    from_dt     date NOT NULL,
    to_dt       date,
    lpa_ref     text
);

-- onboarding ----------------------------------------------------------------

CREATE TABLE onboarding.tax_form (
    form_id          text PRIMARY KEY,
    inv_no           text NOT NULL,
    form_type        text NOT NULL,
    signed_dt        date NOT NULL,
    valid_to         date,
    treaty_claim     char(1) NOT NULL CHECK (treaty_claim IN ('Y', 'N')),
    treaty_country   char(2),
    lob_cd           text,
    is_intermediary  char(1) NOT NULL CHECK (is_intermediary IN ('Y', 'N')),
    form_status      text NOT NULL CHECK (form_status IN ('RECEIVED', 'VALIDATED', 'SUPERSEDED', 'REJECTED')),
    recv_dt          date NOT NULL,
    doc_ref          text
);

-- alloc_basis: OWNERSHIP = who owns the investor; NOMINEE_ALLOC = whose income a nominee receives
CREATE TABLE onboarding.declared_owner (
    decl_id       text PRIMARY KEY,
    owned_inv_no  text NOT NULL,
    owner_inv_no  text NOT NULL,
    pct_econ      numeric(7, 4) NOT NULL,
    pct_vote      numeric(7, 4) NOT NULL,
    alloc_basis   text NOT NULL CHECK (alloc_basis IN ('OWNERSHIP', 'NOMINEE_ALLOC')),
    from_dt       date NOT NULL,
    to_dt         date,
    doc_ref       text
);

CREATE TABLE onboarding.tax_status (
    status_id         text PRIMARY KEY,
    inv_no            text NOT NULL,
    assessed_country  char(2) NOT NULL,
    classification    text NOT NULL,
    from_dt           date NOT NULL,
    to_dt             date,
    recorded_dt       date NOT NULL,
    doc_ref           text
);

CREATE TABLE onboarding.residence_record (
    inv_no       text NOT NULL,
    country      char(2) NOT NULL,
    from_dt      date NOT NULL,
    to_dt        date,
    recorded_dt  date NOT NULL,
    doc_ref      text
);

-- treasury ------------------------------------------------------------------

CREATE TABLE treasury.counterparty (
    cp_id    text PRIMARY KEY,
    cp_name  text NOT NULL,
    reg_no   text,
    lei      char(20),
    country  char(2)
);

CREATE TABLE treasury.distribution (
    dist_id    text PRIMARY KEY,
    fund_cp    text NOT NULL REFERENCES treasury.counterparty,
    record_dt  date NOT NULL,
    pay_dt     date NOT NULL,
    gross_amt  numeric(18, 2) NOT NULL,
    ccy        char(3) NOT NULL,
    status     text NOT NULL
);

CREATE TABLE treasury.distribution_component (
    comp_id         text PRIMARY KEY,
    dist_id         text NOT NULL REFERENCES treasury.distribution,
    income_cd       text NOT NULL,
    source_country  char(2),
    gross_amt       numeric(18, 2) NOT NULL
);

CREATE TABLE treasury.distribution_line (
    comp_id    text NOT NULL REFERENCES treasury.distribution_component,
    payee_cp   text NOT NULL REFERENCES treasury.counterparty,
    gross_amt  numeric(18, 2) NOT NULL,
    PRIMARY KEY (comp_id, payee_cp)
);

CREATE TABLE treasury.payment (
    pay_id       text PRIMARY KEY,
    payer_cp     text NOT NULL REFERENCES treasury.counterparty,
    payee_cp     text NOT NULL REFERENCES treasury.counterparty,
    pay_type_cd  text NOT NULL,
    amt          numeric(18, 2) NOT NULL,
    ccy          char(3) NOT NULL,
    value_dt     date NOT NULL,
    dist_id      text REFERENCES treasury.distribution
);

-- documents -----------------------------------------------------------------

-- file_path is relative to solution/documents; null means the document is not digitised
CREATE TABLE documents.document (
    doc_ref    text PRIMARY KEY,
    doc_type   text NOT NULL,
    title      text NOT NULL,
    doc_dt     date,
    about_ref  text,
    file_path  text
);

-- rulebook ------------------------------------------------------------------

CREATE TABLE rulebook.authority_source (
    authority_id  text PRIMARY KEY,
    title         text NOT NULL,
    citation      text NOT NULL,
    doc_dt        date,
    location      text
);

-- One rate per rule version. min_vote_pct: lowest effective voting percentage in the paying
-- company for the rule to apply (inclusive). treaty_country: residence the recipient must have.
CREATE TABLE rulebook.rule_version (
    rule_id         text NOT NULL,
    version_label   text NOT NULL,
    rule_name       text NOT NULL,
    applies_in      char(2) NOT NULL,
    eff_from        date NOT NULL,
    eff_to          date,
    rate_pct        numeric(5, 2) NOT NULL,
    treaty_country  char(2),
    min_vote_pct    numeric(7, 4),
    PRIMARY KEY (rule_id, version_label)
);

CREATE TABLE rulebook.rule_authority (
    rule_id        text NOT NULL,
    version_label  text NOT NULL,
    authority_id   text NOT NULL REFERENCES rulebook.authority_source,
    FOREIGN KEY (rule_id, version_label) REFERENCES rulebook.rule_version
);

CREATE TABLE rulebook.fact_requirement (
    req_id         text PRIMARY KEY,
    rule_id        text NOT NULL,
    version_label  text NOT NULL,
    description    text NOT NULL,
    mandatory      boolean NOT NULL,
    FOREIGN KEY (rule_id, version_label) REFERENCES rulebook.rule_version
);
