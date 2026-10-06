-- Gold dataset: one synthetic fund, US-source dividends, Luxembourg as the treaty jurisdiction.
-- All names, identifiers and amounts are synthetic. The trap cases are described in
-- solution/gold/answer-key.yaml; the comments below only mark where each one sits.

-- entity_mgmt ---------------------------------------------------------------

INSERT INTO entity_mgmt.legal_entity (entity_id, legal_name, reg_no, lei, legal_form, is_fund, is_spv, is_portco, tax_class_us) VALUES
('E-001', 'Atlas Growth Fund I LP',           'DE 7104411',  'XBPEISYNTH0000E00100', 'Delaware limited partnership',        'Y', 'N', 'N', 'partnership'),
('E-002', 'Atlas Acquisition SPV LLC',        'DE 7104498',  'XBPEISYNTH0000E00200', 'Delaware limited liability company',  'N', 'Y', 'N', 'disregarded'),
('E-003', 'Orion Manufacturing Inc.',         'DE 2893310',  'XBPEISYNTH0000E00300', 'Delaware corporation',                'N', 'N', 'Y', 'corporation'),
('E-004', 'Atlas GP LLC',                     'DE 7104402',  'XBPEISYNTH0000E00400', 'Delaware limited liability company',  'N', 'N', 'N', 'partnership'),
('E-005', 'Atlas Lux Feeder SCSp',            'B 281 904',   'XBPEISYNTH0000E00500', 'Luxembourg special limited partnership', 'Y', 'N', 'N', 'partnership'),
('E-006', 'Borealis Logistik GmbH',           'HRB 151 772', 'XBPEISYNTH0000E00600', 'German limited liability company',    'N', 'N', 'Y', NULL),
('E-007', 'Atlas Borealis Holdco S.à r.l.',   'B 283 115',   'XBPEISYNTH0000E00700', 'Luxembourg private limited company',  'N', 'Y', 'N', NULL),
('E-010', 'Atlas Co-Invest Vehicle LP',       'DE 7230016',  'XBPEISYNTH0000E01000', 'Delaware limited partnership',        'Y', 'N', 'N', 'partnership');

-- The feeder has no tax residence row: it is unknown, not absent.
INSERT INTO entity_mgmt.entity_jurisdiction (entity_id, country, subdivision, capacity_cd, from_dt, to_dt, recorded_dt, doc_ref) VALUES
('E-001', 'US', 'US-DE', 'INC',    '2023-11-01', NULL, '2023-11-03', NULL),
('E-001', 'US', NULL,    'TAXRES', '2023-11-01', NULL, '2023-11-03', NULL),
('E-002', 'US', 'US-DE', 'INC',    '2024-02-12', NULL, '2024-02-14', NULL),
('E-002', 'US', NULL,    'TAXRES', '2024-02-12', NULL, '2024-02-14', NULL),
('E-003', 'US', 'US-DE', 'INC',    '1998-05-12', NULL, '2024-04-02', NULL),
('E-003', 'US', NULL,    'TAXRES', '1998-05-12', NULL, '2024-04-02', NULL),
('E-003', 'US', 'US-OH', 'OPS',    '1998-05-12', NULL, '2024-04-02', NULL),
('E-004', 'US', 'US-DE', 'INC',    '2023-10-20', NULL, '2023-11-03', NULL),
('E-004', 'US', NULL,    'TAXRES', '2023-10-20', NULL, '2023-11-03', NULL),
('E-005', 'LU', NULL,    'INC',    '2023-12-01', NULL, '2023-12-04', NULL),
('E-006', 'DE', NULL,    'INC',    '2009-03-17', NULL, '2025-01-22', NULL),
('E-006', 'DE', NULL,    'TAXRES', '2009-03-17', NULL, '2025-01-22', NULL),
('E-006', 'DE', 'DE-HH', 'OPS',    '2009-03-17', NULL, '2025-01-22', NULL),
('E-006', 'PL', NULL,    'OPS',    '2019-06-01', NULL, '2025-01-22', NULL),
('E-007', 'LU', NULL,    'INC',    '2024-11-05', NULL, '2024-11-07', NULL),
('E-007', 'LU', NULL,    'TAXRES', '2024-11-05', NULL, '2024-11-07', NULL),
('E-010', 'US', 'US-DE', 'INC',    '2024-01-15', NULL, '2024-01-17', NULL),
('E-010', 'US', NULL,    'TAXRES', '2024-01-15', NULL, '2024-01-17', NULL);

