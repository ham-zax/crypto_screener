"""
Version Manager for Database Migrations

Tracks migration versions and provides rollback capabilities.
Supports both SQLite and PostgreSQL databases.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import Column, String, DateTime, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Separate base for migration tracking to avoid circular imports
MigrationBase = declarative_base()

class MigrationVersion(MigrationBase):
    """Model for tracking applied migrations"""
    __tablename__ = 'migration_versions'
    
    version = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)
    rollback_sql = Column(Text)  # SQL for rolling back this migration
    checksum = Column(String(64))  # For integrity verification
    execution_time_ms = Column(Integer)  # Performance tracking

class VersionManager:
    """
    Manages database migration versions with rollback support
    
    Features:
    - Version tracking with timestamps
    - Rollback SQL storage
    - Migration integrity verification
    - Cross-database compatibility
    """
    
    def __init__(self, engine):
        """
        Initialize version manager with database engine
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.session_factory = sessionmaker(bind=engine)
        self._ensure_version_table()
    
    def _ensure_version_table(self):
        """Create migration version tracking table if it doesn't exist"""
        try:
            MigrationBase.metadata.create_all(self.engine)
            logger.info("Migration version table ensured")
        except Exception as e:
            logger.error(f"Failed to create migration version table: {e}")
            raise
    
    def get_current_version(self) -> Optional[str]:
        """
        Get the current migration version
        
        Returns:
            Current version string or None if no migrations applied
        """
        session = self.session_factory()
        try:
            latest = session.query(MigrationVersion)\
                          .order_by(MigrationVersion.applied_at.desc())\
                          .first()
            return latest.version if latest else None
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return None
        finally:
            session.close()
    
    def get_applied_versions(self) -> List[Dict]:
        """
        Get list of all applied migrations
        
        Returns:
            List of migration records with metadata
        """
        session = self.session_factory()
        try:
            versions = session.query(MigrationVersion)\
                            .order_by(MigrationVersion.applied_at.asc())\
                            .all()
            
            return [{
                'version': v.version,
                'name': v.name,
                'applied_at': v.applied_at.isoformat(),
                'execution_time_ms': v.execution_time_ms,
                'has_rollback': bool(v.rollback_sql)
            } for v in versions]
        except Exception as e:
            logger.error(f"Failed to get applied versions: {e}")
            return []
        finally:
            session.close()
    
    def is_version_applied(self, version: str) -> bool:
        """
        Check if a specific version has been applied
        
        Args:
            version: Version string to check
            
        Returns:
            True if version is applied, False otherwise
        """
        session = self.session_factory()
        try:
            exists = session.query(MigrationVersion)\
                          .filter(MigrationVersion.version == version)\
                          .first() is not None
            return exists
        except Exception as e:
            logger.error(f"Failed to check version {version}: {e}")
            return False
        finally:
            session.close()
    
    def record_migration(self, version: str, name: str, rollback_sql: str = None, 
                        execution_time_ms: int = None, checksum: str = None):
        """
        Record a successfully applied migration
        
        Args:
            version: Migration version
            name: Migration name/description
            rollback_sql: SQL for rolling back this migration
            execution_time_ms: Execution time in milliseconds
            checksum: Migration file checksum for integrity
        """
        session = self.session_factory()
        try:
            migration_record = MigrationVersion(
                version=version,
                name=name,
                applied_at=datetime.utcnow(),
                rollback_sql=rollback_sql,
                execution_time_ms=execution_time_ms,
                checksum=checksum
            )
            
            session.add(migration_record)
            session.commit()
            
            logger.info(f"Recorded migration {version}: {name}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record migration {version}: {e}")
            raise
        finally:
            session.close()
    
    def remove_migration_record(self, version: str):
        """
        Remove a migration record (used during rollback)
        
        Args:
            version: Version to remove
        """
        session = self.session_factory()
        try:
            migration = session.query(MigrationVersion)\
                             .filter(MigrationVersion.version == version)\
                             .first()
            
            if migration:
                session.delete(migration)
                session.commit()
                logger.info(f"Removed migration record: {version}")
            else:
                logger.warning(f"Migration record not found: {version}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove migration record {version}: {e}")
            raise
        finally:
            session.close()
    
    def get_rollback_sql(self, version: str) -> Optional[str]:
        """
        Get rollback SQL for a specific version
        
        Args:
            version: Version to get rollback SQL for
            
        Returns:
            Rollback SQL string or None if not available
        """
        session = self.session_factory()
        try:
            migration = session.query(MigrationVersion)\
                             .filter(MigrationVersion.version == version)\
                             .first()
            
            return migration.rollback_sql if migration else None
        except Exception as e:
            logger.error(f"Failed to get rollback SQL for {version}: {e}")
            return None
        finally:
            session.close()
    
    def get_versions_to_rollback(self, target_version: str) -> List[Dict]:
        """
        Get list of versions that need to be rolled back to reach target version
        
        Args:
            target_version: Target version to rollback to
            
        Returns:
            List of versions to rollback (in reverse order)
        """
        session = self.session_factory()
        try:
            # Get target migration timestamp
            target_migration = session.query(MigrationVersion)\
                                   .filter(MigrationVersion.version == target_version)\
                                   .first()
            
            if not target_migration:
                logger.error(f"Target version {target_version} not found")
                return []
            
            # Get all migrations applied after target
            rollback_migrations = session.query(MigrationVersion)\
                                       .filter(MigrationVersion.applied_at > target_migration.applied_at)\
                                       .order_by(MigrationVersion.applied_at.desc())\
                                       .all()
            
            return [{
                'version': m.version,
                'name': m.name,
                'rollback_sql': m.rollback_sql,
                'applied_at': m.applied_at.isoformat()
            } for m in rollback_migrations]
            
        except Exception as e:
            logger.error(f"Failed to get rollback versions: {e}")
            return []
        finally:
            session.close()
    
    def validate_migration_integrity(self) -> Dict:
        """
        Validate the integrity of applied migrations
        
        Returns:
            Validation results with any issues found
        """
        session = self.session_factory()
        try:
            migrations = session.query(MigrationVersion)\
                              .order_by(MigrationVersion.applied_at.asc())\
                              .all()
            
            issues = []
            
            # Check for missing rollback SQL
            no_rollback = [m for m in migrations if not m.rollback_sql]
            if no_rollback:
                issues.append({
                    'type': 'missing_rollback',
                    'message': f'{len(no_rollback)} migrations have no rollback SQL',
                    'versions': [m.version for m in no_rollback]
                })
            
            # Check for duplicate versions
            versions = [m.version for m in migrations]
            duplicates = list(set([v for v in versions if versions.count(v) > 1]))
            if duplicates:
                issues.append({
                    'type': 'duplicate_versions',
                    'message': f'Duplicate migration versions found',
                    'versions': duplicates
                })
            
            return {
                'valid': len(issues) == 0,
                'total_migrations': len(migrations),
                'issues': issues,
                'current_version': migrations[-1].version if migrations else None
            }
            
        except Exception as e:
            logger.error(f"Failed to validate migration integrity: {e}")
            return {
                'valid': False,
                'error': str(e),
                'total_migrations': 0,
                'issues': [{'type': 'validation_error', 'message': str(e)}]
            }
        finally:
            session.close()
    
    def get_migration_history(self, limit: int = 50) -> List[Dict]:
        """
        Get migration history with detailed information
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of migration history records
        """
        session = self.session_factory()
        try:
            migrations = session.query(MigrationVersion)\
                              .order_by(MigrationVersion.applied_at.desc())\
                              .limit(limit)\
                              .all()
            
            return [{
                'version': m.version,
                'name': m.name,
                'applied_at': m.applied_at.isoformat(),
                'execution_time_ms': m.execution_time_ms,
                'has_rollback': bool(m.rollback_sql),
                'checksum': m.checksum
            } for m in migrations]
            
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
        finally:
            session.close()