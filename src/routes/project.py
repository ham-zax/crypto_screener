from flask import Blueprint, request, jsonify
from src.models.project import Project
from src.database import db

project_bp = Blueprint("project_bp", __name__)

@project_bp.route("/projects", methods=["POST"])
def add_project():
    data = request.json
    new_project = Project(
        name=data["name"],
        hot_sector=data.get("hot_sector"),
        value_proposition=data.get("value_proposition"),
        backing_team=data.get("backing_team"),
        initial_float=data.get("initial_float"),
        real_utility=data.get("real_utility"),
        fair_launch_vesting=data.get("fair_launch_vesting"),
        macro_accumulation_divergence=data.get("macro_accumulation_divergence"),
        spot_cvd_ma_cvd=data.get("spot_cvd_ma_cvd"),
        market_structure_shift_retest=data.get("market_structure_shift_retest")
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({"message": "Project added successfully!"}), 201

@project_bp.route("/projects", methods=["GET"])
def get_all_projects():
    projects = Project.query.all()
    output = []
    for project in projects:
        project_data = {
            "id": project.id,
            "name": project.name,
            "hot_sector": project.hot_sector,
            "value_proposition": project.value_proposition,
            "backing_team": project.backing_team,
            "initial_float": project.initial_float,
            "real_utility": project.real_utility,
            "fair_launch_vesting": project.fair_launch_vesting,
            "macro_accumulation_divergence": project.macro_accumulation_divergence,
            "spot_cvd_ma_cvd": project.spot_cvd_ma_cvd,
            "market_structure_shift_retest": project.market_structure_shift_retest
        }
        output.append(project_data)
    return jsonify({"projects": output})

@project_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    project_data = {
        "id": project.id,
        "name": project.name,
        "hot_sector": project.hot_sector,
        "value_proposition": project.value_proposition,
        "backing_team": project.backing_team,
        "initial_float": project.initial_float,
        "real_utility": project.real_utility,
        "fair_launch_vesting": project.fair_launch_vesting,
        "macro_accumulation_divergence": project.macro_accumulation_divergence,
        "spot_cvd_ma_cvd": project.spot_cvd_ma_cvd,
        "market_structure_shift_retest": project.market_structure_shift_retest
    }
    return jsonify({"project": project_data})

@project_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json
    project.name = data.get("name", project.name)
    project.hot_sector = data.get("hot_sector", project.hot_sector)
    project.value_proposition = data.get("value_proposition", project.value_proposition)
    project.backing_team = data.get("backing_team", project.backing_team)
    project.initial_float = data.get("initial_float", project.initial_float)
    project.real_utility = data.get("real_utility", project.real_utility)
    project.fair_launch_vesting = data.get("fair_launch_vesting", project.fair_launch_vesting)
    project.macro_accumulation_divergence = data.get("macro_accumulation_divergence", project.macro_accumulation_divergence)
    project.spot_cvd_ma_cvd = data.get("spot_cvd_ma_cvd", project.spot_cvd_ma_cvd)
    project.market_structure_shift_retest = data.get("market_structure_shift_retest", project.market_structure_shift_retest)
    db.session.commit()
    return jsonify({"message": "Project updated successfully!"})

@project_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted successfully!"})


