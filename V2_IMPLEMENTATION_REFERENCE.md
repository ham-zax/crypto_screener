# Project Omega V2 Implementation Reference

## Quick Implementation Guide for Key V2 Components

This document provides ready-to-implement code examples for the critical V2 features.

---

## 1. Automated Scoring Algorithms (AS-01, AS-02)

### Sector Strength Mapping (AS-01a)
```python
def calculate_sector_strength(coingecko_category):
    """
    Map CoinGecko category to Omega Protocol sector strength score
    AS-01a: AI/DePIN/RWA=9, L1/L2/GameFi/Infrastructure=7, Others=4
    """
    hot_sectors = {
        'artificial-intelligence': 9,
        'ai': 9,
        'depin': 9,
        'real-world-assets': 9,
        'rwa': 9,
        'layer-1': 7,
        'layer-2': 7,
        'gaming': 7,
        'gamefi': 7,
        'infrastructure': 7,
        'blockchain-infrastructure': 7
    }
    
    # Normalize category string
    category = coingecko_category.lower().replace(' ', '-')
    return hot_sectors.get(category, 4)  # Default score for others
```

### Valuation Potential Calculator (AS-02a)
```python
def calculate_valuation_potential(market_cap_usd):
    """
    Score based on market cap ranges - lower cap = higher score
    AS-02a: <$20M=10, <$50M=9, <$100M=8, <$200M=7, <$500M=5, <$1B=3, >=$1B=1
    """
    if market_cap_usd < 20_000_000:
        return 10
    elif market_cap_usd < 50_000_000:
        return 9
    elif market_cap_usd < 100_000_000:
        return 8
    elif market_cap_usd < 200_000_000:
        return 7
    elif market_cap_usd < 500_000_000:
        return 5
    elif market_cap_usd < 1_000_000_000:
        return 3
    else:
        return 1
```

### Supply Risk Calculator (AS-02c)
```python
def calculate_supply_risk(circulating_supply, total_supply):
    """
    Score based on circulation ratio - higher circulation = lower risk
    AS-02c: >=90%=10, >=75%=9, >=50%=7, >=25%=5, >=10%=2, <10%=1
    """
    if not total_supply or total_supply <= 0:
        return 1  # Unknown supply = highest risk
    
    circulation_ratio = circulating_supply / total_supply
    
    if circulation_ratio >= 0.90:
        return 10
    elif circulation_ratio >= 0.75:
        return 9
    elif circulation_ratio >= 0.50:
        return 7
    elif circulation_ratio >= 0.25:
        return 5
    elif circulation_ratio >= 0.10:
        return 2
    else:
        return 1
```

---

## 2. CSV Data Analysis Engine (AS-03)

### CSV Parser and Validator
```python
import pandas as pd
from typing import Tuple, Optional

def parse_and_validate_csv(csv_text: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Parse CSV text and validate requirements (AS-03a)
    Returns: (dataframe, error_message)
    """
    try:
        # Parse CSV
        df = pd.read_csv(io.StringIO(csv_text))
        
        # Required headers check
        required_headers = ['time', 'close', 'Volume Delta (Close)']
        missing_headers = [h for h in required_headers if h not in df.columns]
        
        if missing_headers:
            return None, f"Missing required columns: {', '.join(missing_headers)}"
        
        # Minimum data requirement (90 periods)
        if len(df) < 90:
            return None, f"Insufficient data: {len(df)} periods found, minimum 90 required"
        
        # Data type validation
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['Volume Delta (Close)'] = pd.to_numeric(df['Volume Delta (Close)'], errors='coerce')
        
        # Check for invalid data
        if df['close'].isna().any() or df['Volume Delta (Close)'].isna().any():
            return None, "Invalid numeric data in price or volume delta columns"
        
        return df, None
        
    except Exception as e:
        return None, f"CSV parsing error: {str(e)}"
```

