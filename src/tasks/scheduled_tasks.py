"""
Scheduled Tasks for Project Omega V2
Background tasks for data fetching, cleanup, and monitoring

Implements Celery tasks for:
- Daily cryptocurrency data fetch
- Periodic data cleanup
- System health monitoring
- Test tasks for validation
"""

import os
from dotenv import load_dotenv

load_dotenv()
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)
from typing import Dict, Any, Optional

# Import Celery app
from .celery_config import celery_app

logger = logging.getLogger(__name__)


# Task Decorators and Configuration
def _core_fetch_and_save_logic(
    filters: dict, save_to_database: bool, batch_size: int
) -> dict:
    """
    Core business logic for fetching and saving cryptocurrency projects.
    This function is independent of Celery and can be called directly.
    """
    import os
    import logging
    from datetime import datetime
    from src.api.data_fetcher import ProjectIngestionManager
    from src.models.automated_project import AutomatedProject
    from src.database.config import db_config

    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()

    # Check if V2 dependencies are available
    from src.tasks.scheduled_tasks import _check_v2_dependencies

    if not _check_v2_dependencies():
        error_msg = "V2 dependencies not available for task execution"
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg, "duration": 0}

    # Initialize services
    api_key = os.getenv("COINGECKO_API_KEY")

    # DEBUG: Log API key information in task context
    logger.info(
        f"[DEBUG] Task context - COINGECKO_API_KEY loaded: {api_key is not None}"
    )
    if api_key:
        logger.info(f"[DEBUG] Task context - COINGECKO_API_KEY length: {len(api_key)}")
        logger.info(
            f"[DEBUG] Task context - COINGECKO_API_KEY prefix: {api_key[:10]}..."
        )
    else:
        logger.warning("[DEBUG] Task context - COINGECKO_API_KEY is None or empty!")

    ingestion_manager = ProjectIngestionManager(api_key=api_key)

    # Apply default filters if none provided
    if filters is None:
        filters = {
            "min_market_cap": 1_000_000,
            "max_results": 1000,
            "min_volume_24h": 100_000,
        }

    logger.info(f"Fetching projects with filters: {filters}")

    # Run full ingestion
    result = ingestion_manager.run_full_ingestion(
        filters=filters, task_id=None, batch_size=batch_size
    )
    projects = result["projects"]
    ingestion_record = result["ingestion_record"]

    logger.info(f"Fetched {len(projects)} projects")

    # Save to database if requested and available
    saved_count = 0
    updated_count = 0

    if save_to_database and len(projects) > 0:
        logger.info("Saving projects to database...")

        # Process projects in batches
        session = db_config.get_session()
        try:
            # --- BEGIN N+1 ELIMINATION ---
            # Gather all coingecko_ids from all projects
            project_ids_from_api = [
                p["coingecko_id"] for p in projects if p.get("coingecko_id")
            ]
            # Fetch all existing projects in one query
            existing_projects_query = session.query(AutomatedProject).filter(
                AutomatedProject.coingecko_id.in_(project_ids_from_api)
            )
            # Build a map for fast lookup
            existing_projects_map = {p.coingecko_id: p for p in existing_projects_query}
            # --- END N+1 ELIMINATION ---
            for i in range(0, len(projects), batch_size):
                batch = projects[i : i + batch_size]

                for project_data in batch:
                    try:
                        # Log each coin being processed
                        logger.info(
                            f"Processing coin: coingecko_id={project_data.get('coingecko_id', 'unknown')}, "
                            f"name={project_data.get('name', 'unknown')}, "
                            f"symbol={project_data.get('symbol', 'unknown')}"
                        )
                        # Use map lookup instead of per-project query
                        existing = existing_projects_map.get(
                            project_data.get("coingecko_id")
                        )

                        if existing:
                            # Update existing project (preserve data score)
                            old_data_score = existing.data_score
                            old_accumulation_signal = existing.accumulation_signal
                            old_has_data_score = existing.has_data_score

                            for key, value in project_data.items():
                                if hasattr(existing, key) and key not in [
                                    "id",
                                    "data_score",
                                    "accumulation_signal",
                                    "has_data_score",
                                ]:
                                    setattr(existing, key, value)

                            # Restore data score components
                            existing.data_score = old_data_score
                            existing.accumulation_signal = old_accumulation_signal
                            existing.has_data_score = old_has_data_score

                            from src.services import project_service

                            project_service.update_all_scores(existing)
                            logger.info(
                                f"[DEBUG] Updated all scores for existing project {existing.id} in fetch_and_update_projects"
                            )
                            updated_count += 1
                        else:
                            # Create new project
                            new_project = AutomatedProject(**project_data)
                            from src.services import project_service

                            project_service.update_all_scores(new_project)
                            logger.info(
                                f"[DEBUG] Updated all scores for new project {getattr(new_project, 'id', 'unknown')} in fetch_and_update_projects"
                            )
                            session.add(new_project)
                            saved_count += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to save project {project_data.get('coingecko_id', 'unknown')}: {e}"
                        )
                        continue

                # Commit batch
                session.commit()

            logger.info(
                f"Database update completed: {saved_count} new, {updated_count} updated"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Database batch operation failed: {e}")
            raise
        finally:
            session.close()

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Return success result
    result = {
        "status": "success",
        "projects_fetched": len(projects),
        "projects_saved": saved_count,
        "projects_updated": updated_count,
        "duration": round(duration, 2),
        "ingestion_record": ingestion_record,
        "filters_applied": filters,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(f"Core logic completed successfully in {duration:.1f}s")
    return result


@celery_app.task(bind=True, name="src.tasks.scheduled_tasks.fetch_and_update_projects")
def fetch_and_update_projects(
    self,
    filters: Optional[Dict[str, Any]] = None,
    save_to_database: bool = True,
    batch_size: int = 250,
):
    """
    Scheduled task to fetch and update cryptocurrency projects (Celery wrapper)
    """
    task_id = self.request.id
    logger.info(f"Starting fetch_and_update_projects task {task_id}")

    start_time = datetime.utcnow()

    try:
        # Update task state: fetching
        effective_filters = (
            filters
            if filters is not None
            else {
                "min_market_cap": 1_000_000,
                "max_results": 1000,
                "min_volume_24h": 100_000,
            }
        )
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": effective_filters.get("max_results", 1000),
                "status": "Fetching market data...",
            },
        )

        # Call core business logic
        result = _core_fetch_and_save_logic(
            filters
            if filters is not None
            else {
                "min_market_cap": 1_000_000,
                "max_results": 1000,
                "min_volume_24h": 100_000,
            },
            save_to_database,
            batch_size,
        )

        # If saving, update progress after each batch is not possible here (handled in core logic)
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Attach task_id and duration to result
        result["task_id"] = task_id
        result["duration"] = round(duration, 2)
        result["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Task {task_id} completed successfully in {duration:.1f}s")
        return result

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Task failed: {str(e)}"
        logger.error(f"Task {task_id} failed: {e}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2**self.request.retries), exc=e)

        return {
            "status": "failed",
            "task_id": task_id,
            "error": error_msg,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task(bind=True, name="src.tasks.scheduled_tasks.cleanup_old_data")
def cleanup_old_data(self, days_to_keep: int = 30):
    """
    Scheduled task to cleanup old data and logs

    Args:
        days_to_keep: Number of days of data to retain

    Returns:
        Cleanup results
    """
    task_id = self.request.id
    logger.info(f"Starting cleanup_old_data task {task_id}")

    start_time = datetime.utcnow()
    cutoff_date = start_time - timedelta(days=days_to_keep)

    try:
        # Check if V2 dependencies are available
        if not _check_v2_dependencies():
            error_msg = "V2 dependencies not available for cleanup task"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg, "task_id": task_id}

        from ..models.automated_project import CSVData
        from ..database.config import db_config

        session = db_config.get_session()
        cleanup_results = {
            "csv_data_removed": 0,
            "old_projects_cleaned": 0,
            "log_files_cleaned": 0,
        }

        try:
            # Update task state
            self.update_state(
                state="PROGRESS", meta={"status": "Cleaning up old CSV data..."}
            )

            # Cleanup old CSV data that's no longer valid
            old_csv_query = session.query(CSVData).filter(
                CSVData.analyzed_at < cutoff_date, CSVData.is_valid == False
            )
            old_csv_count = old_csv_query.count()
            old_csv_query.delete()
            cleanup_results["csv_data_removed"] = old_csv_count

            session.commit()
            logger.info(f"Removed {old_csv_count} old CSV records")

            # Update task state
            self.update_state(
                state="PROGRESS", meta={"status": "Cleaning up log files..."}
            )

            # Cleanup old log files
            log_files_cleaned = _cleanup_log_files(cutoff_date)
            cleanup_results["log_files_cleaned"] = log_files_cleaned

            duration = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "status": "success",
                "task_id": task_id,
                "cleanup_results": cleanup_results,
                "cutoff_date": cutoff_date.isoformat(),
                "duration": round(duration, 2),
                "completed_at": datetime.utcnow().isoformat(),
            }

            logger.info(f"Cleanup task {task_id} completed successfully")
            return result

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Cleanup task failed: {str(e)}"
        logger.error(f"Cleanup task {task_id} failed: {e}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying cleanup task {task_id}")
            raise self.retry(countdown=300, exc=e)  # 5 minute retry delay

        return {
            "status": "failed",
            "task_id": task_id,
            "error": error_msg,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task(bind=True, name="src.tasks.scheduled_tasks.health_check_task")
def health_check_task(self):
    """
    Scheduled task for system health monitoring

    Returns:
        System health status
    """
    task_id = self.request.id
    logger.info(f"Starting health_check_task {task_id}")

    start_time = datetime.utcnow()
    health_status = {
        "task_id": task_id,
        "timestamp": start_time.isoformat(),
        "components": {},
    }

    try:
        # Check Redis connection
        self.update_state(
            state="PROGRESS", meta={"status": "Checking Redis connection..."}
        )

        from .celery_config import test_redis_connection

        redis_status = test_redis_connection()
        health_status["components"]["redis"] = {
            "status": "healthy" if redis_status else "unhealthy",
            "details": "Redis connection successful"
            if redis_status
            else "Redis connection failed",
        }

        # Check database connection
        self.update_state(
            state="PROGRESS", meta={"status": "Checking database connection..."}
        )

        if _check_v2_dependencies():
            try:
                from ..database.config import db_config

                session = db_config.get_session()
                from sqlalchemy import text

                session.execute(text("SELECT 1"))
                session.close()

                health_status["components"]["database"] = {
                    "status": "healthy",
                    "details": "Database connection successful",
                }
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "details": f"Database connection failed: {e}",
                }
        else:
            health_status["components"]["database"] = {
                "status": "unavailable",
                "details": "V2 dependencies not available",
            }

        # Check API services
        self.update_state(state="PROGRESS", meta={"status": "Checking API services..."})

        # CoinGecko API health check
        try:
            from ..api.coingecko import CoinGeckoClient

            cg_api_key = os.getenv("COINGECKO_API_KEY")
            cg_client = CoinGeckoClient(api_key=cg_api_key)
            cg_client.get_markets_data(per_page=1, page=1)
            health_status["components"]["coingecko_api"] = {
                "status": "healthy",
                "details": "CoinGecko API accessible",
            }
        except Exception as e:
            health_status["components"]["coingecko_api"] = {
                "status": "degraded",
                "details": f"CoinGecko API issues: {e}",
            }

        # CoinMarketCap API health check
        try:
            from ..api.coinmarketcap import CoinMarketCapClient

            cmc_api_key = os.getenv("COINMARKETCAP_API_KEY")
            cmc_client = CoinMarketCapClient(api_key=cmc_api_key)
            cmc_client.get_listings_latest(limit=1)
            health_status["components"]["coinmarketcap_api"] = {
                "status": "healthy",
                "details": "CoinMarketCap API accessible",
            }
        except Exception as e:
            health_status["components"]["coinmarketcap_api"] = {
                "status": "degraded",
                "details": f"CoinMarketCap API issues: {e}",
            }

        # Overall health determination
        component_statuses = [
            comp["status"] for comp in health_status["components"].values()
        ]
        if all(status in ["healthy", "degraded"] for status in component_statuses):
            overall_status = "healthy"
        elif any(status == "healthy" for status in component_statuses):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "status": "success",
            "overall_health": overall_status,
            "health_details": health_status,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Health check {task_id} completed: {overall_status}")
        return result

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Health check failed: {str(e)}"
        logger.error(f"Health check {task_id} failed: {e}")

        return {
            "status": "failed",
            "overall_health": "unhealthy",
            "error": error_msg,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task(bind=True, name="src.tasks.scheduled_tasks.test_task")
def test_task(self, message: str = "Test task executed"):
    """
    Test task for validation and debugging

    Args:
        message: Test message to include in result

    Returns:
        Test execution result
    """
    task_id = self.request.id
    logger.info(f"Starting test_task {task_id}: {message}")

    start_time = datetime.utcnow()

    try:
        # Simulate some work
        import time

        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing test task...", "message": message},
        )

        time.sleep(2)  # Simulate 2 seconds of work

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "status": "success",
            "task_id": task_id,
            "message": message,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
            "worker_info": {
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "pid": os.getpid(),
            },
        }

        logger.info(f"Test task {task_id} completed successfully")
        return result

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Test task failed: {str(e)}"
        logger.error(f"Test task {task_id} failed: {e}")

        return {
            "status": "failed",
            "task_id": task_id,
            "error": error_msg,
            "duration": round(duration, 2),
            "completed_at": datetime.utcnow().isoformat(),
        }


