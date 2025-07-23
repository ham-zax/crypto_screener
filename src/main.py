import os
import logging
import time
from flask import Flask, send_from_directory, jsonify, request

# Try to import V2 dependencies gracefully
try:
    from flask_sqlalchemy import SQLAlchemy
    from flask_migrate import Migrate
    V2_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"V2 dependencies not installed: {e}")
    V2_DEPENDENCIES_AVAILABLE = False
    SQLAlchemy = None
    Migrate = None

# Initialize Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# V2 Backend Infrastructure Setup
if V2_DEPENDENCIES_AVAILABLE:
    try:
        from .database.config import db_config, get_db_info
        from .database.init_db import initialize_database, get_database_health
        
        # Configure Flask-SQLAlchemy with our database config
        app.config['SQLALCHEMY_DATABASE_URI'] = db_config.database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'echo': os.getenv('DB_ECHO', 'false').lower() == 'true',
            'pool_pre_ping': True,
        }
        
        # Initialize SQLAlchemy and Flask-Migrate
        db = SQLAlchemy(app)
        migrate = Migrate(app, db)
        
        # Enhanced database initialization with migration support
        with app.app_context():
            try:
                logger.info("Starting enhanced V2 database initialization...")
                
                # Get configuration settings
                auto_migrate = os.getenv('AUTO_MIGRATE_ON_STARTUP', 'true').lower() == 'true'
                seed_dev_data = os.getenv('GENERATE_SAMPLE_DATA', 'false').lower() == 'true'
                
                # Run comprehensive database initialization
                init_result = initialize_database(
                    run_migrations=auto_migrate,
                    seed_data=seed_dev_data and db_config.environment == 'development'
                )
                
                if init_result['success']:
                    logger.info("✅ V2 Database initialization completed successfully")
                    logger.info(f"⏱️  Total initialization time: {init_result['total_time_ms']}ms")
                    
                    # Log migration status
                    if 'migration_results' in init_result and init_result['migration_results']:
                        migration_results = init_result['migration_results']
                        if migration_results['success']:
                            applied_count = len([m for m in migration_results.get('applied_migrations', [])
                                               if m.get('status') == 'applied'])
                            if applied_count > 0:
                                logger.info(f"📝 Applied {applied_count} database migrations")
                        else:
                            logger.warning(f"⚠️  Migration issues: {migration_results.get('message', 'Unknown')}")
                    
                    # Log connection info
                    conn_test = init_result.get('connection_test', {})
                    if conn_test.get('success'):
                        logger.info(f"🔌 Database connection: {conn_test.get('database_type')} "
                                   f"({conn_test.get('table_count', 0)} tables)")
                    
                    # Log seeding results
                    if 'seed_results' in init_result and init_result['seed_results']:
                        seed_results = init_result['seed_results']
                        if seed_results['success'] and seed_results.get('projects_created', 0) > 0:
                            logger.info(f"🌱 Created {seed_results['projects_created']} sample projects")
                    
                else:
                    logger.error(f"❌ Database initialization failed at step: {init_result.get('step', 'unknown')}")
                    logger.error(f"Error: {init_result.get('error', 'Unknown error')}")
                    
                    # Still continue for V1 compatibility
                    logger.info("🔄 Continuing with V1 compatibility mode")
                
                # Always log final database info
                db_info = get_db_info()
                logger.info(f"📊 Database status: {db_info}")
                
            except Exception as e:
                logger.error(f"Database initialization failed with exception: {e}")
                logger.info("Falling back to V1 compatibility mode")
                # Continue running for V1 compatibility even if DB fails
                
    except ImportError as e:
        logger.warning(f"V2 backend modules not available: {e}")
        logger.info("Running in V1 compatibility mode only")
        db = None
        migrate = None
    except Exception as e:
        logger.error(f"V2 backend initialization failed: {e}")
        logger.info("Falling back to V1 compatibility mode")
        db = None
        migrate = None
else:
    logger.info("V2 dependencies not installed. Running in V1 compatibility mode.")
    logger.info("To enable V2 features, install dependencies: pip install -r requirements.txt")
    db = None
    migrate = None

