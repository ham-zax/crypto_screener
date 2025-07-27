# Project Omega Summary

**Project "Omega"** is a crypto screening tool that automates the discovery and scoring of crypto assets.

**Core Functionality:**
1.  **Automated Data Ingestion:** It fetches project data from the CoinGecko API on a schedule.
2.  **Scoring Engine:** It calculates a final "Omega Score" based on three components:
    *   **Narrative Score:** Automatically calculated based on the project's sector (e.g., AI, L1, GameFi).
    *   **Tokenomics Score:** Automatically calculated based on market cap and token supply metrics.
    *   **Data Score:** Manually generated when an analyst pastes specific CSV data (from TradingView) into the UI. This score is crucial and required for the final Omega Score calculation.
3.  **Backend & API:** Built with Python, Flask, and SQLAlchemy. It uses Celery and Redis for asynchronous background tasks (like fetching data).
4.  **Database:** The system uses a database (SQLite for development, PostgreSQL for production) to store project data and scores.
5.  **Frontend:** A simple web interface (`index.html`, `app.js`) allows users to view, filter, and interact with the scored assets, including the data-paste functionality.

**Key Files:**
*   `specsV2.md`: The main specification document outlining all business logic and scoring rules.
*   `config.yml`: Contains the parameters for the scoring algorithms (e.g., market cap tiers, sector scores).
*   `src/main.py`: The main Flask application entry point.
*   `src/services/scoring_engine.py`: Likely contains the core logic for calculating the various scores.
*   `src/api/data_fetcher.py`: Handles fetching data from external APIs like CoinGecko.
*   `src/tasks/scheduled_tasks.py`: Defines the recurring background jobs for data ingestion.
*   `src/static/index.html`: The main user interface.
