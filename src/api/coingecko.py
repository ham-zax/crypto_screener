"""
CoinGecko API Client for Project Omega V2

Implements rate limiting, error handling, and retry logic for CoinGecko API integration.
Based on V2 specification requirements for automated project ingestion.
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Any
import json

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass

class APIError(Exception):
    """Raised when API returns an error"""
    pass

class CoinGeckoClient:
    """
    CoinGecko API client with rate limiting and error handling
    
    Features:
    - Rate limiting (30 calls/minute for free tier)
    - Exponential backoff retry logic
    - Response caching to minimize API calls
    - Comprehensive error handling and logging
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 300):
        """
        Initialize CoinGecko API client
        
        Args:
            api_key: Optional CoinGecko Pro API key
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        
        # Set up authentication if API key provided
        if api_key:
            self.session.headers.update({"x-cg-pro-api-key": api_key})
            self.calls_per_minute = 500  # Pro tier limit
        else:
            self.calls_per_minute = 30   # Free tier limit
        
        # Rate limiting tracking
        self.call_timestamps = []
        self.last_call_time = 0
        
        # Simple in-memory cache
        self.cache = {}
        self.cache_ttl = cache_ttl
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1  # seconds
        
        logger.info(f"CoinGecko client initialized with {self.calls_per_minute} calls/minute limit")
    
    def _enforce_rate_limit(self):
        """
        Enforce rate limiting based on configured limits
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        now = time.time()
        
        # Remove calls older than 1 minute
        cutoff_time = now - 60
        self.call_timestamps = [t for t in self.call_timestamps if t > cutoff_time]
        
        # Check if we're at the limit
        if len(self.call_timestamps) >= self.calls_per_minute:
            # Calculate how long to wait
            oldest_call = self.call_timestamps[0]
            wait_time = 61 - (now - oldest_call)  # Wait until oldest call is 61 seconds old
            
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                now = time.time()
        
        # Minimum delay between calls (100ms)
        if now - self.last_call_time < 0.1:
            time.sleep(0.1)
            now = time.time()
        
        self.call_timestamps.append(now)
        self.last_call_time = now
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key for request"""
        # Sort params for consistent keys
        sorted_params = sorted(params.items()) if params else []
        return f"{endpoint}:{json.dumps(sorted_params, sort_keys=True)}"
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cached data is still valid"""
        return time.time() - timestamp < self.cache_ttl
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        Make HTTP request with rate limiting, caching, and retry logic
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            APIError: If API returns an error after retries
            RateLimitError: If rate limiting fails
        """
        if params is None:
            params = {}
        
        # Check cache first
        cache_key = self._get_cache_key(endpoint, params)
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Cache hit for {endpoint}")
                return cached_data
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries + 1):
            try:
                # Enforce rate limiting
                self._enforce_rate_limit()
                
                # Make request
                logger.debug(f"Making request to {endpoint} (attempt {attempt + 1})")
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle HTTP errors
                if response.status_code == 429:
                    # Rate limited by server
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Server rate limit hit. Waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Log the full API response
                logger.info(f"CoinGecko API response for {endpoint}: {json.dumps(data)[:1000]}")  # Truncate to 1000 chars
                
                # Cache successful response
                self.cache[cache_key] = (data, time.time())
                
                logger.debug(f"Successfully fetched {endpoint}")
                return data
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                    raise APIError(f"Request failed: {e}")
                
                # Exponential backoff
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                time.sleep(delay)
        
        raise APIError("Max retries exceeded")
    
    def get_coins_list(self, include_platform: bool = False) -> List[Dict]:
        """
        Fetch all supported cryptocurrencies from CoinGecko
        
        Args:
            include_platform: Include platform contract addresses
            
        Returns:
            List of coin information dictionaries
        """
        try:
            params = {"include_platform": str(include_platform).lower()}
            response = self._make_request("coins/list", params)
            
            # Extract coins list from response
            coins = response.get('coins', [])
            
            logger.info(f"Fetched {len(coins)} coins from CoinGecko")
            return coins
            
        except Exception as e:
            logger.error(f"Failed to fetch coins list: {e}")
            raise APIError(f"Failed to fetch coins list: {e}")
    
    def get_coin_data(
        self, 
        coin_id: str,
        localization: bool = False,
        tickers: bool = False,
        market_data: bool = True,
        community_data: bool = False,
        developer_data: bool = False,
        sparkline: bool = False
    ) -> Dict:
        """
        Get detailed market data for a specific coin
        
        Args:
            coin_id: CoinGecko coin identifier
            localization: Include localized data
            tickers: Include tickers data
            market_data: Include market data
            community_data: Include community data
            developer_data: Include developer data
            sparkline: Include sparkline data
            
        Returns:
            Detailed coin data dictionary
        """
        try:
            params = {
                "localization": str(localization).lower(),
                "tickers": str(tickers).lower(),
                "market_data": str(market_data).lower(),
                "community_data": str(community_data).lower(),
                "developer_data": str(developer_data).lower(),
                "sparkline": str(sparkline).lower()
            }
            
            data = self._make_request(f"coins/{coin_id}", params)
            logger.debug(f"Fetched detailed data for {coin_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {coin_id}: {e}")
            raise APIError(f"Failed to fetch coin data: {e}")
    
    def get_coin_market_chart_range(
        self,
        coin_id: str,
        vs_currency: str,
        from_timestamp: int,
        to_timestamp: int
    ) -> Dict:
        """
        Get historical market data for a coin within a specific date range.

        Args:
            coin_id: The coin's ID.
            vs_currency: The target currency.
            from_timestamp: The start of the date range (Unix timestamp).
            to_timestamp: The end of the date range (Unix timestamp).

        Returns:
            A dictionary containing prices, market caps, and total volumes.
        """
        try:
            params = {
                "vs_currency": vs_currency,
                "from": from_timestamp,
                "to": to_timestamp,
            }
            data = self._make_request(f"coins/{coin_id}/market_chart/range", params)
            logger.debug(f"Fetched market chart data for {coin_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch market chart data for {coin_id}: {e}")
            raise APIError(f"Failed to fetch market chart data for {coin_id}: {e}")
    
    def get_markets_data(
        self,
        vs_currency: str = "usd",
        per_page: int = 250,
        page: int = 1,
        order: str = "market_cap_desc",
        sparkline: bool = False
    ) -> List[Dict]:
        """
        Get market data with pagination support
        
        Args:
            vs_currency: Currency for pricing (default: usd)
            per_page: Number of results per page (max 250)
            page: Page number
            order: Sort order (default: market_cap_desc)
            sparkline: Include sparkline data
            
        Returns:
            List of market data dictionaries
        """
        try:
            params = {
                "vs_currency": vs_currency,
                "order": order,
                "per_page": min(per_page, 250),  # CoinGecko max is 250
                "page": page,
                "sparkline": str(sparkline).lower()
            }
            
            response = self._make_request("coins/markets", params)
            
            # The API returns a list directly
            logger.info(f"Fetched {len(response)} market entries (page {page})")
            return response
            
        except Exception as e:
            logger.error(f"Failed to fetch markets data: {e}")
            raise APIError(f"Failed to fetch markets data: {e}")
    
    def get_markets_data_bulk(
        self, 
        vs_currency: str = "usd",
        max_results: int = 1000,
        min_market_cap: Optional[float] = None,
        order: str = "market_cap_desc"
    ) -> List[Dict]:
        """
        Fetch large amounts of market data with automatic pagination
        
        Args:
            vs_currency: Currency for pricing
            max_results: Maximum number of results to fetch
            min_market_cap: Minimum market cap filter (USD)
            order: Sort order
            
        Returns:
            List of all market data dictionaries
        """
        all_data = []
        page = 1
        per_page = 250
        
        try:
            while len(all_data) < max_results:
                remaining = max_results - len(all_data)
                current_per_page = min(per_page, remaining)
                
                page_data = self.get_markets_data(
                    vs_currency=vs_currency,
                    per_page=current_per_page,
                    page=page,
                    order=order
                )
                
                if not page_data:
                    # No more data available
                    break
                
                all_data.extend(page_data)
                
                # Check if we got less than requested (last page)
                if len(page_data) < current_per_page:
                    break
                
                page += 1
                
                # Brief pause between pages to be respectful
                time.sleep(0.5)
            
            logger.info(f"Fetched {len(all_data)} total market entries across {page} pages")
            return all_data[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to fetch bulk market data: {e}")
            raise APIError(f"Failed to fetch bulk market data: {e}")
    
    def clear_cache(self):
        """Clear the response cache"""
        self.cache.clear()
        logger.info("API cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        valid_entries = sum(
            1 for _, (_, timestamp) in self.cache.items() 
            if self._is_cache_valid(timestamp)
        )
        
        cache_hit_rate = (valid_entries / max(total_entries, 1)) * 100
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cache_ttl_seconds": self.cache_ttl
        }