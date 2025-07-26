import yaml
import logging
from typing import Dict, Any, Optional


# --- FIX: Add the correct, specific imports ---
from src.models.api_responses import CoinGeckoMarket, CoinGeckoCoinDetails

logger = logging.getLogger(__name__)

class ScoringEngine:
    """
    Implements all automated scoring logic based on external configuration.
    Adheres to Project Omega v2 specification rules.
    """
    def __init__(self, config_path: str = 'config.yml'):
        """
        Initializes the scoring engine by loading the configuration file.
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.config = config['scoring']
            logger.info("Scoring configuration loaded successfully.")
        except FileNotFoundError:
            logger.error(f"FATAL: Scoring configuration file not found at {config_path}")
            raise
        except Exception as e:
            logger.error(f"FATAL: Failed to load or parse scoring config: {e}")
            raise

    def _calculate_sector_strength(self, market: CoinGeckoMarket, details: Optional[CoinGeckoCoinDetails]) -> float:
        """Implements rule AS-01a."""
        category_map = self.config['narrative']['sector_strength_map']
        primary_category = details.get_primary_category() if details else None
        if not primary_category:
            return category_map['default_score']
        normalized_category = ''.join(filter(str.isalnum, primary_category.lower()))
        for key, score in category_map.items():
            if key in normalized_category:
                return score
        return category_map['default_score']

    def _calculate_valuation_potential(self, market: CoinGeckoMarket) -> float:
        """Implements rule AS-02a."""
        market_cap = market.market_cap
        if market_cap is None:
            return 1.0 # Lowest score if no market cap data
        tiers = self.config['tokenomics']['valuation_potential_tiers']
        for tier in tiers:
            if market_cap < tier['max_market_cap']:
                return tier['score']
        return 1.0 # Should not be reached due to '.inf' tier

    def _calculate_supply_risk(self, market: CoinGeckoMarket) -> float:
        """Implements rule AS-02c."""
        ratio = market.get_circulation_ratio()
        if ratio is None:
            return 1.0 # Lowest score if data is unavailable, per spec
        tiers = self.config['tokenomics']['supply_risk_tiers']
        for tier in tiers:
            if ratio >= tier['min_ratio']:
                return tier['score']
        return 1.0 # Should not be reached

    def calculate_all_automated_scores(self, market: CoinGeckoMarket, details: Optional[CoinGeckoCoinDetails]) -> Dict[str, Any]:
        """
        Orchestrates the calculation of all automated scores for a project.
        """
        narrative_defaults = self.config['narrative']
        tokenomics_defaults = self.config['tokenomics']

        # --- Calculate Score Components ---
        sector_strength = self._calculate_sector_strength(market, details)
        valuation_potential = self._calculate_valuation_potential(market)
        supply_risk = self._calculate_supply_risk(market)

        # Apply defaults from spec (AS-01b, AS-01c, AS-02b)
        backing_team = narrative_defaults['backing_team_default']
        value_proposition = narrative_defaults['value_proposition_default']
        token_utility = tokenomics_defaults['token_utility_default']

        # --- Calculate Pillar Scores (AS-01, AS-02) ---
        narrative_score = (sector_strength + backing_team + value_proposition) / 3.0
        tokenomics_score = (valuation_potential + token_utility + supply_risk) / 3.0

        return {
            "sector_strength": sector_strength,
            "backing_team": backing_team,
            "value_proposition": value_proposition,
            "valuation_potential": valuation_potential,
            "token_utility": token_utility,
            "supply_risk": supply_risk,
            "narrative_score": round(narrative_score, 2),
            "tokenomics_score": round(tokenomics_score, 2),
            # Data Score is handled separately after user paste
            "data_score": None, 
            "accumulation_signal": None,
            "has_data_score": False,
            # Omega Score is not calculated yet (AS-05)
            "omega_score": None, 
        }
