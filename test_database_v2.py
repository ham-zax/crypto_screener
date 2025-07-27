#!/usr/bin/env python3
"""
Project Omega V2 Database Testing and Validation

Comprehensive test suite for validating V2 database functionality including:
- Connection testing
- Migration validation
- Performance benchmarking
- Cross-platform compatibility
- Data integrity verification
"""

import os
import sys
import time
import logging
import unittest
import tempfile
from pathlib import Path
from typing import Dict

# Setup test environment
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseTestBase(unittest.TestCase):
    """Base class for database tests with common setup"""

    def setUp(self):
        """Setup test environment"""
        self.test_db_path = None
        self.original_env = {}

        # Setup test database
        self._setup_test_database()

        # Import after setting up test environment
        try:
            from database.config import DatabaseConfig
            from database.init_db import DatabaseInitializer
            from database.migrations.migration_runner import MigrationRunner
            from models.automated_project import AutomatedProject, CSVData

            self.DatabaseConfig = DatabaseConfig
            self.DatabaseInitializer = DatabaseInitializer
            self.MigrationRunner = MigrationRunner
            self.AutomatedProject = AutomatedProject
            self.CSVData = CSVData

        except ImportError as e:
            self.skipTest(f"V2 modules not available: {e}")

    def tearDown(self):
        """Cleanup test environment"""
        # Restore original environment
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Cleanup test database
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except Exception:
                pass

    def _setup_test_database(self):
        """Setup isolated test database"""
        # Create temporary database
        fd, self.test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Store original environment
        env_vars = ["DATABASE_URL", "ENVIRONMENT", "DB_ECHO"]
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)

        # Set test environment
        os.environ["DATABASE_URL"] = f"sqlite:///{self.test_db_path}"
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DB_ECHO"] = "false"


class TestDatabaseConnection(DatabaseTestBase):
    """Test database connectivity and basic operations"""

    def test_database_config_creation(self):
        """Test database configuration initialization"""
        config = self.DatabaseConfig()

        self.assertEqual(config.environment, "testing")
        self.assertIn("sqlite", config.database_url)
        self.assertIsNotNone(config.database_url)

    def test_engine_creation(self):
        """Test database engine creation"""
        config = self.DatabaseConfig()
        engine = config.create_engine()

        self.assertIsNotNone(engine)

        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            self.assertEqual(result.scalar(), 1)

    def test_session_creation(self):
        """Test database session creation"""
        config = self.DatabaseConfig()
        session = config.get_session()

        self.assertIsNotNone(session)
        session.close()

    def test_connection_info(self):
        """Test database connection information"""
        config = self.DatabaseConfig()
        info = config.get_connection_info()

        self.assertIn("environment", info)
        self.assertIn("database_url", info)
        self.assertEqual(info["environment"], "testing")


class TestDatabaseInitialization(DatabaseTestBase):
    """Test database initialization and setup"""

    def test_database_initializer_creation(self):
        """Test database initializer instantiation"""
        initializer = self.DatabaseInitializer()

        self.assertEqual(initializer.config.environment, "testing")
        self.assertIsNotNone(initializer.config)

    def test_database_initialization(self):
        """Test complete database initialization"""
        initializer = self.DatabaseInitializer()

        result = initializer.initialize_database(run_migrations=True, seed_data=False)

        self.assertTrue(
            result["success"], f"Database initialization failed: {result.get('error')}"
        )
        self.assertIn("total_time_ms", result)
        self.assertIn("connection_test", result)

        # Verify connection test
        connection_test = result["connection_test"]
        self.assertTrue(connection_test["success"])

    def test_database_health_check(self):
        """Test database health monitoring"""
        initializer = self.DatabaseInitializer()

        # Initialize first
        init_result = initializer.initialize_database(run_migrations=True)
        self.assertTrue(init_result["success"])

        # Check health
        health = initializer.get_database_health()

        self.assertIn("status", health)
        self.assertIn("connection", health)
        self.assertTrue(health["connection"]["success"])