-- H-006 disagrees with the investor register (3.50 here, 3.00 there): case G8.
INSERT INTO entity_mgmt.shareholding (holding_id, owner_entity_id, owned_entity_id, pct_econ, pct_vote, share_class, eff_from, eff_to, doc_ref) VALUES
('H-001', 'E-001', 'E-002', 100,    100,    'Membership interest', '2024-02-12', NULL, NULL),
('H-002', 'E-002', 'E-003', 80,     80,     'Common stock',        '2024-04-02', NULL, 'DOC-0301'),
('H-003', 'E-001', 'E-007', 100,    100,    'Ordinary shares',     '2024-11-05', NULL, NULL),
('H-004', 'E-007', 'E-006', 60,     60,     'Ordinary shares',     '2025-01-22', NULL, NULL),
('H-005', 'E-005', 'E-001', 24,     24,     'LP interest',         '2024-03-01', NULL, NULL),
('H-006', 'E-010', 'E-001', 3.5,    3.5,    'LP interest',         '2024-03-01', NULL, NULL),
('H-007', 'E-004', 'E-001', 4.0125, 7.0125, 'GP interest',         '2024-03-01', NULL, NULL);

-- investor_register ---------------------------------------------------------

INSERT INTO investor_register.fund (fund_code, fund_name, lei, base_ccy) VALUES
('AGF1', 'Atlas Growth Fund I LP', 'XBPEISYNTH0000E00100', 'USD'),
('ALF1', 'Atlas Lux Feeder SCSp',  'XBPEISYNTH0000E00500', 'USD');

-- I-008 and I-009 share a name: case G5. I-014 is an owner the nominee has not disclosed.
INSERT INTO investor_register.investor (inv_no, display_name, inv_type, rec_type, reg_no, lei, legal_form, country_inc, country_res) VALUES
('I-001', 'Harbor Pension Trust',          'ENT', 'INV', 'B 198 220',       'XBPEISYNTH0000I00100', 'Pension fund',                    'LU', 'LU'),
('I-002', 'Atlas Lux Feeder SCSp',         'ENT', 'INV', 'B 281 904',       'XBPEISYNTH0000E00500', 'Special limited partnership',     'LU', NULL),
('I-003', 'Kirchberg Industries S.A.',     'ENT', 'INV', 'B 144 061',       'XBPEISYNTH0000I00300', 'Public limited company',          'LU', 'LU'),
('I-004', 'Limpertsberg Holdings S.A.',    'ENT', 'INV', 'B 152 733',       'XBPEISYNTH0000I00400', 'Public limited company',          'LU', 'LU'),
('I-005', 'Grund Participations S.A.',     'ENT', 'INV', 'B 167 408',       'XBPEISYNTH0000I00500', 'Public limited company',          'LU', 'LU'),
('I-006', 'Meridian Holdings I S.à r.l.',  'ENT', 'INV', 'B 221 590',       'XBPEISYNTH0000I00600', 'Private limited company',         'LU', 'LU'),
('I-007', 'Sterling Nominees Ltd',         'ENT', 'INV', '09417265',        'XBPEISYNTH0000I00700', 'Private company limited by shares', 'GB', 'GB'),
('I-008', 'Alpha Holdings SA',             'ENT', 'INV', 'B 214 577',       'XBPEISYNTH0000I00800', 'Public limited company',          'LU', 'LU'),
('I-009', 'Alpha Holdings SA',             'ENT', 'INV', 'CHE-318.442.907', 'XBPEISYNTH0000I00900', 'Public limited company',          'CH', 'CH'),
('I-010', 'Ardennes Industrial Holding S.A.', 'ENT', 'INV', 'B 139 215',    'XBPEISYNTH0000I01000', 'Public limited company',          'LU', 'LU'),
('I-011', 'Moselle Capital S.A.',          'ENT', 'INV', 'B 176 842',       'XBPEISYNTH0000I01100', 'Public limited company',          'LU', 'LU'),
('I-012', 'Claire Dumont',                 'IND', 'INV', NULL,              NULL,                   NULL,                              NULL, 'FR'),
('I-013', 'Echternach Pension Fund',       'ENT', 'UO',  'B 120 388',       'XBPEISYNTH0000I01300', 'Pension fund',                    'LU', 'LU'),
('I-014', 'Client account 7731',           'ENT', 'UO',  NULL,              NULL,                   NULL,                              NULL, NULL),
('I-015', 'Bertrange Capital S.A.',        'ENT', 'INV', 'B 188 371',       'XBPEISYNTH0000I01500', 'Public limited company',          'LU', 'LU'),
('I-016', 'Atlas Co-Invest Vehicle LP',    'ENT', 'INV', 'DE 7230016',      'XBPEISYNTH0000E01000', 'Limited partnership',             'US', 'US'),
('I-017', 'Atlas GP LLC',                  'ENT', 'INV', 'DE 7104402',      'XBPEISYNTH0000E00400', 'Limited liability company',       'US', 'US'),
('I-018', 'Meridian Holdings II S.à r.l.', 'ENT', 'UO',  'B 221 591',       'XBPEISYNTH0000I01800', 'Private limited company',         'LU', 'LU'),
('I-019', 'Meridian Family Trust',         'ENT', 'UO',  'JE 88214',        NULL,                   'Trust',                           'JE', 'JE');

