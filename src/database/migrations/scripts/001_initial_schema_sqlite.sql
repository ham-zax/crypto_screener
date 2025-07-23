-- Migration: 001_initial_schema_sqlite
-- Description: Create initial AutomatedProject and CSVData tables for SQLite (development)
-- Rollback: DROP TABLE IF EXISTS csv_data; DROP TABLE IF EXISTS projects;

-- Create projects table for AutomatedProject model (SQLite version)
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
    name TEXT NOT NULL,
    ticker TEXT,
    coingecko_id TEXT UNIQUE,
    
    -- Source tracking for hybrid V1/V2 support
    data_source TEXT NOT NULL CHECK (data_source IN ('manual', 'automated')),
    created_via TEXT NOT NULL CHECK (created_via IN ('wizard', 'api_ingestion')),
    
    -- Market data (populated for automated projects from CoinGecko)
    market_cap REAL,
    circulating_supply REAL,
    total_supply REAL,
    category TEXT,
    
    -- Narrative Score Components (AS-01)
    sector_strength REAL CHECK (sector_strength >= 1 AND sector_strength <= 10),
    value_proposition REAL CHECK (value_proposition >= 1 AND value_proposition <= 10),
    backing_team REAL CHECK (backing_team >= 1 AND backing_team <= 10),
    
    -- Tokenomics Score Components (AS-02)
    valuation_potential REAL CHECK (valuation_potential >= 1 AND valuation_potential <= 10),
    token_utility REAL CHECK (token_utility >= 1 AND token_utility <= 10),
    supply_risk REAL CHECK (supply_risk >= 1 AND supply_risk <= 10),
    
    -- Data Score Component (AS-03)
    accumulation_signal REAL CHECK (accumulation_signal >= 1 AND accumulation_signal <= 10),
    
    -- Calculated Pillar Scores
    narrative_score REAL CHECK (narrative_score >= 1 AND narrative_score <= 10),
    tokenomics_score REAL CHECK (tokenomics_score >= 1 AND tokenomics_score <= 10),
    data_score REAL CHECK (data_score >= 1 AND data_score <= 10),
    
    -- Final Omega Score
    omega_score REAL CHECK (omega_score >= 1 AND omega_score <= 10),
    
    -- State management (AS-05)
    has_data_score BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Timestamps
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create CSV data table for storing analysis results (SQLite version)
CREATE TABLE IF NOT EXISTS csv_data (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- CSV data storage
    raw_data TEXT NOT NULL,
    processed_data TEXT, -- JSON stored as TEXT in SQLite
    
    -- Analysis results
    data_score REAL CHECK (data_score >= 1 AND data_score <= 10),
    analysis_metadata TEXT, -- JSON stored as TEXT in SQLite
    
    -- Validation results
    validation_errors TEXT, -- JSON stored as TEXT in SQLite
    is_valid BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    analyzed_at DATETIME
);

-- Create indexes for performance optimization (SQLite version)
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

-- Update timestamp trigger for projects (SQLite version)
CREATE TRIGGER IF NOT EXISTS update_projects_updated_at 
    AFTER UPDATE ON projects 
    FOR EACH ROW
BEGIN
    UPDATE projects SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;