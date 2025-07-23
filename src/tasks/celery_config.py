"""
Celery Configuration for Project Omega V2
Background Task Scheduling with Redis Broker

Provides Celery app configuration, task routing, error handling,
and environment-based configuration for development vs production.
"""

import os
import logging
from celery import Celery
from kombu import Queue, Exchange
from datetime import timedelta

logger = logging.getLogger(__name__)

# Environment Configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Task Queue Configuration
TASK_ROUTES = {
    'src.tasks.scheduled_tasks.fetch_and_update_projects': {'queue': 'data_fetch'},
    'src.tasks.scheduled_tasks.cleanup_old_data': {'queue': 'maintenance'},
    'src.tasks.scheduled_tasks.health_check_task': {'queue': 'monitoring'},
    'src.tasks.scheduled_tasks.test_task': {'queue': 'default'},
}

# Queue Definitions
CELERY_QUEUES = [
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('data_fetch', Exchange('data_fetch'), routing_key='data_fetch'),
    Queue('maintenance', Exchange('maintenance'), routing_key='maintenance'),
    Queue('monitoring', Exchange('monitoring'), routing_key='monitoring'),
]

# Retry Policies
CELERY_TASK_ANNOTATIONS = {
    'src.tasks.scheduled_tasks.fetch_and_update_projects': {
        'rate_limit': '10/m',
        'max_retries': 3,
        'default_retry_delay': 300,  # 5 minutes
    },
    'src.tasks.scheduled_tasks.cleanup_old_data': {
        'max_retries': 2,
        'default_retry_delay': 600,  # 10 minutes
    },
    'src.tasks.scheduled_tasks.health_check_task': {
        'max_retries': 1,
        'default_retry_delay': 60,  # 1 minute
    },
}

def create_celery_app(app_name='omega_v2_tasks'):
    """
    Create and configure Celery application
    
    Args:
        app_name: Name of the Celery application
        
    Returns:
        Configured Celery instance
    """
    
    # Create Celery instance
    celery_app = Celery(app_name)
    
    # Basic Configuration
    celery_app.conf.update(
        # Broker and Backend
        broker_url=CELERY_BROKER_URL,
        result_backend=CELERY_RESULT_BACKEND,
        
        # Task Configuration
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Queue Configuration
        task_routes=TASK_ROUTES,
        task_default_queue='default',
        task_default_exchange='default',
        task_default_exchange_type='direct',
        task_default_routing_key='default',
        
        # Worker Configuration
        worker_hijack_root_logger=False,
        worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
        worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
        
        # Task Execution Configuration
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        
        # Error Handling
        task_reject_on_worker_lost=True,
        task_ignore_result=False,
        result_expires=3600,  # 1 hour
        
        # Task Annotations (retry policies)
        task_annotations=CELERY_TASK_ANNOTATIONS,
    )
    
    # Environment-specific configurations
    if ENVIRONMENT == 'production':
        celery_app.conf.update(
            # Production-specific settings
            worker_pool='prefork',
            worker_concurrency=4,
            broker_connection_retry_on_startup=True,
            broker_connection_retry=True,
            broker_connection_max_retries=10,
            
            # Redis Connection Pool Settings
            broker_transport_options={
                'master_name': 'mymaster',
                'visibility_timeout': 3600,
                'retry_policy': {
                    'timeout': 5.0
                }
            },
            
            # Result Backend Settings
            result_backend_transport_options={
                'master_name': 'mymaster',
                'retry_policy': {
                    'timeout': 5.0
                }
            },
        )
    else:
        celery_app.conf.update(
            # Development-specific settings
            worker_pool='solo' if os.name == 'nt' else 'prefork',  # Windows compatibility
            worker_concurrency=2,
            broker_connection_retry_on_startup=True,
            task_always_eager=os.getenv('CELERY_ALWAYS_EAGER', 'false').lower() == 'true',
            task_eager_propagates=True,
        )
    
    # Beat Schedule Configuration
    celery_app.conf.beat_schedule = get_beat_schedule()
    
    logger.info(f"Celery app configured for {ENVIRONMENT} environment")
    logger.info(f"Broker: {CELERY_BROKER_URL}")
    logger.info(f"Backend: {CELERY_RESULT_BACKEND}")
    
    return celery_app

def get_beat_schedule():
    """
    Get Celery Beat schedule configuration
    
    Returns:
        Dictionary with beat schedule configuration
    """
    
    # Base schedule
    schedule = {
        'fetch-projects-daily': {
            'task': 'src.tasks.scheduled_tasks.fetch_and_update_projects',
            'schedule': timedelta(hours=24),  # Daily at same time
            'args': (),
            'kwargs': {
                'filters': {
                    'min_market_cap': 1_000_000,
                    'max_results': 1000
                },
                'save_to_database': True
            },
            'options': {
                'queue': 'data_fetch',
                'priority': 8
            }
        },
        
        'cleanup-old-data-weekly': {
            'task': 'src.tasks.scheduled_tasks.cleanup_old_data',
            'schedule': timedelta(days=7),  # Weekly
            'args': (),
            'kwargs': {
                'days_to_keep': 30
            },
            'options': {
                'queue': 'maintenance',
                'priority': 3
            }
        },
        
        'health-check-hourly': {
            'task': 'src.tasks.scheduled_tasks.health_check_task',
            'schedule': timedelta(hours=1),  # Every hour
            'args': (),
            'options': {
                'queue': 'monitoring',
                'priority': 5
            }
        },
    }
    
    # Environment-specific schedules
    if ENVIRONMENT == 'development':
        # More frequent schedules for testing
        schedule.update({
            'test-task-every-5min': {
                'task': 'src.tasks.scheduled_tasks.test_task',
                'schedule': timedelta(minutes=5),
                'args': ('Development test',),
                'options': {
                    'queue': 'default',
                    'priority': 1
                }
            }
        })
    
    return schedule

def get_celery_config_info():
    """
    Get current Celery configuration information
    
    Returns:
        Dictionary with configuration details
    """
    return {
        'environment': ENVIRONMENT,
        'broker_url': CELERY_BROKER_URL,
        'result_backend': CELERY_RESULT_BACKEND,
        'task_routes': TASK_ROUTES,
        'queues': [q.name for q in CELERY_QUEUES],
        'beat_schedule_count': len(get_beat_schedule()),
        'retry_policies_configured': len(CELERY_TASK_ANNOTATIONS)
    }

def test_redis_connection():
    """
    Test Redis connection for Celery broker
    
    Returns:
        Boolean indicating connection success
    """
    try:
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False

# Create the default Celery app instance
celery_app = create_celery_app()

# Auto-discover tasks from tasks module
celery_app.autodiscover_tasks(['src.tasks'])