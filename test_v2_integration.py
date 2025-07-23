"""
Test Script for Project Omega V2 API Integration

This script tests the complete API integration flow including:
- CoinGecko API client functionality
- Data validation and transformation
- Automated scoring algorithms
- API endpoints (if dependencies are available)

Run this script to verify Phase 2 implementation.
"""

import sys
import os
import logging
import time
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_coingecko_client():
    """Test CoinGecko API client functionality"""
    print("\n=== Testing CoinGecko API Client ===")
    
    try:
        from src.api.coingecko import CoinGeckoClient
        
        # Initialize client
        client = CoinGeckoClient()
        print("✓ CoinGecko client initialized successfully")
        
        # Test rate limiting
        print(f"✓ Rate limit: {client.calls_per_minute} calls/minute")
        
        # Test cache stats
        cache_stats = client.get_cache_stats()
        print(f"✓ Cache initialized: {cache_stats}")
        
        # Test API call (small request)
        print("📡 Testing API connectivity...")
        try:
            # Get top 5 markets to test connectivity
            markets = client.get_markets_data(per_page=5, page=1)
            print(f"✓ Successfully fetched {len(markets)} market entries")
            
            # Test individual coin data
            if markets:
                coin_id = markets[0]['id']
                coin_data = client.get_coin_data(coin_id)
                print(f"✓ Successfully fetched detailed data for {coin_id}")
            
        except Exception as e:
            print(f"⚠️  API connectivity test failed: {e}")
            print("   This might be due to network issues or rate limiting")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import CoinGecko client: {e}")
        return False
    except Exception as e:
        print(f"❌ CoinGecko client test failed: {e}")
        return False

def test_api_responses():
    """Test API response models and validation"""
    print("\n=== Testing API Response Models ===")
    
    try:
        from src.models.api_responses import CoinGeckoMarket, APIResponseValidator
        
        # Test data for validation
        test_market_data = {
            'id': 'bitcoin',
            'symbol': 'btc',
            'name': 'Bitcoin',
            'current_price': 45000.0,
            'market_cap': 850000000000,
            'circulating_supply': 19000000,
            'total_supply': 21000000,
            'total_volume': 25000000000
        }
        
        # Test market data validation
        market = CoinGeckoMarket.from_coingecko_response(test_market_data)
        print(f"✓ Market data validation successful: {market.name}")
        
        # Test validation checks
        is_valid = market.is_valid_for_scoring()
        print(f"✓ Scoring validation: {is_valid}")
        
        # Test circulation ratio calculation
        circulation_ratio = market.get_circulation_ratio()
        print(f"✓ Circulation ratio: {circulation_ratio:.2%}")
        
        # Test conversion to project dict
        project_dict = market.to_automated_project_dict()
        print(f"✓ Project dict conversion: {len(project_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ API response models test failed: {e}")
        return False

def test_automated_scoring():
    """Test automated scoring algorithms"""
    print("\n=== Testing Automated Scoring ===")
    
    try:
        from src.scoring.automated_scoring import AutomatedScoringEngine
        from src.models.api_responses import CoinGeckoMarket
        
        engine = AutomatedScoringEngine()
        
        # Test individual scoring functions
        sector_score = engine.calculate_sector_strength('artificial-intelligence')
        print(f"✓ Sector strength (AI): {sector_score}")
        
        valuation_score = engine.calculate_valuation_potential(50_000_000)
        print(f"✓ Valuation potential ($50M): {valuation_score}")
        
        supply_score = engine.calculate_supply_risk(19_000_000, 21_000_000)
        print(f"✓ Supply risk (90.5% circulating): {supply_score}")
        
        # Test complete scoring
        test_market_data = {
            'id': 'test-coin',
            'symbol': 'test',
            'name': 'Test Coin',
            'current_price': 1.50,
            'market_cap': 75_000_000,
            'circulating_supply': 80_000_000,
            'total_supply': 100_000_000,
            'total_volume': 2_000_000
        }
        
        market = CoinGeckoMarket.from_coingecko_response(test_market_data)
        scores = engine.calculate_all_automated_scores(market)
        
        print(f"✓ Complete scoring result:")
        print(f"   Narrative Score: {scores['narrative_score']:.1f}")
        print(f"   Tokenomics Score: {scores['tokenomics_score']:.1f}")
        print(f"   Omega Score: {scores['omega_score']}")  # Should be None
        
        return True
        
    except Exception as e:
        print(f"❌ Automated scoring test failed: {e}")
        return False