### Accumulation Signal Calculator (AS-03b)
```python
import numpy as np
from scipy import stats

def calculate_accumulation_signal(df: pd.DataFrame) -> Tuple[float, dict]:
    """
    Calculate Data Score using linear regression analysis (AS-03b)
    Returns: (score, analysis_metadata)
    """
    # Use last 90 periods for analysis
    analysis_data = df.tail(90).copy()
    
    # 1. Calculate price trend using Linear Regression slope
    x_values = np.arange(len(analysis_data))
    price_slope, price_intercept, price_r, _, _ = stats.linregress(x_values, analysis_data['close'])
    
    # 2. Calculate Cumulative Volume Delta trend
    analysis_data['cvd'] = analysis_data['Volume Delta (Close)'].cumsum()
    cvd_slope, cvd_intercept, cvd_r, _, _ = stats.linregress(x_values, analysis_data['cvd'])
    
    # 3. Analyze divergence patterns and assign score
    score = calculate_divergence_score(price_slope, cvd_slope, price_r, cvd_r)
    
    # Metadata for analysis transparency
    metadata = {
        'price_slope': float(price_slope),
        'cvd_slope': float(cvd_slope),
        'price_correlation': float(price_r),
        'cvd_correlation': float(cvd_r),
        'periods_analyzed': len(analysis_data),
        'divergence_type': classify_divergence(price_slope, cvd_slope)
    }
    
    return score, metadata

def calculate_divergence_score(price_slope, cvd_slope, price_r, cvd_r):
    """
    Core divergence analysis algorithm
    Strong positive CVD with flat/negative price = accumulation signal
    """
    # Normalize slopes by their correlation strength
    price_trend = price_slope * abs(price_r)
    cvd_trend = cvd_slope * abs(cvd_r)
    
    # Define trend thresholds
    strong_positive = 0.1
    weak_positive = 0.02
    weak_negative = -0.02
    strong_negative = -0.1
    
    # Classify trends
    if cvd_trend > strong_positive and price_trend < weak_positive:
        # Strong CVD accumulation with flat/declining price = strongest signal
        return 10
    elif cvd_trend > weak_positive and price_trend < weak_negative:
        # Good CVD with declining price = strong signal
        return 9
    elif cvd_trend > strong_positive and price_trend > weak_positive:
        # Strong CVD with rising price = moderate signal
        return 7
    elif cvd_trend > weak_positive and price_trend > weak_positive:
        # Weak CVD with rising price = weak signal
        return 6
    elif cvd_trend < weak_negative and price_trend > strong_positive:
        # Negative CVD with rising price = distribution
        return 3
    elif cvd_trend < strong_negative:
        # Strong negative CVD = selling pressure
        return 2
    else:
        # Unclear/mixed signals
        return 5

def classify_divergence(price_slope, cvd_slope):
    """Classify the type of divergence for reporting"""
    if cvd_slope > 0 and price_slope <= 0:
        return "bullish_divergence"
    elif cvd_slope < 0 and price_slope >= 0:
        return "bearish_divergence"
    elif cvd_slope > 0 and price_slope > 0:
        return "confluence_bullish"
    elif cvd_slope < 0 and price_slope < 0:
        return "confluence_bearish"
    else:
        return "neutral"
```

---

## 3. CoinGecko API Integration

