-- Migration: 001_initial_schema
-- Description: Create initial AutomatedProject and CSVData tables with proper relationships
-- Rollback: DROP TABLE IF EXISTS csv_data; DROP TABLE IF EXISTS projects; DROP TABLE IF EXISTS migration_versions;

-- Create projects table for AutomatedProject model
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(50),
    coingecko_id VARCHAR(255) UNIQUE,
    
    -- Source tracking for hybrid V1/V2 support
    data_source VARCHAR(20) NOT NULL CHECK (data_source IN ('manual', 'automated')),
    created_via VARCHAR(20) NOT NULL CHECK (created_via IN ('wizard', 'api_ingestion')),
    
    -- Market data (populated for automated projects from CoinGecko)
    market_cap DECIMAL,
    circulating_supply DECIMAL,
    total_supply DECIMAL,
    category VARCHAR(100),
    
    -- Narrative Score Components (AS-01)
    sector_strength DECIMAL CHECK (sector_strength >= 1 AND sector_strength <= 10),
    value_proposition DECIMAL CHECK (value_proposition >= 1 AND value_proposition <= 10),
    backing_team DECIMAL CHECK (backing_team >= 1 AND backing_team <= 10),
    
    -- Tokenomics Score Components (AS-02)
    valuation_potential DECIMAL CHECK (valuation_potential >= 1 AND valuation_potential <= 10),
    token_utility DECIMAL CHECK (token_utility >= 1 AND token_utility <= 10),
    supply_risk DECIMAL CHECK (supply_risk >= 1 AND supply_risk <= 10),
    
    -- Data Score Component (AS-03)
    accumulation_signal DECIMAL CHECK (accumulation_signal >= 1 AND accumulation_signal <= 10),
    
    -- Calculated Pillar Scores
    narrative_score DECIMAL CHECK (narrative_score >= 1 AND narrative_score <= 10),
    tokenomics_score DECIMAL CHECK (tokenomics_score >= 1 AND tokenomics_score <= 10),
    data_score DECIMAL CHECK (data_score >= 1 AND data_score <= 10),
    
    -- Final Omega Score
    omega_score DECIMAL CHECK (omega_score >= 1 AND omega_score <= 10),
    
    -- State management (AS-05)
    has_data_score BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Timestamps
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create CSV data table for storing analysis results
CREATE TABLE IF NOT EXISTS csv_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- CSV data storage
    raw_data TEXT NOT NULL,
    processed_data JSONB,
    
    -- Analysis results
    data_score DECIMAL CHECK (data_score >= 1 AND data_score <= 10),
    analysis_metadata JSONB,
    
    -- Validation results
    validation_errors JSONB,
    is_valid BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_ticker ON projects(ticker);
CREATE INDEX IF NOT EXISTS idx_projects_coingecko_id ON projects(coingecko_id);
CREATE INDEX IF NOT EXISTS idx_projects_data_source ON projects(data_source);
CREATE INDEX IF NOT EXISTS idx_projects_market_cap ON projects(market_cap);
CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);
CREATE INDEX IF NOT EXISTS idx_projects_has_data_score ON projects(has_data_score);
CREATE INDEX IF NOT EXISTS idx_projects_omega_score ON projects(omega_score);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);

CREATE INDEX IF NOT EXISTS idx_csv_data_project_id ON csv_data(project_id);
CREATE INDEX IF NOT EXISTS idx_csv_data_uploaded_at ON csv_data(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_csv_data_is_valid ON csv_data(is_valid);

-- Update timestamp trigger for projects (PostgreSQL version)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();