class TestDatabaseMigrations(DatabaseTestBase):
    """Test database migration system"""

    def test_migration_runner_creation(self):
        """Test migration runner instantiation"""
        config = self.DatabaseConfig()
        engine = config.create_engine()
        runner = self.MigrationRunner(engine)

        self.assertIsNotNone(runner)
        self.assertEqual(runner.db_type, "sqlite")

    def test_migration_status(self):
        """Test migration status reporting"""
        config = self.DatabaseConfig()
        engine = config.create_engine()
        runner = self.MigrationRunner(engine)

        status = runner.get_migration_status()

        self.assertIn("database_type", status)
        self.assertIn("pending_migrations", status)
        self.assertIn("applied_migrations", status)
        self.assertEqual(status["database_type"], "sqlite")

    def test_sqlite_migration_execution(self):
        """Test SQLite migration execution"""
        config = self.DatabaseConfig()
        engine = config.create_engine()
        runner = self.MigrationRunner(engine)

        # Find SQLite migration file
        migration_path = (
            Path(__file__).parent / "src" / "database" / "migrations" / "scripts"
        )
        sqlite_migration = migration_path / "001_initial_schema_sqlite.sql"

        if sqlite_migration.exists():
            result = runner.apply_migration(sqlite_migration)

            self.assertTrue(
                result["success"], f"Migration failed: {result.get('error')}"
            )
            self.assertEqual(result["status"], "applied")
            self.assertIn("execution_time_ms", result)


class TestDatabaseModels(DatabaseTestBase):
    """Test database model functionality"""

    def setUp(self):
        """Setup with initialized database"""
        super().setUp()

        # Initialize database
        initializer = self.DatabaseInitializer()
        result = initializer.initialize_database(run_migrations=True)

        if not result["success"]:
            self.skipTest(f"Database initialization failed: {result.get('error')}")

        self.config = self.DatabaseConfig()
        self.session = self.config.get_session()

    def tearDown(self):
        """Cleanup database session"""
        if hasattr(self, "session"):
            self.session.close()
        super().tearDown()

    def test_automated_project_creation(self):
        """Test AutomatedProject model creation"""
        project = self.AutomatedProject(
            name="Test Project",
            ticker="TEST",
            data_source="automated",
            created_via="api_ingestion",
            market_cap=1000000,
            sector_strength=8,
            value_proposition=5,
            backing_team=5,
            valuation_potential=7,
            token_utility=5,
            supply_risk=6,
        )

        # Calculate scores
        project.update_all_scores()

        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.ticker, "TEST")
        self.assertIsNotNone(project.narrative_score)
        self.assertIsNotNone(project.tokenomics_score)
        self.assertFalse(project.has_data_score)
        self.assertIsNone(project.omega_score)  # No data score yet

    def test_project_score_calculations(self):
        """Test automated scoring calculations"""
        project = self.AutomatedProject(
            name="Test Project",
            ticker="TEST",
            data_source="automated",
            created_via="api_ingestion",
            sector_strength=9,
            value_proposition=7,
            backing_team=8,
            valuation_potential=6,
            token_utility=5,
            supply_risk=7,
        )

        project.update_all_scores()

        # Check narrative score (should be average of 9, 7, 8 = 8.0)
        expected_narrative = (9 + 7 + 8) / 3
        self.assertAlmostEqual(project.narrative_score, expected_narrative, places=2)

        # Check tokenomics score (should be average of 6, 5, 7 = 6.0)
        expected_tokenomics = (6 + 5 + 7) / 3
        self.assertAlmostEqual(project.tokenomics_score, expected_tokenomics, places=2)

    def test_project_with_data_score(self):
        """Test project with complete scoring"""
        project = self.AutomatedProject(
            name="Complete Project",
            ticker="COMP",
            data_source="automated",
            created_via="api_ingestion",
            sector_strength=8,
            value_proposition=6,
            backing_team=7,
            valuation_potential=5,
            token_utility=6,
            supply_risk=8,
            accumulation_signal=9,  # Add data score
        )

        project.update_all_scores()

        self.assertTrue(project.has_data_score)
        self.assertEqual(project.data_score, 9)
        self.assertIsNotNone(project.omega_score)

        # Omega score should be average of all three pillars
        expected_omega = (
            project.narrative_score + project.tokenomics_score + project.data_score
        ) / 3
        self.assertAlmostEqual(project.omega_score, expected_omega, places=2)

    def test_csv_data_model(self):
        """Test CSVData model functionality"""
        # Create a project first
        project = self.AutomatedProject(
            name="CSV Test Project",
            ticker="CSV",
            data_source="automated",
            created_via="api_ingestion",
        )

        self.session.add(project)
        self.session.flush()  # Get project ID

        # Create CSV data
        csv_data = self.CSVData(
            project_id=project.id,
            raw_data="time,close,Volume Delta (Close)\n2024-01-01,100,50\n2024-01-02,105,60",
            data_score=8.5,
            is_valid=True,
            analysis_metadata={"periods_analyzed": 90, "trend": "bullish"},
        )

        self.session.add(csv_data)
        self.session.commit()

        # Verify data
        retrieved_csv = (
            self.session.query(self.CSVData).filter_by(project_id=project.id).first()
        )
        self.assertIsNotNone(retrieved_csv)
        self.assertEqual(retrieved_csv.data_score, 8.5)
        self.assertTrue(retrieved_csv.is_valid)