### API Client Implementation
```python
import requests
import time
from typing import List, Dict, Optional

class CoinGeckoClient:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-cg-pro-api-key": api_key})
        
        # Rate limiting (free tier: 30 calls/minute)
        self.calls_per_minute = 30
        self.call_timestamps = []
    
    def _rate_limit(self):
        """Implement rate limiting"""
        now = time.time()
        # Remove calls older than 1 minute
        self.call_timestamps = [t for t in self.call_timestamps if now - t < 60]
        
        if len(self.call_timestamps) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_timestamps[0])
            time.sleep(max(0, sleep_time))
        
        self.call_timestamps.append(now)
    
    def fetch_coins_list(self, include_platform=False) -> List[Dict]:
        """Fetch complete list of coins from CoinGecko"""
        self._rate_limit()
        
        url = f"{self.base_url}/coins/list"
        params = {"include_platform": include_platform}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def fetch_market_data(self, coin_ids: List[str], vs_currency="usd") -> List[Dict]:
        """Fetch market data for specific coins"""
        self._rate_limit()
        
        # CoinGecko limits to 250 IDs per request
        batch_size = 250
        all_data = []
        
        for i in range(0, len(coin_ids), batch_size):
            batch = coin_ids[i:i + batch_size]
            ids_param = ",".join(batch)
            
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": vs_currency,
                "ids": ids_param,
                "order": "market_cap_desc",
                "per_page": batch_size,
                "page": 1,
                "sparkline": False
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            all_data.extend(response.json())
            
            if i + batch_size < len(coin_ids):
                time.sleep(2)  # Brief pause between batches
        
        return all_data
    
    def fetch_coin_details(self, coin_id: str) -> Dict:
        """Fetch detailed information for a specific coin"""
        self._rate_limit()
        
        url = f"{self.base_url}/coins/{coin_id}"
        params = {
            "localization": False,
            "tickers": False,
            "market_data": True,
            "community_data": False,
            "developer_data": False,
            "sparkline": False
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

### Data Processing Pipeline
```python
def process_coingecko_data(market_data: Dict) -> Dict:
    """
    Convert CoinGecko market data to Omega Protocol project format
    """
    # Extract basic information
    project = {
        'coingecko_id': market_data['id'],
        'name': market_data['name'],
        'ticker': market_data['symbol'].upper(),
        'data_source': 'automated',
        'created_via': 'api_ingestion'
    }
    
    # Market data
    project['market_cap'] = market_data.get('market_cap')
    project['circulating_supply'] = market_data.get('circulating_supply')
    project['total_supply'] = market_data.get('total_supply')
    
    # Automated scoring
    category = market_data.get('category', '').lower()
    project['sector_strength'] = calculate_sector_strength(category)
    project['backing_team'] = 5  # Neutral default (AS-01b)
    project['value_proposition'] = 5  # Neutral default (AS-01c)
    
    if project['market_cap']:
        project['valuation_potential'] = calculate_valuation_potential(project['market_cap'])
    else:
        project['valuation_potential'] = 1  # Unknown = lowest score
    
    project['token_utility'] = 5  # Neutral default (AS-02b)
    
    if project['circulating_supply'] and project['total_supply']:
        project['supply_risk'] = calculate_supply_risk(
            project['circulating_supply'], 
            project['total_supply']
        )
    else:
        project['supply_risk'] = 1  # Unknown = highest risk
    
    # Calculate pillar scores
    project['narrative_score'] = (
        project['sector_strength'] + 
        project['value_proposition'] + 
        project['backing_team']
    ) / 3
    
    project['tokenomics_score'] = (
        project['valuation_potential'] + 
        project['token_utility'] + 
        project['supply_risk']
    ) / 3
    
    # Data score and final Omega score remain null until CSV upload
    project['data_score'] = None
    project['omega_score'] = None
    project['has_data_score'] = False
    
    return project
```

---

## 4. Database Schema & Migration

### SQLAlchemy Models
```python
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    ticker = Column(String(50))
    coingecko_id = Column(String(255), unique=True, nullable=True)
    
    # Source tracking
    data_source = Column(String(20), nullable=False)  # 'manual' or 'automated'
    created_via = Column(String(20), nullable=False)  # 'wizard' or 'api_ingestion'
    
    # Market data (for automated projects)
    market_cap = Column(Float)
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    category = Column(String(100))
    
    # Score components (1-10 scale)
    sector_strength = Column(Float)
    value_proposition = Column(Float)
    backing_team = Column(Float)
    valuation_potential = Column(Float)
    token_utility = Column(Float)
    supply_risk = Column(Float)
    accumulation_signal = Column(Float)
    
    # Calculated scores
    narrative_score = Column(Float)
    tokenomics_score = Column(Float)
    data_score = Column(Float)
    omega_score = Column(Float)
    
    # State management
    has_data_score = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class CSVData(Base):
    __tablename__ = 'csv_data'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    raw_data = Column(Text, nullable=False)
    processed_data = Column(JSON)
    data_score = Column(Float)
    analysis_metadata = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
```

### Data Migration Script
```python
def migrate_v1_to_v2():
    """
    Migrate localStorage V1 data to V2 database
    Preserves all manual projects while enabling automated features
    """
    # This would be called from a migration script
    # Implementation would read localStorage JSON and create database records
    pass
```

---

## 5. Frontend Integration Points

### JavaScript API Client
```javascript
class OmegaV2API {
    constructor(baseURL = '/api/v2') {
        this.baseURL = baseURL;
    }
    
    async getAutomatedProjects(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseURL}/projects/automated?${params}`);
        return response.json();
    }
    
    async uploadCSVData(projectId, csvText) {
        const response = await fetch(`${this.baseURL}/projects/${projectId}/csv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csv_data: csvText })
        });
        return response.json();
    }
    
    async triggerDataIngestion() {
        const response = await fetch(`${this.baseURL}/admin/ingest`, {
            method: 'POST'
        });
        return response.json();
    }
}
```

---

This reference provides the core algorithmic implementations needed for V2 integration, following the exact specifications in the V2 document while maintaining compatibility with the existing V1 codebase.