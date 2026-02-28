-- Cortex.OS | Database Schema
-- Defines the immutable logs tracking DAG progression for the DeGen Auditor Swarm

-- 1. Swarms (Project/Workspace Level)
CREATE TABLE public.swarms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    config JSONB DEFAULT '{}'::jsonb,
    wallet_address TEXT -- To link Web3 connections
);

-- 2. Executions (Single run of a Swarm)
CREATE TABLE public.executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    swarm_id UUID REFERENCES public.swarms(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED
    total_latency_ms INTEGER DEFAULT 0,
    ipfs_cid TEXT, -- Settlement anchor hash
    blockchain_tx_hash TEXT
);

-- 3. Node Logs (Granular topological step memory)
-- Required for "Time-Travel Debugging" in the UI
CREATE TABLE public.node_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES public.executions(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL, -- e.g., 'node_1_scanner'
    node_type TEXT NOT NULL,
    status TEXT NOT NULL,
    output_payload TEXT,
    consensus_score NUMERIC DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.swarms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.node_logs ENABLE ROW LEVEL SECURITY;

-- Note: RLS Policies should be restricted via the Wallet Address in Phase 3.
