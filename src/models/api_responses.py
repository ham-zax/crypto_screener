"""
API Response Models for Project Omega V2

Contains Pydantic models for validating and transforming API responses from CoinGecko.
Handles response variations gracefully and provides structured data for the application.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CoinGeckoMarket:
    """
    Structured model for CoinGecko market data
    
    Validates and transforms raw API responses into consistent format
    for use with AutomatedProject model.
    """
    
    # Basic identification
    id: str
    symbol: str
    name: str
    image: Optional[str] = None
    
    # Market data
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = None
    fully_diluted_valuation: Optional[float] = None
    
    # Volume and supply data
    total_volume: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    
    # Price changes
    price_change_24h: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    market_cap_change_24h: Optional[float] = None
    market_cap_change_percentage_24h: Optional[float] = None
    
    # Additional metadata
    ath: Optional[float] = None
    ath_change_percentage: Optional[float] = None
    ath_date: Optional[str] = None
    atl: Optional[float] = None
    atl_change_percentage: Optional[float] = None
    atl_date: Optional[str] = None
    
    # Timestamp
    last_updated: Optional[str] = None
    
    @classmethod
    def from_coingecko_response(cls, data: Dict[str, Any]) -> 'CoinGeckoMarket':
        """
        Create CoinGeckoMarket from raw CoinGecko API response
        
        Handles missing fields gracefully and validates data types
        
        Args:
            data: Raw response dictionary from CoinGecko API
            
        Returns:
            CoinGeckoMarket instance with validated data
        """
        try:
            # Extract and validate required fields
            coin_id = data.get('id', '').strip()
            symbol = data.get('symbol', '').strip().upper()
            name = data.get('name', '').strip()
            
            if not coin_id or not symbol or not name:
                raise ValueError("Missing required fields: id, symbol, or name")
            
            # Safely extract numeric fields
            def safe_float(value: Any) -> Optional[float]:
                """Safely convert value to float"""
                if value is None:
                    return None
                try:
                    return float(value) if value != 0 else 0.0
                except (ValueError, TypeError):
                    return None
            
            def safe_int(value: Any) -> Optional[int]:
                """Safely convert value to int"""
                if value is None:
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            
            return cls(
                id=coin_id,
                symbol=symbol,
                name=name,
                image=data.get('image'),
                current_price=safe_float(data.get('current_price')),
                market_cap=safe_float(data.get('market_cap')),
                market_cap_rank=safe_int(data.get('market_cap_rank')),
                fully_diluted_valuation=safe_float(data.get('fully_diluted_valuation')),
                total_volume=safe_float(data.get('total_volume')),
                circulating_supply=safe_float(data.get('circulating_supply')),
                total_supply=safe_float(data.get('total_supply')),
                max_supply=safe_float(data.get('max_supply')),
                price_change_24h=safe_float(data.get('price_change_24h')),
                price_change_percentage_24h=safe_float(data.get('price_change_percentage_24h')),
                market_cap_change_24h=safe_float(data.get('market_cap_change_24h')),
                market_cap_change_percentage_24h=safe_float(data.get('market_cap_change_percentage_24h')),
                ath=safe_float(data.get('ath')),
                ath_change_percentage=safe_float(data.get('ath_change_percentage')),
                ath_date=data.get('ath_date'),
                atl=safe_float(data.get('atl')),
                atl_change_percentage=safe_float(data.get('atl_change_percentage')),
                atl_date=data.get('atl_date'),
                last_updated=data.get('last_updated')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse CoinGecko market data: {e}")
            logger.debug(f"Raw data: {data}")
            raise ValueError(f"Invalid CoinGecko market data: {e}")
    
    def to_automated_project_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format compatible with AutomatedProject model
        
        Returns:
            Dictionary with AutomatedProject field mapping
        """
        return {
            'coingecko_id': self.id,
            'name': self.name,
            'ticker': self.symbol,
            'market_cap': self.market_cap,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply or self.max_supply,  # Fallback to max_supply
            'data_source': 'automated',
            'created_via': 'api_ingestion'
        }
    
    def get_circulation_ratio(self) -> Optional[float]:
        """
        Calculate circulation ratio for supply risk scoring
        
        Returns:
            Circulation ratio (circulating/total) or None if data unavailable
        """
        if not self.circulating_supply:
            return None
        
        total = self.total_supply or self.max_supply
        if not total or total <= 0:
            return None
        
        return self.circulating_supply / total
    
    def is_valid_for_scoring(self) -> bool:
        """
        Check if market data has minimum requirements for automated scoring
        
        Returns:
            True if data is sufficient for scoring algorithms
        """
        # Must have basic identification
        if not self.id or not self.symbol or not self.name:
            return False
        
        # Must have market cap for valuation scoring
        if not self.market_cap or self.market_cap <= 0:
            return False
        
        return True
    
    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors for debugging
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.id:
            errors.append("Missing CoinGecko ID")
        if not self.symbol:
            errors.append("Missing symbol")
        if not self.name:
            errors.append("Missing name")
        if not self.market_cap or self.market_cap <= 0:
            errors.append("Invalid or missing market cap")
        if self.circulating_supply and self.circulating_supply < 0:
            errors.append("Negative circulating supply")
        if self.total_supply and self.total_supply < 0:
            errors.append("Negative total supply")
        
        return errors