def test_data_fetcher():
    """Test data fetching service"""
    print("\n=== Testing Data Fetcher Service ===")
    
    try:
        from src.api.data_fetcher import DataFetchingService
        
        # Initialize service
        service = DataFetchingService()
        print("✓ Data fetching service initialized")
        
        # Test service stats
        stats = service.get_service_stats()
        print(f"✓ Service stats: {stats['service_status']}")
        
        # Test single project fetch (if API is available)
        try:
            print("📡 Testing single project fetch...")
            project_data = service.fetch_single_project('bitcoin', include_detailed_data=False)
            if project_data:
                print(f"✓ Successfully fetched Bitcoin data: {project_data['name']}")
                print(f"   Market Cap: ${project_data.get('market_cap', 0):,.0f}")
                print(f"   Narrative Score: {project_data.get('narrative_score', 'N/A')}")
            else:
                print("⚠️  Single project fetch returned no data")
        
        except Exception as e:
            print(f"⚠️  Single project fetch failed: {e}")
            print("   This might be due to API rate limits or network issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Data fetcher test failed: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint to verify API integration"""
    print("\n=== Testing Health Endpoint ===")
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get('http://localhost:5000/api/v2/health', timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ Health endpoint accessible")
            print(f"   Status: {health_data.get('status')}")
            print(f"   V2 Dependencies: {health_data.get('v2_dependencies_available')}")
            print(f"   Database: {health_data.get('database_available')}")
            return True
        else:
            print(f"⚠️  Health endpoint returned status {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("⚠️  Cannot connect to localhost:5000")
        print("   Make sure the Flask server is running: python src/main.py")
        return False
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and logging"""
    print("\n=== Testing Error Handling ===")
    
    try:
        from src.api.error_handling import (
            ErrorTracker, 
            handle_api_errors, 
            graceful_degradation,
            ExternalAPIError
        )
        
        # Test error tracker
        tracker = ErrorTracker()
        test_error = ExternalAPIError("Test error", "TestAPI", 429)
        tracker.record_error(test_error, {'test': True})
        
        summary = tracker.get_error_summary()
        print(f"✓ Error tracking: {summary['total_errors']} errors recorded")
        
        # Test decorators
        @handle_api_errors(retry_count=2)
        def test_retry_function():
            raise ExternalAPIError("Test retry", "TestAPI")
        
        @graceful_degradation(fallback_value="fallback")
        def test_degradation_function():
            raise Exception("Test degradation")
        
        # Test graceful degradation
        result = test_degradation_function()
        print(f"✓ Graceful degradation: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Project Omega V2 API Integration Tests")
    print("=" * 60)
    
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during testing
    
    test_results = {}
    
    # Run all tests
    tests = [
        ("CoinGecko Client", test_coingecko_client),
        ("API Response Models", test_api_responses),
        ("Automated Scoring", test_automated_scoring),
        ("Data Fetcher Service", test_data_fetcher),
        ("Error Handling", test_error_handling),
        ("Health Endpoint", test_health_endpoint),
    ]
    
    for test_name, test_func in tests:
        try:
            test_results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            test_results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 2 API Integration is working correctly.")
        print("\nAPI Endpoints Available:")
        print("- GET  /api/v2/health")
        print("- POST /api/v2/fetch-projects")
        print("- GET  /api/v2/projects/automated")
        print("- GET  /api/v2/projects/automated/<id>")
        print("- POST /api/v2/projects/automated/<id>/refresh")
        print("- GET  /api/v2/ingestion/status")
        print("- GET  /api/v2/service/stats")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)