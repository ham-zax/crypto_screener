"""
Database Models for Project Omega V2

Contains SQLAlchemy models for automated projects and CSV data analysis.
Based on V2 specification requirements for hybrid manual/automated scoring.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Try to import Flask-SQLAlchemy db, fallback to pure SQLAlchemy Base
try:
    from ..database.config import db
    BaseClass = db.Model
except (ImportError, AttributeError):
    from ..database.config import Base
    BaseClass = Base

class AutomatedProject(BaseClass):
    """
    Main project model supporting both manual (V1) and automated (V2) projects
    
    Tracks all scoring components for the Omega Protocol:
    - Narrative Score (Sector Strength + Value Proposition + Backing & Team)
    - Tokenomics Score (Valuation Potential + Token Utility + Supply Risk)
    - Data Score (calculated from user-uploaded CSV data)
    """
    
    __tablename__ = 'projects'
    
    # Primary key and identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    ticker = Column(String(50), index=True)
    coingecko_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Source tracking for hybrid V1/V2 support
    data_source = Column(String(20), nullable=False, index=True)  # 'manual' or 'automated'
    created_via = Column(String(20), nullable=False)  # 'wizard' or 'api_ingestion'
    
    # Market data (populated for automated projects from CoinGecko)
    market_cap = Column(Float)  # USD market capitalization
    circulating_supply = Column(Float)  # Circulating token supply
    total_supply = Column(Float)  # Total/max token supply
    category = Column(String(100), index=True)  # CoinGecko category
    
    # Narrative Score Components (AS-01)
    sector_strength = Column(Float)  # AS-01a: Automated mapping from category
    value_proposition = Column(Float)  # AS-01c: Default 5 (neutral)
    backing_team = Column(Float)  # AS-01b: Default 5 (neutral)
    
    # Tokenomics Score Components (AS-02)
    valuation_potential = Column(Float)  # AS-02a: Market cap based scoring
    token_utility = Column(Float)  # AS-02b: Default 5 (neutral)
    supply_risk = Column(Float)  # AS-02c: Circulation ratio based scoring
    
    # Data Score Component (AS-03)
    accumulation_signal = Column(Float)  # AS-03b: Calculated from CSV analysis
    
    # Calculated Pillar Scores
    narrative_score = Column(Float)  # Average of narrative components
    tokenomics_score = Column(Float)  # Average of tokenomics components
    data_score = Column(Float)  # Same as accumulation_signal
    
    # Final Omega Score
    omega_score = Column(Float)  # Calculated only when all pillars present
    
    # State management (AS-05)
    has_data_score = Column(Boolean, default=False, index=True)  # Tracks completion state
    
    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    csv_uploads = relationship("CSVData", back_populates="project", cascade="all, delete-orphan")
    
    def calculate_narrative_score(self):
        """Calculate Narrative Score as average of components (AS-01)"""
        components = [self.sector_strength, self.value_proposition, self.backing_team]
        valid_components = [c for c in components if c is not None]
        
        if valid_components:
            self.narrative_score = sum(valid_components) / len(valid_components)
        else:
            self.narrative_score = None
        
        return self.narrative_score
    
    def calculate_tokenomics_score(self):
        """Calculate Tokenomics Score as average of components (AS-02)"""
        components = [self.valuation_potential, self.token_utility, self.supply_risk]
        valid_components = [c for c in components if c is not None]
        
        if valid_components:
            self.tokenomics_score = sum(valid_components) / len(valid_components)
        else:
            self.tokenomics_score = None
        
        return self.tokenomics_score
    
    def calculate_data_score(self):
        """Set Data Score equal to Accumulation Signal (AS-03)"""
        if self.accumulation_signal is not None:
            self.data_score = self.accumulation_signal
            self.has_data_score = True
        else:
            self.data_score = None
            self.has_data_score = False
        
        return self.data_score
    
    def calculate_omega_score(self):
        """
        Calculate final Omega Score only when all pillars are present (AS-05)
        
        Returns None if any pillar is missing, preventing display of incomplete scores.
        """
        if all(score is not None for score in [self.narrative_score, self.tokenomics_score, self.data_score]):
            self.omega_score = (self.narrative_score + self.tokenomics_score + self.data_score) / 3
        else:
            self.omega_score = None
        
        return self.omega_score
    
    def update_all_scores(self):
        """Recalculate all derived scores"""
        self.calculate_narrative_score()
        self.calculate_tokenomics_score()
        self.calculate_data_score()
        self.calculate_omega_score()
        self.last_updated = datetime.utcnow()
    
    def get_omega_status(self):
        """Get the current Omega Score status for UI display"""
        if self.omega_score is not None:
            return {
                'status': 'complete',
                'score': round(self.omega_score, 2),
                'display': f"{round(self.omega_score, 2)}"
            }
        elif not self.has_data_score:
            return {
                'status': 'awaiting_data',
                'score': None,
                'display': 'Awaiting Data'
            }
        else:
            return {
                'status': 'incomplete',
                'score': None,
                'display': 'N/A'
            }
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'name': self.name,
            'ticker': self.ticker,
            'coingecko_id': self.coingecko_id,
            'data_source': self.data_source,
            'created_via': self.created_via,
            'market_cap': self.market_cap,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply,
            'category': self.category,
            'sector_strength': self.sector_strength,
            'value_proposition': self.value_proposition,
            'backing_team': self.backing_team,
            'valuation_potential': self.valuation_potential,
            'token_utility': self.token_utility,
            'supply_risk': self.supply_risk,
            'accumulation_signal': self.accumulation_signal,
            'narrative_score': self.narrative_score,
            'tokenomics_score': self.tokenomics_score,
            'data_score': self.data_score,
            'omega_score': self.omega_score,
            'has_data_score': self.has_data_score,
            'omega_status': self.get_omega_status(),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<AutomatedProject(name='{self.name}', ticker='{self.ticker}', source='{self.data_source}')>"


class CSVData(BaseClass):
    """
    Model for tracking CSV data uploads and analysis results
    
    Supports the US-06 requirement for pasting TradingView CSV data
    and calculating Data Scores through linear regression analysis.
    """
    
    __tablename__ = 'csv_data'
    
    # Primary key and foreign key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False, index=True)
    
    # CSV data storage
    raw_data = Column(Text, nullable=False)  # Original pasted CSV text
    processed_data = Column(JSON)  # Parsed and validated data structure
    
    # Analysis results
    data_score = Column(Float)  # Calculated accumulation signal score (1-10)
    analysis_metadata = Column(JSON)  # Analysis details for transparency
    
    # Validation results
    validation_errors = Column(JSON)  # Any parsing or validation errors
    is_valid = Column(Boolean, default=False)  # Whether data passed validation
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)  # When analysis was completed
    
    # Relationship
    project = relationship("AutomatedProject", back_populates="csv_uploads")
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'data_score': self.data_score,
            'analysis_metadata': self.analysis_metadata,
            'validation_errors': self.validation_errors,
            'is_valid': self.is_valid,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None
        }
    
    def __repr__(self):
        return f"<CSVData(project_id='{self.project_id}', score={self.data_score}, valid={self.is_valid})>"