-- Fund size USD 200m; feeder size USD 48m. Current rows sum to 100 per fund.
-- C-003 and C-004 sit on and just under the threshold once multiplied through to Orion: case G6.
-- C-005 has more economic than voting rights: case G6. C-008a and C-015a are superseded: case G7.
INSERT INTO investor_register.commitment (commit_id, inv_no, fund_code, commit_amt, unit_pct, vote_pct, unit_class, from_dt, to_dt, lpa_ref) VALUES
('C-001',  'I-001', 'AGF1', 20000000, 10,      10,      'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-002',  'I-002', 'AGF1', 48000000, 24,      24,      'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-003',  'I-003', 'AGF1', 25000000, 12.5,    12.5,    'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-004',  'I-004', 'AGF1', 24975000, 12.4875, 12.4875, 'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-005',  'I-005', 'AGF1', 26000000, 13,      10,      'B (limited voting)', '2024-03-01', NULL,         'DOC-0001'),
('C-006',  'I-006', 'AGF1',  6000000, 3,       3,       'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-007',  'I-007', 'AGF1', 12000000, 6,       6,       'A',                  '2025-03-01', NULL,         'DOC-0001'),
('C-007a', 'I-005', 'AGF1', 12000000, 6,       6,       'A',                  '2024-03-01', '2025-02-28', 'DOC-0001'),
('C-008a', 'I-008', 'AGF1', 16000000, 8,       8,       'A',                  '2024-03-01', '2026-06-30', 'DOC-0001'),
('C-008',  'I-008', 'AGF1', 12000000, 6,       6,       'A',                  '2026-07-01', NULL,         'DOC-0001'),
('C-009',  'I-009', 'AGF1',  2000000, 1,       1,       'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-015a', 'I-015', 'AGF1',  6000000, 3,       3,       'A',                  '2024-03-01', '2026-06-30', 'DOC-0001'),
('C-015',  'I-015', 'AGF1', 10000000, 5,       5,       'A',                  '2026-07-01', NULL,         'DOC-0001'),
('C-016',  'I-016', 'AGF1',  6000000, 3,       3,       'A',                  '2024-03-01', NULL,         'DOC-0001'),
('C-017',  'I-017', 'AGF1',  8025000, 4.0125,  7.0125,  'GP',                 '2024-03-01', NULL,         'DOC-0001'),
('C-110',  'I-010', 'ALF1', 24000000, 50,      50,      'A',                  '2024-03-01', NULL,         'DOC-0002'),
('C-111',  'I-011', 'ALF1', 14400000, 30,      30,      'A',                  '2024-03-01', NULL,         'DOC-0002'),
('C-112',  'I-012', 'ALF1',  9600000, 20,      20,      'A',                  '2024-03-01', NULL,         'DOC-0002');

-- onboarding ----------------------------------------------------------------