@dataclass
class CoinGeckoCoinDetails:
    """
    Model for detailed coin information from CoinGecko coin/{id} endpoint
    
    Used for enriching project data with additional metadata
    """
    
    id: str
    symbol: str
    name: str
    categories: List[str]
    description: Optional[str] = None
    homepage: Optional[str] = None
    blockchain_site: List[str] = None
    
    # Market data (from market_data object)
    market_cap_usd: Optional[float] = None
    current_price_usd: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    
    @classmethod
    def from_coingecko_response(cls, data: Dict[str, Any]) -> 'CoinGeckoCoinDetails':
        """
        Create CoinGeckoCoinDetails from detailed coin API response
        
        Args:
            data: Raw response from CoinGecko coins/{id} endpoint
            
        Returns:
            CoinGeckoCoinDetails instance
        """
        try:
            # Basic info
            coin_id = data.get('id', '').strip()
            symbol = data.get('symbol', '').strip().upper()
            name = data.get('name', '').strip()
            
            # Categories
            categories = data.get('categories', [])
            if categories:
                categories = [cat for cat in categories if cat]  # Remove empty strings
            
            # Description (extract English)
            description = None
            desc_obj = data.get('description', {})
            if isinstance(desc_obj, dict):
                description = desc_obj.get('en', '').strip()
            
            # Links
            links = data.get('links', {})
            homepage = None
            if links and links.get('homepage'):
                homepage = links['homepage'][0] if links['homepage'] else None
            
            blockchain_site = []
            if links and links.get('blockchain_site'):
                blockchain_site = [site for site in links['blockchain_site'] if site]
            
            # Market data
            market_data = data.get('market_data', {})
            
            def safe_usd_value(field_name: str) -> Optional[float]:
                """Extract USD value from market data"""
                field_data = market_data.get(field_name, {})
                if isinstance(field_data, dict):
                    usd_value = field_data.get('usd')
                    try:
                        return float(usd_value) if usd_value is not None else None
                    except (ValueError, TypeError):
                        return None
                return None
            
            def safe_supply_value(field_name: str) -> Optional[float]:
                """Extract supply value from market data"""
                value = market_data.get(field_name)
                try:
                    return float(value) if value is not None else None
                except (ValueError, TypeError):
                    return None
            
            return cls(
                id=coin_id,
                symbol=symbol,
                name=name,
                categories=categories,
                description=description,
                homepage=homepage,
                blockchain_site=blockchain_site,
                market_cap_usd=safe_usd_value('market_cap'),
                current_price_usd=safe_usd_value('current_price'),
                circulating_supply=safe_supply_value('circulating_supply'),
                total_supply=safe_supply_value('total_supply'),
                max_supply=safe_supply_value('max_supply')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse CoinGecko coin details: {e}")
            raise ValueError(f"Invalid CoinGecko coin details: {e}")
    
    def get_primary_category(self) -> Optional[str]:
        """
        Get the primary category for sector strength scoring
        
        Returns:
            Primary category string or None
        """
        if not self.categories:
            return None
        
        # Return first category as primary
        return self.categories[0].lower().replace(' ', '-')
    
    def to_automated_project_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for AutomatedProject model
        
        Returns:
            Dictionary with relevant fields for database model
        """
        return {
            'coingecko_id': self.id,
            'name': self.name,
            'ticker': self.symbol,
            'category': self.get_primary_category(),
            'market_cap': self.market_cap_usd,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply or self.max_supply,
            'data_source': 'automated',
            'created_via': 'api_ingestion'
        }


class APIResponseValidator:
    """
    Utility class for validating and transforming API responses
    """
    
    @staticmethod
    def validate_markets_response(data: List[Dict[str, Any]]) -> List[CoinGeckoMarket]:
        """
        Validate and transform markets API response
        
        Args:
            data: Raw markets response data
            
        Returns:
            List of validated CoinGeckoMarket instances
        """
        validated_markets = []
        errors = []
        
        for i, item in enumerate(data):
            try:
                market = CoinGeckoMarket.from_coingecko_response(item)
                if market.is_valid_for_scoring():
                    validated_markets.append(market)
                else:
                    logger.warning(f"Market data for {market.id} failed validation: {market.get_validation_errors()}")
            except Exception as e:
                errors.append(f"Item {i}: {e}")
                logger.warning(f"Failed to validate market item {i}: {e}")
        
        if errors:
            logger.warning(f"Validation errors in markets response: {len(errors)} failed out of {len(data)} items")
        
        logger.info(f"Successfully validated {len(validated_markets)} markets out of {len(data)} total")
        return validated_markets
    
    @staticmethod
    def validate_coin_details_response(data: Dict[str, Any]) -> CoinGeckoCoinDetails:
        """
        Validate and transform coin details API response
        
        Args:
            data: Raw coin details response data
            
        Returns:
            Validated CoinGeckoCoinDetails instance
        """
        return CoinGeckoCoinDetails.from_coingecko_response(data)
    
    @staticmethod
    def filter_by_market_cap(
        markets: List[CoinGeckoMarket], 
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None
    ) -> List[CoinGeckoMarket]:
        """
        Filter markets by market cap criteria
        
        Args:
            markets: List of market data
            min_market_cap: Minimum market cap (USD)
            max_market_cap: Maximum market cap (USD)
            
        Returns:
            Filtered list of markets
        """
        filtered = markets
        
        if min_market_cap is not None:
            filtered = [
                m for m in filtered 
                if m.market_cap and m.market_cap >= min_market_cap
            ]
        
        if max_market_cap is not None:
            filtered = [
                m for m in filtered 
                if m.market_cap and m.market_cap <= max_market_cap
            ]
        
        logger.info(f"Filtered {len(filtered)} markets from {len(markets)} based on market cap criteria")
        return filtered
    
    @staticmethod
    def filter_by_volume(
        markets: List[CoinGeckoMarket], 
        min_volume: Optional[float] = None
    ) -> List[CoinGeckoMarket]:
        """
        Filter markets by volume criteria
        
        Args:
            markets: List of market data
            min_volume: Minimum 24h volume (USD)
            
        Returns:
            Filtered list of markets
        """
        if min_volume is None:
            return markets
        
        filtered = [
            m for m in markets 
            if m.total_volume and m.total_volume >= min_volume
        ]
        
        logger.info(f"Filtered {len(filtered)} markets from {len(markets)} based on volume criteria")
        return filtered