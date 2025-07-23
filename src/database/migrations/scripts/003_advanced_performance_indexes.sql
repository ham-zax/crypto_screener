-- Migration: 003_advanced_performance_indexes
-- Description: Advanced performance indexes for high-volume queries and analytics
-- Rollback: DROP INDEX IF EXISTS idx_projects_analytics_composite; DROP INDEX IF EXISTS idx_projects_search_text; DROP INDEX IF EXISTS idx_projects_score_ranges; DROP INDEX IF EXISTS idx_csv_data_analysis_composite; DROP INDEX IF EXISTS idx_projects_market_segments;

-- Advanced composite index for analytics and reporting queries
CREATE INDEX IF NOT EXISTS idx_projects_analytics_composite 
ON projects(data_source, category, market_cap DESC, omega_score DESC, has_data_score, created_at DESC);

-- Full-text search optimization for project names and tickers
CREATE INDEX IF NOT EXISTS idx_projects_search_text 
ON projects(name, ticker) WHERE data_source = 'automated';

-- Score range filtering optimization
CREATE INDEX IF NOT EXISTS idx_projects_score_ranges 
ON projects(omega_score, narrative_score, tokenomics_score) 
WHERE omega_score IS NOT NULL;

-- Market segment analysis optimization
CREATE INDEX IF NOT EXISTS idx_projects_market_segments 
ON projects(market_cap, category, sector_strength DESC) 
WHERE market_cap IS NOT NULL AND category IS NOT NULL;

-- CSV data analysis optimization for batch processing
CREATE INDEX IF NOT EXISTS idx_csv_data_analysis_composite 
ON csv_data(is_valid, data_score DESC, analyzed_at DESC, project_id);

-- Time-based cleanup and maintenance optimization
CREATE INDEX IF NOT EXISTS idx_projects_maintenance 
ON projects(last_updated, created_at) WHERE data_source = 'automated';

-- Category-based filtering with score sorting
CREATE INDEX IF NOT EXISTS idx_projects_category_performance 
ON projects(category, omega_score DESC, market_cap DESC) 
WHERE category IS NOT NULL AND omega_score IS NOT NULL;

-- Data completion status optimization
CREATE INDEX IF NOT EXISTS idx_projects_completion_status 
ON projects(has_data_score, data_source, omega_score DESC) 
WHERE data_source = 'automated';

-- Supply risk analysis optimization
CREATE INDEX IF NOT EXISTS idx_projects_supply_analysis 
ON projects(supply_risk DESC, circulating_supply, total_supply) 
WHERE supply_risk IS NOT NULL;

-- Valuation analysis optimization
CREATE INDEX IF NOT EXISTS idx_projects_valuation_analysis 
ON projects(valuation_potential DESC, market_cap DESC, tokenomics_score DESC) 
WHERE valuation_potential IS NOT NULL;

-- CSV data performance for project lookups
CREATE INDEX IF NOT EXISTS idx_csv_data_recent_analysis 
ON csv_data(project_id, uploaded_at DESC, data_score DESC) 
WHERE is_valid = TRUE;

-- Omega score distribution analysis
CREATE INDEX IF NOT EXISTS idx_projects_score_distribution 
ON projects(omega_score, narrative_score, tokenomics_score, data_score) 
WHERE omega_score IS NOT NULL AND data_source = 'automated';