# Phase 4 - Background Task Scheduling Implementation

## Overview

Phase 4 implements a comprehensive background task scheduling system for Project Omega V2 using Celery with Redis broker. This implementation provides automated cryptocurrency data fetching, system maintenance, monitoring capabilities, and graceful fallback when background services are unavailable.

## Architecture

### Core Components

1. **Celery Configuration** (`src/tasks/celery_config.py`)
   - Redis broker integration
   - Task routing and queue management
   - Environment-based configuration
   - Retry policies and error handling

2. **Scheduled Tasks** (`src/tasks/scheduled_tasks.py`)
   - `fetch_and_update_projects()` - Daily crypto data ingestion
   - `cleanup_old_data()` - Periodic data cleanup
   - `health_check_task()` - System health monitoring
   - `test_task()` - Validation and testing

3. **Task Manager** (`src/tasks/task_manager.py`)
   - Manual task triggering
   - Status monitoring and reporting
   - Worker health checks
   - Task history tracking

4. **Dynamic Scheduler** (`src/tasks/scheduler.py`)
   - Celery Beat configuration
   - Runtime schedule modification
   - Timezone-aware scheduling
   - Schedule persistence

5. **Fallback System** (`src/tasks/fallback.py`)
   - Graceful degradation when Celery unavailable
   - Synchronous task execution
   - Backward compatibility with V1

## API Endpoints

### Task Management Endpoints

- **POST /api/v2/tasks/fetch-projects** - Trigger manual data fetch
- **GET /api/v2/tasks/status** - Get all task statuses
- **POST /api/v2/tasks/schedule** - Modify task schedules
- **GET /api/v2/tasks/schedule** - Get schedule information
- **GET /api/v2/tasks/history** - Get task execution history
- **POST /api/v2/tasks/cleanup** - Trigger manual cleanup
- **POST /api/v2/tasks/health-check** - Trigger health check
- **POST /api/v2/tasks/test** - Trigger test task

## Key Features

### 1. Daily Automated Data Ingestion

**Production Schedule:**
- Daily at 2 AM UTC
- Processes 1000+ projects
- Batch processing for efficiency
- Preserves existing data scores

**Development Schedule:**
- Every 6 hours
- Limited to 100 projects
- Higher market cap threshold

### 2. Batch Processing

- Configurable batch sizes (default: 250 projects)
- Progress tracking with Celery task updates
- Rate limiting between batches
- Partial success handling

### 3. Error Handling & Retry Logic

**Retry Policies:**
- Data fetch: 3 retries, 5-minute exponential backoff
- Cleanup: 2 retries, 10-minute delay
- Health check: 1 retry, 1-minute delay

**Error Recovery:**
- Database transaction rollback
- Partial data preservation
- Comprehensive error logging

### 4. Task Monitoring

**Real-time Monitoring:**
- Active task tracking
- Worker status monitoring
- Queue length monitoring
- Performance metrics

**Historical Tracking:**
- Task execution history
- Duration tracking
- Success/failure rates
- Error categorization

### 5. Dynamic Scheduling

**Schedule Types:**
- Interval schedules (seconds, minutes, hours, days)
- Crontab schedules (minute, hour, day, month, day_of_week)
- Solar schedules (sunrise, sunset)

**Runtime Management:**
- Add/remove schedules without restart
- Enable/disable schedules
- Schedule persistence across restarts

### 6. Graceful Fallback

**Fallback Capabilities:**
- V1 functionality preserved
- Synchronous task execution
- Limited batch processing
- Basic health monitoring

**Automatic Detection:**
- Redis connection testing
- Celery worker availability
- Seamless mode switching

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Environment
ENVIRONMENT=development|production

# Optional
COINGECKO_API_KEY=your_api_key
CELERY_ALWAYS_EAGER=false  # For testing
```

### Queue Configuration

- **default** - General tasks
- **data_fetch** - Data ingestion tasks
- **maintenance** - Cleanup and maintenance
- **monitoring** - Health checks and monitoring

## Deployment

### Redis Setup

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Celery Workers

```bash
# Start Celery worker
celery -A src.tasks.celery_config:celery_app worker --loglevel=info

