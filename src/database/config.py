"""
Database Configuration for Project Omega V2

Supports both SQLite (development) and PostgreSQL (production) environments.
Provides connection management and SQLAlchemy configuration.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# Create the declarative base for models
Base = declarative_base()

# Flask-SQLAlchemy db object will be set by Flask app
db = None

class DatabaseConfig:
    """Database configuration manager"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.database_url = self._get_database_url()
        self.engine = None
        self.session_factory = None
    
    def _get_database_url(self):
        """Get database URL based on environment"""
        if self.environment == 'production':
            # PostgreSQL configuration for production
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            name = os.getenv('DB_NAME', 'omega_v2')
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', '')
            
            # URL encode password to handle special characters
            encoded_password = quote_plus(password) if password else ''
            
            if encoded_password:
                return f"postgresql://{user}:{encoded_password}@{host}:{port}/{name}"
            else:
                return f"postgresql://{user}@{host}:{port}/{name}"
        else:
            # SQLite configuration for development
            db_path = os.path.join(os.getcwd(), 'data', 'omega_v2.db')
            # Ensure data directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return f"sqlite:///{db_path}"
    
    def create_engine(self, **kwargs):
        """Create SQLAlchemy engine with appropriate configuration"""
        default_config = {
            'echo': os.getenv('DB_ECHO', 'false').lower() == 'true',
            'pool_pre_ping': True,
        }
        
        if self.environment == 'development':
            # SQLite specific configuration
            default_config.update({
                'connect_args': {'check_same_thread': False}
            })
        else:
            # PostgreSQL specific configuration
            default_config.update({
                'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
                'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
                'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
                'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            })
        
        # Override with any provided kwargs
        default_config.update(kwargs)
        
        self.engine = create_engine(self.database_url, **default_config)
        return self.engine
    
    def create_session_factory(self):
        """Create session factory for database operations"""
        if not self.engine:
            self.create_engine()
        
        self.session_factory = sessionmaker(bind=self.engine)
        return self.session_factory
    
    def get_session(self):
        """Get a new database session"""
        if not self.session_factory:
            self.create_session_factory()
        
        return self.session_factory()
    
    def initialize_database(self):
        """Initialize database tables"""
        if not self.engine:
            self.create_engine()
        
        # Import models to ensure they're registered with Base
        from ..models.automated_project import AutomatedProject, CSVData
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
        return True
    
    def get_connection_info(self):
        """Get connection information for debugging"""
        return {
            'environment': self.environment,
            'database_url': self.database_url.replace(
                self.database_url.split('@')[0].split('://')[-1] + '@', 
                '***:***@'
            ) if '@' in self.database_url else self.database_url,
            'engine_created': self.engine is not None,
            'session_factory_created': self.session_factory is not None
        }

# Global database configuration instance
db_config = DatabaseConfig()

# Convenience functions for easy access
def get_engine():
    """Get the database engine"""
    return db_config.create_engine()

def get_session():
    """Get a new database session"""
    return db_config.get_session()

def init_db():
    """Initialize the database"""
    return db_config.initialize_database()

def get_db_info():
    """Get database connection information"""
    return db_config.get_connection_info()