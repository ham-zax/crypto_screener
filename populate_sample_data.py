#!/usr/bin/env python3
"""
Script to populate sample automated projects for testing the UI
This ensures there's data to display when clicking the "Automated" tab
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def populate_sample_automated_projects():
    """Create sample automated projects for testing"""
    try:
        from src.database.config import get_session, init_db
        from src.models.automated_project import AutomatedProject
        from datetime import datetime, timezone
        import uuid
        
        # Initialize database tables first
        print("🔧 Initializing database tables...")
        init_db()
        
        # Create session
        session = get_session()
        
        print("🔄 Checking existing automated projects...")
        
        # Check if automated projects already exist
        existing_count = session.query(AutomatedProject).filter_by(data_source='automated').count()
        print(f"Found {existing_count} existing automated projects")
        
        if existing_count > 0:
            print("✅ Automated projects already exist in database")
            return
        
        print("🌱 Creating sample automated projects...")
        
        # Sample automated projects with realistic data
        sample_projects = [
            {
                'name': 'Bitcoin',
                'ticker': 'BTC',
                'coingecko_id': 'bitcoin',
                'category': 'L1',
                'market_cap': 850000000000,
                'price_usd': 43500.0,
                'volume_24h': 15000000000,
                'narrative_score': 9.2,
                'tokenomics_score': 8.8,
                'sector_strength': 9.5,
                'value_proposition': 9.0,
                'backing_team': 8.5,
                'valuation_potential': 7.5,
                'token_utility': 9.0,
                'supply_risk': 9.5,
                'has_data_score': False
            },
            {
                'name': 'Ethereum',
                'ticker': 'ETH',
                'coingecko_id': 'ethereum',
                'category': 'L1',
                'market_cap': 290000000000,
                'price_usd': 2420.0,
                'volume_24h': 8500000000,
                'narrative_score': 8.8,
                'tokenomics_score': 8.5,
                'sector_strength': 9.0,
                'value_proposition': 9.2,
                'backing_team': 9.0,
                'valuation_potential': 8.0,
                'token_utility': 8.8,
                'supply_risk': 7.8,
                'has_data_score': False
            },
            {
                'name': 'Chainlink',
                'ticker': 'LINK',
                'coingecko_id': 'chainlink',
                'category': 'Infrastructure',
                'market_cap': 8500000000,
                'price_usd': 14.20,
                'volume_24h': 450000000,
                'narrative_score': 8.5,
                'tokenomics_score': 7.8,
                'sector_strength': 8.5,
                'value_proposition': 8.8,
                'backing_team': 8.2,
                'valuation_potential': 7.5,
                'token_utility': 8.5,
                'supply_risk': 7.5,
                'has_data_score': False
            },
            {
                'name': 'Arbitrum',
                'ticker': 'ARB',
                'coingecko_id': 'arbitrum',
                'category': 'L2',
                'market_cap': 2100000000,
                'price_usd': 0.52,
                'volume_24h': 185000000,
                'narrative_score': 7.8,
                'tokenomics_score': 7.2,
                'sector_strength': 8.0,
                'value_proposition': 8.2,
                'backing_team': 8.5,
                'valuation_potential': 8.5,
                'token_utility': 7.0,
                'supply_risk': 6.5,
                'has_data_score': False
            },
            {
                'name': 'Render',
                'ticker': 'RNDR',
                'coingecko_id': 'render-token',
                'category': 'AI',
                'market_cap': 1800000000,
                'price_usd': 4.85,
                'volume_24h': 125000000,
                'narrative_score': 8.2,
                'tokenomics_score': 7.5,
                'sector_strength': 9.0,
                'value_proposition': 8.0,
                'backing_team': 7.8,
                'valuation_potential': 8.8,
                'token_utility': 8.2,
                'supply_risk': 6.8,
                'has_data_score': False
            },
            {
                'name': 'Helium',
                'ticker': 'HNT',
                'coingecko_id': 'helium',
                'category': 'DePIN',
                'market_cap': 750000000,
                'price_usd': 4.92,
                'volume_24h': 28000000,
                'narrative_score': 7.5,
                'tokenomics_score': 7.8,
                'sector_strength': 8.5,
                'value_proposition': 7.8,
                'backing_team': 7.2,
                'valuation_potential': 8.2,
                'token_utility': 8.5,
                'supply_risk': 7.0,
                'has_data_score': False
            }
        ]
        
        created_count = 0
        for project_data in sample_projects:
            # Add required fields
            project_data.update({
                'id': str(uuid.uuid4()),
                'data_source': 'automated',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'accumulation_signal': None,
                'data_score': None,
                'omega_score': None
            })
            
            # Create project instance
            project = AutomatedProject(**project_data)
            
            # Calculate scores (will set narrative_score, tokenomics_score, but not omega_score due to missing data_score)
            project.update_all_scores()
            
            session.add(project)
            created_count += 1
        
        session.commit()
        session.close()
        
        print(f"✅ Created {created_count} sample automated projects")
        print("📊 Projects are in 'Awaiting Data' state - ready for CSV analysis")
        print("🚀 The 'Automated' tab should now show projects!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()

def check_database_status():
    """Check database connection and table status"""
    try:
        from src.database.config import get_engine
        from src.models.automated_project import AutomatedProject
        
        engine = get_engine()
        
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful")
        
        # Check table existence
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Found {len(tables)} tables: {tables}")
        
        if 'automated_projects' in tables:
            print("✅ automated_projects table exists")
        else:
            print("❌ automated_projects table missing")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    print("🧪 Sample Data Population Script")
    print("=" * 50)
    
    print("\n1️⃣ Checking database status...")
    check_database_status()
    
    print("\n2️⃣ Populating sample automated projects...")
    populate_sample_automated_projects()
    
    print("\n🎯 Next Steps:")
    print("1. Refresh the browser (Ctrl+Shift+R)")
    print("2. Click on the 'Automated Projects' tab")
    print("3. You should see 6 sample projects in 'Awaiting Data' state")
    print("4. Try clicking 'Add Data' on any project to test CSV upload")