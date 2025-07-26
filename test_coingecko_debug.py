#!/usr/bin/env python3
"""
Debug script to test CoinGecko API integration and diagnose API key usage issues.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging to see all debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_environment_loading():
    """Test environment variable loading"""
    logger.info("=== TESTING ENVIRONMENT VARIABLE LOADING ===")
    
    coingecko_key = os.getenv('COINGECKO_API_KEY')
    coinmarketcap_key = os.getenv('COINMARKETCAP_API_KEY')
    
    logger.info(f"COINGECKO_API_KEY loaded: {coingecko_key is not None}")
    if coingecko_key:
        logger.info(f"COINGECKO_API_KEY length: {len(coingecko_key)}")
        logger.info(f"COINGECKO_API_KEY prefix: {coingecko_key[:10]}...")
    
    logger.info(f"COINMARKETCAP_API_KEY loaded: {coinmarketcap_key is not None}")
    if coinmarketcap_key:
        logger.info(f"COINMARKETCAP_API_KEY length: {len(coinmarketcap_key)}")
        logger.info(f"COINMARKETCAP_API_KEY prefix: {coinmarketcap_key[:10]}...")
    
    return coingecko_key, coinmarketcap_key

def test_coingecko_client():
    """Test CoinGecko client initialization and API call"""
    logger.info("=== TESTING COINGECKO CLIENT ===")
    
    try:
        from src.api.coingecko import CoinGeckoClient
        
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        client = CoinGeckoClient(api_key=coingecko_key)
        
        logger.info("CoinGecko client initialized successfully")
        
        # Test a simple API call
        logger.info("Making test API call to CoinGecko...")
        markets = client.get_markets_data(per_page=5, page=1)
        
        logger.info(f"CoinGecko API call successful - received {len(markets)} markets")
        return True, markets
        
    except Exception as e:
        logger.error(f"CoinGecko client test failed: {e}")
        return False, str(e)

def test_data_fetcher():
    """Test DataFetchingService initialization"""
    logger.info("=== TESTING DATA FETCHING SERVICE ===")
    
    try:
        from src.api.data_fetcher import DataFetchingService
        
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        fetcher = DataFetchingService(api_key=coingecko_key)
        
        logger.info("DataFetchingService initialized successfully")
        
        # Test service stats
        stats = fetcher.get_service_stats()
        logger.info(f"Service stats: {stats}")
        
        return True, stats
        
    except Exception as e:
        logger.error(f"DataFetchingService test failed: {e}")
        return False, str(e)

def test_scheduled_task_context():
    """Test environment loading in task context"""
    logger.info("=== TESTING SCHEDULED TASK CONTEXT ===")
    
    try:
        from src.tasks.scheduled_tasks import _core_fetch_and_save_logic
        
        # Test with minimal filters
        filters = {
            'min_market_cap': 1_000_000,
            'max_results': 5,  # Small number for testing
            'min_volume_24h': 100_000
        }
        
        logger.info("Testing core fetch logic...")
        result = _core_fetch_and_save_logic(
            filters=filters,
            save_to_database=False,  # Don't save for testing
            batch_size=5
        )
        
        logger.info(f"Core fetch logic result: {result}")
        return True, result
        
    except Exception as e:
        logger.error(f"Scheduled task context test failed: {e}")
        return False, str(e)

def main():
    """Run all diagnostic tests"""
    logger.info("Starting CoinGecko API diagnostic tests...")
    
    # Test 1: Environment loading
    coingecko_key, coinmarketcap_key = test_environment_loading()
    
    # Test 2: CoinGecko client
    cg_success, cg_result = test_coingecko_client()
    
    # Test 3: Data fetcher
    df_success, df_result = test_data_fetcher()
    
    # Test 4: Scheduled task context
    st_success, st_result = test_scheduled_task_context()
    
    # Summary
    logger.info("=== DIAGNOSTIC SUMMARY ===")
    logger.info(f"Environment loading: {'✓' if coingecko_key else '✗'}")
    logger.info(f"CoinGecko client: {'✓' if cg_success else '✗'}")
    logger.info(f"Data fetcher: {'✓' if df_success else '✗'}")
    logger.info(f"Scheduled task: {'✓' if st_success else '✗'}")
    
    if not coingecko_key:
        logger.error("DIAGNOSIS: COINGECKO_API_KEY is not loaded from environment!")
    elif not cg_success:
        logger.error(f"DIAGNOSIS: CoinGecko API client failed: {cg_result}")
    elif not df_success:
        logger.error(f"DIAGNOSIS: Data fetching service failed: {df_result}")
    elif not st_success:
        logger.error(f"DIAGNOSIS: Scheduled task context failed: {st_result}")
    else:
        logger.info("DIAGNOSIS: All components appear to be working correctly")

if __name__ == "__main__":
    main()