# Helper Functions


def _check_v2_dependencies() -> bool:
    """
    Check if V2 dependencies are available

    Returns:
        Boolean indicating if V2 dependencies are available
    """
    try:
        from flask_sqlalchemy import SQLAlchemy
        from ..database.config import db_config
        from ..models.automated_project import AutomatedProject

        return True
    except ImportError:
        return False


def _cleanup_log_files(cutoff_date: datetime) -> int:
    """
    Cleanup old log files

    Args:
        cutoff_date: Date before which to remove logs

    Returns:
        Number of log files cleaned
    """
    import glob

    log_patterns = ["logs/*.log", "logs/*.log.*", "*.log", "celery.log*"]

    files_cleaned = 0

    for pattern in log_patterns:
        try:
            for log_file in glob.glob(pattern):
                try:
                    file_stat = os.stat(log_file)
                    file_date = datetime.fromtimestamp(file_stat.st_mtime)

                    if file_date < cutoff_date:
                        os.remove(log_file)
                        files_cleaned += 1
                        logger.info(f"Removed old log file: {log_file}")

                except Exception as e:
                    logger.warning(f"Failed to remove log file {log_file}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to process log pattern {pattern}: {e}")
            continue

    return files_cleaned


# Task Registration - ensure tasks are discoverable
__all__ = [
    "fetch_and_update_projects",
    "cleanup_old_data",
    "health_check_task",
    "test_task",
]
