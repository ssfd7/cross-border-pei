-- The role agents connect as. It can read every schema and add rows to Clearance; it cannot
-- change or delete anything, and it cannot write to a legacy system.

CREATE ROLE xbpei_agent LOGIN PASSWORD 'xbpei_agent';

GRANT USAGE ON SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance TO xbpei_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_mgmt, investor_register, onboarding, treasury, documents, rulebook, clearance TO xbpei_agent;
GRANT INSERT ON ALL TABLES IN SCHEMA clearance TO xbpei_agent;
