-- Migration: 002_performance_indexes
-- Description: Add performance optimization indexes for common queries
-- Rollback: DROP INDEX IF EXISTS idx_projects_omega_score_desc; DROP INDEX IF EXISTS idx_projects_market_cap_desc; DROP INDEX IF EXISTS idx_projects_composite_search; DROP INDEX IF EXISTS idx_csv_data_composite;

-- Performance indexes for common query patterns

-- Composite index for main project listing with sorting
CREATE INDEX IF NOT EXISTS idx_projects_composite_search 
ON projects(data_source, has_data_score, market_cap DESC, omega_score DESC);

-- Optimized index for omega score sorting (most common sort)
CREATE INDEX IF NOT EXISTS idx_projects_omega_score_desc 
ON projects(omega_score DESC) WHERE omega_score IS NOT NULL;

-- Optimized index for market cap sorting and filtering
CREATE INDEX IF NOT EXISTS idx_projects_market_cap_desc 
ON projects(market_cap DESC) WHERE market_cap IS NOT NULL;

-- Category-based filtering optimization
CREATE INDEX IF NOT EXISTS idx_projects_category_filtered 
ON projects(category, market_cap DESC) WHERE category IS NOT NULL;

-- Time-based queries optimization
CREATE INDEX IF NOT EXISTS idx_projects_recent_updates 
ON projects(last_updated DESC, data_source);

-- CSV data performance optimization
CREATE INDEX IF NOT EXISTS idx_csv_data_composite 
ON csv_data(project_id, is_valid, uploaded_at DESC);

-- Partial index for projects awaiting data (common filter)
CREATE INDEX IF NOT EXISTS idx_projects_awaiting_data 
ON projects(market_cap DESC, created_at DESC) 
WHERE has_data_score = FALSE AND data_source = 'automated';

-- Partial index for completed projects (with omega scores)
CREATE INDEX IF NOT EXISTS idx_projects_completed 
ON projects(omega_score DESC, market_cap DESC) 
WHERE omega_score IS NOT NULL;

-- Score component indexes for analytics
CREATE INDEX IF NOT EXISTS idx_projects_narrative_score 
ON projects(narrative_score DESC) WHERE narrative_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_tokenomics_score 
ON projects(tokenomics_score DESC) WHERE tokenomics_score IS NOT NULL;

-- Foreign key performance for CSV lookups
CREATE INDEX IF NOT EXISTS idx_csv_data_project_lookup 
ON csv_data(project_id, analyzed_at DESC) WHERE is_valid = TRUE;