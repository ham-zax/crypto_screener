# Temporary script to fetch and print all fields for selected projects

from src.database.config import get_session
from src.models.automated_project import AutomatedProject

def main():
    session = get_session()
    try:
        names = ["Bitcoin", "Ethereum", "Tether"]
        projects = (
            session.query(AutomatedProject)
            .filter(AutomatedProject.name.in_(names))
            .all()
        )
        if not projects:
            print("No matching projects found.")
            return
        for project in projects:
            print(f"--- Project: {project.name} ---")
            for k, v in project.to_dict().items():
                print(f"{k}: {v}")
            print()
    finally:
        session.close()

if __name__ == "__main__":
    main()