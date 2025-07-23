"""
V2 Database Models
This package contains SQLAlchemy models for automated and manual projects.
"""

from .automated_project import AutomatedProject, CSVData

__version__ = "2.0.0"
__all__ = ['AutomatedProject', 'CSVData']