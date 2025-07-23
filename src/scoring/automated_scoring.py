"""
Automated Scoring Algorithms for Project Omega V2

Implements the automated scoring rules defined in V2 specification:
- AS-01: Narrative Score (Sector Strength + defaults for Value Proposition & Backing Team)
- AS-02: Tokenomics Score (Valuation Potential + defaults + Supply Risk)
- AS-03: Data Score (CSV analysis - implemented in separate module)

These algorithms provide objective, deterministic scoring for automated projects.
"""

import logging
from typing import Optional, Dict, Any
from ..models.api_responses import CoinGeckoMarket, CoinGeckoCoinDetails

logger = logging.getLogger(__name__)

class AutomatedScoringEngine:
    """
    Main scoring engine implementing V2 automated scoring algorithms
    
    Provides methods to calculate all score components based on V2 specification rules.
    """
    
    @staticmethod
    def calculate_sector_strength(category: Optional[str]) -> float:
        """
        Calculate Sector Strength score based on CoinGecko category (AS-01a)
        
        Scoring rules:
        - AI, DePIN, RWA: Score 9 (Hot sectors)
        - L1, L2, GameFi, Infrastructure: Score 7 (Solid sectors)
        - All others: Score 4 (Default)
        
        Args:
            category: CoinGecko category string
            
        Returns:
            Sector strength score (1-10 scale)
        """
        if not category:
            logger.debug("No category provided, using default sector strength score")
            return 4.0
        
        # Normalize category string
        normalized_category = category.lower().replace(' ', '-').replace('_', '-')
        
        # Hot sectors (Score 9)
        hot_sectors = {
            'artificial-intelligence', 'ai', 'ai-agents', 'artificial-intelligence-agents',
            'depin', 'decentralized-physical-infrastructure-networks', 'physical-infrastructure',
            'real-world-assets', 'rwa', 'real-world-asset', 'tokenized-assets'
        }
        
        # Solid sectors (Score 7)
        solid_sectors = {
            'layer-1', 'layer-2', 'l1', 'l2', 'blockchain', 'smart-contracts',
            'gaming', 'gamefi', 'game-fi', 'play-to-earn', 'metaverse',
            'infrastructure', 'blockchain-infrastructure', 'developer-tools',
            'oracle', 'oracles', 'bridges', 'cross-chain'
        }
        
        if normalized_category in hot_sectors:
            logger.debug(f"Category '{category}' classified as hot sector: score 9")
            return 9.0
        elif normalized_category in solid_sectors:
            logger.debug(f"Category '{category}' classified as solid sector: score 7")
            return 7.0
        else:
            logger.debug(f"Category '{category}' classified as other sector: score 4")
            return 4.0
    
    @staticmethod
    def calculate_value_proposition(category: Optional[str] = None) -> float:
        """
        Calculate Value Proposition score (AS-01c)
        
        Per V2 spec: "This score MUST be set to a default, neutral value of 5"
        This is a qualitative metric that cannot be reliably automated.
        
        Args:
            category: Unused parameter for consistency
            
        Returns:
            Fixed neutral score of 5.0
        """
        return 5.0
    
    @staticmethod
    def calculate_backing_team(category: Optional[str] = None) -> float:
        """
        Calculate Backing & Team score (AS-01b)
        
        Per V2 spec: "This score MUST be set to a default, neutral value of 5"
        Selected APIs do not provide reliable data for this metric.
        
        Args:
            category: Unused parameter for consistency
            
        Returns:
            Fixed neutral score of 5.0
        """
        return 5.0
    
    @staticmethod
    def calculate_valuation_potential(market_cap_usd: Optional[float]) -> float:
        """
        Calculate Valuation Potential score based on market cap (AS-02a)
        
        Scoring rules (lower market cap = higher upside potential):
        - < $20M: Score 10
        - < $50M: Score 9
        - < $100M: Score 8
        - < $200M: Score 7
        - < $500M: Score 5
        - < $1B: Score 3
        - >= $1B: Score 1
        
        Args:
            market_cap_usd: Market capitalization in USD
            
        Returns:
            Valuation potential score (1-10 scale)
        """
        if not market_cap_usd or market_cap_usd <= 0:
            logger.warning("Invalid or missing market cap, assigning lowest score")
            return 1.0
        
        if market_cap_usd < 20_000_000:  # $20M
            score = 10.0
        elif market_cap_usd < 50_000_000:  # $50M
            score = 9.0
        elif market_cap_usd < 100_000_000:  # $100M
            score = 8.0
        elif market_cap_usd < 200_000_000:  # $200M
            score = 7.0
        elif market_cap_usd < 500_000_000:  # $500M
            score = 5.0
        elif market_cap_usd < 1_000_000_000:  # $1B
            score = 3.0
        else:  # >= $1B
            score = 1.0
        
        logger.debug(f"Market cap ${market_cap_usd:,.0f} assigned valuation score: {score}")
        return score
    
    @staticmethod
    def calculate_token_utility(category: Optional[str] = None) -> float:
        """
        Calculate Token Utility score (AS-02b)
        
        Per V2 spec: "This score MUST be set to a default, neutral value of 5"
        This is a qualitative metric and APIs don't provide structured value accrual data.
        
        Args:
            category: Unused parameter for consistency
            
        Returns:
            Fixed neutral score of 5.0
        """
        return 5.0
    
    @staticmethod
    def calculate_supply_risk(
        circulating_supply: Optional[float], 
        total_supply: Optional[float]
    ) -> float:
        """
        Calculate Supply Risk score based on circulation ratio (AS-02c)
        
        Scoring rules (higher circulation = lower supply risk):
        - >= 90% circulating: Score 10 (lowest risk)
        - >= 75% circulating: Score 9
        - >= 50% circulating: Score 7
        - >= 25% circulating: Score 5
        - >= 10% circulating: Score 2
        - < 10% circulating or data unavailable: Score 1 (highest risk)
        
        Args:
            circulating_supply: Circulating token supply
            total_supply: Total/max token supply
            
        Returns:
            Supply risk score (1-10 scale)
        """
        if not circulating_supply or not total_supply or total_supply <= 0:
            logger.debug("Missing or invalid supply data, assigning highest risk score")
            return 1.0
        
        circulation_ratio = circulating_supply / total_supply
        
        # Clamp ratio to reasonable range
        circulation_ratio = max(0.0, min(1.0, circulation_ratio))
        
        if circulation_ratio >= 0.90:
            score = 10.0
        elif circulation_ratio >= 0.75:
            score = 9.0
        elif circulation_ratio >= 0.50:
            score = 7.0
        elif circulation_ratio >= 0.25:
            score = 5.0
        elif circulation_ratio >= 0.10:
            score = 2.0
        else:
            score = 1.0
        
        logger.debug(f"Circulation ratio {circulation_ratio:.2%} assigned supply risk score: {score}")
        return score
    
    @classmethod
    def calculate_narrative_score(
        cls, 
        category: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate complete Narrative Score with all components (AS-01)
        
        Components:
        - Sector Strength: Based on category mapping
        - Value Proposition: Fixed at 5 (neutral)
        - Backing & Team: Fixed at 5 (neutral)
        
        Args:
            category: CoinGecko category for sector strength
            
        Returns:
            Dictionary with component scores and final narrative score
        """
        sector_strength = cls.calculate_sector_strength(category)
        value_proposition = cls.calculate_value_proposition()
        backing_team = cls.calculate_backing_team()
        
        narrative_score = (sector_strength + value_proposition + backing_team) / 3
        
        return {
            'sector_strength': sector_strength,
            'value_proposition': value_proposition,
            'backing_team': backing_team,
            'narrative_score': narrative_score
        }
    
    @classmethod
    def calculate_tokenomics_score(
        cls,
        market_cap_usd: Optional[float],
        circulating_supply: Optional[float],
        total_supply: Optional[float],
        category: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate complete Tokenomics Score with all components (AS-02)
        
        Components:
        - Valuation Potential: Based on market cap
        - Token Utility: Fixed at 5 (neutral)
        - Supply Risk: Based on circulation ratio
        
        Args:
            market_cap_usd: Market capitalization in USD
            circulating_supply: Circulating token supply
            total_supply: Total/max token supply
            category: Unused, for consistency
            
        Returns:
            Dictionary with component scores and final tokenomics score
        """
        valuation_potential = cls.calculate_valuation_potential(market_cap_usd)
        token_utility = cls.calculate_token_utility()
        supply_risk = cls.calculate_supply_risk(circulating_supply, total_supply)
        
        tokenomics_score = (valuation_potential + token_utility + supply_risk) / 3
        
        return {
            'valuation_potential': valuation_potential,
            'token_utility': token_utility,
            'supply_risk': supply_risk,
            'tokenomics_score': tokenomics_score
        }
    
    @classmethod
    def calculate_all_automated_scores(
        cls,
        market_data: CoinGeckoMarket,
        coin_details: Optional[CoinGeckoCoinDetails] = None
    ) -> Dict[str, Any]:
        """
        Calculate all automated scores for a project
        
        Args:
            market_data: CoinGeckoMarket instance with market data
            coin_details: Optional detailed coin information
            
        Returns:
            Dictionary with all calculated scores and metadata
        """
        # Determine category from coin details or fallback
        category = None
        if coin_details:
            category = coin_details.get_primary_category()
        
        # Calculate pillar scores
        narrative_scores = cls.calculate_narrative_score(category)
        tokenomics_scores = cls.calculate_tokenomics_score(
            market_data.market_cap,
            market_data.circulating_supply,
            market_data.total_supply,
            category
        )
        
        # Compile results
        result = {
            # Individual components
            'sector_strength': narrative_scores['sector_strength'],
            'value_proposition': narrative_scores['value_proposition'],
            'backing_team': narrative_scores['backing_team'],
            'valuation_potential': tokenomics_scores['valuation_potential'],
            'token_utility': tokenomics_scores['token_utility'],
            'supply_risk': tokenomics_scores['supply_risk'],
            
            # Pillar scores
            'narrative_score': narrative_scores['narrative_score'],
            'tokenomics_score': tokenomics_scores['tokenomics_score'],
            
            # Data score remains null until CSV upload (AS-03)
            'accumulation_signal': None,
            'data_score': None,
            'has_data_score': False,
            
            # Final omega score remains null until all pillars complete (AS-05)
            'omega_score': None,
            
            # Metadata
            'category': category,
            'scoring_metadata': {
                'market_cap_usd': market_data.market_cap,
                'circulation_ratio': market_data.get_circulation_ratio(),
                'scored_at': logger.handlers[0].stream.name if logger.handlers else 'unknown',
                'scoring_version': 'v2.0'
            }
        }
        
        logger.info(f"Automated scoring completed for {market_data.id}: "
                   f"Narrative={narrative_scores['narrative_score']:.1f}, "
                   f"Tokenomics={tokenomics_scores['tokenomics_score']:.1f}")
        
        return result


class ScoringValidator:
    """
    Utility class for validating scoring inputs and results
    """
    
    @staticmethod
    def validate_market_data_for_scoring(market_data: CoinGeckoMarket) -> bool:
        """
        Validate that market data has minimum requirements for scoring
        
        Args:
            market_data: CoinGeckoMarket instance
            
        Returns:
            True if data is valid for scoring
        """
        if not market_data.is_valid_for_scoring():
            logger.warning(f"Market data for {market_data.id} failed basic validation")
            return False
        
        # Additional scoring-specific validations
        if not market_data.market_cap or market_data.market_cap <= 0:
            logger.warning(f"Invalid market cap for {market_data.id}: {market_data.market_cap}")
            return False
        
        return True
    
    @staticmethod
    def validate_scoring_results(scores: Dict[str, Any]) -> bool:
        """
        Validate that scoring results are within expected ranges
        
        Args:
            scores: Dictionary of calculated scores
            
        Returns:
            True if scores are valid
        """
        score_fields = [
            'sector_strength', 'value_proposition', 'backing_team',
            'valuation_potential', 'token_utility', 'supply_risk',
            'narrative_score', 'tokenomics_score'
        ]
        
        for field in score_fields:
            score = scores.get(field)
            if score is None:
                logger.error(f"Missing score field: {field}")
                return False
            
            if not (1.0 <= score <= 10.0):
                logger.error(f"Score {field} out of range: {score}")
                return False
        
        return True