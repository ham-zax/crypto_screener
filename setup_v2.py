#!/usr/bin/env python3
"""
Project Omega V2 Setup and Installation Script

Automated setup script for Project Omega V2 that handles:
- Dependency installation and verification
- Database setup and migration execution
- Configuration file generation
- Environment validation
- Service testing

Usage:
    python setup_v2.py [--environment dev|prod] [--skip-deps] [--force-reset]
"""

import os
import sys
import argparse
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OmegaV2Setup:
    """
    Comprehensive setup manager for Project Omega V2
    
    Handles all aspects of V2 installation and configuration
    """
    
    def __init__(self, environment: str = 'development', skip_deps: bool = False, force_reset: bool = False):
        """
        Initialize setup manager
        
        Args:
            environment: Target environment (development/production)
            skip_deps: Skip dependency installation
            force_reset: Force database reset
        """
        self.environment = environment
        self.skip_deps = skip_deps
        self.force_reset = force_reset
        self.project_root = Path(__file__).parent
        self.setup_results = {}
        
        logger.info(f"🚀 Starting Project Omega V2 setup for {environment} environment")
    
    def run_full_setup(self) -> Dict:
        """
        Execute complete V2 setup process
        
        Returns:
            Setup results and status
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate environment
            logger.info("📋 Step 1: Validating environment...")
            env_result = self._validate_environment()
            self.setup_results['environment_validation'] = env_result
            
            if not env_result['success']:
                return self._format_failure_result('environment_validation', env_result)
            
            # Step 2: Install dependencies
            if not self.skip_deps:
                logger.info("📦 Step 2: Installing dependencies...")
                deps_result = self._install_dependencies()
                self.setup_results['dependency_installation'] = deps_result
                
                if not deps_result['success']:
                    return self._format_failure_result('dependency_installation', deps_result)
            else:
                logger.info("⏭️  Step 2: Skipped dependency installation")
                self.setup_results['dependency_installation'] = {'success': True, 'message': 'Skipped'}
            
            # Step 3: Generate configuration
            logger.info("⚙️  Step 3: Generating configuration...")
            config_result = self._generate_configuration()
            self.setup_results['configuration'] = config_result
            
            if not config_result['success']:
                return self._format_failure_result('configuration', config_result)
            
            # Step 4: Setup database
            logger.info("🗄️  Step 4: Setting up database...")
            db_result = self._setup_database()
            self.setup_results['database_setup'] = db_result
            
            if not db_result['success']:
                return self._format_failure_result('database_setup', db_result)
            
            # Step 5: Validate installation
            logger.info("✅ Step 5: Validating installation...")
            validation_result = self._validate_installation()
            self.setup_results['validation'] = validation_result
            
            total_time = time.time() - start_time
            
            if validation_result['success']:
                logger.info(f"🎉 Project Omega V2 setup completed successfully in {total_time:.1f}s!")
                return {
                    'success': True,
                    'message': 'V2 setup completed successfully',
                    'total_time_seconds': total_time,
                    'environment': self.environment,
                    'results': self.setup_results
                }
            else:
                return self._format_failure_result('validation', validation_result)
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Setup failed with exception: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'failed_at': 'exception',
                'total_time_seconds': total_time,
                'results': self.setup_results
            }
    
    def _validate_environment(self) -> Dict:
        """Validate system environment and requirements"""
        try:
            issues = []
            
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                issues.append(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
            
            # Check if we're in the correct directory
            required_files = ['src/main.py', 'requirements.txt', '.env.example']
            for file in required_files:
                if not (self.project_root / file).exists():
                    issues.append(f"Missing required file: {file}")
            
            # Check write permissions
            try:
                test_file = self.project_root / '.setup_test'
                test_file.write_text('test')
                test_file.unlink()
            except Exception:
                issues.append("No write permission in project directory")
            
            # Check for virtual environment (recommended)
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            if not in_venv:
                logger.warning("⚠️  Not running in a virtual environment (recommended)")
            
            return {
                'success': len(issues) == 0,
                'issues': issues,
                'python_version': f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                'in_virtual_env': in_venv,
                'project_root': str(self.project_root)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issues': [f"Environment validation failed: {str(e)}"]
            }
    
    def _install_dependencies(self) -> Dict:
        """Install Python dependencies"""
        try:
            requirements_file = self.project_root / 'requirements.txt'
            
            if not requirements_file.exists():
                return {
                    'success': False,
                    'error': 'requirements.txt not found'
                }
            
            logger.info("Installing Python packages...")
            
            # Install dependencies
            cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"pip install failed: {result.stderr}",
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            
            # Verify critical imports
            verification_result = self._verify_dependencies()
            
            return {
                'success': verification_result['success'],
                'message': 'Dependencies installed successfully',
                'verification': verification_result,
                'pip_output': result.stdout
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Dependency installation failed: {str(e)}"
            }
    
    def _verify_dependencies(self) -> Dict:
        """Verify that critical dependencies can be imported"""
        critical_imports = [
            'flask',
            'sqlalchemy',
            'flask_sqlalchemy',
            'flask_migrate',
            'requests',
            'pandas',
            'scipy'
        ]
        
        optional_imports = [
            'celery',
            'redis',
            'psycopg2'
        ]
        
        import_results = {}
        
        # Test critical imports
        for module in critical_imports:
            try:
                __import__(module)
                import_results[module] = {'success': True, 'required': True}
            except ImportError as e:
                import_results[module] = {'success': False, 'required': True, 'error': str(e)}
        
        # Test optional imports
        for module in optional_imports:
            try:
                __import__(module)
                import_results[module] = {'success': True, 'required': False}
            except ImportError as e:
                import_results[module] = {'success': False, 'required': False, 'error': str(e)}
        
        # Check if all critical imports succeeded
        critical_failures = [
            module for module, result in import_results.items()
            if result['required'] and not result['success']
        ]
        
        optional_failures = [
            module for module, result in import_results.items()
            if not result['required'] and not result['success']
        ]
        
        success = len(critical_failures) == 0
        
        return {
            'success': success,
            'critical_failures': critical_failures,
            'optional_failures': optional_failures,
            'import_results': import_results
        }
    
    def _generate_configuration(self) -> Dict:
        """Generate .env configuration file"""
        try:
            env_example_file = self.project_root / '.env.example'
            env_file = self.project_root / '.env'
            
            if not env_example_file.exists():
                return {
                    'success': False,
                    'error': '.env.example template not found'
                }
            
            # Check if .env already exists
            env_exists = env_file.exists()
            if env_exists and not self.force_reset:
                logger.info("📁 .env file already exists, skipping configuration generation")
                logger.info("   Use --force-reset to regenerate configuration")
                return {
                    'success': True,
                    'message': '.env file already exists',
                    'action': 'skipped'
                }
            
            # Read template
            template_content = env_example_file.read_text()
            
            # Generate environment-specific configuration
            config_content = self._customize_config_for_environment(template_content)
            
            # Write .env file
            env_file.write_text(config_content)
            
            action = 'regenerated' if env_exists else 'created'
            logger.info(f"✅ Configuration file {action}: .env")
            
            return {
                'success': True,
                'message': f'.env file {action} successfully',
                'action': action,
                'environment': self.environment
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Configuration generation failed: {str(e)}"
            }
    
    def _customize_config_for_environment(self, template_content: str) -> str:
        """Customize configuration template for specific environment"""
        
        # Environment-specific defaults
        if self.environment == 'development':
            replacements = {
                'ENVIRONMENT=development': 'ENVIRONMENT=development',
                'DATABASE_URL=sqlite:///data/omega_v2.db': 'DATABASE_URL=sqlite:///data/omega_v2.db',
                'FLASK_DEBUG=true': 'FLASK_DEBUG=true',
                'LOG_LEVEL=INFO': 'LOG_LEVEL=DEBUG',
                'GENERATE_SAMPLE_DATA=false': 'GENERATE_SAMPLE_DATA=true',
                'AUTO_MIGRATE_ON_STARTUP=true': 'AUTO_MIGRATE_ON_STARTUP=true'
            }
        else:  # production
            replacements = {
                'ENVIRONMENT=development': 'ENVIRONMENT=production',
                'FLASK_DEBUG=true': 'FLASK_DEBUG=false',
                'LOG_LEVEL=INFO': 'LOG_LEVEL=INFO',
                'GENERATE_SAMPLE_DATA=false': 'GENERATE_SAMPLE_DATA=false',
                'AUTO_MIGRATE_ON_STARTUP=true': 'AUTO_MIGRATE_ON_STARTUP=true',
                'FORCE_HTTPS=false': 'FORCE_HTTPS=true'
            }
        
        # Apply replacements
        config_content = template_content
        for old, new in replacements.items():
            config_content = config_content.replace(old, new)
        
        return config_content
    
    def _setup_database(self) -> Dict:
        """Setup database with migrations"""
        try:
            # Import database setup functions
            sys.path.insert(0, str(self.project_root))
            
            try:
                from src.database.init_db import initialize_database
                from src.database.config import DatabaseConfig
            except ImportError as e:
                return {
                    'success': False,
                    'error': f"Failed to import database modules: {str(e)}",
                    'suggestion': 'Ensure dependencies are installed and project structure is correct'
                }
            
            # Initialize database
            logger.info("🔧 Initializing database...")
            
            init_result = initialize_database(
                run_migrations=True,
                seed_data=(self.environment == 'development')
            )
            
            if init_result['success']:
                logger.info("✅ Database setup completed successfully")
                
                # Log setup details
                if 'migration_results' in init_result:
                    migration_results = init_result['migration_results']
                    if migration_results and migration_results.get('success'):
                        applied_count = len([
                            m for m in migration_results.get('applied_migrations', [])
                            if m.get('status') == 'applied'
                        ])
                        if applied_count > 0:
                            logger.info(f"📝 Applied {applied_count} database migrations")
                
                if 'seed_results' in init_result and init_result['seed_results']:
                    seed_results = init_result['seed_results']
                    if seed_results.get('success') and seed_results.get('projects_created', 0) > 0:
                        logger.info(f"🌱 Created {seed_results['projects_created']} sample projects")
                
                return {
                    'success': True,
                    'message': 'Database setup completed successfully',
                    'initialization_result': init_result
                }
            else:
                return {
                    'success': False,
                    'error': init_result.get('error', 'Unknown database setup error'),
                    'initialization_result': init_result
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Database setup failed: {str(e)}"
            }
    
    def _validate_installation(self) -> Dict:
        """Validate complete installation"""
        try:
            validation_results = {}
            
            # Test 1: Import main application
            try:
                sys.path.insert(0, str(self.project_root))
                from src.main import app
                validation_results['app_import'] = {'success': True}
                logger.info("✅ Main application imports successfully")
            except Exception as e:
                validation_results['app_import'] = {'success': False, 'error': str(e)}
                logger.error(f"❌ Main application import failed: {e}")
            
            # Test 2: Database connectivity
            try:
                from src.database.init_db import validate_database_connection
                db_connected = validate_database_connection()
                validation_results['database_connection'] = {'success': db_connected}
                if db_connected:
                    logger.info("✅ Database connection validated")
                else:
                    logger.error("❌ Database connection failed")
            except Exception as e:
                validation_results['database_connection'] = {'success': False, 'error': str(e)}
                logger.error(f"❌ Database validation failed: {e}")
            
            # Test 3: API endpoints accessibility
            try:
                with app.test_client() as client:
                    # Test basic health endpoint
                    response = client.get('/api/v2/health')
                    api_accessible = response.status_code == 200
                    validation_results['api_endpoints'] = {'success': api_accessible, 'status_code': response.status_code}
                    
                    if api_accessible:
                        logger.info("✅ API endpoints accessible")
                    else:
                        logger.error(f"❌ API endpoints not accessible (status: {response.status_code})")
            except Exception as e:
                validation_results['api_endpoints'] = {'success': False, 'error': str(e)}
                logger.error(f"❌ API endpoint test failed: {e}")
            
            # Overall validation
            all_tests_passed = all(
                result.get('success', False) 
                for result in validation_results.values()
            )
            
            return {
                'success': all_tests_passed,
                'validation_results': validation_results,
                'message': 'All validation tests passed' if all_tests_passed else 'Some validation tests failed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Installation validation failed: {str(e)}"
            }
    
    def _format_failure_result(self, failed_step: str, step_result: Dict) -> Dict:
        """Format failure result with helpful information"""
        return {
            'success': False,
            'failed_at': failed_step,
            'error': step_result.get('error', 'Unknown error'),
            'step_result': step_result,
            'results': self.setup_results,
            'suggestion': self._get_failure_suggestion(failed_step, step_result)
        }
    
    def _get_failure_suggestion(self, failed_step: str, step_result: Dict) -> str:
        """Get helpful suggestion based on failure type"""
        suggestions = {
            'environment_validation': "Ensure you're running Python 3.8+ and have write permissions in the project directory.",
            'dependency_installation': "Try running 'pip install -r requirements.txt' manually. Consider using a virtual environment.",
            'configuration': "Check that .env.example exists and you have write permissions. Use --force-reset to regenerate.",
            'database_setup': "Verify database configuration in .env file. Check that database server is running if using PostgreSQL.",
            'validation': "Review the validation results to identify specific issues. Check logs for more details."
        }
        
        return suggestions.get(failed_step, "Check the error details and logs for more information.")

def main():
    """Main entry point for setup script"""
    parser = argparse.ArgumentParser(
        description='Project Omega V2 Setup Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_v2.py                           # Development setup with all features
  python setup_v2.py --environment prod        # Production setup
  python setup_v2.py --skip-deps               # Skip dependency installation
  python setup_v2.py --force-reset             # Force regeneration of configuration
        """
    )
    
    parser.add_argument(
        '--environment',
        choices=['dev', 'development', 'prod', 'production'],
        default='development',
        help='Target environment (default: development)'
    )
    
    parser.add_argument(
        '--skip-deps',
        action='store_true',
        help='Skip dependency installation'
    )
    
    parser.add_argument(
        '--force-reset',
        action='store_true',
        help='Force reset of configuration and database'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Normalize environment name
    if args.environment in ['dev', 'development']:
        environment = 'development'
    else:
        environment = 'production'
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run setup
    setup_manager = OmegaV2Setup(
        environment=environment,
        skip_deps=args.skip_deps,
        force_reset=args.force_reset
    )
    
    result = setup_manager.run_full_setup()
    
    # Print results
    if result['success']:
        print("\n" + "="*60)
        print("🎉 PROJECT OMEGA V2 SETUP COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Environment: {result['environment']}")
        print(f"Setup time: {result['total_time_seconds']:.1f} seconds")
        print("\nNext steps:")
        print("1. Review the generated .env file and update any necessary values")
        print("2. Add your CoinGecko API key to the .env file")
        print("3. Start the application: python src/main.py")
        print("4. Visit http://localhost:5000 to access the application")
        print("5. Check API health: http://localhost:5000/api/v2/health")
        
        # Environment-specific notes
        if environment == 'development':
            print("\nDevelopment Notes:")
            print("- Sample data has been generated for testing")
            print("- Debug mode is enabled")
            print("- Database migrations run automatically on startup")
        else:
            print("\nProduction Notes:")
            print("- Review security settings in .env file")
            print("- Configure proper database connection for production")
            print("- Set up proper secret keys and API keys")
            print("- Consider setting up Redis for background tasks")
        
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ PROJECT OMEGA V2 SETUP FAILED")
        print("="*60)
        print(f"Failed at: {result['failed_at']}")
        print(f"Error: {result['error']}")
        if 'suggestion' in result:
            print(f"Suggestion: {result['suggestion']}")
        
        print(f"\nFor more details, check the logs above.")
        sys.exit(1)

if __name__ == '__main__':
    main()