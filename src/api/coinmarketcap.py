"""
CoinMarketCap API Client for Project Omega V2

Implements rate limiting, error handling, and retry logic for CoinMarketCap API integration.
Follows the structure and conventions of the CoinGecko client.
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Any
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    pass


class APIError(Exception):
    pass


class CoinMarketCapClient:
    """
    CoinMarketCap API client with rate limiting and error handling

    Features:
    - Rate limiting (30 calls/minute for free tier)
    - Exponential backoff retry logic
    - Response caching to minimize API calls
    - Comprehensive error handling and logging
    """

    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 300):
        self.base_url = "https://pro-api.coinmarketcap.com"
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-CMC_PRO_API_KEY": api_key})
            self.calls_per_minute = 30  # Free tier default
        else:
            raise ValueError("CoinMarketCap API key is required.")
        self.call_timestamps = []
        self.last_call_time = 0
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.max_retries = 3
        self.base_delay = 1
        logger.info(
            f"CoinMarketCap client initialized with {self.calls_per_minute} calls/minute limit"
        )

    def _enforce_rate_limit(self):
        now = time.time()
        cutoff_time = now - 60
        self.call_timestamps = [t for t in self.call_timestamps if t > cutoff_time]
        if len(self.call_timestamps) >= self.calls_per_minute:
            oldest_call = self.call_timestamps[0]
            wait_time = 61 - (now - oldest_call)
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                now = time.time()
        if now - self.last_call_time < 0.1:
            time.sleep(0.1)
            now = time.time()
        self.call_timestamps.append(now)
        self.last_call_time = now

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        sorted_params = sorted(params.items()) if params else []
        return f"{endpoint}:{json.dumps(sorted_params, sort_keys=True)}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        return time.time() - timestamp < self.cache_ttl

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        if params is None:
            params = {}
        cache_key = self._get_cache_key(endpoint, params)
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Cache hit for {endpoint}")
                return cached_data
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        for attempt in range(self.max_retries + 1):
            try:
                self._enforce_rate_limit()
                logger.debug(f"Making request to {endpoint} (attempt {attempt + 1})")
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Server rate limit hit. Waiting {retry_after} seconds"
                    )
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                data = response.json()
                logger.info(
                    f"CoinMarketCap API response for {endpoint}: {json.dumps(data)[:1000]}"
                )
                self.cache[cache_key] = (data, time.time())
                logger.debug(f"Successfully fetched {endpoint}")
                return data
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    logger.error(
                        f"Request failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise APIError(f"Request failed: {e}")
                delay = self.base_delay * (2**attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                )
                time.sleep(delay)
        raise APIError("Max retries exceeded")

    def get_listings_latest(
        self, start: int = 1, limit: int = 100, convert: str = "USD"
    ) -> List[Dict]:
        try:
            params = {"start": start, "limit": limit, "convert": convert}
            response = self._make_request("v1/cryptocurrency/listings/latest", params)
            coins = response.get("data", [])
            logger.info(f"Fetched {len(coins)} coins from CoinMarketCap")
            return coins
        except Exception as e:
            logger.error(f"Failed to fetch listings: {e}")
            raise APIError(f"Failed to fetch listings: {e}")

    def get_quotes_latest(self, symbol: str, convert: str = "USD") -> Dict:
        try:
            params = {"symbol": symbol, "convert": convert}
            response = self._make_request("v2/cryptocurrency/quotes/latest", params)
            data = response.get("data", {})
            logger.info(f"Fetched quote for {symbol} from CoinMarketCap")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise APIError(f"Failed to fetch quote for {symbol}: {e}")

    def clear_cache(self):
        self.cache.clear()
        logger.info("API cache cleared")

    def get_cache_stats(self) -> Dict:
        total_entries = len(self.cache)
        valid_entries = sum(
            1
            for _, (_, timestamp) in self.cache.items()
            if self._is_cache_valid(timestamp)
        )
        cache_hit_rate = (valid_entries / max(total_entries, 1)) * 100
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cache_ttl_seconds": self.cache_ttl,
        }
