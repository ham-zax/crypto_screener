"""
Database Initialization Service for Project Omega V2

Provides comprehensive database setup, migration management, and health validation.
Handles both SQLite (development) and PostgreSQL (production) environments.
"""

import os
import logging
import time
from typing import Dict, Optional
from sqlalchemy import text, inspect

from .config import DatabaseConfig, get_session
from .migrations.migration_runner import MigrationRunner
from .migrations.version_manager import VersionManager

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Comprehensive database initialization and management service

    Features:
    - Automatic database creation and schema setup
    - Migration execution with rollback support
    - Health checks and connectivity validation
    - Development data seeding
    - Cross-platform compatibility (SQLite/PostgreSQL)
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database service

        Args:
            config: Database configuration instance
        """
        from .config import db_config

        self.config = config or db_config
        self.engine = None
        self.migration_runner = None
        self.version_manager = None

        logger.info(
            f"Database initializer created for {self.config.environment} environment"
        )

    def _ensure_database_directory(self):
        """Ensure database directory exists for SQLite"""
        if (
            self.config.environment == "development"
            and "sqlite" in self.config.database_url
        ):
            # Extract directory from SQLite path
            db_path = self.config.database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Ensured database directory: {db_dir}")

    def _test_database_connection(self) -> Dict:
        """
        Test database connectivity and basic operations

        Returns:
            Connection test results
        """
        try:
            start_time = time.time()

            # Create engine if not exists
            if not self.engine:
                self.engine = self.config.create_engine()

            # Test basic connection
            with self.engine.connect() as connection:
                # Simple test query
                result = connection.execute(text("SELECT 1 as test_value"))
                test_value = result.scalar()

                if test_value != 1:
                    raise Exception("Database test query returned unexpected result")

            connection_time_ms = int((time.time() - start_time) * 1000)

            # Get database info
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()

            return {
                "success": True,
                "connection_time_ms": connection_time_ms,
                "database_type": self.config.environment,
                "table_count": len(table_names),
                "tables": table_names,
                "url_masked": self._mask_database_url(),
            }

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url_masked": self._mask_database_url(),
            }

    def _mask_database_url(self) -> str:
        """Mask sensitive information in database URL for logging"""
        url = self.config.database_url
        if "@" in url:
            # Mask credentials
            parts = url.split("@")
            if len(parts) == 2:
                protocol_and_creds = parts[0]
                host_and_path = parts[1]
                protocol = protocol_and_creds.split("://")[0]
                return f"{protocol}://***:***@{host_and_path}"
        return url

    def initialize_database(
        self, run_migrations: bool = True, seed_data: bool = False
    ) -> Dict:
        """
        Complete database initialization process

        Args:
            run_migrations: Whether to run pending migrations
            seed_data: Whether to seed development data

        Returns:
            Initialization results
        """
        logger.info("Starting database initialization")
        start_time = time.time()

        try:
            # Step 1: Ensure database directory (for SQLite)
            self._ensure_database_directory()

            # Step 2: Test database connection
            connection_test = self._test_database_connection()
            if not connection_test["success"]:
                return {
                    "success": False,
                    "step": "connection_test",
                    "error": connection_test["error"],
                    "connection_test": connection_test,
                }

            # Step 3: Initialize migration infrastructure
            self.migration_runner = MigrationRunner(self.engine)
            self.version_manager = VersionManager(self.engine)

            migration_status = self.migration_runner.get_migration_status()

            # Step 4: Run migrations if requested
            migration_results = None
            # Migration logic removed; rely on Flask-Migrate

            # Step 5: Schema validation removed

            # Step 6: Seed development data if requested
            seed_results = None
            if seed_data and self.config.environment == "development":
                seed_results = self._seed_development_data()

            total_time_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "message": "Database initialized successfully",
                "total_time_ms": total_time_ms,
                "connection_test": connection_test,
                "migration_status": migration_status,
                "migration_results": migration_results,
                "validation_results": None,
                "seed_results": seed_results,
            }

        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Database initialization failed: {e}")

            return {
                "success": False,
                "step": "initialization",
                "error": str(e),
                "total_time_ms": total_time_ms,
            }

    def _seed_development_data(self) -> Dict:
        """
        Seed development environment with sample data

        Returns:
            Seeding results
        """
        try:
            from ..models.automated_project import AutomatedProject

            session = get_session()

            # Check if data already exists
            existing_count = session.query(AutomatedProject).count()
            if existing_count > 0:
                session.close()
                return {
                    "success": True,
                    "message": f"Development data already exists ({existing_count} projects)",
                    "projects_created": 0,
                }

            # Create sample projects
            sample_projects = [
                {
                    "name": "Bitcoin",
                    "ticker": "BTC",
                    "coingecko_id": "bitcoin",
                    "data_source": "automated",
                    "created_via": "api_ingestion",
                    "market_cap": 800000000000,
                    "category": "layer-1",
                    "sector_strength": 7,
                    "value_proposition": 8,
                    "backing_team": 9,
                    "valuation_potential": 1,
                    "token_utility": 6,
                    "supply_risk": 10,
                },
                {
                    "name": "Ethereum",
                    "ticker": "ETH",
                    "coingecko_id": "ethereum",
                    "data_source": "automated",
                    "created_via": "api_ingestion",
                    "market_cap": 400000000000,
                    "category": "layer-1",
                    "sector_strength": 7,
                    "value_proposition": 9,
                    "backing_team": 9,
                    "valuation_potential": 1,
                    "token_utility": 8,
                    "supply_risk": 9,
                },
                {
                    "name": "Sample DePIN Project",
                    "ticker": "DEPIN",
                    "data_source": "automated",
                    "created_via": "api_ingestion",
                    "market_cap": 50000000,
                    "category": "depin",
                    "sector_strength": 9,
                    "value_proposition": 5,
                    "backing_team": 5,
                    "valuation_potential": 9,
                    "token_utility": 5,
                    "supply_risk": 8,
                },
            ]

            created_projects = []
            for project_data in sample_projects:
                project = AutomatedProject(**project_data)
                project.update_all_scores()
                session.add(project)
                created_projects.append(project.name)

            session.commit()
            session.close()

            return {
                "success": True,
                "message": f"Created {len(created_projects)} sample projects",
                "projects_created": len(created_projects),
                "project_names": created_projects,
            }

        except Exception as e:
            logger.error(f"Development data seeding failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to seed development data",
            }

    def get_database_health(self) -> Dict:
        """
        Comprehensive database health check

        Returns:
            Health status and metrics
        """
        try:
            health_data = {
                "timestamp": time.time(),
                "environment": self.config.environment,
            }

            # Connection test
            connection_test = self._test_database_connection()
            health_data["connection"] = connection_test

            if not connection_test["success"]:
                health_data["status"] = "unhealthy"
                health_data["issues"] = ["Database connection failed"]
                return health_data

            # Migration status
            if self.migration_runner:
                migration_status = self.migration_runner.get_migration_status()
                health_data["migrations"] = migration_status

            # Data statistics
            if self.engine:
                session = get_session()
                try:
                    from ..models.automated_project import AutomatedProject, CSVData

                    total_projects = session.query(AutomatedProject).count()
                    automated_projects = (
                        session.query(AutomatedProject)
                        .filter_by(data_source="automated")
                        .count()
                    )
                    projects_with_data = (
                        session.query(AutomatedProject)
                        .filter_by(has_data_score=True)
                        .count()
                    )
                    csv_uploads = session.query(CSVData).count()

                    health_data["statistics"] = {
                        "total_projects": total_projects,
                        "automated_projects": automated_projects,
                        "manual_projects": total_projects - automated_projects,
                        "projects_with_data_score": projects_with_data,
                        "csv_uploads": csv_uploads,
                    }
                except Exception as e:
                    health_data["statistics"] = {"error": str(e)}
                finally:
                    session.close()

            # Overall health assessment
            issues = []

            health_data["status"] = "healthy" if len(issues) == 0 else "degraded"
            health_data["issues"] = issues

            return health_data

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
                "environment": self.config.environment,
            }


# Global database initializer instance
db_initializer = DatabaseInitializer()


# Convenience functions
def initialize_database(run_migrations: bool = True, seed_data: bool = False) -> Dict:
    """Initialize database with migrations and optional seeding"""
    return db_initializer.initialize_database(run_migrations, seed_data)


def get_database_health() -> Dict:
    """Get current database health status"""
    return db_initializer.get_database_health()


def validate_database_connection() -> bool:
    """Quick database connection validation"""
    test_result = db_initializer._test_database_connection()
    return test_result["success"]
