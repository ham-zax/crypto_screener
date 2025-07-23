"""
Migration Runner for Database Schema Changes

Executes migrations safely with validation, rollback support, and cross-platform compatibility.
Handles both SQLite (development) and PostgreSQL (production) environments.
"""

import os
import re
import hashlib
import logging
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from .version_manager import VersionManager

logger = logging.getLogger(__name__)

class MigrationRunner:
    """
    Executes database migrations with comprehensive safety features
    
    Features:
    - Safe migration execution with transactions
    - Automatic rollback on failure
    - Cross-database compatibility
    - Performance tracking
    - Integrity validation
    """
    
    def __init__(self, engine, migrations_path: str = None):
        """
        Initialize migration runner
        
        Args:
            engine: SQLAlchemy engine instance
            migrations_path: Path to migration files directory
        """
        self.engine = engine
        self.version_manager = VersionManager(engine)
        
        # Set migrations path
        if migrations_path:
            self.migrations_path = Path(migrations_path)
        else:
            current_dir = Path(__file__).parent
            self.migrations_path = current_dir / 'scripts'
        
        # Ensure migrations directory exists
        self.migrations_path.mkdir(exist_ok=True)
        
        # Database type detection for compatibility
        self.db_type = self._detect_database_type()
        
        logger.info(f"Migration runner initialized for {self.db_type} database")
        logger.info(f"Migrations path: {self.migrations_path}")
    
    def _detect_database_type(self) -> str:
        """Detect database type from engine URL"""
        url = str(self.engine.url)
        if url.startswith('sqlite'):
            return 'sqlite'
        elif url.startswith('postgresql'):
            return 'postgresql'
        elif url.startswith('mysql'):
            return 'mysql'
        else:
            return 'unknown'
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of migration file"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _parse_migration_file(self, file_path: Path) -> Dict:
        """
        Parse migration file to extract metadata and SQL
        
        Expected format:
        -- Migration: 001_initial_schema
        -- Description: Create initial AutomatedProject and CSVData tables
        -- Rollback: DROP TABLE csv_data; DROP TABLE projects;
        
        SQL content here...
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from comments
            metadata = {
                'file_path': file_path,
                'version': file_path.stem,
                'name': '',
                'description': '',
                'rollback_sql': '',
                'sql': content
            }
            
            # Parse header comments
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-- Migration:'):
                    metadata['name'] = line.replace('-- Migration:', '').strip()
                elif line.startswith('-- Description:'):
                    metadata['description'] = line.replace('-- Description:', '').strip()
                elif line.startswith('-- Rollback:'):
                    metadata['rollback_sql'] = line.replace('-- Rollback:', '').strip()
            
            # Use filename as version if not specified
            if not metadata['name']:
                metadata['name'] = file_path.stem
            
            # Extract main SQL (remove comment lines)
            sql_lines = [line for line in lines if not line.strip().startswith('--')]
            metadata['sql'] = '\n'.join(sql_lines).strip()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to parse migration file {file_path}: {e}")
            raise
    
    def _get_migration_files(self) -> List[Path]:
        """Get list of migration files sorted by version"""
        try:
            pattern = re.compile(r'^\d{3}_.*\.sql$')
            files = [
                f for f in self.migrations_path.glob('*.sql')
                if pattern.match(f.name)
            ]
            return sorted(files, key=lambda x: x.name)
        except Exception as e:
            logger.error(f"Failed to get migration files: {e}")
            return []
    
    def _execute_sql_safely(self, sql: str, migration_name: str) -> Tuple[bool, Optional[str]]:
        """
        Execute SQL with proper transaction handling and error recovery
        
        Args:
            sql: SQL to execute
            migration_name: Name for logging
            
        Returns:
            (success, error_message)
        """
        connection = self.engine.connect()
        transaction = connection.begin()
        
        try:
            # Split SQL into individual statements for better error reporting
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements):
                try:
                    connection.execute(text(statement))
                    logger.debug(f"Executed statement {i+1}/{len(statements)} for {migration_name}")
                except Exception as e:
                    logger.error(f"Failed at statement {i+1} in {migration_name}: {statement[:100]}...")
                    raise
            
            transaction.commit()
            logger.info(f"Successfully executed migration: {migration_name}")
            return True, None
            
        except Exception as e:
            transaction.rollback()
            error_msg = f"Migration {migration_name} failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        finally:
            connection.close()
    
    def apply_migration(self, migration_file: Path) -> Dict:
        """
        Apply a single migration file
        
        Args:
            migration_file: Path to migration file
            
        Returns:
            Migration result with metadata
        """
        start_time = time.time()
        
        try:
            # Parse migration file
            migration_data = self._parse_migration_file(migration_file)
            version = migration_data['version']
            
            logger.info(f"Applying migration {version}: {migration_data['name']}")
            
            # Check if already applied
            if self.version_manager.is_version_applied(version):
                return {
                    'success': True,
                    'version': version,
                    'name': migration_data['name'],
                    'status': 'already_applied',
                    'execution_time_ms': 0
                }
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(migration_file)
            
            # Execute migration SQL
            success, error = self._execute_sql_safely(
                migration_data['sql'], 
                migration_data['name']
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if success:
                # Record successful migration
                self.version_manager.record_migration(
                    version=version,
                    name=migration_data['name'],
                    rollback_sql=migration_data['rollback_sql'],
                    execution_time_ms=execution_time_ms,
                    checksum=checksum
                )
                
                return {
                    'success': True,
                    'version': version,
                    'name': migration_data['name'],
                    'status': 'applied',
                    'execution_time_ms': execution_time_ms
                }
            else:
                return {
                    'success': False,
                    'version': version,
                    'name': migration_data['name'],
                    'status': 'failed',
                    'error': error,
                    'execution_time_ms': execution_time_ms
                }
                
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Migration application failed: {e}")
            
            return {
                'success': False,
                'version': migration_file.stem,
                'name': str(migration_file),
                'status': 'failed',
                'error': str(e),
                'execution_time_ms': execution_time_ms
            }
    
    def run_migrations(self, target_version: str = None) -> Dict:
        """
        Run all pending migrations up to target version
        
        Args:
            target_version: Stop at this version (None = run all)
            
        Returns:
            Migration run results
        """
        logger.info("Starting migration run")
        start_time = time.time()
        
        try:
            # Get migration files
            migration_files = self._get_migration_files()
            if not migration_files:
                return {
                    'success': True,
                    'message': 'No migration files found',
                    'applied_migrations': [],
                    'total_time_ms': 0
                }
            
            # Filter to target version if specified
            if target_version:
                migration_files = [
                    f for f in migration_files 
                    if f.stem <= target_version
                ]
            
            # Apply migrations in order
            applied_migrations = []
            failed_migration = None
            
            for migration_file in migration_files:
                result = self.apply_migration(migration_file)
                applied_migrations.append(result)
                
                if not result['success']:
                    failed_migration = result
                    break
                
                # Skip already applied migrations
                if result['status'] == 'already_applied':
                    continue
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            if failed_migration:
                return {
                    'success': False,
                    'message': f"Migration failed at {failed_migration['version']}",
                    'applied_migrations': applied_migrations,
                    'failed_migration': failed_migration,
                    'total_time_ms': total_time_ms
                }
            else:
                successful_migrations = [
                    m for m in applied_migrations 
                    if m['status'] == 'applied'
                ]
                
                return {
                    'success': True,
                    'message': f"Applied {len(successful_migrations)} migrations successfully",
                    'applied_migrations': applied_migrations,
                    'total_time_ms': total_time_ms,
                    'current_version': self.version_manager.get_current_version()
                }
                
        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Migration run failed: {e}")
            
            return {
                'success': False,
                'message': f"Migration run failed: {str(e)}",
                'error': str(e),
                'total_time_ms': total_time_ms
            }
    
    def rollback_migration(self, target_version: str) -> Dict:
        """
        Rollback migrations to target version
        
        Args:
            target_version: Version to rollback to
            
        Returns:
            Rollback operation results
        """
        logger.info(f"Starting rollback to version {target_version}")
        start_time = time.time()
        
        try:
            # Get migrations to rollback
            rollback_migrations = self.version_manager.get_versions_to_rollback(target_version)
            
            if not rollback_migrations:
                return {
                    'success': True,
                    'message': f'Already at or before version {target_version}',
                    'rolled_back_migrations': [],
                    'total_time_ms': 0
                }
            
            # Execute rollbacks in reverse order
            rolled_back = []
            failed_rollback = None
            
            for migration in rollback_migrations:
                if not migration['rollback_sql']:
                    failed_rollback = {
                        'version': migration['version'],
                        'error': 'No rollback SQL available'
                    }
                    break
                
                # Execute rollback SQL
                success, error = self._execute_sql_safely(
                    migration['rollback_sql'],
                    f"Rollback {migration['version']}"
                )
                
                if success:
                    # Remove from version tracking
                    self.version_manager.remove_migration_record(migration['version'])
                    rolled_back.append(migration['version'])
                    logger.info(f"Rolled back migration {migration['version']}")
                else:
                    failed_rollback = {
                        'version': migration['version'],
                        'error': error
                    }
                    break
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            if failed_rollback:
                return {
                    'success': False,
                    'message': f"Rollback failed at {failed_rollback['version']}",
                    'rolled_back_migrations': rolled_back,
                    'failed_rollback': failed_rollback,
                    'total_time_ms': total_time_ms
                }
            else:
                return {
                    'success': True,
                    'message': f"Successfully rolled back {len(rolled_back)} migrations",
                    'rolled_back_migrations': rolled_back,
                    'total_time_ms': total_time_ms,
                    'current_version': self.version_manager.get_current_version()
                }
                
        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Rollback failed: {e}")
            
            return {
                'success': False,
                'message': f"Rollback operation failed: {str(e)}",
                'error': str(e),
                'total_time_ms': total_time_ms
            }
    
    def get_migration_status(self) -> Dict:
        """
        Get comprehensive migration status
        
        Returns:
            Status information including pending migrations
        """
        try:
            current_version = self.version_manager.get_current_version()
            applied_versions = self.version_manager.get_applied_versions()
            migration_files = self._get_migration_files()
            
            # Find pending migrations
            applied_version_strings = [v['version'] for v in applied_versions]
            pending_migrations = [
                {
                    'version': f.stem,
                    'name': f.name,
                    'file_path': str(f)
                }
                for f in migration_files
                if f.stem not in applied_version_strings
            ]
            
            # Validate migration integrity
            integrity_check = self.version_manager.validate_migration_integrity()
            
            return {
                'current_version': current_version,
                'database_type': self.db_type,
                'applied_migrations': applied_versions,
                'pending_migrations': pending_migrations,
                'total_migration_files': len(migration_files),
                'integrity_check': integrity_check,
                'migrations_path': str(self.migrations_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                'error': str(e),
                'database_type': self.db_type,
                'migrations_path': str(self.migrations_path)
            }