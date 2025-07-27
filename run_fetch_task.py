# run_fetch_task.py
import logging
import os
import sys

# This is necessary to allow the script to find your project's modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# We must initialize the database and app context *before* importing tasks that use them
print("--- Initializing Flask app context and database ---")
from main import app
from src.tasks.scheduled_tasks import _core_fetch_and_save_logic

# Configure basic logging to see all output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_task_manually():
    print("\n--- Manually executing the _core_fetch_and_save_logic function ---")

    with app.app_context():
        try:
            default_filters = {
                "min_market_cap": 1000000,
                "min_volume_24h": 100000,
                "max_results": 250,  # Keep it small for a test run
            }
            result = _core_fetch_and_save_logic(
                default_filters, save_to_database=True, batch_size=50
            )

            print("\n--- TASK COMPLETED SUCCESSFULLY ---")
            print(result)
        except Exception as e:
            print("\n--- TASK FAILED WITH A CRITICAL EXCEPTION ---")
            logging.exception(e)


if __name__ == "__main__":
    run_task_manually()
