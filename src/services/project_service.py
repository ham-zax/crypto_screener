"""
Project Service Layer for Project Omega V2

Handles business logic and orchestration related to the AutomatedProject model.
This decouples the business logic from the data model, following the
Service Layer architectural pattern.
"""
import logging
from datetime import datetime
from ..models.automated_project import AutomatedProject
from ..scoring.automated_scoring import AutomatedScoringEngine

logger = logging.getLogger(__name__)

def _calculate_narrative_score(project: AutomatedProject) -> None:
    """Calculate Narrative Score as average of components (AS-01)"""
    logger.debug(f"Calculating narrative score for project {project.id}")
    components = [project.sector_strength, project.value_proposition, project.backing_team]
    valid_components = [c for c in components if c is not None]
    if not valid_components:
        project.narrative_score = None
        logger.debug("No valid narrative components found.")
        return
    project.narrative_score = sum(valid_components) / len(valid_components)
    logger.debug(f"Narrative score set to {project.narrative_score}")

def _calculate_tokenomics_score(project: AutomatedProject) -> None:
    """Calculate Tokenomics Score as average of components (AS-02)"""
    logger.debug(f"Calculating tokenomics score for project {project.id}")
    components = [project.valuation_potential, project.token_utility, project.supply_risk]
    valid_components = [c for c in components if c is not None]
    if not valid_components:
        project.tokenomics_score = None
        logger.debug("No valid tokenomics components found.")
        return
    project.tokenomics_score = sum(valid_components) / len(valid_components)
    logger.debug(f"Tokenomics score set to {project.tokenomics_score}")

def _calculate_data_score(project: AutomatedProject) -> None:
    """Set Data Score equal to Accumulation Signal (AS-03)"""
    logger.debug(f"Calculating data score for project {project.id}")
    if project.accumulation_signal is not None:
        project.data_score = project.accumulation_signal
        project.has_data_score = True
        logger.debug(f"Data score set to {project.data_score}")
    else:
        project.data_score = None
        project.has_data_score = False
        logger.debug("No accumulation signal found; data score set to None.")

def update_all_scores(project: AutomatedProject) -> AutomatedProject:
    """
    Recalculates all derived scores for a given project instance.
    This is the primary orchestration function for project scoring.

    Args:
        project: The AutomatedProject instance to update.

    Returns:
        The updated AutomatedProject instance.
    """
    logger.info(f"Updating all scores for project {project.id}")
    _calculate_narrative_score(project)
    _calculate_tokenomics_score(project)
    _calculate_data_score(project)

    scores = [project.narrative_score, project.tokenomics_score, project.data_score]
    # Robustly sum scores, treating None as 0.0 to avoid TypeError
    if all(score is not None for score in scores):
        project.omega_score = sum(s if s is not None else 0.0 for s in scores) / 3
        logger.debug(f"Omega score set to {project.omega_score}")
    else:
        project.omega_score = None
        logger.debug("Not all pillar scores present; omega score set to None.")

    project.last_updated = datetime.utcnow()
    logger.info(f"Scores updated for project {project.id} at {project.last_updated}")
    return project