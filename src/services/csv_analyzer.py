# src/services/csv_analyzer.py

import pandas as pd
from scipy.stats import linregress
from typing import Dict, Any
import yaml
import logging
import io  # <-- Moved to top

logger = logging.getLogger(__name__)


class CSVAnalyzer:
    """
    Analyzes user-pasted CSV data for Project Omega Data Score (AS-03).
    Validates, transforms, and scores the data per spec using external config.
    """

    REQUIRED_COLUMNS = ["time", "close", "Volume Delta (Close)"]

    def __init__(self, config_path: str = "config.yml"):
        """Initializes the analyzer by loading its configuration."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            self.rules = config["data_score_rules"]
            self.min_periods = self.rules["min_periods"]
            logger.info("CSVAnalyzer configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load CSVAnalyzer config: {e}")
            # Fallback for core functionality
            self.rules = {"divergence_scores": []}
            self.min_periods = 90

    def _score_divergence(self, price_slope: float, cvd_slope: float) -> float:
        """Scores divergence based on rules from the config file."""
        for rule in self.rules["divergence_scores"]:
            price_cond = rule["price_slope"]
            cvd_cond = rule["cvd_slope"]

            price_match = (
                (price_cond == "positive" and price_slope > 0)
                or (price_cond == "non_positive" and price_slope <= 0)
                or (price_cond == "any")
            )

            cvd_match = (
                (cvd_cond == "positive" and cvd_slope > 0)
                or (cvd_cond == "non_positive" and cvd_slope <= 0)
                or (cvd_cond == "any")
            )

            if price_match and cvd_match:
                return rule["score"]

        return 1.0  # Default fallback score

    def analyze(self, csv_text: str) -> Dict[str, Any]:
        """Runs the full validation, analysis, and scoring pipeline."""
        # 1. Parse
        try:
            df = pd.read_csv(io.StringIO(csv_text))
        except Exception as e:
            return {"success": False, "error": f"CSV parsing failed: {e}"}

        # 2. Validate columns and rows
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            return {
                "success": False,
                "error": f"Missing required columns: {', '.join(missing)}",
            }

        if len(df) < self.min_periods:
            return {
                "success": False,
                "error": f"Insufficient data: {len(df)} rows found, minimum is {self.min_periods}.",
            }

        # 3. Transform & Analyze
        df = df.copy()  # Avoid SettingWithCopyWarning
        df["CVD"] = df["Volume Delta (Close)"].cumsum()

        try:
            price_reg: Any = linregress(range(len(df)), df["close"])
            price_slope = price_reg.slope
            cvd_reg: Any = linregress(range(len(df)), df["CVD"])
            cvd_slope = cvd_reg.slope
        except Exception as e:
            return {
                "success": False,
                "error": f"Linear regression calculation failed: {e}",
            }

        # 4. Score using the externalized logic
        score = self._score_divergence(price_slope, cvd_slope)

        return {
            "success": True,
            "data_score": score,
            "accumulation_signal": score,  # Per AS-03, Data Score is the Accumulation Signal
            "price_slope": price_slope,
            "cvd_slope": cvd_slope,
            "n_periods": len(df),
        }
