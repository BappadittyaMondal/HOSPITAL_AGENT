-- ==============================================================================
-- HOSPITAL PLATFORM — MULTI-TENANCY ROW-LEVEL SECURITY (RLS) MIGRATION 002
-- Strict Tenant Isolation: Every query enforces current_setting('app.current_tenant_id')
-- ==============================================================================

-- 1. Helper function to extract active session tenant
CREATE OR REPLACE FUNCTION identity.get_current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 2. Enable Row-Level Security on Identity & Clinical tables
ALTER TABLE identity.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical.patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical.encounters ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical.vitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.event_log ENABLE ROW LEVEL SECURITY;

-- 3. Policy: Tenant Isolation for identity.users
DROP POLICY IF EXISTS tenant_isolation_users ON identity.users;
CREATE POLICY tenant_isolation_users ON identity.users
    FOR ALL
    USING (tenant_id = identity.get_current_tenant_id())
    WITH CHECK (tenant_id = identity.get_current_tenant_id());

-- 4. Policy: Tenant Isolation for clinical.patients
DROP POLICY IF EXISTS tenant_isolation_patients ON clinical.patients;
CREATE POLICY tenant_isolation_patients ON clinical.patients
    FOR ALL
    USING (tenant_id = identity.get_current_tenant_id())
    WITH CHECK (tenant_id = identity.get_current_tenant_id());

-- 5. Policy: Tenant Isolation for clinical.encounters
DROP POLICY IF EXISTS tenant_isolation_encounters ON clinical.encounters;
CREATE POLICY tenant_isolation_encounters ON clinical.encounters
    FOR ALL
    USING (tenant_id = identity.get_current_tenant_id())
    WITH CHECK (tenant_id = identity.get_current_tenant_id());

-- 6. Policy: Tenant Isolation for clinical.vitals
DROP POLICY IF EXISTS tenant_isolation_vitals ON clinical.vitals;
CREATE POLICY tenant_isolation_vitals ON clinical.vitals
    FOR ALL
    USING (tenant_id = identity.get_current_tenant_id())
    WITH CHECK (tenant_id = identity.get_current_tenant_id());

-- 7. Policy: Tenant Isolation for audit.event_log
DROP POLICY IF EXISTS tenant_isolation_audit ON audit.event_log;
CREATE POLICY tenant_isolation_audit ON audit.event_log
    FOR ALL
    USING (tenant_id = identity.get_current_tenant_id())
    WITH CHECK (tenant_id = identity.get_current_tenant_id());