# V1 Static File Serving (100% preserved functionality)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """
    Serve static files and SPA routing (V1 functionality preserved)
    This route maintains complete backward compatibility with the existing V1 implementation.
    """
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# V2 API Health Check Endpoint
@app.route('/api/v2/health')
def health_check():
    """Health check endpoint for V2 backend infrastructure"""
    health_status = {
        'status': 'healthy',
        'version': '2.0.0',
        'v1_compatibility': True,
        'v2_dependencies_available': V2_DEPENDENCIES_AVAILABLE,
        'database_available': db is not None,
        'timestamp': os.environ.get('REQUEST_TIME', 'unknown')
    }
    
    if not V2_DEPENDENCIES_AVAILABLE:
        health_status['message'] = 'V2 dependencies not installed. Install with: pip install -r requirements.txt'
        health_status['status'] = 'v1_only'
    elif db is not None:
        try:
            from .database.config import get_db_info
            db_info = get_db_info()
            health_status['database_info'] = db_info
        except Exception as e:
            health_status['database_error'] = str(e)
            health_status['status'] = 'degraded'
    
    return jsonify(health_status)

# V2 Database Health Check Endpoint
@app.route('/api/v2/database/health')
def database_health_check():
    """Comprehensive database health check endpoint"""
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'status': 'unavailable',
            'message': 'V2 database not available',
            'v2_dependencies_available': V2_DEPENDENCIES_AVAILABLE,
            'database_initialized': False
        }), 503
    
    try:
        from .database.init_db import get_database_health
        health_data = get_database_health()
        
        # Determine HTTP status code based on health
        if health_data['status'] == 'healthy':
            status_code = 200
        elif health_data['status'] == 'degraded':
            status_code = 200  # Still operational but with issues
        else:
            status_code = 503  # Service unavailable
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'timestamp': time.time()
        }), 500

# V2 Migration Management Endpoint
@app.route('/api/v2/database/migrations')
def get_migration_status():
    """Get database migration status and history"""
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        from .database.migrations.migration_runner import MigrationRunner
        from .database.config import get_engine
        
        migration_runner = MigrationRunner(get_engine())
        status = migration_runner.get_migration_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        return jsonify({
            'error': 'Migration status query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/database/migrations/run', methods=['POST'])
def run_migrations():
    """Manually trigger database migrations"""
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        from .database.migrations.migration_runner import MigrationRunner
        from .database.config import get_engine
        
        request_data = request.get_json() or {}
        target_version = request_data.get('target_version')
        
        migration_runner = MigrationRunner(get_engine())
        result = migration_runner.run_migrations(target_version)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Manual migration run failed: {e}")
        return jsonify({
            'error': 'Migration execution failed',
            'message': str(e)
        }), 500

# V2 API Endpoints for Automated Project Integration
if V2_DEPENDENCIES_AVAILABLE:
    try:
        from .api.data_fetcher import DataFetchingService, ProjectIngestionManager
        from .models.automated_project import AutomatedProject
        from .database.config import db
        
        # Initialize services
        api_key = os.getenv('COINGECKO_API_KEY')
        data_fetcher = DataFetchingService(api_key=api_key)
        ingestion_manager = ProjectIngestionManager(api_key=api_key)
        
        logger.info("V2 API services initialized successfully")
        
    except ImportError as e:
        logger.warning(f"V2 API services not available: {e}")
        data_fetcher = None
        ingestion_manager = None
    except Exception as e:
        logger.error(f"V2 API services initialization failed: {e}")
        data_fetcher = None
        ingestion_manager = None
else:
    data_fetcher = None
    ingestion_manager = None

@app.route('/api/v2/fetch-projects', methods=['POST'])
def fetch_projects():
    """
    Trigger manual project fetch from CoinGecko API
    
    Request body (optional):
    {
        "filters": {
            "min_market_cap": 1000000,
            "max_market_cap": null,
            "min_volume_24h": 100000,
            "max_results": 1000
        },
        "save_to_database": true
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not data_fetcher:
        return jsonify({
            'error': 'V2 API not available',
            'message': 'Install V2 dependencies: pip install -r requirements.txt'
        }), 503
    
    try:
        # Parse request parameters
        request_data = request.get_json() or {}
        filters = request_data.get('filters', {})
        save_to_db = request_data.get('save_to_database', False)
        
        logger.info(f"Manual project fetch requested with filters: {filters}")
        
        # Perform the fetch
        result = ingestion_manager.run_full_ingestion(filters)
        projects = result['projects']
        ingestion_record = result['ingestion_record']
        
        # Save to database if requested and available
        saved_count = 0
        if save_to_db and db is not None:
            try:
                for project_data in projects:
                    # Check if project already exists
                    existing = AutomatedProject.query.filter_by(
                        coingecko_id=project_data['coingecko_id']
                    ).first()
                    
                    if existing:
                        # Update existing project
                        for key, value in project_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.update_all_scores()
                    else:
                        # Create new project
                        new_project = AutomatedProject(**project_data)
                        new_project.update_all_scores()
                        db.session.add(new_project)
                    
                    saved_count += 1
                
                db.session.commit()
                logger.info(f"Saved {saved_count} projects to database")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Database save failed: {e}")
                return jsonify({
                    'error': 'Database save failed',
                    'message': str(e),
                    'projects_fetched': len(projects),
                    'ingestion_record': ingestion_record
                }), 500
        
        # Return results
        response = {
            'status': 'success',
            'projects_fetched': len(projects),
            'projects_saved': saved_count if save_to_db else None,
            'ingestion_record': ingestion_record,
            'projects': projects if not save_to_db else None  # Don't return full data if saved
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Manual project fetch failed: {e}")
        return jsonify({
            'error': 'Fetch failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated', methods=['GET'])
def get_automated_projects():
    """
    Get list of automated projects with filtering and pagination
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 200)
    - min_market_cap: Minimum market cap filter
    - max_market_cap: Maximum market cap filter
    - category: Category filter
    - has_data_score: Filter by data score availability (true/false)
    - sort_by: Sort field (market_cap, omega_score, created_at)
    - sort_order: Sort order (asc/desc, default: desc)
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Parse query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 200)
        min_market_cap = request.args.get('min_market_cap', type=float)
        max_market_cap = request.args.get('max_market_cap', type=float)
        category = request.args.get('category')
        has_data_score = request.args.get('has_data_score')
        sort_by = request.args.get('sort_by', 'market_cap')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = AutomatedProject.query.filter_by(data_source='automated')
        
        # Apply filters
        if min_market_cap is not None:
            query = query.filter(AutomatedProject.market_cap >= min_market_cap)
        if max_market_cap is not None:
            query = query.filter(AutomatedProject.market_cap <= max_market_cap)
        if category:
            query = query.filter(AutomatedProject.category == category)
        if has_data_score is not None:
            has_data = has_data_score.lower() == 'true'
            query = query.filter(AutomatedProject.has_data_score == has_data)
        
        # Apply sorting
        sort_field = getattr(AutomatedProject, sort_by, AutomatedProject.market_cap)
        if sort_order.lower() == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
        
        # Execute query with pagination
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format response
        projects = [project.to_dict() for project in paginated.items]
        
        response = {
            'projects': projects,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            },
            'filters_applied': {
                'min_market_cap': min_market_cap,
                'max_market_cap': max_market_cap,
                'category': category,
                'has_data_score': has_data_score,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Failed to get automated projects: {e}")
        return jsonify({
            'error': 'Query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated/<project_id>', methods=['GET'])
def get_automated_project(project_id):
    """
    Get specific automated project by ID
    
    Returns detailed project information including all scores and metadata
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Find project by ID
        project = AutomatedProject.query.filter_by(
            id=project_id,
            data_source='automated'
        ).first()
        
        if not project:
            return jsonify({
                'error': 'Project not found',
                'message': f'No automated project found with ID: {project_id}'
            }), 404
        
        # Return detailed project data
        return jsonify({
            'project': project.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        return jsonify({
            'error': 'Query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated/<project_id>/refresh', methods=['POST'])
def refresh_automated_project(project_id):
    """
    Refresh market data for a specific automated project
    
    Fetches latest data from CoinGecko and updates the project scores
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None or not data_fetcher:
        return jsonify({
            'error': 'V2 services not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Find existing project
        project = AutomatedProject.query.filter_by(
            id=project_id,
            data_source='automated'
        ).first()
        
        if not project:
            return jsonify({
                'error': 'Project not found',
                'message': f'No automated project found with ID: {project_id}'
            }), 404
        
        if not project.coingecko_id:
            return jsonify({
                'error': 'Cannot refresh',
                'message': 'Project has no CoinGecko ID'
            }), 400
        
        # Fetch fresh data
        logger.info(f"Refreshing project {project_id} (CoinGecko ID: {project.coingecko_id})")
        fresh_data = data_fetcher.fetch_single_project(project.coingecko_id)
        
        if not fresh_data:
            return jsonify({
                'error': 'Refresh failed',
                'message': 'Could not fetch fresh data from CoinGecko'
            }), 502
        
        # Update project with fresh data (preserving data score)
        old_data_score = project.data_score
        old_accumulation_signal = project.accumulation_signal
        old_has_data_score = project.has_data_score
        
        for key, value in fresh_data.items():
            if hasattr(project, key) and key not in ['id', 'data_score', 'accumulation_signal', 'has_data_score']:
                setattr(project, key, value)
        
        # Restore data score components
        project.data_score = old_data_score
        project.accumulation_signal = old_accumulation_signal
        project.has_data_score = old_has_data_score
        
        # Recalculate scores
        project.update_all_scores()
        
        # Save to database
        db.session.commit()
        
        logger.info(f"Successfully refreshed project {project_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Project data refreshed successfully',
            'project': project.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to refresh project {project_id}: {e}")
        return jsonify({
            'error': 'Refresh failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/ingestion/status', methods=['GET'])
def get_ingestion_status():
    """
    Get current ingestion status and history
    
    Returns information about recent ingestion runs and service status
    """
    if not V2_DEPENDENCIES_AVAILABLE or not ingestion_manager:
        return jsonify({
            'error': 'V2 services not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        status = ingestion_manager.get_ingestion_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}")
        return jsonify({
            'error': 'Status query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/service/stats', methods=['GET'])
def get_service_stats():
    """
    Get comprehensive service statistics
    
    Returns information about API usage, cache stats, and service health
    """
    if not V2_DEPENDENCIES_AVAILABLE:
        return jsonify({
            'error': 'V2 services not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        stats = {
            'v2_status': 'active',
            'database_available': db is not None,
            'api_services_available': data_fetcher is not None
        }
        
        if data_fetcher:
            stats['data_fetcher'] = data_fetcher.get_service_stats()
        
        if ingestion_manager:
            stats['ingestion_manager'] = ingestion_manager.get_ingestion_status()
        
        if db is not None:
            try:
                # Get database stats
                total_projects = AutomatedProject.query.count()
                automated_projects = AutomatedProject.query.filter_by(data_source='automated').count()
                projects_with_data = AutomatedProject.query.filter_by(has_data_score=True).count()
                
                stats['database'] = {
                    'total_projects': total_projects,
                    'automated_projects': automated_projects,
                    'manual_projects': total_projects - automated_projects,
                    'projects_with_data_score': projects_with_data
                }
            except Exception as e:
                stats['database_error'] = str(e)
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        return jsonify({
            'error': 'Stats query failed',
            'message': str(e)
        }), 500

# V2 CSV Analysis API Endpoints
if V2_DEPENDENCIES_AVAILABLE:
    try:
        from .scoring.csv_analyzer import CSVAnalyzer, CSVFormatValidator
        from .models.automated_project import CSVData
        from datetime import datetime
        
        logger.info("CSV analysis services initialized successfully")
        
    except ImportError as e:
        logger.warning(f"CSV analysis services not available: {e}")
        CSVAnalyzer = None
        CSVFormatValidator = None
    except Exception as e:
        logger.error(f"CSV analysis services initialization failed: {e}")
        CSVAnalyzer = None
        CSVFormatValidator = None
else:
    CSVAnalyzer = None
    CSVFormatValidator = None

@app.route('/api/v2/csv/validate', methods=['POST'])
def validate_csv():
    """
    Validate CSV format before upload (US-06)
    
    Request body:
    {
        "csv_data": "time,close,Volume Delta (Close)\n2024-01-01,100,50\n..."
    }
    
    Returns validation results and preview of parsed data
    """
    if not V2_DEPENDENCIES_AVAILABLE or not CSVFormatValidator:
        return jsonify({
            'error': 'CSV analysis not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        request_data = request.get_json()
        if not request_data or 'csv_data' not in request_data:
            return jsonify({
                'error': 'Missing CSV data',
                'message': 'Request must include csv_data field'
            }), 400
        
        csv_text = request_data['csv_data']
        if not csv_text or not csv_text.strip():
            return jsonify({
                'error': 'Empty CSV data',
                'message': 'CSV data cannot be empty'
            }), 400
        
        # Validate and preview CSV
        validation_result = CSVFormatValidator.validate_csv_format_preview(csv_text)
        
        # Add requirements info
        validation_result['requirements'] = CSVFormatValidator.get_csv_requirements()
        
        return jsonify(validation_result)
        
    except Exception as e:
        logger.error(f"CSV validation failed: {e}")
        return jsonify({
            'error': 'Validation failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated/<project_id>/csv', methods=['POST'])
def upload_csv_data(project_id):
    """
    Upload CSV data for a specific project and calculate Data Score (US-06)
    
    Request body:
    {
        "csv_data": "time,close,Volume Delta (Close)\n2024-01-01,100,50\n..."
    }
    
    Processes CSV data, calculates accumulation signal, and updates project scores
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None or not CSVAnalyzer:
        return jsonify({
            'error': 'CSV analysis not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Find the project
        project = AutomatedProject.query.filter_by(
            id=project_id,
            data_source='automated'
        ).first()
        
        if not project:
            return jsonify({
                'error': 'Project not found',
                'message': f'No automated project found with ID: {project_id}'
            }), 404
        
        # Parse request data
        request_data = request.get_json()
        if not request_data or 'csv_data' not in request_data:
            return jsonify({
                'error': 'Missing CSV data',
                'message': 'Request must include csv_data field'
            }), 400
        
        csv_text = request_data['csv_data']
        if not csv_text or not csv_text.strip():
            return jsonify({
                'error': 'Empty CSV data',
                'message': 'CSV data cannot be empty'
            }), 400
        
        logger.info(f"Processing CSV upload for project {project_id} ({project.name})")
        
        # Analyze CSV data
        analysis_result = CSVAnalyzer.analyze_csv_data(csv_text)
        
        if not analysis_result['success']:
            return jsonify({
                'error': 'CSV analysis failed',
                'message': analysis_result['error'],
                'validation_errors': analysis_result['validation_errors']
            }), 400
        
        # Create or update CSV data record
        existing_csv = CSVData.query.filter_by(project_id=project_id).first()
        
        if existing_csv:
            # Update existing record
            existing_csv.raw_data = csv_text
            existing_csv.processed_data = analysis_result['processed_data']
            existing_csv.data_score = analysis_result['data_score']
            existing_csv.analysis_metadata = analysis_result['analysis_metadata']
            existing_csv.validation_errors = analysis_result['validation_errors']
            existing_csv.is_valid = analysis_result['is_valid']
            existing_csv.analyzed_at = datetime.utcnow()
            csv_record = existing_csv
        else:
            # Create new record
            csv_record = CSVData(
                project_id=project_id,
                raw_data=csv_text,
                processed_data=analysis_result['processed_data'],
                data_score=analysis_result['data_score'],
                analysis_metadata=analysis_result['analysis_metadata'],
                validation_errors=analysis_result['validation_errors'],
                is_valid=analysis_result['is_valid'],
                analyzed_at=datetime.utcnow()
            )
            db.session.add(csv_record)
        
        # Update project with new data score
        project.accumulation_signal = analysis_result['data_score']
        project.data_score = analysis_result['data_score']
        project.has_data_score = True
        
        # Recalculate all scores including omega score (AS-05)
        project.update_all_scores()
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"CSV analysis completed for project {project_id}: "
                   f"Data Score={analysis_result['data_score']:.1f}, "
                   f"Omega Score={project.omega_score:.1f if project.omega_score else 'N/A'}")
        
        # Return results
        response = {
            'status': 'success',
            'message': 'CSV data processed successfully',
            'project_id': project_id,
            'data_score': analysis_result['data_score'],
            'analysis_metadata': analysis_result['analysis_metadata'],
            'project_scores': {
                'narrative_score': project.narrative_score,
                'tokenomics_score': project.tokenomics_score,
                'data_score': project.data_score,
                'omega_score': project.omega_score,
                'omega_status': project.get_omega_status()
            },
            'csv_record_id': str(csv_record.id)
        }
        
        return jsonify(response)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"CSV upload failed for project {project_id}: {e}")
        return jsonify({
            'error': 'Upload failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated/<project_id>/csv', methods=['GET'])
def get_csv_analysis(project_id):
    """
    Get CSV analysis results for a specific project
    
    Returns current CSV data and analysis metadata if available
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Find the project
        project = AutomatedProject.query.filter_by(
            id=project_id,
            data_source='automated'
        ).first()
        
        if not project:
            return jsonify({
                'error': 'Project not found',
                'message': f'No automated project found with ID: {project_id}'
            }), 404
        
        # Find CSV data
        csv_record = CSVData.query.filter_by(project_id=project_id).first()
        
        if not csv_record:
            return jsonify({
                'has_csv_data': False,
                'project_id': project_id,
                'project_name': project.name,
                'message': 'No CSV data uploaded for this project'
            })
        
        # Return CSV analysis results
        response = {
            'has_csv_data': True,
            'project_id': project_id,
            'project_name': project.name,
            'csv_data': csv_record.to_dict(),
            'current_scores': {
                'data_score': project.data_score,
                'omega_score': project.omega_score,
                'omega_status': project.get_omega_status()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Failed to get CSV analysis for project {project_id}: {e}")
        return jsonify({
            'error': 'Query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/projects/automated/<project_id>/csv', methods=['DELETE'])
def delete_csv_data(project_id):
    """
    Remove CSV data and reset Data Score for a project
    
    Resets project to "Awaiting Data" state (AS-05)
    """
    if not V2_DEPENDENCIES_AVAILABLE or db is None:
        return jsonify({
            'error': 'V2 database not available',
            'message': 'V2 backend not properly initialized'
        }), 503
    
    try:
        # Find the project
        project = AutomatedProject.query.filter_by(
            id=project_id,
            data_source='automated'
        ).first()
        
        if not project:
            return jsonify({
                'error': 'Project not found',
                'message': f'No automated project found with ID: {project_id}'
            }), 404
        
        # Find and delete CSV data
        csv_record = CSVData.query.filter_by(project_id=project_id).first()
        
        if csv_record:
            db.session.delete(csv_record)
        
        # Reset project data score
        project.accumulation_signal = None
        project.data_score = None
        project.has_data_score = False
        
        # Recalculate scores (omega_score will become None due to missing data_score)
        project.update_all_scores()
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"CSV data removed for project {project_id}, reset to 'Awaiting Data' state")
        
        response = {
            'status': 'success',
            'message': 'CSV data removed successfully',
            'project_id': project_id,
            'project_scores': {
                'narrative_score': project.narrative_score,
                'tokenomics_score': project.tokenomics_score,
                'data_score': project.data_score,
                'omega_score': project.omega_score,
                'omega_status': project.get_omega_status()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete CSV data for project {project_id}: {e}")
        return jsonify({
            'error': 'Delete failed',
            'message': str(e)
        }), 500

# V2 Task Management API Endpoints with Fallback Support
if V2_DEPENDENCIES_AVAILABLE:
    try:
        from .tasks.fallback import get_task_manager
        from .tasks.scheduler import get_scheduler
        from .tasks.celery_config import celery_app
        
        # Get appropriate task manager (with fallback)
        task_manager = get_task_manager()
        
        # Try to initialize scheduler (may fallback)
        try:
            scheduler = get_scheduler(celery_app)
            logger.info("Full task management services initialized successfully")
        except Exception as e:
            logger.warning(f"Scheduler initialization failed, using fallback: {e}")
            scheduler = None
        
    except ImportError as e:
        logger.warning(f"Task management services not available: {e}")
        # Import fallback directly
        from .tasks.fallback import fallback_task_manager
        task_manager = fallback_task_manager
        scheduler = None
    except Exception as e:
        logger.error(f"Task management services initialization failed: {e}")
        # Import fallback directly
        from .tasks.fallback import fallback_task_manager
        task_manager = fallback_task_manager
        scheduler = None
else:
    logger.info("V2 dependencies not available, using fallback task management")
    try:
        from .tasks.fallback import fallback_task_manager
        task_manager = fallback_task_manager
        scheduler = None
    except Exception as e:
        logger.error(f"Fallback task manager failed to initialize: {e}")
        task_manager = None
        scheduler = None

@app.route('/api/v2/tasks/fetch-projects', methods=['POST'])
def trigger_fetch_projects():
    """
    Trigger manual project fetch task
    
    Request body (optional):
    {
        "filters": {
            "min_market_cap": 1000000,
            "max_market_cap": null,
            "min_volume_24h": 100000,
            "max_results": 1000
        },
        "save_to_database": true,
        "priority": 5
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        # Parse request parameters
        request_data = request.get_json() or {}
        filters = request_data.get('filters')
        save_to_db = request_data.get('save_to_database', True)
        priority = request_data.get('priority', 5)
        
        logger.info(f"Manual project fetch triggered with filters: {filters}")
        
        # Trigger task
        result = task_manager.trigger_manual_fetch(
            filters=filters,
            save_to_database=save_to_db,
            priority=priority
        )
        
        if result['status'] == 'failed':
            return jsonify(result), 503
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to trigger fetch task: {e}")
        return jsonify({
            'error': 'Task trigger failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/status', methods=['GET'])
def get_task_statuses():
    """
    Get status of all background tasks
    
    Query parameters:
    - task_id: Specific task ID to check (optional)
    - include_history: Include task execution history (default: true)
    - include_workers: Include worker statistics (default: true)
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        # Parse query parameters
        task_id = request.args.get('task_id')
        include_history = request.args.get('include_history', 'true').lower() == 'true'
        include_workers = request.args.get('include_workers', 'true').lower() == 'true'
        
        if task_id:
            # Get specific task status
            result = task_manager.get_task_status(task_id)
            return jsonify({
                'task_status': result,
                'requested_task_id': task_id
            })
        else:
            # Get all task statuses
            result = {
                'system_status': task_manager.get_system_status(),
                'all_tasks': task_manager.get_all_task_statuses()
            }
            
            if include_history:
                result['task_history'] = task_manager.get_task_history(limit=20)
            
            if include_workers:
                result['worker_stats'] = task_manager.get_worker_stats()
                result['queue_info'] = task_manager.get_queue_info()
            
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get task statuses: {e}")
        return jsonify({
            'error': 'Status query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/schedule', methods=['POST'])
def modify_task_schedule():
    """
    Create or modify task schedules
    
    Request body:
    {
        "action": "add|update|remove|enable|disable",
        "name": "schedule-name",
        "task": "task.name",
        "schedule_type": "interval|crontab|solar",
        "schedule_value": {...},
        "args": [],
        "kwargs": {},
        "options": {}
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not scheduler:
        return jsonify({
            'error': 'Task scheduling not available',
            'message': 'Background task scheduler not properly initialized'
        }), 503
    
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'error': 'Missing request data',
                'message': 'Request body is required'
            }), 400
        
        action = request_data.get('action')
        name = request_data.get('name')
        
        if not action or not name:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'action and name are required'
            }), 400
        
        logger.info(f"Schedule {action} requested for '{name}'")
        
        if action == 'add':
            # Add new schedule
            required_fields = ['task', 'schedule_type', 'schedule_value']
            for field in required_fields:
                if field not in request_data:
                    return jsonify({
                        'error': f'Missing required field: {field}',
                        'message': f'{field} is required for add action'
                    }), 400
            
            success = scheduler.add_schedule(
                name=name,
                task=request_data['task'],
                schedule_type=request_data['schedule_type'],
                schedule_value=request_data['schedule_value'],
                args=tuple(request_data.get('args', [])),
                kwargs=request_data.get('kwargs', {}),
                options=request_data.get('options', {})
            )
            
        elif action == 'update':
            # Update existing schedule
            success = scheduler.update_schedule(
                name=name,
                schedule_type=request_data.get('schedule_type'),
                schedule_value=request_data.get('schedule_value'),
                args=tuple(request_data['args']) if 'args' in request_data else None,
                kwargs=request_data.get('kwargs'),
                options=request_data.get('options'),
                enabled=request_data.get('enabled')
            )
            
        elif action == 'remove':
            # Remove schedule
            success = scheduler.remove_schedule(name)
            
        elif action == 'enable':
            # Enable schedule
            success = scheduler.enable_schedule(name)
            
        elif action == 'disable':
            # Disable schedule
            success = scheduler.disable_schedule(name)
            
        else:
            return jsonify({
                'error': 'Invalid action',
                'message': f'Action must be one of: add, update, remove, enable, disable'
            }), 400
        
        if success:
            return jsonify({
                'status': 'success',
                'action': action,
                'schedule_name': name,
                'message': f'Schedule {action} completed successfully'
            })
        else:
            return jsonify({
                'status': 'failed',
                'action': action,
                'schedule_name': name,
                'message': f'Schedule {action} failed'
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to modify schedule: {e}")
        return jsonify({
            'error': 'Schedule modification failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/schedule', methods=['GET'])
def get_task_schedules():
    """
    Get task schedule information
    
    Query parameters:
    - name: Specific schedule name (optional)
    """
    if not V2_DEPENDENCIES_AVAILABLE or not scheduler:
        return jsonify({
            'error': 'Task scheduling not available',
            'message': 'Background task scheduler not properly initialized'
        }), 503
    
    try:
        schedule_name = request.args.get('name')
        
        if schedule_name:
            # Get specific schedule
            schedule_info = scheduler.get_schedule(schedule_name)
            if schedule_info:
                return jsonify({
                    'schedule': schedule_info,
                    'schedule_name': schedule_name
                })
            else:
                return jsonify({
                    'error': 'Schedule not found',
                    'message': f'No schedule found with name: {schedule_name}'
                }), 404
        else:
            # Get all schedules
            schedules = scheduler.list_schedules()
            return jsonify(schedules)
        
    except Exception as e:
        logger.error(f"Failed to get schedules: {e}")
        return jsonify({
            'error': 'Schedule query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/history', methods=['GET'])
def get_task_history():
    """
    Get task execution history
    
    Query parameters:
    - limit: Maximum number of entries to return (default: 50, max: 200)
    - task_name: Filter by specific task name (optional)
    - status: Filter by task status (optional)
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 50)), 200)
        task_name = request.args.get('task_name')
        status = request.args.get('status')
        
        # Get task history
        history = task_manager.get_task_history(limit=limit)
        
        # Apply filters if specified
        if task_name:
            history = [h for h in history if h.get('task_name') == task_name]
        
        if status:
            history = [h for h in history if h.get('status') == status]
        
        return jsonify({
            'task_history': history,
            'total_entries': len(history),
            'filters_applied': {
                'limit': limit,
                'task_name': task_name,
                'status': status
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get task history: {e}")
        return jsonify({
            'error': 'History query failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/cleanup', methods=['POST'])
def trigger_cleanup_task():
    """
    Trigger manual cleanup task
    
    Request body (optional):
    {
        "days_to_keep": 30,
        "priority": 3
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        request_data = request.get_json() or {}
        days_to_keep = request_data.get('days_to_keep', 30)
        priority = request_data.get('priority', 3)
        
        logger.info(f"Manual cleanup task triggered: keep {days_to_keep} days")
        
        # Trigger task
        result = task_manager.trigger_cleanup_task(
            days_to_keep=days_to_keep,
            priority=priority
        )
        
        if result['status'] == 'failed':
            return jsonify(result), 503
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to trigger cleanup task: {e}")
        return jsonify({
            'error': 'Task trigger failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/health-check', methods=['POST'])
def trigger_health_check_task():
    """
    Trigger manual health check task
    
    Request body (optional):
    {
        "priority": 5
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        request_data = request.get_json() or {}
        priority = request_data.get('priority', 5)
        
        logger.info("Manual health check task triggered")
        
        # Trigger task
        result = task_manager.trigger_health_check(priority=priority)
        
        if result['status'] == 'failed':
            return jsonify(result), 503
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to trigger health check task: {e}")
        return jsonify({
            'error': 'Task trigger failed',
            'message': str(e)
        }), 500

@app.route('/api/v2/tasks/test', methods=['POST'])
def trigger_test_task():
    """
    Trigger test task for validation
    
    Request body (optional):
    {
        "message": "Test message",
        "priority": 1
    }
    """
    if not V2_DEPENDENCIES_AVAILABLE or not task_manager:
        return jsonify({
            'error': 'Task management not available',
            'message': 'Background task system not properly initialized'
        }), 503
    
    try:
        request_data = request.get_json() or {}
        message = request_data.get('message', 'Manual test task')
        priority = request_data.get('priority', 1)
        
        logger.info(f"Test task triggered: {message}")
        
        # Trigger task
        result = task_manager.trigger_test_task(
            message=message,
            priority=priority
        )
        
        if result['status'] == 'failed':
            return jsonify(result), 503
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to trigger test task: {e}")
        return jsonify({
            'error': 'Task trigger failed',
            'message': str(e)
        }), 500

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    """Enhanced 404 handler with API support"""
    if '/api/' in str(error):
        return jsonify({'error': 'API endpoint not found', 'status': 404}), 404
    
    # For non-API requests, serve index.html for SPA routing (V1 behavior)
    static_folder_path = app.static_folder
    if static_folder_path:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
    
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    """Enhanced 500 handler with logging"""
    logger.error(f"Internal server error: {error}")
    
    if '/api/' in str(error):
        return jsonify({'error': 'Internal server error', 'status': 500}), 500
    
    return "Internal server error", 500

# Application factory pattern support
def create_app(config_name='development'):
    """Application factory for testing and deployment"""
    return app

if __name__ == '__main__':
    logger.info("Starting Project Omega V2 with V1 compatibility")
    logger.info(f"V2 Backend available: {db is not None}")
    logger.info("V1 functionality: 100% preserved")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
