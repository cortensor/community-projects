-- Cortensor Agent Auditor Database Schema
-- PostgreSQL 14+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Agents table: Registry of all agents with reputation tracking
CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),  -- 'code', 'content', 'reasoning', 'medical', 'legal', etc.
    overall_confidence FLOAT DEFAULT 0.0 CHECK (overall_confidence >= 0 AND overall_confidence <= 1),
    total_audits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_audit_at TIMESTAMP,
    
    -- Indexes
    CONSTRAINT agents_confidence_check CHECK (overall_confidence >= 0 AND overall_confidence <= 1)
);

CREATE INDEX idx_agents_confidence ON agents(overall_confidence DESC);
CREATE INDEX idx_agents_category ON agents(category);
CREATE INDEX idx_agents_last_audit ON agents(last_audit_at DESC);

-- Audits table: Individual audit records
CREATE TABLE IF NOT EXISTS audits (
    audit_id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Task details
    task_description TEXT NOT NULL,
    task_input TEXT NOT NULL,
    category VARCHAR(100),
    
    -- Cortensor session details
    session_id_poi INTEGER,
    session_id_pouw INTEGER,
    task_id INTEGER,
    
    -- Results
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    poi_similarity FLOAT CHECK (poi_similarity >= 0 AND poi_similarity <= 1),
    pouw_mean_score FLOAT CHECK (pouw_mean_score >= 0 AND pouw_mean_score <= 1),
    consensus_output TEXT,
    
    -- Evidence
    evidence_bundle_ipfs_hash VARCHAR(255),
    evidence_bundle_json JSONB,
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT audits_confidence_check CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

CREATE INDEX idx_audits_agent_id ON audits(agent_id);
CREATE INDEX idx_audits_status ON audits(status);
CREATE INDEX idx_audits_created_at ON audits(created_at DESC);
CREATE INDEX idx_audits_confidence ON audits(confidence_score DESC);
CREATE INDEX idx_audits_ipfs_hash ON audits(evidence_bundle_ipfs_hash);

-- Reputation history: Historical snapshots for trend analysis
CREATE TABLE IF NOT EXISTS reputation_history (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    total_audits INTEGER NOT NULL,
    trend VARCHAR(20),  -- 'improving', 'declining', 'stable'
    
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reputation_history_agent_id ON reputation_history(agent_id);
CREATE INDEX idx_reputation_history_recorded_at ON reputation_history(recorded_at DESC);

-- Validator stats: Track validator performance and consistency
CREATE TABLE IF NOT EXISTS validator_stats (
    validator_address VARCHAR(255) PRIMARY KEY,
    total_validations INTEGER DEFAULT 0,
    average_score_given FLOAT DEFAULT 0.0,
    consistency_score FLOAT DEFAULT 0.0,  -- How often they agree with consensus
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validator_stats_consistency ON validator_stats(consistency_score DESC);

-- Function to update agent reputation (called after each audit)
CREATE OR REPLACE FUNCTION update_agent_reputation()
RETURNS TRIGGER AS $$
BEGIN
    -- Update agent's overall confidence using exponential moving average
    UPDATE agents
    SET 
        overall_confidence = CASE 
            WHEN overall_confidence = 0 THEN NEW.confidence_score
            ELSE (0.3 * NEW.confidence_score) + (0.7 * overall_confidence)
        END,
        total_audits = total_audits + 1,
        last_audit_at = NEW.completed_at
    WHERE agent_id = NEW.agent_id;
    
    -- Insert reputation history snapshot
    INSERT INTO reputation_history (agent_id, confidence_score, total_audits, trend)
    SELECT 
        NEW.agent_id,
        overall_confidence,
        total_audits,
        CASE
            WHEN overall_confidence > LAG(overall_confidence) OVER (ORDER BY last_audit_at) THEN 'improving'
            WHEN overall_confidence < LAG(overall_confidence) OVER (ORDER BY last_audit_at) THEN 'declining'
            ELSE 'stable'
        END
    FROM agents
    WHERE agent_id = NEW.agent_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update reputation after audit completion
CREATE TRIGGER trigger_update_agent_reputation
AFTER INSERT OR UPDATE OF confidence_score ON audits
FOR EACH ROW
WHEN (NEW.status = 'completed' AND NEW.confidence_score IS NOT NULL)
EXECUTE FUNCTION update_agent_reputation();

-- View: Agent leaderboard
CREATE OR REPLACE VIEW agent_leaderboard AS
SELECT 
    a.agent_id,
    a.name,
    a.category,
    a.overall_confidence,
    a.total_audits,
    a.last_audit_at,
    COUNT(DISTINCT au.audit_id) FILTER (WHERE au.created_at > NOW() - INTERVAL '30 days') as audits_last_30_days,
    AVG(au.confidence_score) FILTER (WHERE au.created_at > NOW() - INTERVAL '30 days') as avg_confidence_30d
FROM agents a
LEFT JOIN audits au ON a.agent_id = au.agent_id AND au.status = 'completed'
GROUP BY a.agent_id, a.name, a.category, a.overall_confidence, a.total_audits, a.last_audit_at
ORDER BY a.overall_confidence DESC;

-- View: Recent audits with agent info
CREATE OR REPLACE VIEW recent_audits_with_agents AS
SELECT 
    au.audit_id,
    au.agent_id,
    a.name as agent_name,
    a.category,
    au.task_description,
    au.confidence_score,
    au.poi_similarity,
    au.pouw_mean_score,
    au.status,
    au.evidence_bundle_ipfs_hash,
    au.created_at,
    au.completed_at
FROM audits au
JOIN agents a ON au.agent_id = a.agent_id
ORDER BY au.created_at DESC;

-- Seed some example data (optional)
INSERT INTO agents (agent_id, name, description, category) VALUES
('agent-code-assistant', 'Code Assistant', 'Helps with code generation and debugging', 'code'),
('agent-content-writer', 'Content Writer', 'Generates marketing and blog content', 'content'),
('agent-data-analyst', 'Data Analyst', 'Analyzes data and generates insights', 'reasoning')
ON CONFLICT (agent_id) DO NOTHING;

COMMENT ON TABLE agents IS 'Registry of AI agents with reputation tracking';
COMMENT ON TABLE audits IS 'Individual audit records with PoI and PoUW results';
COMMENT ON TABLE reputation_history IS 'Historical reputation snapshots for trend analysis';
COMMENT ON TABLE validator_stats IS 'Performance metrics for validator nodes';
