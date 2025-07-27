#!/usr/bin/env python3
"""
Test script to verify the Demo API fix works correctly.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_demo_api_fix():
    """Test that the Demo API authentication is working correctly"""
    logger.info("=== TESTING DEMO API FIX ===")

    try:
        from src.api.coingecko import CoinGeckoClient

        # Test with Demo API key
        demo_api_key = os.getenv(
            "COINGECKO_API_KEY", ""
        )  # Ensure it's a string, even if empty
        if not demo_api_key:
            logger.error("❌ COINGECKO_API_KEY is not set in environment variables.")
            return False
        logger.info(
            f"Testing with API key: {demo_api_key[:10]}..."
        )  # Now safe to slice

        client = CoinGeckoClient(api_key=demo_api_key)

        # Test a simple ping endpoint first
        logger.info("Testing ping endpoint...")
        try:
            # Make a simple request to test authentication
            markets = client.get_markets_data(per_page=2, page=1)
            logger.info(f"✅ SUCCESS: Received {len(markets)} markets")
            logger.info(
                f"First market: {markets[0]['id']} - ${markets[0]['current_price']}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            return False

    except Exception as e:
        logger.error(f"❌ IMPORT FAILED: {e}")
        return False


if __name__ == "__main__":
    success = test_demo_api_fix()
    if success:
        logger.info("🎉 Demo API fix is working correctly!")
    else:
        logger.error("💥 Demo API fix needs more work")
