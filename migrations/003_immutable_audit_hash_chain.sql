-- ==============================================================================
-- HOSPITAL PLATFORM — CRYPTOGRAPHIC IMMUTABLE AUDIT HASH CHAIN MIGRATION 003
-- Implements Merkle-style SHA-256 chain linking every audit event to prior event
-- Prohibits UPDATE or DELETE on audit.event_log
-- ==============================================================================

-- 1. Trigger Function: Compute Cryptographic Hash Chain before INSERT
CREATE OR REPLACE FUNCTION audit.fn_enforce_audit_hash_chain()
RETURNS TRIGGER AS $$
DECLARE
    v_prev_hash VARCHAR(64);
BEGIN
    -- Fetch the hash of the latest event for this tenant
    SELECT current_event_hash INTO v_prev_hash
    FROM audit.event_log
    WHERE tenant_id = NEW.tenant_id
    ORDER BY recorded_at DESC, event_id DESC
    LIMIT 1;

    -- If first event for tenant, use genesis hash
    IF v_prev_hash IS NULL THEN
        v_prev_hash := encode(digest('HOSPITAL_GENESIS_BLOCK_' || NEW.tenant_id::TEXT, 'sha256'), 'hex');
    END IF;

    NEW.previous_event_hash := v_prev_hash;

    -- Compute current event hash: SHA256(prev_hash + tenant_id + event_type + entity_id + payload + timestamp)
    NEW.current_event_hash := encode(
        digest(
            v_prev_hash ||
            NEW.tenant_id::TEXT ||
            NEW.event_type ||
            NEW.entity_table ||
            NEW.entity_id ||
            NEW.action ||
            NEW.event_payload::TEXT ||
            CURRENT_TIMESTAMP::TEXT,
            'sha256'
        ),
        'hex'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_audit_hash_chain ON audit.event_log;
CREATE TRIGGER trg_audit_hash_chain
    BEFORE INSERT ON audit.event_log
    FOR EACH ROW
    EXECUTE FUNCTION audit.fn_enforce_audit_hash_chain();

-- 2. Anti-Tamper Trigger: Prohibit UPDATE or DELETE on audit.event_log
CREATE OR REPLACE FUNCTION audit.fn_prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY VIOLATION: audit.event_log is an append-only cryptographic ledger. Modifications and deletions are strictly prohibited.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_audit_update_delete ON audit.event_log;
CREATE TRIGGER trg_prevent_audit_update_delete
    BEFORE UPDATE OR DELETE ON audit.event_log
    FOR EACH ROW
    EXECUTE FUNCTION audit.fn_prevent_audit_tampering();
