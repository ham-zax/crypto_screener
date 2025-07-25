"""
Comprehensive Error Handling and Logging for Project Omega V2

Provides centralized error handling, logging configuration, and monitoring
for the API integration components. Includes rate limit handling, exponential
backoff, and graceful degradation when APIs are unavailable.
"""

import logging
import time
import functools
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import traceback
import sys

# Custom exception classes for better error categorization
class OmegaAPIError(Exception):
    """Base exception for Omega API errors"""
    pass

class ExternalAPIError(OmegaAPIError):
    """Errors from external APIs (CoinGecko, etc.)"""
    def __init__(self, message: str, api_name: str = "Unknown", status_code: Optional[int] = None):
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code
        self.timestamp = datetime.utcnow()

class RateLimitExceededError(ExternalAPIError):
    """Rate limit exceeded for external API"""
    def __init__(self, message: str, api_name: str, retry_after: Optional[int] = None):
        super().__init__(message, api_name)
        self.retry_after = retry_after

class DataValidationError(OmegaAPIError):
    """Data validation or processing errors"""
    def __init__(self, message: str, data_source: str = "Unknown"):
        super().__init__(message)
        self.data_source = data_source

class ScoringError(OmegaAPIError):
    """Errors in automated scoring algorithms"""
    def __init__(self, message: str, project_id: str = "Unknown"):
        super().__init__(message)
        self.project_id = project_id

class DatabaseError(OmegaAPIError):
    """Database operation errors"""
    def __init__(self, message: str, operation: str = "Unknown"):
        super().__init__(message)
        self.operation = operation


class ErrorTracker:
    """
    Track and analyze error patterns for monitoring and alerting
    """
    
    def __init__(self, max_errors: int = 1000):
        self.errors = []
        self.max_errors = max_errors
        self.error_counts = {}
        self.last_cleanup = datetime.utcnow()
    
    def record_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Record an error with context information"""
        error_record = {
            'timestamp': datetime.utcnow(),
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context or {},
            'traceback': traceback.format_exc() if hasattr(error, '__traceback__') else None
        }
        
        # Add to error list
        self.errors.append(error_record)
        
        # Maintain size limit
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Update error counts
        error_type = error_record['error_type']
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Periodic cleanup (every hour)
        if datetime.utcnow() - self.last_cleanup > timedelta(hours=1):
            self._cleanup_old_errors()
    
    def _cleanup_old_errors(self):
        """Remove errors older than 24 hours"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.errors = [e for e in self.errors if e['timestamp'] > cutoff]
        self.last_cleanup = datetime.utcnow()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.errors if e['timestamp'] > cutoff]
        
        # Count by type
        type_counts = {}
        for error in recent_errors:
            error_type = error['error_type']
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        
        return {
            'total_errors': len(recent_errors),
            'error_types': type_counts,
            'error_rate_per_hour': len(recent_errors) / max(hours, 1),
            'last_error': recent_errors[-1] if recent_errors else None,
            'period_hours': hours
        }
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """Get most recent errors"""
        return self.errors[-limit:] if self.errors else []


class LoggingManager:
    """
    Centralized logging configuration and management
    """
    
    @staticmethod
    def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
        """
        Setup comprehensive logging configuration
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional log file path
        """
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Setup specific loggers for V2 components
        loggers = [
            'src.api.coingecko',
            'src.api.data_fetcher',
            'src.scoring.automated_scoring',
            'src.models.api_responses'
        ]
        
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, log_level.upper()))
    
    @staticmethod
    def get_api_logger(name: str) -> logging.Logger:
        """Get a configured logger for API components"""
        return logging.getLogger(f"omega.api.{name}")


# Global error tracker instance
error_tracker = ErrorTracker()


def handle_api_errors(
    retry_count: int = 3,
    backoff_factor: float = 1.5,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for handling API errors with retry logic and exponential backoff
    
    Args:
        retry_count: Number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                
                except RateLimitExceededError as e:
                    # Special handling for rate limits
                    if attempt < retry_count:
                        wait_time = e.retry_after or (backoff_factor ** attempt)
                        logger = LoggingManager.get_api_logger(func.__name__)
                        logger.warning(f"Rate limit exceeded, waiting {wait_time}s before retry {attempt + 1}")
                        time.sleep(wait_time)
                        continue
                    last_exception = e
                    break
                
                except exceptions as e:
                    last_exception = e
                    if attempt < retry_count:
                        wait_time = backoff_factor ** attempt
                        logger = LoggingManager.get_api_logger(func.__name__)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    break
            
            # Record the error and re-raise
            if last_exception is not None:
                error_tracker.record_error(last_exception, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'attempts': retry_count + 1
                })
                raise last_exception
            else:
                # This shouldn't happen, but handle it gracefully
                raise RuntimeError(f"Function {func.__name__} failed after {retry_count + 1} attempts")
        
        return wrapper
    return decorator