-- F-015 still reads VALIDATED but ended on 31 December 2025: case G7. F-008a is superseded by F-008.
INSERT INTO onboarding.tax_form (form_id, inv_no, form_type, signed_dt, valid_to, treaty_claim, treaty_country, lob_cd, is_intermediary, form_status, recv_dt, doc_ref) VALUES
('F-001',  'I-001', 'W-8BEN-E', '2025-02-01', '2028-12-31', 'Y', 'LU', 'PENSION',                'N', 'VALIDATED',  '2025-02-03', 'DOC-0101'),
('F-002',  'I-002', 'W-8IMY',   '2025-01-20', NULL,         'N', NULL, NULL,                     'Y', 'VALIDATED',  '2025-01-21', NULL),
('F-003',  'I-003', 'W-8BEN-E', '2024-06-03', '2027-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2024-06-04', NULL),
('F-004',  'I-004', 'W-8BEN-E', '2024-06-05', '2027-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2024-06-06', NULL),
('F-005',  'I-005', 'W-8BEN-E', '2024-07-11', '2027-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2024-07-12', NULL),
('F-006',  'I-006', 'W-8BEN-E', '2024-03-05', '2027-12-31', 'Y', 'LU', 'OWNERSHIP_BASE_EROSION', 'N', 'VALIDATED',  '2024-03-06', NULL),
('F-007',  'I-007', 'W-8IMY',   '2025-03-01', NULL,         'N', NULL, NULL,                     'Y', 'VALIDATED',  '2025-03-03', 'DOC-0107'),
('F-008a', 'I-008', 'W-8BEN-E', '2021-05-10', '2024-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'SUPERSEDED', '2021-05-12', NULL),
('F-008',  'I-008', 'W-8BEN-E', '2024-11-20', '2027-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2024-11-22', NULL),
('F-009',  'I-009', 'W-8BEN-E', '2025-04-14', '2028-12-31', 'N', NULL, NULL,                     'N', 'VALIDATED',  '2025-04-15', NULL),
('F-010',  'I-010', 'W-8BEN-E', '2025-01-15', '2028-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2025-01-16', NULL),
('F-011',  'I-011', 'W-8BEN-E', '2025-01-18', '2028-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2025-01-20', NULL),
('F-012',  'I-012', 'W-8BEN',   '2025-01-22', '2028-12-31', 'N', NULL, NULL,                     'N', 'VALIDATED',  '2025-01-23', NULL),
('F-013',  'I-013', 'W-8BEN-E', '2025-03-04', '2028-12-31', 'Y', 'LU', 'PENSION',                'N', 'VALIDATED',  '2025-03-05', NULL),
('F-015',  'I-015', 'W-8BEN-E', '2022-03-10', '2025-12-31', 'Y', 'LU', 'ACTIVE_TRADE',           'N', 'VALIDATED',  '2022-03-11', 'DOC-0115'),
('F-016',  'I-016', 'W-9',      '2024-02-01', NULL,         'N', NULL, NULL,                     'N', 'VALIDATED',  '2024-02-02', NULL),
('F-017',  'I-017', 'W-9',      '2024-02-01', NULL,         'N', NULL, NULL,                     'N', 'VALIDATED',  '2024-02-02', NULL);

-- DO-001/002: the nominee's allocation, one owner undocumented: case G4.
-- DO-004 to DO-007: the Meridian entities hold shares in each other from 1 August 2026: case G3.
INSERT INTO onboarding.declared_owner (decl_id, owned_inv_no, owner_inv_no, pct_econ, pct_vote, alloc_basis, from_dt, to_dt, doc_ref) VALUES
('DO-001', 'I-007', 'I-013', 62.5, 62.5, 'NOMINEE_ALLOC', '2025-03-01', NULL,         'DOC-0107'),
('DO-002', 'I-007', 'I-014', 37.5, 37.5, 'NOMINEE_ALLOC', '2025-03-01', NULL,         'DOC-0107'),
('DO-003', 'I-006', 'I-019', 100,  100,  'OWNERSHIP',     '2024-03-01', '2026-07-31', NULL),
('DO-004', 'I-006', 'I-018', 30,   30,   'OWNERSHIP',     '2026-08-01', NULL,         'DOC-0106'),
('DO-005', 'I-006', 'I-019', 70,   70,   'OWNERSHIP',     '2026-08-01', NULL,         'DOC-0106'),
('DO-006', 'I-018', 'I-006', 30,   30,   'OWNERSHIP',     '2026-08-01', NULL,         'DOC-0106'),
('DO-007', 'I-018', 'I-019', 70,   70,   'OWNERSHIP',     '2026-08-01', NULL,         'DOC-0106');

INSERT INTO onboarding.tax_status (status_id, inv_no, assessed_country, classification, from_dt, to_dt, recorded_dt, doc_ref) VALUES
('TS-001', 'I-001', 'US', 'opaque',      '2025-02-01', NULL, '2025-02-10', 'DOC-0101'),
('TS-002', 'I-002', 'US', 'transparent', '2025-01-20', NULL, '2025-02-12', NULL),
('TS-003', 'I-003', 'US', 'opaque',      '2024-06-03', NULL, '2024-06-20', NULL),
('TS-004', 'I-004', 'US', 'opaque',      '2024-06-05', NULL, '2024-06-20', NULL),
('TS-005', 'I-005', 'US', 'opaque',      '2024-07-11', NULL, '2024-07-25', NULL),
('TS-006', 'I-006', 'US', 'opaque',      '2024-03-05', NULL, '2024-03-20', NULL),
('TS-007', 'I-007', 'US', 'transparent', '2025-03-01', NULL, '2025-03-15', 'DOC-0107'),
('TS-008', 'I-008', 'US', 'opaque',      '2021-05-10', NULL, '2021-05-20', NULL),
('TS-009', 'I-009', 'US', 'opaque',      '2025-04-14', NULL, '2025-04-20', NULL),
('TS-010', 'I-010', 'US', 'opaque',      '2025-01-15', NULL, '2025-02-12', NULL),
('TS-011', 'I-011', 'US', 'opaque',      '2025-01-18', NULL, '2025-02-12', NULL),
('TS-013', 'I-013', 'US', 'opaque',      '2025-03-04', NULL, '2025-03-15', NULL),
('TS-015', 'I-015', 'US', 'opaque',      '2022-03-10', NULL, '2022-03-20', 'DOC-0115');

INSERT INTO onboarding.residence_record (inv_no, country, from_dt, to_dt, recorded_dt, doc_ref) VALUES
('I-001', 'LU', '2011-01-01', NULL, '2025-02-10', 'DOC-0101'),
('I-003', 'LU', '2004-01-01', NULL, '2024-06-20', NULL),
('I-004', 'LU', '2006-01-01', NULL, '2024-06-20', NULL),
('I-005', 'LU', '2008-01-01', NULL, '2024-07-25', NULL),
('I-006', 'LU', '2017-01-01', NULL, '2024-03-20', NULL),
('I-007', 'GB', '2015-01-01', NULL, '2025-03-15', NULL),
('I-008', 'LU', '2016-01-01', NULL, '2021-05-20', NULL),
('I-009', 'CH', '2012-01-01', NULL, '2025-04-20', NULL),
('I-010', 'LU', '2003-01-01', NULL, '2025-02-12', NULL),
('I-011', 'LU', '2010-01-01', NULL, '2025-02-12', NULL),
('I-012', 'FR', '1999-01-01', NULL, '2025-02-12', NULL),
('I-013', 'LU', '2001-01-01', NULL, '2025-03-15', NULL),
('I-015', 'LU', '2013-01-01', NULL, '2022-03-20', 'DOC-0115'),
('I-016', 'US', '2024-01-15', NULL, '2024-02-05', NULL),
('I-017', 'US', '2023-10-20', NULL, '2024-02-05', NULL);

-- treasury ------------------------------------------------------------------

-- Treasury holds names in capitals and has its own identifiers; CP-108 and CP-109 share a name.
INSERT INTO treasury.counterparty (cp_id, cp_name, reg_no, lei, country) VALUES
('CP-001', 'ATLAS GROWTH FUND I LP',         'DE 7104411',      'XBPEISYNTH0000E00100', 'US'),
('CP-002', 'ATLAS ACQUISITION SPV LLC',      'DE 7104498',      'XBPEISYNTH0000E00200', 'US'),
('CP-003', 'ORION MANUFACTURING INC',        'DE 2893310',      'XBPEISYNTH0000E00300', 'US'),
('CP-006', 'BOREALIS LOGISTIK GMBH',         'HRB 151 772',     'XBPEISYNTH0000E00600', 'DE'),
('CP-007', 'ATLAS BOREALIS HOLDCO SARL',     'B 283 115',       'XBPEISYNTH0000E00700', 'LU'),
('CP-020', 'ATLAS CAPITAL MANAGEMENT LLC',   'DE 7098820',      NULL,                   'US'),
('CP-101', 'HARBOR PENSION TRUST',           'B 198 220',       'XBPEISYNTH0000I00100', 'LU'),
('CP-102', 'ATLAS LUX FEEDER SCSP',          'B 281 904',       'XBPEISYNTH0000E00500', 'LU'),
('CP-103', 'KIRCHBERG INDUSTRIES SA',        'B 144 061',       'XBPEISYNTH0000I00300', 'LU'),
('CP-104', 'LIMPERTSBERG HOLDINGS SA',       'B 152 733',       'XBPEISYNTH0000I00400', 'LU'),
('CP-105', 'GRUND PARTICIPATIONS SA',        'B 167 408',       'XBPEISYNTH0000I00500', 'LU'),
('CP-106', 'MERIDIAN HOLDINGS I SARL',       'B 221 590',       'XBPEISYNTH0000I00600', 'LU'),
('CP-107', 'STERLING NOMINEES LTD',          '09417265',        'XBPEISYNTH0000I00700', 'GB'),
('CP-108', 'ALPHA HOLDINGS SA',              'B 214 577',       'XBPEISYNTH0000I00800', 'LU'),
('CP-109', 'ALPHA HOLDINGS SA',              'CHE-318.442.907', 'XBPEISYNTH0000I00900', 'CH'),
('CP-115', 'BERTRANGE CAPITAL SA',           'B 188 371',       'XBPEISYNTH0000I01500', 'LU'),
('CP-116', 'ATLAS CO-INVEST VEHICLE LP',     'DE 7230016',      'XBPEISYNTH0000E01000', 'US'),
('CP-117', 'ATLAS GP LLC',                   'DE 7104402',      'XBPEISYNTH0000E00400', 'US');

INSERT INTO treasury.distribution (dist_id, fund_cp, record_dt, pay_dt, gross_amt, ccy, status) VALUES
('D-001', 'CP-001', '2026-10-30', '2026-11-16', 12000000, 'USD', 'PROPOSED');

INSERT INTO treasury.distribution_component (comp_id, dist_id, income_cd, source_country, gross_amt) VALUES
('D-001-A', 'D-001', 'DIV', 'US', 10000000),
('D-001-B', 'D-001', 'ROC', NULL,  2000000);

-- One line per investor of record and component, on the register's holdings at the record date.
INSERT INTO treasury.distribution_line (comp_id, payee_cp, gross_amt)
SELECT dc.comp_id, cp.cp_id, round(c.unit_pct / 100 * dc.gross_amt, 2)
FROM investor_register.commitment c
JOIN investor_register.investor i ON i.inv_no = c.inv_no
JOIN treasury.counterparty cp ON cp.lei = i.lei
CROSS JOIN treasury.distribution_component dc
JOIN treasury.distribution d ON d.dist_id = dc.dist_id
WHERE c.fund_code = 'AGF1'
  AND c.from_dt <= d.record_dt AND (c.to_dt IS NULL OR c.to_dt >= d.record_dt);

INSERT INTO treasury.payment (pay_id, payer_cp, payee_cp, pay_type_cd, amt, ccy, value_dt, dist_id) VALUES
('P-001', 'CP-101', 'CP-001', 'CAPCALL', 5000000,  'USD', '2024-03-15', NULL),
('P-002', 'CP-102', 'CP-001', 'CAPCALL', 12000000, 'USD', '2024-03-18', NULL),
('P-003', 'CP-116', 'CP-001', 'CAPCALL', 1500000,  'USD', '2024-03-18', NULL),
('P-004', 'CP-001', 'CP-020', 'MGMTFEE', 1000000,  'USD', '2026-07-01', NULL),
('P-005', 'CP-006', 'CP-007', 'DIV',     3000000,  'EUR', '2026-09-18', NULL),
('P-006', 'CP-007', 'CP-001', 'DIV',     3000000,  'EUR', '2026-09-25', NULL),
('P-007', 'CP-003', 'CP-002', 'DIV',     10000000, 'USD', '2026-10-09', NULL),
('P-008', 'CP-002', 'CP-001', 'DIV',     10000000, 'USD', '2026-10-12', NULL);

-- documents -----------------------------------------------------------------

INSERT INTO documents.document (doc_ref, doc_type, title, doc_dt, about_ref, file_path) VALUES
('DOC-0001', 'LPA',          'Atlas Growth Fund I LP limited partnership agreement',  '2024-02-20', 'AGF1',   NULL),
('DOC-0002', 'LPA',          'Atlas Lux Feeder SCSp limited partnership agreement',   '2024-02-22', 'ALF1',   NULL),
('DOC-0101', 'TAXFORM',      'Harbor Pension Trust W-8BEN-E',                         '2025-02-01', 'I-001',  'DOC-0101-harbor-w8bene.md'),
('DOC-0106', 'OWNERSHIP',    'Meridian Holdings I ownership declaration',             '2026-08-18', 'I-006',  'DOC-0106-meridian-ownership-declaration.md'),
('DOC-0107', 'TAXFORM',      'Sterling Nominees W-8IMY and withholding statement',    '2025-03-01', 'I-007',  'DOC-0107-sterling-w8imy-statement.md'),
('DOC-0115', 'TAXFORM',      'Bertrange Capital W-8BEN-E',                            '2022-03-10', 'I-015',  'DOC-0115-bertrange-w8bene.md'),
('DOC-0201', 'DISTNOTICE',   'Distribution notice D-001',                             '2026-10-02', 'D-001',  'DOC-0201-distribution-notice-d001.md'),
('DOC-0301', 'SPA',          'Orion Manufacturing share purchase agreement',          '2024-04-02', 'E-003',  NULL);

-- rulebook ------------------------------------------------------------------
-- Illustrative. Rates and citations have not been checked against the primary text, and measuring
-- the holding threshold on effective voting rights through the chain is a simplification.

INSERT INTO rulebook.authority_source (authority_id, title, citation, doc_dt, location) VALUES
('AU-01', 'US Internal Revenue Code, withholding of tax on foreign persons', '26 U.S.C. §§ 1441, 1442', NULL, 'https://www.irs.gov/publications/p515'),
('AU-02', 'United States – Luxembourg income tax convention, dividends',     'Convention of 3 April 1996, Article 10', '1996-04-03', NULL);

-- A recipient certified as a US person is outside R-01: the assessment result is notApplicable.
INSERT INTO rulebook.rule_version (rule_id, version_label, rule_name, applies_in, eff_from, eff_to, rate_pct, treaty_country, min_vote_pct) VALUES
('R-01', '2026.1', 'Statutory withholding on US-source dividends paid to foreign persons; also the default where documentation is missing or not valid', 'US', '2026-01-01', NULL, 30, NULL, NULL),
('R-02', '2026.1', 'Treaty rate on US-source dividends paid to a resident of Luxembourg',                                                                'US', '2026-01-01', NULL, 15, 'LU', NULL),
('R-03', '2026.1', 'Treaty rate on US-source dividends paid to a Luxembourg company with a qualifying holding in the paying company',                    'US', '2026-01-01', NULL, 5,  'LU', 10);

INSERT INTO rulebook.rule_authority (rule_id, version_label, authority_id) VALUES
('R-01', '2026.1', 'AU-01'),
('R-02', '2026.1', 'AU-02'),
('R-03', '2026.1', 'AU-02');

INSERT INTO rulebook.fact_requirement (req_id, rule_id, version_label, description, mandatory) VALUES
('FR-01', 'R-01', '2026.1', 'Income type and source jurisdiction of the distribution component', true),
('FR-02', 'R-01', '2026.1', 'Tax certification of the recipient, valid on the payment date', true),
('FR-03', 'R-01', '2026.1', 'For an intermediary or flow-through recipient: the tax certification of each underlying owner and its share', true),
('FR-04', 'R-02', '2026.1', 'Tax residence of the recipient in the treaty jurisdiction', true),
('FR-05', 'R-02', '2026.1', 'A treaty claim with a completed limitation-on-benefits statement', true),
('FR-07', 'R-02', '2026.1', 'For an ownership-based limitation-on-benefits claim: the owners of the recipient up to its ultimate owners', false),
('FR-06', 'R-03', '2026.1', 'Effective voting percentage of the recipient in the paying company, and every fact R-02 requires', true);
