"""
Backward Compatibility and Graceful Fallback for Project Omega V2
Task System Fallback Implementation

Provides graceful degradation when Redis/Celery is unavailable,
ensuring V1 functionality continues working without background tasks.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

class FallbackTaskManager:
    """
    Fallback task manager that provides basic task execution
    without Celery when Redis/Celery is unavailable
    """
    
    def __init__(self):
        """Initialize fallback task manager"""
        self.is_celery_available = False
        self.task_history = []
        self._background_threads = {}
        
        logger.info("FallbackTaskManager initialized (no Celery)")
    
    def trigger_manual_fetch(
        self,
        filters: Optional[Dict[str, Any]] = None,
        save_to_database: bool = True,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Trigger manual project fetch using fallback mechanism
        
        Args:
            filters: Project filtering criteria
            save_to_database: Whether to save results to database
            priority: Task priority (ignored in fallback)
            
        Returns:
            Task execution information
        """
        logger.info("Triggering manual project fetch (fallback mode)")
        
        try:
            # Check if V2 dependencies are available
            if not self._check_v2_dependencies():
                return {
                    'status': 'failed',
                    'error': 'V2 dependencies not available',
                    'message': 'Background task system requires V2 dependencies',
                    'fallback_mode': True
                }
            
            # Import V2 services
            from ..api.data_fetcher import ProjectIngestionManager
            
            # Initialize services
            api_key = os.getenv('COINGECKO_API_KEY')
            ingestion_manager = ProjectIngestionManager(api_key=api_key)
            
            # Apply default filters if none provided
            if filters is None:
                filters = {
                    'min_market_cap': 1_000_000,
                    'max_results': 100,  # Reduced for fallback mode
                    'min_volume_24h': 100_000
                }
            else:
                # Limit results in fallback mode for performance
                filters['max_results'] = min(filters.get('max_results', 100), 100)
            
            # Generate pseudo task ID
            task_id = f"fallback_{int(time.time())}"
            
            logger.info(f"Fallback fetch task {task_id} with filters: {filters}")
            
            # Run synchronous ingestion
            start_time = datetime.utcnow()
            result = ingestion_manager.run_full_ingestion(filters)
            projects = result['projects']
            
            # Save to database if requested
            saved_count = 0
            if save_to_database and len(projects) > 0:
                saved_count = self._save_projects_fallback(projects)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            task_info = {
                'status': 'completed',
                'task_id': task_id,
                'task_name': 'fetch_and_update_projects',
                'projects_fetched': len(projects),
                'projects_saved': saved_count,
                'duration': round(duration, 2),
                'filters': filters,
                'save_to_database': save_to_database,
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            # Add to history
            self._add_to_history(task_info)
            
            logger.info(f"Fallback fetch completed: {len(projects)} projects, {saved_count} saved")
            return task_info
            
        except Exception as e:
            error_msg = f"Fallback fetch failed: {e}"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
    
    def trigger_cleanup_task(
        self,
        days_to_keep: int = 30,
        priority: int = 3
    ) -> Dict[str, Any]:
        """
        Trigger cleanup task using fallback mechanism
        
        Args:
            days_to_keep: Number of days of data to retain
            priority: Task priority (ignored in fallback)
            
        Returns:
            Task execution information
        """
        logger.info("Triggering cleanup task (fallback mode)")
        
        try:
            task_id = f"fallback_cleanup_{int(time.time())}"
            start_time = datetime.utcnow()
            
            # Basic cleanup operations
            cleanup_results = self._perform_basic_cleanup(days_to_keep)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            task_info = {
                'status': 'completed',
                'task_id': task_id,
                'task_name': 'cleanup_old_data',
                'cleanup_results': cleanup_results,
                'days_to_keep': days_to_keep,
                'duration': round(duration, 2),
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            self._add_to_history(task_info)
            
            logger.info(f"Fallback cleanup completed in {duration:.1f}s")
            return task_info
            
        except Exception as e:
            error_msg = f"Fallback cleanup failed: {e}"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
    
    def trigger_health_check(self, priority: int = 5) -> Dict[str, Any]:
        """
        Trigger health check using fallback mechanism
        
        Args:
            priority: Task priority (ignored in fallback)
            
        Returns:
            Health check results
        """
        logger.info("Triggering health check (fallback mode)")
        
        try:
            task_id = f"fallback_health_{int(time.time())}"
            start_time = datetime.utcnow()
            
            # Basic health checks
            health_results = self._perform_basic_health_check()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            task_info = {
                'status': 'completed',
                'task_id': task_id,
                'task_name': 'health_check_task',
                'health_results': health_results,
                'duration': round(duration, 2),
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            self._add_to_history(task_info)
            
            logger.info("Fallback health check completed")
            return task_info
            
        except Exception as e:
            error_msg = f"Fallback health check failed: {e}"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'fallback_mode': True,
                'completed_at': datetime.utcnow().isoformat()
            }
    
    def trigger_test_task(
        self,
        message: str = "Fallback test task",
        priority: int = 1
    ) -> Dict[str, Any]:
        """
        Trigger test task using fallback mechanism
        
        Args:
            message: Test message
            priority: Task priority (ignored in fallback)
            
        Returns:
            Test results
        """
        logger.info("Triggering test task (fallback mode)")
        
        task_id = f"fallback_test_{int(time.time())}"
        start_time = datetime.utcnow()
        
        # Simulate some work
        time.sleep(1)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        task_info = {
            'status': 'completed',
            'task_id': task_id,
            'task_name': 'test_task',
            'message': message,
            'duration': round(duration, 2),
            'fallback_mode': True,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        self._add_to_history(task_info)
        
        logger.info(f"Fallback test task completed: {message}")
        return task_info
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status (fallback implementation)
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Task status information
        """
        # Search in history
        for task in reversed(self.task_history):
            if task.get('task_id') == task_id:
                return {
                    'task_id': task_id,
                    'status': 'SUCCESS' if task['status'] == 'completed' else 'FAILURE',
                    'ready': True,
                    'successful': task['status'] == 'completed',
                    'failed': task['status'] == 'failed',
                    'result': task,
                    'fallback_mode': True
                }
        
        return {
            'task_id': task_id,
            'status': 'PENDING',
            'ready': False,
            'error': 'Task not found in fallback history',
            'fallback_mode': True
        }
    
    def get_all_task_statuses(self) -> Dict[str, Any]:
        """
        Get all task statuses (fallback implementation)
        
        Returns:
            All task status information
        """
        return {
            'celery_available': False,
            'fallback_mode': True,
            'active_tasks': [],
            'recent_history': self.get_task_history(limit=10),
            'worker_count': 0,
            'total_active': 0,
            'total_scheduled': 0,
            'total_reserved': 0,
            'message': 'Running in fallback mode - no background task system available'
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status (fallback implementation)
        
        Returns:
            System status information
        """
        return {
            'overall_status': 'fallback',
            'timestamp': datetime.utcnow().isoformat(),
            'celery_available': False,
            'fallback_mode': True,
            'message': 'Background task system unavailable - running in fallback mode',
            'v2_dependencies_available': self._check_v2_dependencies(),
            'recent_tasks': self.get_task_history(limit=3)
        }
    
    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get task execution history (fallback implementation)
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of task history entries
        """
        return self.task_history[-limit:] if self.task_history else []
    
    def is_celery_available(self) -> bool:
        """Check if Celery is available (always False for fallback)"""
        return False
    
    def _save_projects_fallback(self, projects: List[Dict[str, Any]]) -> int:
        """
        Save projects using fallback method
        
        Args:
            projects: List of project data to save
            
        Returns:
            Number of projects saved
        """
        try:
            from ..models.automated_project import AutomatedProject
            from ..database.config import db_config
            
            session = db_config.get_session()
            saved_count = 0
            
            try:
                for project_data in projects:
                    try:
                        # Check if project exists
                        existing = session.query(AutomatedProject).filter_by(
                            coingecko_id=project_data['coingecko_id']
                        ).first()
                        
                        if existing:
                            # Update existing project (preserve data score)
                            old_data_score = existing.data_score
                            old_accumulation_signal = existing.accumulation_signal
                            old_has_data_score = existing.has_data_score
                            
                            for key, value in project_data.items():
                                if hasattr(existing, key) and key not in ['id', 'data_score', 'accumulation_signal', 'has_data_score']:
                                    setattr(existing, key, value)
                            
                            # Restore data score components
                            existing.data_score = old_data_score
                            existing.accumulation_signal = old_accumulation_signal
                            existing.has_data_score = old_has_data_score
                            
                            existing.update_all_scores()
                        else:
                            # Create new project
                            new_project = AutomatedProject(**project_data)
                            new_project.update_all_scores()
                            session.add(new_project)
                        
                        saved_count += 1
                    
                    except Exception as e:
                        logger.error(f"Failed to save project {project_data.get('coingecko_id', 'unknown')}: {e}")
                        continue
                
                session.commit()
                logger.info(f"Fallback save completed: {saved_count} projects")
                return saved_count
                
            except Exception as e:
                session.rollback()
                logger.error(f"Fallback database operation failed: {e}")
                return 0
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Fallback save setup failed: {e}")
            return 0
    
    def _perform_basic_cleanup(self, days_to_keep: int) -> Dict[str, Any]:
        """
        Perform basic cleanup operations
        
        Args:
            days_to_keep: Number of days to keep
            
        Returns:
            Cleanup results
        """
        cleanup_results = {
            'csv_data_removed': 0,
            'log_files_cleaned': 0,
            'fallback_mode': True
        }
        
        try:
            # Basic log file cleanup
            import glob
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            log_patterns = ['*.log', 'logs/*.log']
            
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
                        except Exception:
                            continue
                except Exception:
                    continue
            
            cleanup_results['log_files_cleaned'] = files_cleaned
            
        except Exception as e:
            logger.error(f"Basic cleanup failed: {e}")
        
        return cleanup_results
    
    def _perform_basic_health_check(self) -> Dict[str, Any]:
        """
        Perform basic health check
        
        Returns:
            Health check results
        """
        health_results = {
            'overall_health': 'degraded',
            'components': {
                'celery': {
                    'status': 'unavailable',
                    'details': 'Celery not available - running in fallback mode'
                },
                'redis': {
                    'status': 'unavailable', 
                    'details': 'Redis not available'
                }
            },
            'fallback_mode': True
        }
        
        # Check database if available
        if self._check_v2_dependencies():
            try:
                from ..database.config import db_config
                session = db_config.get_session()
                session.execute('SELECT 1')
                session.close()
                
                health_results['components']['database'] = {
                    'status': 'healthy',
                    'details': 'Database connection successful'
                }
            except Exception as e:
                health_results['components']['database'] = {
                    'status': 'unhealthy',
                    'details': f'Database connection failed: {e}'
                }
        else:
            health_results['components']['database'] = {
                'status': 'unavailable',
                'details': 'V2 dependencies not available'
            }
        
        # Check API services
        try:
            from ..api.coingecko import CoinGeckoClient
            client = CoinGeckoClient()
            # Simple ping test
            client.get_markets_data(per_page=1, page=1)
            
            health_results['components']['coingecko_api'] = {
                'status': 'healthy',
                'details': 'CoinGecko API accessible'
            }
        except Exception as e:
            health_results['components']['coingecko_api'] = {
                'status': 'degraded',
                'details': f'CoinGecko API issues: {e}'
            }
        
        return health_results
    
    def _check_v2_dependencies(self) -> bool:
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
    
    def _add_to_history(self, task_info: Dict[str, Any]):
        """
        Add task to execution history
        
        Args:
            task_info: Task information to add
        """
        self.task_history.append(task_info)
        
        # Keep only last 50 entries
        if len(self.task_history) > 50:
            self.task_history = self.task_history[-50:]

def get_task_manager():
    """
    Get appropriate task manager based on Celery availability
    
    Returns:
        TaskManager or FallbackTaskManager instance
    """
    try:
        # Try to import and test Celery
        from .celery_config import test_redis_connection
        from .task_manager import task_manager
        
        # Test if Redis/Celery is available
        if test_redis_connection() and task_manager.is_celery_available():
            logger.info("Using full TaskManager with Celery")
            return task_manager
        else:
            logger.warning("Redis/Celery unavailable, using FallbackTaskManager")
            return FallbackTaskManager()
            
    except Exception as e:
        logger.warning(f"Failed to initialize Celery task manager: {e}")
        logger.info("Using FallbackTaskManager")
        return FallbackTaskManager()

# Global fallback task manager instance
fallback_task_manager = FallbackTaskManager()