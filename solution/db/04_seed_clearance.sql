-- Starting state of the Clearance schema: decisions people made in earlier onboarding and upkeep
-- work, before distribution D-001 was proposed. STAFF-* are synthetic members of the tax team.

INSERT INTO clearance.change_event (change_id, changes_ref, description, occurred_on, learned_on, recorded_on) VALUES
('CE-001', 'onboarding.declared_owner:DO-003', 'Meridian Holdings I reports a restructuring: Meridian Holdings II now holds 30% of it', '2026-08-01', '2026-08-18', '2026-08-20');

INSERT INTO clearance.case (case_id, case_kind, concerns_party, concerns_distribution, triggered_by, opened_on, closed_on, case_outcome) VALUES
('K-006', 'change',  'I-006', NULL, 'CE-001', '2026-08-20', NULL,         NULL),
('K-008', 'renewal', 'I-008', NULL, NULL,     '2024-10-01', '2024-12-02', 'renewed'),
('K-015', 'renewal', 'I-015', NULL, NULL,     '2025-10-01', '2026-01-01', 'withdrawn: no reply before the form ended');

-- CL-006 is still on record as cleared while change case K-006 is open: case G3.
-- CL-015 ended and CL-015W withdrew it: case G7.
INSERT INTO clearance.clearance (clearance_id, case_id, clearance_of, in_context_of, clearance_status, decided_on, valid_from, valid_to, default_treatment, reviewed_by) VALUES
('CL-001',  NULL,    'I-001', 'AGF1', 'cleared',               '2025-02-10', '2025-02-10', '2028-12-31', NULL, 'STAFF-02'),
('CL-002',  NULL,    'I-002', 'AGF1', 'cleared',               '2025-02-12', '2025-02-12', '2028-12-31', NULL, 'STAFF-02'),
('CL-003',  NULL,    'I-003', 'AGF1', 'cleared',               '2024-06-20', '2024-06-20', '2027-12-31', NULL, 'STAFF-02'),
('CL-004',  NULL,    'I-004', 'AGF1', 'cleared',               '2024-06-20', '2024-06-20', '2027-12-31', NULL, 'STAFF-02'),
('CL-005',  NULL,    'I-005', 'AGF1', 'cleared',               '2024-07-25', '2024-07-25', '2027-12-31', NULL, 'STAFF-02'),
('CL-006',  NULL,    'I-006', 'AGF1', 'cleared',               '2024-03-20', '2024-03-20', '2027-12-31', NULL, 'STAFF-02'),
('CL-007',  NULL,    'I-007', 'AGF1', 'admittedWithOpenItems', '2025-03-15', '2025-03-15', '2028-12-31', '30% default rate on the share of the undocumented owner', 'STAFF-02'),
('CL-008A', NULL,    'I-008', 'AGF1', 'cleared',               '2021-05-20', '2021-05-20', '2024-12-31', NULL, 'STAFF-03'),
('CL-008',  'K-008', 'I-008', 'AGF1', 'cleared',               '2024-12-02', '2025-01-01', '2027-12-31', NULL, 'STAFF-02'),
('CL-009',  NULL,    'I-009', 'AGF1', 'cleared',               '2025-04-20', '2025-04-20', '2028-12-31', NULL, 'STAFF-02'),
('CL-015',  NULL,    'I-015', 'AGF1', 'cleared',               '2022-03-20', '2022-03-20', '2025-12-31', NULL, 'STAFF-03'),
('CL-015W', 'K-015', 'I-015', 'AGF1', 'withdrawn',             '2026-01-01', '2026-01-01', NULL,         '30% default rate until a valid form is supplied', 'STAFF-02'),
('CL-016',  NULL,    'I-016', 'AGF1', 'cleared',               '2024-02-05', '2024-02-05', NULL,         NULL, 'STAFF-02'),
('CL-017',  NULL,    'I-017', 'AGF1', 'cleared',               '2024-02-05', '2024-02-05', NULL,         NULL, 'STAFF-02');

INSERT INTO clearance.clearance_reliance (clearance_id, reliance_kind, source_ref) VALUES
('CL-001',  'certification', 'onboarding.tax_form:F-001'),
('CL-002',  'certification', 'onboarding.tax_form:F-002'),
('CL-002',  'certification', 'onboarding.tax_form:F-010'),
('CL-002',  'certification', 'onboarding.tax_form:F-011'),
('CL-002',  'certification', 'onboarding.tax_form:F-012'),
('CL-003',  'certification', 'onboarding.tax_form:F-003'),
('CL-004',  'certification', 'onboarding.tax_form:F-004'),
('CL-005',  'certification', 'onboarding.tax_form:F-005'),
('CL-006',  'certification', 'onboarding.tax_form:F-006'),
('CL-006',  'fact',          'onboarding.declared_owner:DO-003'),
('CL-007',  'certification', 'onboarding.tax_form:F-007'),
('CL-007',  'certification', 'onboarding.tax_form:F-013'),
('CL-008A', 'certification', 'onboarding.tax_form:F-008a'),
('CL-008',  'certification', 'onboarding.tax_form:F-008'),
('CL-009',  'certification', 'onboarding.tax_form:F-009'),
('CL-015',  'certification', 'onboarding.tax_form:F-015'),
('CL-016',  'certification', 'onboarding.tax_form:F-016'),
('CL-017',  'certification', 'onboarding.tax_form:F-017');

INSERT INTO clearance.missing_fact_finding (finding_id, clearance_id, assessment_id, unmet_requirement, about_party, description, recorded_on) VALUES
('MF-001', 'CL-007',  NULL, 'FR-03', 'I-014', 'No tax certification for the owner of 37.5% of the income Sterling Nominees receives', '2025-03-15'),
('MF-002', 'CL-015W', NULL, 'FR-02', 'I-015', 'Form F-015 ended on 31 December 2025 and no new form was received',                    '2026-01-01');
