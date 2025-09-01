-- AI Oracle Database Schema
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enums
CREATE TYPE query_type AS ENUM ('fact', 'opinion', 'calculation', 'prediction');
CREATE TYPE query_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE verification_status AS ENUM ('verified', 'disputed', 'pending');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    wallet_address VARCHAR(42) UNIQUE,
    username VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    subscription_tier VARCHAR(50) DEFAULT 'free'
);

-- Queries table
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    query_type query_type NOT NULL,
    status query_status DEFAULT 'pending',
    miner_count INTEGER DEFAULT 3,
    consensus_threshold DECIMAL(3,2) DEFAULT 0.80,
    timeout_ms INTEGER DEFAULT 30000,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Miners table
CREATE TABLE miners (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    endpoint VARCHAR(500),
    reputation DECIMAL(5,4) DEFAULT 0.5000,
    specializations TEXT[],
    total_queries INTEGER DEFAULT 0,
    successful_queries INTEGER DEFAULT 0,
    average_response_time INTEGER,
    last_seen TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Miner responses table
CREATE TABLE miner_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES queries(id) ON DELETE CASCADE,
    miner_id VARCHAR(255) REFERENCES miners(id),
    response_text TEXT NOT NULL,
    confidence_score DECIMAL(5,4),
    response_time_ms INTEGER,
    sources JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Truth records table
CREATE TABLE truth_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES queries(id) ON DELETE CASCADE,
    consensus_answer TEXT NOT NULL,
    truth_score DECIMAL(5,4) NOT NULL,
    consensus_algorithm VARCHAR(100) NOT NULL,
    miner_count INTEGER NOT NULL,
    verification_status verification_status DEFAULT 'pending',
    blockchain_hash VARCHAR(66),
    consensus_details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Query categories table
CREATE TABLE query_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    consensus_threshold DECIMAL(3,2) DEFAULT 0.80,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hallucination reports table
CREATE TABLE hallucination_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES queries(id) ON DELETE CASCADE,
    miner_response_id UUID REFERENCES miner_responses(id) ON DELETE CASCADE,
    hallucination_type VARCHAR(100),
    confidence DECIMAL(5,4),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- System metrics table
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4),
    metadata JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_queries_user_id ON queries(user_id);
CREATE INDEX idx_queries_status ON queries(status);
CREATE INDEX idx_queries_created_at ON queries(created_at);
CREATE INDEX idx_miner_responses_query_id ON miner_responses(query_id);
CREATE INDEX idx_miner_responses_miner_id ON miner_responses(miner_id);
CREATE INDEX idx_truth_records_query_id ON truth_records(query_id);
CREATE INDEX idx_miners_reputation ON miners(reputation DESC);
CREATE INDEX idx_miners_active ON miners(is_active);

-- Insert default query categories
INSERT INTO query_categories (name, description, consensus_threshold) VALUES
('factual', 'Objective facts that can be verified', 0.85),
('opinion', 'Subjective opinions and preferences', 0.60),
('calculation', 'Mathematical calculations and computations', 0.90),
('prediction', 'Future predictions and forecasts', 0.70),
('analysis', 'Data analysis and interpretation', 0.75);

-- Insert sample miners (for development)
INSERT INTO miners (id, name, endpoint, reputation, specializations) VALUES
('miner_001', 'General AI Miner 1', 'http://miner1.cortensor.network', 0.8500, ARRAY['general', 'factual']),
('miner_002', 'Math Specialist Miner', 'http://miner2.cortensor.network', 0.9200, ARRAY['calculation', 'analysis']),
('miner_003', 'Opinion Analysis Miner', 'http://miner3.cortensor.network', 0.7800, ARRAY['opinion', 'prediction']);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
