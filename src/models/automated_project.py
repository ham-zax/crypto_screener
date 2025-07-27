"""
Database Models for Project Omega V2

Contains SQLAlchemy models for automated projects and CSV data analysis.
Based on V2 specification requirements for hybrid manual/automated scoring.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

# --- NEW IMPORTS for Modern Typing ---
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List

from typing import Any

try:
    from ..database.config import db

    BaseClass: Any
    # Only assign BaseClass if db and db.Model exist, else fallback
    if hasattr(db, "Model"):
        BaseClass = getattr(db, "Model")
    else:
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()
        BaseClass = Base
except Exception:
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()
    BaseClass = Base


class AutomatedProject(BaseClass):
    """
    Main project model using the fully type-annotated SQLAlchemy 2.0 style.
    This provides maximum safety and editor support.
    """

    __tablename__ = "projects"

    # --- Correctly Typed Model Attributes using Mapped ---

    # Primary key and identification
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    coingecko_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Source tracking
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_via: Mapped[str] = mapped_column(String(20), nullable=False)

    # Market data
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    circulating_supply: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_supply: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )

    # Score Components
    sector_strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_proposition: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backing_team: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valuation_potential: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    token_utility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    supply_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accumulation_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Calculated Pillar Scores
    narrative_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tokenomics_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Final Omega Score
    omega_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # State management
    has_data_score: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    # Note the special syntax for typed relationships
    csv_uploads: Mapped[List["CSVData"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    # --- BUSINESS LOGIC MOVED TO ProjectService ---
    # The methods calculate_narrative_score, calculate_tokenomics_score,
    # calculate_data_score, calculate_omega_score, and update_all_scores
    # have been removed from this class.

    def get_omega_status(self):
        """Get the current Omega Score status for UI display"""
        # Add assertions to guide the type checker
        assert isinstance(self.omega_score, (float, int)) or self.omega_score is None
        assert isinstance(self.has_data_score, bool)

        if self.omega_score is not None:
            return {
                "status": "complete",
                "score": round(self.omega_score, 2),
                "display": f"{round(self.omega_score, 2)}",
            }
        elif not self.has_data_score:
            return {
                "status": "awaiting_data",
                "score": None,
                "display": "Awaiting Data",
            }
        else:
            return {"status": "incomplete", "score": None, "display": "Incomplete"}

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "name": self.name,
            "ticker": self.ticker,
            "coingecko_id": self.coingecko_id,
            "data_source": self.data_source,
            "created_via": self.created_via,
            "market_cap": self.market_cap,
            "circulating_supply": self.circulating_supply,
            "total_supply": self.total_supply,
            "category": self.category,
            "sector_strength": self.sector_strength,
            "value_proposition": self.value_proposition,
            "backing_team": self.backing_team,
            "valuation_potential": self.valuation_potential,
            "token_utility": self.token_utility,
            "supply_risk": self.supply_risk,
            "accumulation_signal": self.accumulation_signal,
            "narrative_score": self.narrative_score,
            "tokenomics_score": self.tokenomics_score,
            "data_score": self.data_score,
            "omega_score": self.omega_score,
            "has_data_score": self.has_data_score,
            "omega_status": self.get_omega_status(),
            "last_updated": self.last_updated.isoformat()
            if getattr(self, "last_updated", None)
            else None,
            "created_at": self.created_at.isoformat()
            if getattr(self, "created_at", None)
            else None,
        }

    def __repr__(self):
        return f"<AutomatedProject(name='{self.name}', ticker='{self.ticker}', source='{self.data_source}')>"


class CSVData(BaseClass):
    """
    Model for tracking CSV data uploads and analysis results,
    updated to the fully type-annotated SQLAlchemy 2.0 style.
    """

    __tablename__ = "csv_data"

    # --- Correctly Typed Model Attributes using Mapped ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )

    # CSV data storage
    raw_data: Mapped[str] = mapped_column(Text, nullable=False)
    processed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Analysis results
    data_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Validation results
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    project: Mapped["AutomatedProject"] = relationship(back_populates="csv_uploads")

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        uploaded_at_val = getattr(self, "uploaded_at", None)
        analyzed_at_val = getattr(self, "analyzed_at", None)
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "data_score": self.data_score,
            "analysis_metadata": self.analysis_metadata,
            "validation_errors": self.validation_errors,
            "is_valid": self.is_valid,
            "uploaded_at": uploaded_at_val.isoformat()
            if isinstance(uploaded_at_val, datetime)
            else None,
            "analyzed_at": analyzed_at_val.isoformat()
            if isinstance(analyzed_at_val, datetime)
            else None,
        }

    def __repr__(self):
        return f"<CSVData(project_id='{self.project_id}', score={self.data_score}, valid={self.is_valid})>"
