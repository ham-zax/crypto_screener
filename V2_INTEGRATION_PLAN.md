# Project Omega V2 Integration Plan

## Executive Summary

This plan outlines the integration of Project Omega V2.7 specifications with the existing V1 implementation. V2 introduces **semi-automated discovery and scoring** while maintaining the V1 manual wizard for custom projects.

## Current State Analysis (V1 Implementation)

### ✅ V1 Assets in Place
- **Three-step wizard**: Manual data entry for all 7 scoring components
- **localStorage persistence**: Client-side data storage
- **Omega Score calculation**: Exact V1 formula implementation
- **Filtering system**: Sector and score-based filtering
- **Responsive UI**: Modern interface with validation

### 🔄 V1 Components to Evolve
- **Data model**: Extend to support automated vs manual projects
- **Scoring engine**: Hybrid manual/automated calculation
- **UI components**: Add automated project views and CSV input
- **Architecture**: Introduce backend services for API integration

---

## V2 Key Changes Analysis

### New Features Required
1. **Automated Project Ingestion** (US-04)
   - CoinGecko API integration for cryptocurrency universe
   - Automated Narrative and Tokenomics scoring
   - Scheduled data fetching

2. **CSV Data Analysis** (US-06) 
   - CSV parsing for TradingView exports
   - Linear regression analysis for Data Score calculation
   - Accumulation signal detection algorithm

3. **Hybrid Scoring System**
   - Automated scoring for API-sourced projects
   - Manual scoring preservation for wizard-created projects
   - "Awaiting Data" state management

---

## Architecture Evolution Plan

### Phase 1: Backend Infrastructure (Weeks 1-2)

#### 1.1 Database Migration Strategy
```
Current: localStorage-only (V1)
Target: Hybrid localStorage + Server DB (V2)

Migration Approach:
- Preserve V1 localStorage for manual projects
- Add server-side database for automated projects
- Implement data sync between both systems
```

#### 1.2 Backend Services Architecture
```
src/
├── api/
│   ├── coingecko.py         # CoinGecko API client
│   ├── defillama.py         # DefiLlama API client (optional)
│   └── scheduler.py         # Data fetch scheduling
├── scoring/
│   ├── automated.py         # Automated scoring algorithms
│   ├── csv_analyzer.py      # CSV parsing and analysis
│   └── calculator.py        # Unified Omega Score calculation
├── models/
│   ├── project_v2.py        # Enhanced project model
│   └── data_source.py       # Track manual vs automated sources
└── services/
    ├── ingestion.py         # Project ingestion service
    └── analysis.py          # Data analysis service
```

#### 1.3 Database Schema Design
```sql
-- Projects table (replaces localStorage for automated projects)
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(50),
    coingecko_id VARCHAR(255),
    
    -- Source tracking
    data_source ENUM('manual', 'automated') NOT NULL,
    created_via ENUM('wizard', 'api_ingestion') NOT NULL,
    
    -- Automated data fields
    market_cap DECIMAL,
    circulating_supply DECIMAL,
    total_supply DECIMAL,
    category VARCHAR(100),
    
    -- Score components
    sector_strength DECIMAL(3,2),
    value_proposition DECIMAL(3,2),
    backing_team DECIMAL(3,2),
    valuation_potential DECIMAL(3,2),
    token_utility DECIMAL(3,2),
    supply_risk DECIMAL(3,2),
    accumulation_signal DECIMAL(3,2),
    
    -- Calculated scores
    narrative_score DECIMAL(3,2),
    tokenomics_score DECIMAL(3,2),
    data_score DECIMAL(3,2),
    omega_score DECIMAL(3,2),
    
    -- State management
    has_data_score BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CSV Data uploads table
CREATE TABLE csv_data (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    raw_data TEXT,
    processed_data JSONB,
    data_score DECIMAL(3,2),
    analysis_metadata JSONB,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Phase 2: API Integration (Weeks 3-4)

#### 2.1 CoinGecko Integration (BR-06)
```python
# api/coingecko.py implementation preview
class CoinGeckoClient:
    def fetch_coin_list(self, page=1, per_page=250):
        """Fetch paginated cryptocurrency list"""
        
    def get_coin_details(self, coin_id):
        """Get detailed information for specific coin"""
        
    def get_market_data(self, coin_ids):
        """Batch fetch market data for multiple coins"""
        
    def map_category_to_sector(self, category):
        """Map CoinGecko categories to Omega sectors"""
        # Implementation of AS-01a mapping rules
```

#### 2.2 Automated Scoring Algorithms
```python
# scoring/automated.py implementation preview
class AutomatedScoring:
    def calculate_sector_strength(self, category):
        """AS-01a: Map category to sector strength score"""
        mapping = {
            'AI': 9, 'DePIN': 9, 'RWA': 9,
            'L1': 7, 'L2': 7, 'GameFi': 7, 'Infrastructure': 7,
            'default': 4
        }
        
    def calculate_valuation_potential(self, market_cap):
        """AS-02a: Score based on market cap ranges"""
        if market_cap < 20_000_000: return 10
        elif market_cap < 50_000_000: return 9
        # ... additional ranges
        
    def calculate_supply_risk(self, circulating, total):
        """AS-02c: Score based on circulation ratio"""
        ratio = circulating / total if total > 0 else 0
        if ratio >= 0.9: return 10
        elif ratio >= 0.75: return 9
        # ... additional ranges
