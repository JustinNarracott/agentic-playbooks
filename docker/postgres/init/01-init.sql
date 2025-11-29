-- Initialize dev databases
CREATE DATABASE n8n_dev;
CREATE DATABASE playbooks_test;

-- Playbooks schema
\c playbooks_dev;

CREATE SCHEMA IF NOT EXISTS playbooks;

-- Skill definitions table
CREATE TABLE playbooks.skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Playbook definitions table
CREATE TABLE playbooks.playbooks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Execution traces table
CREATE TABLE playbooks.execution_traces (
    id SERIAL PRIMARY KEY,
    playbook_name VARCHAR(100) NOT NULL,
    execution_id UUID NOT NULL,
    input JSONB,
    output JSONB,
    trace JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Feedback events table (for learning loop)
CREATE TABLE playbooks.feedback_events (
    id SERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    step_id VARCHAR(100),
    ai_value JSONB,
    human_value JSONB,
    feedback_type VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_traces_playbook ON playbooks.execution_traces(playbook_name);
CREATE INDEX idx_traces_execution ON playbooks.execution_traces(execution_id);
CREATE INDEX idx_feedback_execution ON playbooks.feedback_events(execution_id);
