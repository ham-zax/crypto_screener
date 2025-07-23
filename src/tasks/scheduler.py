"""
Celery Beat Scheduler Configuration for Project Omega V2
Periodic Task Scheduling with Dynamic Updates

Features:
- Configurable schedules (daily, weekly, custom intervals)
- Timezone-aware scheduling
- Dynamic schedule updates without restart
- Schedule persistence and management
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from celery.beat import ScheduleEntry
from celery.schedules import crontab, solar
from celery import Celery

logger = logging.getLogger(__name__)

class DynamicScheduleManager:
    """
    Manages dynamic Celery Beat schedules
    
    Allows runtime modification of task schedules without requiring
    worker restarts, with persistence across application restarts.
    """
    
    def __init__(self, celery_app: Celery):
        """
        Initialize scheduler manager
        
        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
        self.custom_schedules = {}
        self.schedule_file = os.path.join(os.getcwd(), 'data', 'celery_schedules.json')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
        
        # Load existing schedules
        self._load_schedules()
        
        logger.info("DynamicScheduleManager initialized")
    
    def add_schedule(
        self,
        name: str,
        task: str,
        schedule_type: str,
        schedule_value: Union[int, str, Dict],
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        options: Dict[str, Any] = None
    ) -> bool:
        """
        Add a new schedule entry
        
        Args:
            name: Schedule name/identifier
            task: Task name to execute
            schedule_type: Type of schedule ('interval', 'crontab', 'solar')
            schedule_value: Schedule configuration
            args: Task arguments
            kwargs: Task keyword arguments
            options: Task execution options
            
        Returns:
            Boolean indicating success
        """
        try:
            kwargs = kwargs or {}
            options = options or {}
            
            # Create schedule object based on type
            schedule_obj = self._create_schedule_object(schedule_type, schedule_value)
            
            if not schedule_obj:
                logger.error(f"Failed to create schedule object for {name}")
                return False
            
            # Create schedule entry
            schedule_entry = {
                'task': task,
                'schedule': schedule_obj,
                'args': args,
                'kwargs': kwargs,
                'options': options,
                'created_at': datetime.utcnow().isoformat(),
                'enabled': True
            }
            
            # Add to custom schedules
            self.custom_schedules[name] = {
                'task': task,
                'schedule_type': schedule_type,
                'schedule_value': schedule_value,
                'args': args,
                'kwargs': kwargs,
                'options': options,
                'created_at': datetime.utcnow().isoformat(),
                'enabled': True
            }
            
            # Update Celery beat schedule
            self.celery_app.conf.beat_schedule[name] = schedule_entry
            
            # Save to persistence
            self._save_schedules()
            
            logger.info(f"Added schedule '{name}' for task '{task}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add schedule {name}: {e}")
            return False
    
    def remove_schedule(self, name: str) -> bool:
        """
        Remove a schedule entry
        
        Args:
            name: Schedule name to remove
            
        Returns:
            Boolean indicating success
        """
        try:
            # Remove from custom schedules
            if name in self.custom_schedules:
                del self.custom_schedules[name]
            
            # Remove from Celery beat schedule
            if name in self.celery_app.conf.beat_schedule:
                del self.celery_app.conf.beat_schedule[name]
            
            # Save changes
            self._save_schedules()
            
            logger.info(f"Removed schedule '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove schedule {name}: {e}")
            return False
    
    def update_schedule(
        self,
        name: str,
        schedule_type: Optional[str] = None,
        schedule_value: Optional[Union[int, str, Dict]] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """
        Update an existing schedule
        
        Args:
            name: Schedule name to update
            schedule_type: New schedule type
            schedule_value: New schedule value
            args: New task arguments
            kwargs: New task keyword arguments
            options: New task options
            enabled: Enable/disable schedule
            
        Returns:
            Boolean indicating success
        """
        try:
            if name not in self.custom_schedules:
                logger.error(f"Schedule '{name}' not found")
                return False
            
            current_schedule = self.custom_schedules[name]
            
            # Update fields if provided
            if schedule_type is not None:
                current_schedule['schedule_type'] = schedule_type
            if schedule_value is not None:
                current_schedule['schedule_value'] = schedule_value
            if args is not None:
                current_schedule['args'] = args
            if kwargs is not None:
                current_schedule['kwargs'] = kwargs
            if options is not None:
                current_schedule['options'] = options
            if enabled is not None:
                current_schedule['enabled'] = enabled
            
            current_schedule['updated_at'] = datetime.utcnow().isoformat()
            
            # Recreate schedule entry
            if current_schedule['enabled']:
                schedule_obj = self._create_schedule_object(
                    current_schedule['schedule_type'],
                    current_schedule['schedule_value']
                )
                
                self.celery_app.conf.beat_schedule[name] = {
                    'task': current_schedule['task'],
                    'schedule': schedule_obj,
                    'args': current_schedule['args'],
                    'kwargs': current_schedule['kwargs'],
                    'options': current_schedule['options']
                }
            else:
                # Remove disabled schedule from active schedules
                if name in self.celery_app.conf.beat_schedule:
                    del self.celery_app.conf.beat_schedule[name]
            
            # Save changes
            self._save_schedules()
            
            logger.info(f"Updated schedule '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update schedule {name}: {e}")
            return False
    
    def enable_schedule(self, name: str) -> bool:
        """Enable a schedule"""
        return self.update_schedule(name, enabled=True)
    
    def disable_schedule(self, name: str) -> bool:
        """Disable a schedule"""
        return self.update_schedule(name, enabled=False)
    
    def get_schedule(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get schedule information
        
        Args:
            name: Schedule name
            
        Returns:
            Schedule information or None if not found
        """
        return self.custom_schedules.get(name)
    
    def list_schedules(self) -> Dict[str, Any]:
        """
        List all schedules
        
        Returns:
            Dictionary with all schedule information
        """
        try:
            # Get active Celery schedules
            active_schedules = dict(self.celery_app.conf.beat_schedule)
            
            # Combine with custom schedule metadata
            schedule_list = {}
            
            for name, schedule_config in self.custom_schedules.items():
                schedule_info = dict(schedule_config)
                schedule_info['active'] = name in active_schedules
                
                # Add next run time if available
                if name in active_schedules:
                    try:
                        schedule_obj = active_schedules[name]['schedule']
                        if hasattr(schedule_obj, 'remaining_estimate'):
                            remaining = schedule_obj.remaining_estimate(datetime.utcnow())
                            schedule_info['next_run'] = (datetime.utcnow() + remaining).isoformat()
                    except Exception as e:
                        logger.debug(f"Could not calculate next run for {name}: {e}")
                
                schedule_list[name] = schedule_info
            
            return {
                'schedules': schedule_list,
                'total_schedules': len(schedule_list),
                'active_schedules': len([s for s in schedule_list.values() if s.get('active', False)]),
                'enabled_schedules': len([s for s in schedule_list.values() if s.get('enabled', False)])
            }
            
        except Exception as e:
            logger.error(f"Failed to list schedules: {e}")
            return {'schedules': {}, 'error': str(e)}
    
    def _create_schedule_object(self, schedule_type: str, schedule_value: Union[int, str, Dict]):
        """
        Create Celery schedule object
        
        Args:
            schedule_type: Type of schedule
            schedule_value: Schedule configuration
            
        Returns:
            Celery schedule object
        """
        try:
            if schedule_type == 'interval':
                # Interval in seconds
                if isinstance(schedule_value, (int, float)):
                    return timedelta(seconds=schedule_value)
                elif isinstance(schedule_value, dict):
                    return timedelta(**schedule_value)
                else:
                    raise ValueError(f"Invalid interval value: {schedule_value}")
            
            elif schedule_type == 'crontab':
                # Crontab schedule
                if isinstance(schedule_value, dict):
                    return crontab(**schedule_value)
                elif isinstance(schedule_value, str):
                    # Parse crontab string: "minute hour day month day_of_week"
                    parts = schedule_value.split()
                    if len(parts) == 5:
                        return crontab(
                            minute=parts[0],
                            hour=parts[1],
                            day_of_month=parts[2],
                            month_of_year=parts[3],
                            day_of_week=parts[4]
                        )
                    else:
                        raise ValueError(f"Invalid crontab format: {schedule_value}")
                else:
                    raise ValueError(f"Invalid crontab value: {schedule_value}")
            
            elif schedule_type == 'solar':
                # Solar schedule
                if isinstance(schedule_value, dict):
                    return solar(**schedule_value)
                else:
                    raise ValueError(f"Invalid solar value: {schedule_value}")
            
            else:
                raise ValueError(f"Unknown schedule type: {schedule_type}")
                
        except Exception as e:
            logger.error(f"Failed to create schedule object: {e}")
            return None
    
    def _load_schedules(self):
        """Load schedules from persistence"""
        try:
            import json
            
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r') as f:
                    saved_schedules = json.load(f)
                
                # Restore schedules
                for name, schedule_config in saved_schedules.items():
                    if schedule_config.get('enabled', True):
                        self.add_schedule(
                            name=name,
                            task=schedule_config['task'],
                            schedule_type=schedule_config['schedule_type'],
                            schedule_value=schedule_config['schedule_value'],
                            args=tuple(schedule_config.get('args', [])),
                            kwargs=schedule_config.get('kwargs', {}),
                            options=schedule_config.get('options', {})
                        )
                    else:
                        # Add to custom schedules but don't activate
                        self.custom_schedules[name] = schedule_config
                
                logger.info(f"Loaded {len(saved_schedules)} schedules from persistence")
            
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
    
    def _save_schedules(self):
        """Save schedules to persistence"""
        try:
            import json
            
            with open(self.schedule_file, 'w') as f:
                json.dump(self.custom_schedules, f, indent=2, default=str)
            
            logger.debug("Saved schedules to persistence")
            
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

def create_default_schedules(celery_app: Celery) -> DynamicScheduleManager:
    """
    Create default schedule configuration
    
    Args:
        celery_app: Celery application instance
        
    Returns:
        Configured DynamicScheduleManager
    """
    scheduler = DynamicScheduleManager(celery_app)
    
    # Environment-based default schedules
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment == 'production':
        # Production schedules
        
        # Daily project fetch at 2 AM UTC
        scheduler.add_schedule(
            name='daily-project-fetch',
            task='src.tasks.scheduled_tasks.fetch_and_update_projects',
            schedule_type='crontab',
            schedule_value={'hour': 2, 'minute': 0},
            kwargs={
                'filters': {
                    'min_market_cap': 1_000_000,
                    'max_results': 1000,
                    'min_volume_24h': 100_000
                },
                'save_to_database': True
            },
            options={'queue': 'data_fetch', 'priority': 8}
        )
        
        # Weekly cleanup on Sundays at 3 AM UTC
        scheduler.add_schedule(
            name='weekly-cleanup',
            task='src.tasks.scheduled_tasks.cleanup_old_data',
            schedule_type='crontab',
            schedule_value={'hour': 3, 'minute': 0, 'day_of_week': 0},
            kwargs={'days_to_keep': 30},
            options={'queue': 'maintenance', 'priority': 3}
        )
        
        # Hourly health checks
        scheduler.add_schedule(
            name='hourly-health-check',
            task='src.tasks.scheduled_tasks.health_check_task',
            schedule_type='crontab',
            schedule_value={'minute': 0},
            options={'queue': 'monitoring', 'priority': 5}
        )
        
    else:
        # Development schedules (more frequent for testing)
        
        # Project fetch every 6 hours
        scheduler.add_schedule(
            name='dev-project-fetch',
            task='src.tasks.scheduled_tasks.fetch_and_update_projects',
            schedule_type='interval',
            schedule_value={'hours': 6},
            kwargs={
                'filters': {
                    'min_market_cap': 10_000_000,  # Higher threshold for dev
                    'max_results': 100,
                    'min_volume_24h': 500_000
                },
                'save_to_database': True
            },
            options={'queue': 'data_fetch', 'priority': 8}
        )
        
        # Daily cleanup
        scheduler.add_schedule(
            name='dev-daily-cleanup',
            task='src.tasks.scheduled_tasks.cleanup_old_data',
            schedule_type='interval',
            schedule_value={'days': 1},
            kwargs={'days_to_keep': 7},  # Keep less data in dev
            options={'queue': 'maintenance', 'priority': 3}
        )
        
        # Health check every 30 minutes
        scheduler.add_schedule(
            name='dev-health-check',
            task='src.tasks.scheduled_tasks.health_check_task',
            schedule_type='interval',
            schedule_value={'minutes': 30},
            options={'queue': 'monitoring', 'priority': 5}
        )
        
        # Test task every 10 minutes
        scheduler.add_schedule(
            name='dev-test-task',
            task='src.tasks.scheduled_tasks.test_task',
            schedule_type='interval',
            schedule_value={'minutes': 10},
            args=('Development test task',),
            options={'queue': 'default', 'priority': 1}
        )
    
    logger.info(f"Created default schedules for {environment} environment")
    return scheduler

def get_timezone_aware_schedules() -> Dict[str, Any]:
    """
    Get timezone-aware schedule examples
    
    Returns:
        Dictionary with timezone-aware schedule configurations
    """
    import pytz
    
    # Common timezone-aware schedules
    schedules = {
        'market_open_est': {
            'description': 'US Market Open (9:30 AM EST)',
            'schedule_type': 'crontab',
            'schedule_value': {
                'hour': 9,
                'minute': 30,
                'day_of_week': '1-5'  # Monday to Friday
            },
            'timezone': 'US/Eastern'
        },
        
        'market_close_est': {
            'description': 'US Market Close (4:00 PM EST)',
            'schedule_type': 'crontab',
            'schedule_value': {
                'hour': 16,
                'minute': 0,
                'day_of_week': '1-5'
            },
            'timezone': 'US/Eastern'
        },
        
        'asia_market_hours': {
            'description': 'Asian Market Hours (9:00 AM JST)',
            'schedule_type': 'crontab',
            'schedule_value': {
                'hour': 9,
                'minute': 0,
                'day_of_week': '1-5'
            },
            'timezone': 'Asia/Tokyo'
        },
        
        'europe_market_hours': {
            'description': 'European Market Hours (9:00 AM CET)',
            'schedule_type': 'crontab',
            'schedule_value': {
                'hour': 9,
                'minute': 0,
                'day_of_week': '1-5'
            },
            'timezone': 'Europe/Berlin'
        }
    }
    
    return schedules

# Default scheduler instance will be created when imported
_default_scheduler = None

def get_scheduler(celery_app: Celery) -> DynamicScheduleManager:
    """
    Get or create the default scheduler instance
    
    Args:
        celery_app: Celery application instance
        
    Returns:
        DynamicScheduleManager instance
    """
    global _default_scheduler
    
    if _default_scheduler is None:
        _default_scheduler = create_default_schedules(celery_app)
    
    return _default_scheduler