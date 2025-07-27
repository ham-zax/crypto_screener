"""
Task Management Service for Project Omega V2
Coordinates scheduled tasks, provides monitoring, and manages task execution

Features:
- Manual task triggering
- Task status monitoring and reporting
- Queue management and worker health checks
- Task history and statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from celery.result import AsyncResult

# Import tasks and Celery app
from .celery_config import celery_app, get_celery_config_info, test_redis_connection
from . import scheduled_tasks

logger = logging.getLogger(__name__)


class TaskManager:
    """
    High-level task management and coordination service

    Provides centralized control over Celery tasks including:
    - Manual task execution
    - Status monitoring
    - Queue management
    - Worker health checks
    - Task history tracking
    """

    def __init__(self):
        """Initialize task manager"""
        self.celery_app = celery_app
        self.task_history = []
        self._worker_stats_cache = {}
        self._cache_timestamp = None

        logger.info("TaskManager initialized")

    def trigger_manual_fetch(
        self,
        filters: Optional[Dict[str, Any]] = None,
        save_to_database: bool = True,
        priority: int = 5,
    ) -> Dict[str, Any]:
        """
        Trigger manual project fetch task

        Args:
            filters: Project filtering criteria
            save_to_database: Whether to save results to database
            priority: Task priority (1-10, higher is more priority)

        Returns:
            Task execution information
        """
        logger.info("Triggering manual project fetch")

        try:
            # Check if Celery is available
            if not self.is_celery_available():
                return {
                    "status": "failed",
                    "error": "Celery not available",
                    "message": "Background task system is not running",
                }

            # Apply default filters if none provided
            if filters is None:
                filters = {
                    "min_market_cap": 1_000_000,
                    "max_results": 1000,
                    "min_volume_24h": 100_000,
                }

            # Submit task
            task_result = scheduled_tasks.fetch_and_update_projects.apply_async(  # type: ignore[attr-defined]
                kwargs={"filters": filters, "save_to_database": save_to_database},
                priority=priority,
                queue="data_fetch",
            )

            task_info = {
                "status": "submitted",
                "task_id": task_result.id,
                "task_name": "fetch_and_update_projects",
                "submitted_at": datetime.utcnow().isoformat(),
                "filters": filters,
                "save_to_database": save_to_database,
                "queue": "data_fetch",
                "priority": priority,
            }

            # Add to history
            self._add_to_history(task_info)

            logger.info(f"Manual fetch task submitted: {task_result.id}")
            return task_info

        except Exception as e:
            error_msg = f"Failed to trigger manual fetch: {e}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "submitted_at": datetime.utcnow().isoformat(),
            }

    def trigger_cleanup_task(
        self, days_to_keep: int = 30, priority: int = 3
    ) -> Dict[str, Any]:
        """
        Trigger manual cleanup task

        Args:
            days_to_keep: Number of days of data to retain
            priority: Task priority

        Returns:
            Task execution information
        """
        logger.info("Triggering manual cleanup task")

        try:
            if not self.is_celery_available():
                return {
                    "status": "failed",
                    "error": "Celery not available",
                    "message": "Background task system is not running",
                }

            task_result = scheduled_tasks.cleanup_old_data.apply_async(  # type: ignore[attr-defined]
                kwargs={"days_to_keep": days_to_keep},
                priority=priority,
                queue="maintenance",
            )

            task_info = {
                "status": "submitted",
                "task_id": task_result.id,
                "task_name": "cleanup_old_data",
                "submitted_at": datetime.utcnow().isoformat(),
                "days_to_keep": days_to_keep,
                "queue": "maintenance",
                "priority": priority,
            }

            self._add_to_history(task_info)

            logger.info(f"Manual cleanup task submitted: {task_result.id}")
            return task_info

        except Exception as e:
            error_msg = f"Failed to trigger cleanup task: {e}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "submitted_at": datetime.utcnow().isoformat(),
            }

    def trigger_health_check(self, priority: int = 5) -> Dict[str, Any]:
        """
        Trigger manual health check task

        Args:
            priority: Task priority

        Returns:
            Task execution information
        """
        logger.info("Triggering manual health check")

        try:
            if not self.is_celery_available():
                return {
                    "status": "failed",
                    "error": "Celery not available",
                    "message": "Background task system is not running",
                }

            task_result = scheduled_tasks.health_check_task.apply_async(  # type: ignore[attr-defined]
                priority=priority, queue="monitoring"
            )

            task_info = {
                "status": "submitted",
                "task_id": task_result.id,
                "task_name": "health_check_task",
                "submitted_at": datetime.utcnow().isoformat(),
                "queue": "monitoring",
                "priority": priority,
            }

            self._add_to_history(task_info)

            logger.info(f"Manual health check task submitted: {task_result.id}")
            return task_info

        except Exception as e:
            error_msg = f"Failed to trigger health check: {e}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "submitted_at": datetime.utcnow().isoformat(),
            }

    def trigger_test_task(
        self, message: str = "Manual test task", priority: int = 1
    ) -> Dict[str, Any]:
        """
        Trigger test task for validation

        Args:
            message: Test message
            priority: Task priority

        Returns:
            Task execution information
        """
        logger.info("Triggering test task")

        try:
            if not self.is_celery_available():
                return {
                    "status": "failed",
                    "error": "Celery not available",
                    "message": "Background task system is not running",
                }

            task_result = scheduled_tasks.test_task.apply_async(  # type: ignore[attr-defined]
                args=[message], priority=priority, queue="default"
            )

            task_info = {
                "status": "submitted",
                "task_id": task_result.id,
                "task_name": "test_task",
                "submitted_at": datetime.utcnow().isoformat(),
                "message": message,
                "queue": "default",
                "priority": priority,
            }

            self._add_to_history(task_info)

            logger.info(f"Test task submitted: {task_result.id}")
            return task_info

        except Exception as e:
            error_msg = f"Failed to trigger test task: {e}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "submitted_at": datetime.utcnow().isoformat(),
            }

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a specific task

        Args:
            task_id: Celery task ID

        Returns:
            Task status information
        """
        from celery.exceptions import NotRegistered

        try:
            if not self.is_celery_available():
                return {"status": "unavailable", "error": "Celery not available"}

            result = AsyncResult(task_id, app=self.celery_app)

            # --- Robust serialization fix ---
            if result.ready():
                if isinstance(result.result, NotRegistered):
                    serializable_result = "Task ID not found in the result backend. It may have expired or is invalid."
                elif isinstance(result.result, Exception):
                    serializable_result = str(result.result)
                else:
                    # Defensive: if result.result is not JSON serializable, convert to string
                    try:
                        import json

                        json.dumps(result.result)
                        serializable_result = result.result
                    except Exception:
                        serializable_result = str(result.result)
            else:
                serializable_result = None

            status_info = {
                "task_id": task_id,
                "status": result.status,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "result": serializable_result,
                "traceback": result.traceback if result.failed() else None,
                "info": result.info,
            }

            # Add timing information if available
            if hasattr(result, "date_done") and result.date_done:
                status_info["completed_at"] = result.date_done.isoformat()

            return status_info

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {"status": "error", "error": str(e), "task_id": task_id}

    def get_all_task_statuses(self) -> Dict[str, Any]:
        """
        Get status of all recent tasks

        Returns:
            Dictionary with all task statuses
        """
        try:
            if not self.is_celery_available():
                return {
                    "celery_available": False,
                    "error": "Celery not available",
                    "tasks": [],
                }

            # Get active tasks from Celery
            inspect = self.celery_app.control.inspect()

            active_tasks = {}
            scheduled_tasks_info = {}
            reserved_tasks = {}

            try:
                active_tasks = inspect.active() or {}
                scheduled_tasks_info = inspect.scheduled() or {}
                reserved_tasks = inspect.reserved() or {}
            except Exception as e:
                logger.warning(f"Failed to inspect Celery workers: {e}")

            # Combine task information
            all_tasks = []

            # Process active tasks
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "task_id": task["id"],
                            "name": task["name"],
                            "status": "ACTIVE",
                            "worker": worker,
                            "args": task.get("args", []),
                            "kwargs": task.get("kwargs", {}),
                            "time_start": task.get("time_start"),
                        }
                    )

            # Process scheduled tasks
            for worker, tasks in scheduled_tasks_info.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "task_id": task["request"]["id"],
                            "name": task["request"]["task"],
                            "status": "SCHEDULED",
                            "worker": worker,
                            "eta": task.get("eta"),
                        }
                    )

            # Process reserved tasks
            for worker, tasks in reserved_tasks.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "task_id": task["id"],
                            "name": task["name"],
                            "status": "RESERVED",
                            "worker": worker,
                        }
                    )

            # Add recent task history
            recent_history = self.get_task_history(limit=10)

            return {
                "celery_available": True,
                "active_tasks": all_tasks,
                "recent_history": recent_history,
                "worker_count": len(active_tasks.keys()),
                "total_active": sum(len(tasks) for tasks in active_tasks.values()),
                "total_scheduled": sum(
                    len(tasks) for tasks in scheduled_tasks_info.values()
                ),
                "total_reserved": sum(len(tasks) for tasks in reserved_tasks.values()),
            }

        except Exception as e:
            logger.error(f"Failed to get all task statuses: {e}")
            return {"celery_available": False, "error": str(e), "tasks": []}

    def get_worker_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get Celery worker statistics

        Args:
            force_refresh: Force refresh of cached stats

        Returns:
            Worker statistics
        """
        # Use cache if available and not expired
        if (
            not force_refresh
            and self._cache_timestamp
            and datetime.utcnow() - self._cache_timestamp < timedelta(minutes=1)
        ):
            return self._worker_stats_cache

        try:
            if not self.is_celery_available():
                return {
                    "celery_available": False,
                    "error": "Celery not available",
                    "workers": [],
                }

            inspect = self.celery_app.control.inspect()

            # Get worker information
            stats = {}
            try:
                inspect = self.celery_app.control.inspect()
                stats = inspect.stats() or {}
                try:
                    active = inspect.active() or {}
                except Exception:
                    active = {}
                try:
                    registered = inspect.registered() or {}
                except Exception:
                    registered = {}
                conf = inspect.conf() or {}
            except Exception as e:
                logger.warning(f"Failed to inspect workers: {e}")
                stats = {}
                active = {}
                registered = {}

            workers = []
            for worker_name, worker_stats in stats.items():
                worker_info = {
                    "name": worker_name,
                    "status": "online",
                    "pool": worker_stats.get("pool", {}).get(
                        "implementation", "unknown"
                    ),
                    "processes": worker_stats.get("pool", {}).get("processes", []),
                    "total_tasks": worker_stats.get("total", {}),
                    "active_tasks": len(active.get(worker_name, []))
                    if "active" in locals()
                    else 0,
                    "registered_tasks": len(registered.get(worker_name, []))
                    if "registered" in locals()
                    else 0,
                    "broker_info": worker_stats.get("broker", {}),
                    "clock": worker_stats.get("clock"),
                    "rusage": worker_stats.get("rusage", {}),
                }
                workers.append(worker_info)

            worker_stats = {
                "celery_available": True,
                "workers": workers,
                "total_workers": len(workers),
                "online_workers": len([w for w in workers if w["status"] == "online"]),
                "last_updated": datetime.utcnow().isoformat(),
            }

            # Cache results
            self._worker_stats_cache = worker_stats
            self._cache_timestamp = datetime.utcnow()

            return worker_stats

        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {"celery_available": False, "error": str(e), "workers": []}

    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get information about Celery queues

        Returns:
            Queue information
        """
        try:
            if not self.is_celery_available():
                return {
                    "celery_available": False,
                    "error": "Celery not available",
                    "queues": [],
                }

            # Get configured queues from Celery
            from .celery_config import CELERY_QUEUES, TASK_ROUTES

            queue_info = []
            for queue in CELERY_QUEUES:
                # Count tasks routed to this queue
                routed_tasks = [
                    task
                    for task, route in TASK_ROUTES.items()
                    if route.get("queue") == queue.name
                ]

                queue_info.append(
                    {
                        "name": queue.name if queue is not None else None,
                        "exchange": queue.exchange.name
                        if queue and queue.exchange
                        else None,
                        "routing_key": queue.routing_key if queue is not None else None,
                        "routed_tasks": routed_tasks,
                        "task_count": len(routed_tasks),
                    }
                )

            return {
                "celery_available": True,
                "queues": queue_info,
                "total_queues": len(queue_info),
                "task_routes": TASK_ROUTES,
            }

        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {"celery_available": False, "error": str(e), "queues": []}

    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get task execution history

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of task history entries
        """
        return self.task_history[-limit:] if self.task_history else []

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status

        Returns:
            Complete system status information
        """
        try:
            # Check Celery availability
            celery_available = self.is_celery_available()

            # Check Redis connection
            redis_available = test_redis_connection()

            # Get Celery configuration
            celery_config = get_celery_config_info()

            # Get worker stats
            worker_stats = self.get_worker_stats()

            # Get queue info
            queue_info = self.get_queue_info()

            # Determine overall status
            if (
                celery_available
                and redis_available
                and worker_stats["total_workers"] > 0
            ):
                overall_status = "healthy"
            elif celery_available and redis_available:
                overall_status = "degraded"  # No workers
            elif redis_available:
                overall_status = "partial"  # Redis OK but Celery issues
            else:
                overall_status = "unhealthy"

            return {
                "overall_status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "celery": {"available": celery_available, "config": celery_config},
                    "redis": {"available": redis_available},
                    "workers": worker_stats,
                    "queues": queue_info,
                },
                "recent_tasks": self.get_task_history(limit=5),
            }

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "overall_status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def is_celery_available(self) -> bool:
        """
        Check if Celery is available and responsive

        Returns:
            Boolean indicating Celery availability
        """
        try:
            # Try to get Celery app control
            inspect = self.celery_app.control.inspect()
            # Try a simple operation with timeout
            stats = inspect.stats()
            return True
        except Exception as e:
            logger.debug(f"Celery not available: {e}")
            return False

    def _add_to_history(self, task_info: Dict[str, Any]):
        """
        Add task to execution history

        Args:
            task_info: Task information to add
        """
        self.task_history.append(task_info)

        # Keep only last 100 entries
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]


# Global task manager instance
task_manager = TaskManager()