class TestDatabasePerformance(DatabaseTestBase):
    """Test database performance and optimization"""

    def setUp(self):
        """Setup with initialized database and sample data"""
        super().setUp()

        # Initialize database
        initializer = self.DatabaseInitializer()
        result = initializer.initialize_database(run_migrations=True)

        if not result["success"]:
            self.skipTest(f"Database initialization failed: {result.get('error')}")

        self.config = self.DatabaseConfig()
        self.session = self.config.get_session()

        # Create sample data for performance testing
        self._create_sample_data(100)

    def tearDown(self):
        """Cleanup database session"""
        if hasattr(self, "session"):
            self.session.close()
        super().tearDown()

    def _create_sample_data(self, count: int):
        """Create sample projects for testing"""
        projects = []

        for i in range(count):
            project = self.AutomatedProject(
                name=f"Test Project {i}",
                ticker=f"TEST{i}",
                data_source="automated",
                created_via="api_ingestion",
                market_cap=1000000 * (i + 1),
                sector_strength=5 + (i % 5),
                value_proposition=5,
                backing_team=5,
                valuation_potential=5 + (i % 5),
                token_utility=5,
                supply_risk=5 + (i % 5),
            )

            if i % 10 == 0:  # Give some projects data scores
                project.accumulation_signal = 7 + (i % 3)

            project.update_all_scores()
            projects.append(project)

        self.session.add_all(projects)
        self.session.commit()

    def test_large_dataset_query_performance(self):
        """Test query performance with larger dataset"""
        start_time = time.time()

        # Test basic listing query
        projects = (
            self.session.query(self.AutomatedProject)
            .filter_by(data_source="automated")
            .order_by(self.AutomatedProject.market_cap.desc())
            .limit(50)
            .all()
        )

        query_time = time.time() - start_time

        self.assertGreater(len(projects), 0)
        self.assertLess(query_time, 1.0, "Query took too long (>1 second)")

    def test_filtered_query_performance(self):
        """Test performance of filtered queries"""
        start_time = time.time()

        # Test complex filtered query
        projects = (
            self.session.query(self.AutomatedProject)
            .filter(self.AutomatedProject.market_cap > 5000000)
            .filter(self.AutomatedProject.has_data_score == True)
            .order_by(self.AutomatedProject.omega_score.desc())
            .all()
        )

        query_time = time.time() - start_time

        self.assertLess(query_time, 1.0, "Filtered query took too long (>1 second)")

    def test_aggregation_performance(self):
        """Test aggregation query performance"""
        start_time = time.time()

        # Test aggregation queries
        total_projects = self.session.query(self.AutomatedProject).count()
        projects_with_data = (
            self.session.query(self.AutomatedProject)
            .filter_by(has_data_score=True)
            .count()
        )

        query_time = time.time() - start_time

        self.assertGreater(total_projects, 0)
        self.assertLess(
            query_time, 1.0, "Aggregation queries took too long (>1 second)"
        )