```

#### 2.3 Scheduled Data Ingestion
```python
# api/scheduler.py implementation preview
from celery import Celery
from datetime import timedelta

app = Celery('omega_scheduler')

@app.task
def daily_coin_ingestion():
    """Daily task to fetch and score new coins"""
    
@app.task  
def weekly_market_data_update():
    """Weekly task to update market data for existing coins"""
```

### Phase 3: CSV Analysis Engine (Weeks 5-6)

#### 3.1 CSV Parser (AS-03a)
```python
# scoring/csv_analyzer.py implementation preview
class CSVAnalyzer:
    def parse_csv_text(self, csv_text):
        """Parse pasted CSV text with validation"""
        required_headers = ['time', 'close', 'Volume Delta (Close)']
        
    def validate_data_requirements(self, df):
        """Ensure minimum 90 periods and required columns"""
        
    def calculate_accumulation_signal(self, df):
        """AS-03b: Linear regression analysis for Data Score"""
        # 1. Calculate price trend (close prices)
        # 2. Calculate CVD trend (cumulative Volume Delta)
        # 3. Analyze divergence patterns
        # 4. Return score 1-10
```

#### 3.2 Linear Regression Analysis
```python
from scipy import stats
import numpy as np

def calculate_data_score(price_data, volume_delta_data):
    """
    Implement AS-03b algorithm:
    1. Linear regression slope of close prices
    2. Linear regression slope of cumulative volume delta
    3. Divergence analysis and scoring
    """
    # Price trend calculation
    x = np.arange(len(price_data))
    price_slope, _, _, _, _ = stats.linregress(x, price_data)
    
    # CVD trend calculation  
    cvd = np.cumsum(volume_delta_data)
    cvd_slope, _, _, _, _ = stats.linregress(x, cvd)
    
    # Divergence scoring logic
    return calculate_divergence_score(price_slope, cvd_slope)
```

### Phase 4: UI/UX Evolution (Weeks 7-8)

#### 4.1 Hybrid Interface Design
```
Current V1 Layout:
[Add Project Wizard] | [Manual Watchlist]

New V2 Layout:
[Automated Universe] | [Manual Projects] | [Analysis Tools]
    |                      |                    |
[API Projects]        [Wizard Projects]   [CSV Upload]
[Auto-scored]         [Manual scores]    [Data Analysis]
[Awaiting Data]       [Complete scores]  [Score Updates]
```

#### 4.2 New UI Components

##### Automated Projects View
```html
<!-- New automated projects section -->
<div class="automated-projects">
  <div class="section-header">
    <h2>Automated Universe</h2>
    <span class="last-updated">Last updated: 2 hours ago</span>
  </div>
  
  <div class="filters">
    <select id="categoryFilter">...</select>
    <input id="marketCapFilter" placeholder="Min Market Cap">
    <select id="dataStatusFilter">
      <option value="">All Projects</option>
      <option value="awaiting">Awaiting Data</option>
      <option value="complete">Complete Analysis</option>
    </select>
  </div>
  
  <div class="project-grid automated">
    <!-- Project cards with automation indicators -->
  </div>
</div>
```

##### CSV Analysis Modal
```html
<!-- CSV upload and analysis interface -->
<div class="csv-modal">
  <div class="modal-header">
    <h3>Analyze Chart Data for {projectName}</h3>
    <div class="requirements">
      <p><strong>Required columns:</strong> time, close, Volume Delta (Close)</p>
      <p><strong>Minimum data:</strong> 90 periods</p>
    </div>
  </div>
  
  <div class="modal-body">
    <textarea id="csvInput" placeholder="Paste your TradingView CSV data here..."></textarea>
    <div class="analysis-results" style="display:none;">
      <div class="score-result">
        <span class="label">Data Score:</span>
        <span class="score" id="dataScore">--</span>
      </div>
      <div class="analysis-details">
        <p>Price Trend: <span id="priceTrend">--</span></p>
        <p>CVD Trend: <span id="cvdTrend">--</span></p>
        <p>Divergence: <span id="divergenceAnalysis">--</span></p>
      </div>
    </div>
  </div>
  
  <div class="modal-footer">
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="analyzeCSV()">Analyze Data</button>
  </div>
