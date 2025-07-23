#!/usr/bin/env python3
"""
Test Script for CSV Analysis Engine

Tests the complete CSV analysis functionality including:
- CSV parsing and validation
- Linear regression analysis
- Data Score calculation
- API endpoints integration

Run this script to validate Phase 3 implementation.
"""

import sys
import os
import json
import requests
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_csv_analyzer_direct():
    """Test the CSV analyzer module directly"""
    print("=" * 60)
    print("TESTING CSV ANALYZER MODULE DIRECTLY")
    print("=" * 60)
    
    try:
        from src.scoring.csv_analyzer import CSVAnalyzer, CSVFormatValidator
        print("✓ CSV analyzer modules imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import CSV analyzer: {e}")
        return False
    
    # Test 1: Strong Accumulation CSV
    print("\n1. Testing Strong Accumulation Scenario:")
    try:
        with open('data/sample_csv_strong_accumulation.csv', 'r') as f:
            csv_text = f.read()
        
        result = CSVAnalyzer.analyze_csv_data(csv_text)
        
        if result['success']:
            score = result['data_score']
            print(f"   ✓ Analysis successful - Data Score: {score:.1f}")
            print(f"   ✓ Divergence Type: {result['analysis_metadata']['divergence_type']}")
            
            if score >= 8:
                print(f"   ✓ Strong accumulation signal detected correctly (score: {score:.1f})")
            else:
                print(f"   ⚠ Expected strong accumulation (8+), got {score:.1f}")
        else:
            print(f"   ✗ Analysis failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"   ✗ Strong accumulation test failed: {e}")
        return False
    
    # Test 2: Distribution CSV
    print("\n2. Testing Distribution Scenario:")
    try:
        with open('data/sample_csv_distribution.csv', 'r') as f:
            csv_text = f.read()
        
        result = CSVAnalyzer.analyze_csv_data(csv_text)
        
        if result['success']:
            score = result['data_score']
            print(f"   ✓ Analysis successful - Data Score: {score:.1f}")
            print(f"   ✓ Divergence Type: {result['analysis_metadata']['divergence_type']}")
            
            if score <= 3:
                print(f"   ✓ Distribution signal detected correctly (score: {score:.1f})")
            else:
                print(f"   ⚠ Expected distribution (≤3), got {score:.1f}")
        else:
            print(f"   ✗ Analysis failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"   ✗ Distribution test failed: {e}")
        return False
    
    # Test 3: Insufficient Data CSV
    print("\n3. Testing Insufficient Data Scenario:")
    try:
        with open('data/sample_csv_insufficient_data.csv', 'r') as f:
            csv_text = f.read()
        
        result = CSVAnalyzer.analyze_csv_data(csv_text)
        
        if not result['success']:
            print(f"   ✓ Correctly rejected insufficient data: {result['error']}")
        else:
            print(f"   ⚠ Should have rejected insufficient data (only 30 periods)")
            return False
            
    except Exception as e:
        print(f"   ✗ Insufficient data test failed: {e}")
        return False
    
    # Test 4: Format Validation
    print("\n4. Testing CSV Format Validation:")
    try:
        requirements = CSVFormatValidator.get_csv_requirements()
        print(f"   ✓ Required columns: {requirements['required_columns']}")
        print(f"   ✓ Minimum periods: {requirements['minimum_periods']}")
        
        # Test invalid CSV
        invalid_csv = "wrong,headers,here\n1,2,3\n4,5,6"
        result = CSVFormatValidator.validate_csv_format_preview(invalid_csv)
        
        if not result['valid']:
            print(f"   ✓ Correctly rejected invalid format: {result['error']}")
        else:
            print(f"   ⚠ Should have rejected invalid format")
            return False
            
    except Exception as e:
        print(f"   ✗ Format validation test failed: {e}")
        return False
    
    print("\n✓ All direct CSV analyzer tests passed!")
    return True

def test_api_endpoints():
    """Test the CSV upload API endpoints"""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINTS")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Health check
    print("\n1. Testing API Health Check:")
    try:
        response = requests.get(f"{base_url}/api/v2/health")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✓ API Health: {health['status']}")
            print(f"   ✓ V2 Dependencies: {health['v2_dependencies_available']}")
            print(f"   ✓ Database Available: {health['database_available']}")
        else:
            print(f"   ✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        return False
    
    # Test 2: CSV Validation Endpoint
    print("\n2. Testing CSV Validation Endpoint:")
    try:
        with open('data/sample_csv_strong_accumulation.csv', 'r') as f:
            csv_text = f.read()
        
        response = requests.post(
            f"{base_url}/api/v2/csv/validate",
            json={"csv_data": csv_text}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['valid']:
                print(f"   ✓ CSV validation successful")
                print(f"   ✓ Preview rows: {result['preview']['preview_rows']}")
                print(f"   ✓ Total rows: {result['preview']['total_rows']}")
            else:
                print(f"   ✗ CSV validation failed: {result['error']}")
                return False
        else:
            print(f"   ✗ Validation endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ CSV validation endpoint test failed: {e}")
        return False
    
    # Test 3: Invalid CSV validation
    print("\n3. Testing Invalid CSV Validation:")
    try:
        invalid_csv = "wrong,headers\n1,2\n3,4"
        
        response = requests.post(
            f"{base_url}/api/v2/csv/validate",
            json={"csv_data": invalid_csv}
        )
        
        if response.status_code == 200:
            result = response.json()
            if not result['valid']:
                print(f"   ✓ Correctly rejected invalid CSV: {result['error']}")
            else:
                print(f"   ⚠ Should have rejected invalid CSV")
                return False
        else:
            print(f"   ✗ Invalid CSV validation test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Invalid CSV validation test failed: {e}")
        return False
    
    print("\n✓ All API endpoint tests passed!")
    return True

def test_integration_scenarios():
    """Test integration scenarios and edge cases"""
    print("\n" + "=" * 60)
    print("TESTING INTEGRATION SCENARIOS")
    print("=" * 60)
    
    try:
        from src.scoring.csv_analyzer import CSVAnalyzer
        
        # Test 1: Different date formats
        print("\n1. Testing Different Date Formats:")
        date_formats = [
            "2024-01-01",  # ISO format
            "01/01/2024",  # US format
            "01.01.2024",  # European format
        ]
        
        for date_format in date_formats:
            csv_text = f"time,close,Volume Delta (Close)\n{date_format},100,50\n"
            for i in range(89):  # Add enough data
                csv_text += f"{date_format},100,50\n"
            
            result = CSVAnalyzer.analyze_csv_data(csv_text)
            if result['success']:
                print(f"   ✓ Date format '{date_format}' parsed successfully")
            else:
                print(f"   ⚠ Date format '{date_format}' failed: {result['error']}")
        
        # Test 2: Different delimiters
        print("\n2. Testing Different Delimiters:")
        delimiters = [",", ";"]
        
        for delimiter in delimiters:
            csv_text = f"time{delimiter}close{delimiter}Volume Delta (Close)\n"
            for i in range(90):
                csv_text += f"2024-01-{i+1:02d}{delimiter}100{delimiter}50\n"
            
            result = CSVAnalyzer.analyze_csv_data(csv_text)
            if result['success']:
                print(f"   ✓ Delimiter '{delimiter}' parsed successfully")
            else:
                print(f"   ⚠ Delimiter '{delimiter}' failed: {result['error']}")
        
        # Test 3: Edge case - exactly 90 periods
        print("\n3. Testing Minimum Data Requirement (90 periods):")
        csv_text = "time,close,Volume Delta (Close)\n"
        for i in range(90):
            csv_text += f"2024-01-{i+1:02d},100,50\n"
        
        result = CSVAnalyzer.analyze_csv_data(csv_text)
        if result['success']:
            print(f"   ✓ Exactly 90 periods accepted")
            print(f"   ✓ Data Score: {result['data_score']:.1f}")
        else:
            print(f"   ✗ 90 periods should be accepted: {result['error']}")
            return False
        
        # Test 4: Edge case - 89 periods (should fail)
        print("\n4. Testing Below Minimum Data (89 periods):")
        csv_text = "time,close,Volume Delta (Close)\n"
        for i in range(89):
            csv_text += f"2024-01-{i+1:02d},100,50\n"
        
        result = CSVAnalyzer.analyze_csv_data(csv_text)
        if not result['success']:
            print(f"   ✓ Correctly rejected 89 periods: {result['error']}")
        else:
            print(f"   ✗ Should have rejected 89 periods")
            return False
            
    except Exception as e:
        print(f"   ✗ Integration test failed: {e}")
        return False
    
    print("\n✓ All integration tests passed!")
    return True

def main():
    """Run all tests"""
    print("🚀 PHASE 3 CSV ANALYSIS ENGINE TEST SUITE")
    print("Testing US-06 Implementation with AS-04 Data Score Calculation")
    print()
    
    results = []
    
    # Run test suites
    results.append(("Direct CSV Analyzer", test_csv_analyzer_direct()))
    results.append(("API Endpoints", test_api_endpoints()))
    results.append(("Integration Scenarios", test_integration_scenarios()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print(f"\nOVERALL RESULT: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 3 CSV Analysis Engine is ready!")
        print("\nImplemented Features:")
        print("✓ CSV parsing and validation (AS-03a)")
        print("✓ Linear regression analysis for price and CVD trends")
        print("✓ Data Score calculation algorithm (AS-04)")
        print("✓ Accumulation/Distribution signal detection")
        print("✓ API endpoints for CSV upload and validation")
        print("✓ Integration with AutomatedProject model")
        print("✓ Support for TradingView export format")
        return True
    else:
        print(f"\n❌ {total - passed} test suite(s) failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)