# Start with specific queues
celery -A src.tasks.celery_config:celery_app worker -Q data_fetch,maintenance --loglevel=info
```

### Celery Beat Scheduler

```bash
# Start Celery Beat
celery -A src.tasks.celery_config:celery_app beat --loglevel=info

# With schedule file persistence
celery -A src.tasks.celery_config:celery_app beat --schedule=data/celerybeat-schedule --loglevel=info
```

### Production Deployment

```bash
# Multi-worker setup
celery multi start w1 w2 w3 -A src.tasks.celery_config:celery_app -l info -Q:1 data_fetch -Q:2 maintenance -Q:3 monitoring

# Beat scheduler
celery -A src.tasks.celery_config:celery_app beat --detach --loglevel=info
```

## Monitoring & Observability

### Task Status Monitoring

```bash
# Monitor tasks
curl http://localhost:5000/api/v2/tasks/status

# Check specific task
curl http://localhost:5000/api/v2/tasks/status?task_id=abc123

# View task history
curl http://localhost:5000/api/v2/tasks/history?limit=20
```

### Health Monitoring

```bash
# System health check
curl http://localhost:5000/api/v2/tasks/health-check -X POST

# Overall system status
curl http://localhost:5000/api/v2/health
```

### Performance Metrics

- Task execution times
- Success/failure rates
- Worker utilization
- Queue lengths
- API rate limit usage

## Integration with Existing Systems

### Database Integration

- Preserves existing data scores during updates
- Transaction management for reliability
- Batch database operations
- Connection pooling

### API Rate Limiting

- Respects CoinGecko API limits
- Configurable rate limiting
- Request spacing between batches
- API key rotation support

### Error Notifications

- Comprehensive error logging
- Failed task tracking
- Performance degradation alerts
- System health notifications

## Testing

### Manual Testing

```bash
# Test data fetch
curl -X POST http://localhost:5000/api/v2/tasks/fetch-projects \
  -H "Content-Type: application/json" \
  -d '{"filters": {"max_results": 10}}'

# Test cleanup
curl -X POST http://localhost:5000/api/v2/tasks/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days_to_keep": 7}'

# Test task
curl -X POST http://localhost:5000/api/v2/tasks/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'
```

### Schedule Management

```bash
# Add custom schedule
curl -X POST http://localhost:5000/api/v2/tasks/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add",
    "name": "custom-fetch",
    "task": "src.tasks.scheduled_tasks.fetch_and_update_projects",
    "schedule_type": "interval",
    "schedule_value": {"hours": 2}
  }'

# List schedules
curl http://localhost:5000/api/v2/tasks/schedule
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis service status
   - Verify connection URL
   - Check network connectivity

2. **No Celery Workers**
   - Start Celery worker processes
   - Check worker logs
   - Verify queue configuration

3. **Tasks Failing**
   - Check task logs
   - Verify database connectivity
   - Check API key validity

4. **Fallback Mode**
   - Expected when Redis/Celery unavailable
   - Limited functionality
   - Check system requirements

### Debugging

```bash
# Check Celery status
celery -A src.tasks.celery_config:celery_app status

# Monitor tasks
celery -A src.tasks.celery_config:celery_app events

# Inspect workers
celery -A src.tasks.celery_config:celery_app inspect active
celery -A src.tasks.celery_config:celery_app inspect stats
```

## Future Enhancements

### Planned Features

1. **Advanced Scheduling**
   - Market hours awareness
   - Holiday calendars
   - Conditional scheduling

2. **Enhanced Monitoring**
   - Grafana dashboards
   - Prometheus metrics
   - Alerting integration

3. **Scalability**
   - Multi-node Redis cluster
   - Worker auto-scaling
   - Load balancing

4. **Data Pipeline**
   - Stream processing
   - Real-time updates
   - Event-driven architecture

## Security Considerations

- API key protection
- Redis authentication
- Task input validation
- Rate limiting protection
- Secure configuration management

## Performance Optimization

- Connection pooling
- Batch processing
- Efficient database queries
- Memory usage optimization
- Resource monitoring

---

**Implementation Status**: ✅ Complete

Phase 4 Background Task Scheduling has been successfully implemented with full Celery integration, comprehensive fallback support, and robust monitoring capabilities. The system provides automated daily data ingestion, flexible scheduling, and graceful degradation when background services are unavailable.