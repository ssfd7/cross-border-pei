-- Recomputes the figures in answer-key.yaml from the seeded data, independently of any agent.
-- Run: docker compose exec -T db psql -U xbpei_admin -d xbpei < gold/verify.sql

\set asof '2026-10-30'
\pset footer off

\echo '1. Commitments at the record date sum to 100 per fund'
SELECT fund_code, sum(unit_pct) AS econ, sum(vote_pct) AS vote
FROM investor_register.commitment
WHERE from_dt <= :'asof' AND (to_dt IS NULL OR to_dt >= :'asof')
GROUP BY fund_code ORDER BY fund_code;

\echo '2. Effective holding of each ultimate holder in each portfolio company (CQ1, G2, G4, G6)'
WITH RECURSIVE edge (owner, owned, econ, vote) AS (
    SELECT c.inv_no, CASE c.fund_code WHEN 'AGF1' THEN 'E-001' WHEN 'ALF1' THEN 'I-002' END, c.unit_pct, c.vote_pct
    FROM investor_register.commitment c
    WHERE c.from_dt <= :'asof' AND (c.to_dt IS NULL OR c.to_dt >= :'asof')
    UNION ALL
    SELECT s.owner_entity_id, s.owned_entity_id, s.pct_econ, s.pct_vote
    FROM entity_mgmt.shareholding s
    WHERE s.owner_entity_id IN ('E-001', 'E-002', 'E-007')
      AND s.eff_from <= :'asof' AND (s.eff_to IS NULL OR s.eff_to >= :'asof')
    UNION ALL
    SELECT d.owner_inv_no, d.owned_inv_no, d.pct_econ, d.pct_vote
    FROM onboarding.declared_owner d
    WHERE d.alloc_basis = 'NOMINEE_ALLOC'
      AND d.from_dt <= :'asof' AND (d.to_dt IS NULL OR d.to_dt >= :'asof')
), walk (holder, target, econ, vote, path) AS (
    SELECT owner, owned, econ::numeric, vote::numeric, ARRAY[owner, owned] FROM edge
    UNION ALL
    SELECT w.holder, e.owned, w.econ * e.econ / 100, w.vote * e.vote / 100, w.path || e.owned
    FROM walk w JOIN edge e ON e.owner = w.target
    WHERE e.owned <> ALL (w.path)
)
SELECT w.target AS company, w.holder, i.display_name, round(w.econ, 4) AS econ, round(w.vote, 4) AS vote,
       sum(round(w.econ, 4)) OVER (PARTITION BY w.target) AS total_econ
FROM walk w JOIN investor_register.investor i ON i.inv_no = w.holder
WHERE w.target IN ('E-003', 'E-006') AND w.holder NOT IN (SELECT owned FROM edge)
ORDER BY w.target, w.holder;

\echo '3. Ownership declarations that point at each other (G3)'
SELECT a.owned_inv_no, a.owner_inv_no, a.pct_econ AS a_holds, b.pct_econ AS b_holds
FROM onboarding.declared_owner a
JOIN onboarding.declared_owner b ON b.owned_inv_no = a.owner_inv_no AND b.owner_inv_no = a.owned_inv_no
WHERE a.alloc_basis = 'OWNERSHIP' AND b.alloc_basis = 'OWNERSHIP'
  AND a.to_dt IS NULL AND b.to_dt IS NULL AND a.owned_inv_no < a.owner_inv_no;

\echo '4. Same name, different party (G5)'
SELECT display_name, array_agg(inv_no ORDER BY inv_no) AS inv_nos, array_agg(reg_no ORDER BY inv_no) AS reg_nos
FROM investor_register.investor GROUP BY display_name HAVING count(*) > 1;

\echo '5. Tax forms ended before the payment date but not marked as such (G7)'
SELECT f.form_id, f.inv_no, f.valid_to, f.form_status, d.pay_dt
FROM onboarding.tax_form f CROSS JOIN treasury.distribution d
WHERE f.form_status = 'VALIDATED' AND f.valid_to < d.pay_dt;

\echo '6. Holdings where entity management and the investor register disagree (G8)'
SELECT i.inv_no, i.display_name, c.unit_pct AS register_pct, s.pct_econ AS entity_mgmt_pct
FROM entity_mgmt.shareholding s
JOIN entity_mgmt.legal_entity o ON o.entity_id = s.owner_entity_id
JOIN entity_mgmt.legal_entity t ON t.entity_id = s.owned_entity_id
JOIN investor_register.investor i ON i.lei = o.lei
JOIN investor_register.fund f ON f.lei = t.lei
JOIN investor_register.commitment c ON c.inv_no = i.inv_no AND c.fund_code = f.fund_code
WHERE c.from_dt <= :'asof' AND (c.to_dt IS NULL OR c.to_dt >= :'asof')
  AND (c.unit_pct <> s.pct_econ OR c.vote_pct <> s.pct_vote);

\echo '7. Expected withholding on component D-001-A, by beneficial recipient'
WITH expected (payee_cp, recipient, share_pct, rate_pct) AS (VALUES
    ('CP-101', 'I-001', 100.0, 15), ('CP-102', 'I-010', 50.0, 15), ('CP-102', 'I-011', 30.0, 15),
    ('CP-102', 'I-012', 20.0, 30),  ('CP-103', 'I-003', 100.0, 5), ('CP-104', 'I-004', 100.0, 15),
    ('CP-105', 'I-005', 100.0, 15), ('CP-106', 'I-006', 100.0, 30), ('CP-107', 'I-013', 62.5, 15),
    ('CP-107', 'I-014', 37.5, 30),  ('CP-108', 'I-008', 100.0, 15), ('CP-109', 'I-009', 100.0, 30),
    ('CP-115', 'I-015', 100.0, 30), ('CP-116', 'I-016', 100.0, 0),  ('CP-117', 'I-017', 100.0, 0)
), line AS (
    SELECT e.payee_cp, e.recipient, e.rate_pct,
           round(l.gross_amt * e.share_pct / 100, 2) AS gross,
           round(l.gross_amt * e.share_pct / 100 * e.rate_pct / 100, 2) AS tax
    FROM expected e JOIN treasury.distribution_line l ON l.payee_cp = e.payee_cp AND l.comp_id = 'D-001-A'
)
SELECT payee_cp, recipient, rate_pct, gross, tax, gross - tax AS net,
       sum(gross) OVER () AS total_gross, sum(tax) OVER () AS total_tax
FROM line ORDER BY payee_cp, recipient;