def graceful_degradation(
    fallback_value: Any = None,
    log_error: bool = True
):
    """
    Decorator for graceful degradation when services are unavailable
    
    Args:
        fallback_value: Value to return when function fails
        log_error: Whether to log the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = LoggingManager.get_api_logger(func.__name__)
                    logger.error(f"Graceful degradation triggered for {func.__name__}: {e}")
                    error_tracker.record_error(e, {
                        'function': func.__name__,
                        'degradation_mode': True
                    })
                
                return fallback_value
        
        return wrapper
    return decorator


class HealthMonitor:
    """
    Monitor system health and API availability
    """
    
    def __init__(self):
        self.health_checks = {}
        self.last_check = {}
    
    def register_health_check(self, name: str, check_func: Callable[[], bool], interval: int = 300):
        """
        Register a health check function
        
        Args:
            name: Health check name
            check_func: Function that returns True if healthy
            interval: Check interval in seconds
        """
        self.health_checks[name] = {
            'function': check_func,
            'interval': interval,
            'last_result': None,
            'last_error': None
        }
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_config in self.health_checks.items():
            # Check if we need to run this check
            last_check_time = self.last_check.get(name, datetime.min)
            if datetime.utcnow() - last_check_time < timedelta(seconds=check_config['interval']):
                # Use cached result
                results[name] = check_config['last_result']
                continue
            
            # Run the health check
            try:
                is_healthy = check_config['function']()
                result = {
                    'healthy': is_healthy,
                    'checked_at': datetime.utcnow().isoformat(),
                    'error': None
                }
                
                if not is_healthy:
                    overall_healthy = False
                
            except Exception as e:
                result = {
                    'healthy': False,
                    'checked_at': datetime.utcnow().isoformat(),
                    'error': str(e)
                }
                overall_healthy = False
                check_config['last_error'] = str(e)
            
            # Cache the result
            check_config['last_result'] = result
            self.last_check[name] = datetime.utcnow()
            results[name] = result
        
        return {
            'overall_healthy': overall_healthy,
            'checks': results,
            'error_summary': error_tracker.get_error_summary()
        }


# Global health monitor instance
health_monitor = HealthMonitor()


def setup_v2_error_handling():
    """
    Setup comprehensive error handling for V2 components
    """
    # Setup logging
    LoggingManager.setup_logging()
    
    # Register health checks
    def coingecko_health():
        """Check CoinGecko API health"""
        try:
            import requests
            response = requests.get("https://api.coingecko.com/api/v3/ping", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def database_health():
        """Check database health"""
        try:
            from ..database.config import get_db_info
            get_db_info()
            return True
        except:
            return False
    
    health_monitor.register_health_check('coingecko_api', coingecko_health, 300)
    health_monitor.register_health_check('database', database_health, 60)
    
    logger = LoggingManager.get_api_logger('setup')
    logger.info("V2 error handling and monitoring configured")


def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    return health_monitor.run_health_checks()


def get_error_summary() -> Dict[str, Any]:
    """Get error summary and statistics"""
    return error_tracker.get_error_summary()


def log_api_call(api_name: str, endpoint: str, duration: float, success: bool):
    """Log API call metrics"""
    logger = LoggingManager.get_api_logger('metrics')
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"API_CALL - {api_name}:{endpoint} - {status} - {duration:.3f}s")


# Context manager for API call tracking
class APICallTracker:
    """Context manager to track API call metrics"""
    
    def __init__(self, api_name: str, endpoint: str):
        self.api_name = api_name
        self.endpoint = endpoint
        self.start_time: Optional[float] = None
        self.success = False
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
        else:
            duration = 0.0
        
        self.success = exc_type is None
        log_api_call(self.api_name, self.endpoint, duration, self.success)
        
        if not self.success and exc_val:
            error_tracker.record_error(exc_val, {
                'api_name': self.api_name,
                'endpoint': self.endpoint,
                'duration': duration
            })