</div>
```

#### 4.3 Enhanced Project Cards
```html
<!-- Enhanced project card for V2 -->
<div class="project-card" data-source="automated">
  <div class="project-header">
    <div class="project-info">
      <h3>{projectName}</h3>
      <span class="ticker">{ticker}</span>
      <span class="category-badge">{category}</span>
      <span class="source-indicator automated">Auto</span>
    </div>
    <div class="omega-score-section">
      <div class="omega-score awaiting" id="omega-{id}">
        <span class="score-value">N/A</span>
        <span class="score-label">Awaiting Data</span>
      </div>
    </div>
  </div>
  
  <div class="score-breakdown">
    <div class="score-pillar">
      <span class="pillar-score">{narrativeScore}</span>
      <span class="pillar-label">Narrative</span>
      <span class="pillar-source">Auto</span>
    </div>
    <div class="score-pillar">
      <span class="pillar-score">{tokenomicsScore}</span>
      <span class="pillar-label">Tokenomics</span>
      <span class="pillar-source">Auto</span>
    </div>
    <div class="score-pillar pending">
      <span class="pillar-score">--</span>
      <span class="pillar-label">Data</span>
      <span class="pillar-source">Manual</span>
    </div>
  </div>
  
  <div class="project-actions">
    <button class="btn btn-primary btn-small" onclick="uploadCSV('{id}')">
      📊 Add Data
    </button>
    <button class="btn btn-secondary btn-small" onclick="viewDetails('{id}')">
      Details
    </button>
  </div>
</div>
```

### Phase 5: Integration & Testing (Weeks 9-10)

#### 5.1 Data Migration Strategy
1. **Preserve V1 localStorage data** as "manual" projects
2. **Import to server database** with `data_source: 'manual'`
3. **Maintain localStorage sync** for offline capability
4. **Add automated projects** with `data_source: 'automated'`

#### 5.2 Backward Compatibility
- V1 wizard remains fully functional
- Manual projects retain all current functionality  
- localStorage continues working for manual projects
- New server endpoints for automated features

#### 5.3 Testing Strategy
```python
# Test categories for V2 integration
def test_api_integration():
    """Test CoinGecko and DefiLlama API connections"""
    
def test_automated_scoring():
    """Verify AS-01, AS-02 scoring algorithms"""
    
def test_csv_analysis():
    """Test AS-03 CSV parsing and analysis"""
    
def test_hybrid_data_model():
    """Ensure manual and automated projects coexist"""
    
def test_v1_compatibility():
    """Verify V1 features still work correctly"""
```

---

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Database schema implementation
- [ ] Basic API service structure
- [ ] V1 data migration tools

### Week 3-4: API Integration  
- [ ] CoinGecko client implementation
- [ ] Automated scoring algorithms
- [ ] Scheduled ingestion system

### Week 5-6: CSV Analysis
- [ ] CSV parser with validation
- [ ] Linear regression analysis engine
- [ ] Data Score calculation

### Week 7-8: UI Evolution
- [ ] Automated projects interface
- [ ] CSV upload modal
- [ ] Enhanced project cards

### Week 9-10: Integration
- [ ] End-to-end testing
- [ ] V1 compatibility verification
- [ ] Performance optimization

---

## Technical Dependencies

### New Backend Dependencies
```python
# requirements.txt additions
requests>=2.31.0        # API calls
celery>=5.3.0          # Background tasks
redis>=5.0.0           # Celery broker
scipy>=1.11.0          # Linear regression
pandas>=2.1.0          # CSV processing
sqlalchemy>=2.0.0      # Database ORM
alembic>=1.12.0        # Database migrations
```

### New Frontend Dependencies
```javascript
// package.json additions  
"chart.js": "^4.4.0",     // Data visualization
"papaparse": "^5.4.1",    // CSV parsing
"date-fns": "^2.30.0"     // Date handling
```

---

## Risk Mitigation

### Technical Risks
1. **API Rate Limits**: Implement caching and request throttling
2. **Data Quality**: Add validation for all API responses  
3. **CSV Format Variations**: Robust parsing with error handling
4. **Performance**: Database indexing and query optimization

### Business Risks  
1. **V1 User Disruption**: Maintain full backward compatibility
2. **Data Loss**: Comprehensive backup and migration testing
3. **Scoring Accuracy**: Thorough testing of automated algorithms

### Mitigation Strategies
- Gradual rollout with feature flags
- Comprehensive test coverage
- Rollback procedures for each phase
- User communication and documentation

---

## Success Metrics

### Functional Metrics
- ✅ All V2 user stories (US-04, US-06) implemented
- ✅ All V2 behavioral rules (BR-06 through AS-05) satisfied  
- ✅ 100% V1 functionality preserved
- ✅ All acceptance criteria met

### Performance Metrics
- API response time < 2 seconds
- CSV analysis completion < 5 seconds  
- Daily ingestion of 1000+ projects
- 99.9% uptime for automated services

### User Experience Metrics
- Zero breaking changes for V1 users
- Intuitive automated project discovery
- Clear manual vs automated project distinction
- Seamless CSV data upload workflow

---

## Post-Implementation Roadmap

### V2.1 Enhancements
- DefiLlama integration for DeFi-specific metrics (BR-08)
- Advanced filtering for automated projects
- Bulk CSV processing capabilities

### V3.0 Vision (Future)
- AI-powered qualitative analysis (US-05)
- Real-time data updates
- Advanced charting and visualization
- Portfolio management capabilities

---

This integration plan transforms Project Omega from a manual screening tool into a powerful semi-automated discovery platform while preserving the proven V1 functionality that users depend on.