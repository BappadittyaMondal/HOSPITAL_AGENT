-- ==============================================================================
-- HOSPITAL PLATFORM — CORE DATABASE FOUNDATION MIGRATION 001
-- PostgreSQL 16 + TimescaleDB + pgvector + Citus / RLS Multi-Tenancy
-- ==============================================================================

-- 1. Enable Core Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- TimescaleDB and pgvector (conditionally enabled if extensions installed)
DO $$
BEGIN
    PERFORM 1 FROM pg_available_extensions WHERE name = 'timescaledb';
    IF FOUND THEN
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    END IF;
    PERFORM 1 FROM pg_available_extensions WHERE name = 'vector';
    IF FOUND THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    END IF;
END $$;

-- 2. Create Core Domain Schemas
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS pharmacy;
CREATE SCHEMA IF NOT EXISTS diagnostics;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS operations;
CREATE SCHEMA IF NOT EXISTS audit;

-- ==============================================================================
-- IDENTITY SCHEMA: Multi-Tenant Facilities, Users, Roles & Credentials
-- ==============================================================================

CREATE TABLE IF NOT EXISTS identity.tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_code VARCHAR(50) UNIQUE NOT NULL,
    facility_name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50) NOT NULL DEFAULT 'HOSPITAL', -- HOSPITAL, CLINIC, LAB, SATELLITE
    jurisdiction_state VARCHAR(50) NOT NULL, -- e.g., 'WEST_BENGAL', 'DELHI'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES identity.tenants(tenant_id) ON DELETE RESTRICT,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    registration_number VARCHAR(100), -- Medical Council Registration (NMC/SMC)
    registration_council VARCHAR(100),
    registration_expiry_date DATE,
    primary_role VARCHAR(50) NOT NULL, -- CONSULTANT, RESIDENT, NURSE, PHARMACIST, TECHNICIAN, ADMIN
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_username UNIQUE(tenant_id, username)
);

-- ==============================================================================
-- CLINICAL SCHEMA: Patients, Encounters, Vitals & Rules
-- ==============================================================================

CREATE TABLE IF NOT EXISTS clinical.patients (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES identity.tenants(tenant_id) ON DELETE RESTRICT,
    mrn VARCHAR(50) NOT NULL, -- Medical Record Number
    abha_id VARCHAR(50),      -- Ayushman Bharat Health Account Number
    abha_address VARCHAR(100),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    dob DATE NOT NULL,
    blood_group VARCHAR(10),
    primary_phone VARCHAR(20) NOT NULL,
    emergency_contact_phone VARCHAR(20),
    primary_language VARCHAR(30) DEFAULT 'BENGALI',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_mrn UNIQUE(tenant_id, mrn)
);

CREATE TABLE IF NOT EXISTS clinical.encounters (
    encounter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES identity.tenants(tenant_id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES clinical.patients(patient_id) ON DELETE RESTRICT,
    encounter_type VARCHAR(30) NOT NULL, -- EMERGENCY, OPD, IPD, ICU, DAYCARE, TELEMEDICINE
    status VARCHAR(30) NOT NULL DEFAULT 'IN_PROGRESS', -- ARRIVED, TRIAGED, IN_PROGRESS, DISCHARGE_PENDING, DISCHARGED
    acuity_level INT CHECK (acuity_level BETWEEN 1 AND 5), -- ESI 1 (Immediate) to 5 (Non-urgent)
    attending_doctor_id UUID REFERENCES identity.users(user_id),
    admitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    discharged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinical.vitals (
    vital_id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES identity.tenants(tenant_id),
    encounter_id UUID NOT NULL REFERENCES clinical.encounters(encounter_id),
    patient_id UUID NOT NULL REFERENCES clinical.patients(patient_id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    heart_rate INT,
    systolic_bp INT,
    diastolic_bp INT,
    spo2 NUMERIC(5,2),
    respiratory_rate INT,
    temperature_celsius NUMERIC(4,2),
    etco2 NUMERIC(5,2),
    mean_arterial_pressure NUMERIC(5,2),
    recorded_by_user_id UUID REFERENCES identity.users(user_id),
    PRIMARY KEY (vital_id, recorded_at)
);

-- ==============================================================================
-- AUDIT SCHEMA: Cryptographic Immutable Event Log (Gap 8, 35)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS audit.event_log (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES identity.tenants(tenant_id),
    user_id UUID REFERENCES identity.users(user_id),
    event_type VARCHAR(100) NOT NULL, -- LOGIN, RECORD_ACCESS, ORDER_SIGNED, BREAK_GLASS, DISPENSE
    entity_table VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE, VIEW, OVERRIDE
    event_payload JSONB NOT NULL,
    ip_address INET,
    user_agent TEXT,
    previous_event_hash VARCHAR(64), -- SHA-256 hash of prior event for tamper proofing
    current_event_hash VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for sub-millisecond retrieval
CREATE INDEX IF NOT EXISTS idx_users_tenant_username ON identity.users(tenant_id, username);
CREATE INDEX IF NOT EXISTS idx_patients_tenant_mrn ON clinical.patients(tenant_id, mrn);
CREATE INDEX IF NOT EXISTS idx_patients_tenant_abha ON clinical.patients(tenant_id, abha_id);
CREATE INDEX IF NOT EXISTS idx_encounters_patient ON clinical.encounters(tenant_id, patient_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit.event_log(tenant_id, recorded_at DESC);