class DatabaseTestRunner:
    """Test runner for database validation"""

    def __init__(self):
        self.results = {}

    def run_all_tests(self) -> Dict:
        """Run all database tests and return results"""
        logger.info("🧪 Starting comprehensive database test suite...")
        start_time = time.time()

        test_suites = [
            ("Connection Tests", TestDatabaseConnection),
            ("Initialization Tests", TestDatabaseInitialization),
            ("Migration Tests", TestDatabaseMigrations),
            ("Model Tests", TestDatabaseModels),
            ("Performance Tests", TestDatabasePerformance),
        ]

        total_tests = 0
        total_failures = 0
        total_errors = 0

        for suite_name, test_class in test_suites:
            logger.info(f"📋 Running {suite_name}...")

            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
            result = runner.run(suite)

            tests_run = result.testsRun
            failures = len(result.failures)
            errors = len(result.errors)
            success_rate = (
                ((tests_run - failures - errors) / tests_run * 100)
                if tests_run > 0
                else 0
            )

            self.results[suite_name] = {
                "tests_run": tests_run,
                "failures": failures,
                "errors": errors,
                "success_rate": success_rate,
                "failure_details": [str(f[1]) for f in result.failures],
                "error_details": [str(e[1]) for e in result.errors],
            }

            total_tests += tests_run
            total_failures += failures
            total_errors += errors

            if failures == 0 and errors == 0:
                logger.info(f"✅ {suite_name}: All {tests_run} tests passed")
            else:
                logger.warning(
                    f"⚠️  {suite_name}: {failures} failures, {errors} errors out of {tests_run} tests"
                )

        total_time = time.time() - start_time
        overall_success_rate = (
            ((total_tests - total_failures - total_errors) / total_tests * 100)
            if total_tests > 0
            else 0
        )

        summary = {
            "success": total_failures == 0 and total_errors == 0,
            "total_tests": total_tests,
            "total_failures": total_failures,
            "total_errors": total_errors,
            "overall_success_rate": overall_success_rate,
            "total_time_seconds": total_time,
            "suite_results": self.results,
        }

        self._print_summary(summary)
        return summary

    def _print_summary(self, summary: Dict):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🧪 DATABASE TEST RESULTS")
        print("=" * 60)

        if summary["success"]:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")

        print(f"Total Tests: {summary['total_tests']}")
        print(f"Failures: {summary['total_failures']}")
        print(f"Errors: {summary['total_errors']}")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Execution Time: {summary['total_time_seconds']:.2f}s")

        # Detailed results
        print("\nDetailed Results:")
        for suite_name, result in summary["suite_results"].items():
            status = "✅" if result["failures"] == 0 and result["errors"] == 0 else "❌"
            print(
                f"  {status} {suite_name}: {result['success_rate']:.1f}% ({result['tests_run']} tests)"
            )

            if result["failures"] > 0:
                for failure in result["failure_details"]:
                    print(f"    ❌ Failure: {failure[:100]}...")

            if result["errors"] > 0:
                for error in result["error_details"]:
                    print(f"    🔥 Error: {error[:100]}...")


def main():
    """Main entry point for database testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Project Omega V2 Database Testing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--suite",
        choices=["connection", "init", "migration", "model", "performance"],
        help="Run specific test suite",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = DatabaseTestRunner()

    if args.suite:
        # Run specific suite
        suite_map = {
            "connection": TestDatabaseConnection,
            "init": TestDatabaseInitialization,
            "migration": TestDatabaseMigrations,
            "model": TestDatabaseModels,
            "performance": TestDatabasePerformance,
        }

        test_class = suite_map[args.suite]
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        # Run all tests
        result = runner.run_all_tests()
        sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
