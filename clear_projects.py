import logging
from src.main import app, db

# Gracefully import the model
try:
    from src.models.automated_project import AutomatedProject

    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def clear_automated_projects():
    """Deletes all projects from the 'projects' table."""
    if not db or not MODEL_AVAILABLE:
        logger.error(
            "❌ Database or Project Model not available. Cannot clear projects."
        )
        return

    with app.app_context():
        try:
            logger.info("🗑️  Attempting to delete all projects...")
            num_deleted = db.session.query(AutomatedProject).delete()
            db.session.commit()
            logger.info(f"✅ Successfully deleted {num_deleted} project(s).")
        except Exception as e:
            logger.error(f"❌ An error occurred while clearing projects: {e}")
            db.session.rollback()


if __name__ == "__main__":
    clear_automated_projects()
