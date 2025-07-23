"""
CSV Analysis Engine for Project Omega V2

Implements US-06 specification for CSV data analysis:
- CSV parsing and validation (AS-03a)
- Linear regression analysis for price and CVD trends
- Accumulation signal detection (AS-03b)
- Data Score calculation algorithm (AS-04)

Supports TradingView export format with required columns: Date, Close, CVD
"""

import io
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from scipy import stats
from scipy.stats import linregress

logger = logging.getLogger(__name__)

class CSVValidationError(Exception):
    """Custom exception for CSV validation errors"""
    pass

class CSVAnalyzer:
    """
    Main CSV analysis engine implementing V2 specification requirements
    
    Handles CSV parsing, validation, and accumulation signal calculation
    according to AS-03 and AS-04 specifications.
    """
    
    # Required column names as per V2 specification
    REQUIRED_COLUMNS = ['time', 'close', 'Volume Delta (Close)']
    MINIMUM_PERIODS = 90  # AS-03b requirement
    
    @classmethod
    def parse_and_validate_csv(cls, csv_text: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Parse CSV text and validate requirements (AS-03a)
        
        Validation rules:
        - Must contain required headers: time, close, Volume Delta (Close)
        - Must have at least 90 periods of data
        - Numeric data must be valid
        - Date parsing should be robust
        
        Args:
            csv_text: Raw CSV text from user input
            
        Returns:
            Tuple of (parsed_dataframe, error_message)
            - If successful: (DataFrame, None)
            - If failed: (None, error_message)
        """
        try:
            # Handle common CSV formatting issues
            csv_text = csv_text.strip()
            if not csv_text:
                return None, "Empty CSV data provided"
            
            # Parse CSV with flexible delimiter detection
            try:
                # Try comma first (most common)
                df = pd.read_csv(io.StringIO(csv_text), delimiter=',')
            except:
                try:
                    # Try semicolon (European format)
                    df = pd.read_csv(io.StringIO(csv_text), delimiter=';')
                except:
                    # Try tab
                    df = pd.read_csv(io.StringIO(csv_text), delimiter='\t')
            
            logger.info(f"Parsed CSV with {len(df)} rows and columns: {list(df.columns)}")
            
            # Clean column names (remove extra spaces, normalize case)
            df.columns = df.columns.str.strip()
            
            # Check for required headers with flexible matching
            missing_headers = []
            column_mapping = {}
            
            for required_col in cls.REQUIRED_COLUMNS:
                found = False
                for actual_col in df.columns:
                    # Flexible column matching
                    if cls._match_column_name(required_col, actual_col):
                        column_mapping[required_col] = actual_col
                        found = True
                        break
                
                if not found:
                    missing_headers.append(required_col)
            
            if missing_headers:
                available_cols = ', '.join(df.columns)
                return None, f"Missing required columns: {', '.join(missing_headers)}. Available columns: {available_cols}"
            
            # Rename columns to standard names
            df = df.rename(columns=column_mapping)
            
            # Minimum data requirement (90 periods)
            if len(df) < cls.MINIMUM_PERIODS:
                return None, f"Insufficient data: {len(df)} periods found, minimum {cls.MINIMUM_PERIODS} required"
            
            # Parse and validate time column
            try:
                df['time'] = pd.to_datetime(df['time'], errors='coerce')
                if df['time'].isna().any():
                    return None, "Invalid date format in time column"
            except Exception as e:
                return None, f"Date parsing error: {str(e)}"
            
            # Validate and convert numeric columns
            try:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['Volume Delta (Close)'] = pd.to_numeric(df['Volume Delta (Close)'], errors='coerce')
            except Exception as e:
                return None, f"Numeric conversion error: {str(e)}"
            
            # Check for invalid numeric data
            if df['close'].isna().any():
                return None, "Invalid or missing data in 'close' price column"
            
            if df['Volume Delta (Close)'].isna().any():
                return None, "Invalid or missing data in 'Volume Delta (Close)' column"
            
            # Check for non-positive prices
            if (df['close'] <= 0).any():
                return None, "Close prices must be positive values"
            
            # Sort by time to ensure chronological order
            df = df.sort_values('time').reset_index(drop=True)
            
            # Remove any duplicate timestamps
            duplicate_count = df.duplicated(subset=['time']).sum()
            if duplicate_count > 0:
                logger.warning(f"Removing {duplicate_count} duplicate timestamps")
                df = df.drop_duplicates(subset=['time'], keep='last').reset_index(drop=True)
            
            logger.info(f"CSV validation successful: {len(df)} periods from {df['time'].min()} to {df['time'].max()}")
            return df, None
            
        except Exception as e:
            logger.error(f"CSV parsing failed: {str(e)}")
            return None, f"CSV parsing error: {str(e)}"
    
    @staticmethod
    def _match_column_name(required: str, actual: str) -> bool:
        """
        Flexible column name matching to handle variations in CSV headers
        
        Args:
            required: Required column name
            actual: Actual column name from CSV
            
        Returns:
            True if columns match
        """
        # Normalize both names
        req_norm = required.lower().replace(' ', '').replace('_', '').replace('-', '')
        act_norm = actual.lower().replace(' ', '').replace('_', '').replace('-', '')
        
        # Direct match
        if req_norm == act_norm:
            return True
        
        # Special cases for common variations
        if required == 'time':
            return act_norm in ['time', 'date', 'datetime', 'timestamp']
        elif required == 'close':
            return act_norm in ['close', 'closeprice', 'price', 'closingprice']
        elif required == 'Volume Delta (Close)':
            return act_norm in [
                'volumedelta', 'volumedeltaclose', 'voledelta', 'voldelta', 'cvd',
                'cumulativevolumedelta', 'volumedelta(close)'
            ]
        
        return False
    
    @classmethod
    def calculate_accumulation_signal(cls, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate Data Score using linear regression analysis (AS-03b)
        
        Algorithm:
        1. Use last 90 periods for analysis
        2. Calculate price trend using Linear Regression slope of close prices
        3. Calculate CVD trend using Linear Regression slope of cumulative Volume Delta
        4. Analyze divergence patterns for accumulation signals
        5. Assign score based on AS-04 Data Score calculation rules
        
        Args:
            df: Validated DataFrame with time, close, and Volume Delta columns
            
        Returns:
            Tuple of (data_score, analysis_metadata)
        """
        try:
            # Use last 90 periods for analysis (AS-03b requirement)
            analysis_data = df.tail(cls.MINIMUM_PERIODS).copy().reset_index(drop=True)
            
            logger.info(f"Analyzing accumulation signal using {len(analysis_data)} periods")
            
            # Prepare data for linear regression
            x_values = np.arange(len(analysis_data))
            close_prices = analysis_data['close'].values
            volume_delta = analysis_data['Volume Delta (Close)'].values
            
            # 1. Calculate price trend using Linear Regression slope
            price_slope, price_intercept, price_r, price_p_value, price_std_err = linregress(x_values, close_prices)
            
            # 2. Calculate Cumulative Volume Delta trend
            analysis_data['cvd'] = analysis_data['Volume Delta (Close)'].cumsum()
            cvd_values = analysis_data['cvd'].values
            cvd_slope, cvd_intercept, cvd_r, cvd_p_value, cvd_std_err = linregress(x_values, cvd_values)
            
            # Calculate R-squared values for trend strength
            price_r_squared = price_r ** 2
            cvd_r_squared = cvd_r ** 2
            
            # 3. Calculate Data Score based on AS-04 rules
            data_score = cls._calculate_data_score(
                price_slope, cvd_slope, price_r_squared, cvd_r_squared
            )
            
            # Classify divergence type for reporting
            divergence_type = cls._classify_divergence(price_slope, cvd_slope)
            
            # Compile analysis metadata for transparency
            metadata = {
                'periods_analyzed': len(analysis_data),
                'analysis_period': {
                    'start_date': analysis_data['time'].iloc[0].isoformat(),
                    'end_date': analysis_data['time'].iloc[-1].isoformat()
                },
                'price_analysis': {
                    'slope': float(price_slope),
                    'r_squared': float(price_r_squared),
                    'p_value': float(price_p_value),
                    'trend_direction': 'positive' if price_slope > 0 else 'negative'
                },
                'cvd_analysis': {
                    'slope': float(cvd_slope),
                    'r_squared': float(cvd_r_squared),
                    'p_value': float(cvd_p_value),
                    'trend_direction': 'positive' if cvd_slope > 0 else 'negative'
                },
                'divergence_type': divergence_type,
                'data_score': float(data_score),
                'score_rationale': cls._get_score_rationale(data_score, price_slope, cvd_slope, price_r_squared, cvd_r_squared),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Accumulation analysis complete: Score={data_score:.1f}, "
                       f"Price trend={'up' if price_slope > 0 else 'down'} (R²={price_r_squared:.3f}), "
                       f"CVD trend={'up' if cvd_slope > 0 else 'down'} (R²={cvd_r_squared:.3f})")
            
            return data_score, metadata
            
        except Exception as e:
            logger.error(f"Accumulation signal calculation failed: {str(e)}")
            raise CSVValidationError(f"Analysis failed: {str(e)}")
    
    @staticmethod
    def _calculate_data_score(
        price_slope: float,
        cvd_slope: float, 
        price_r_squared: float,
        cvd_r_squared: float
    ) -> float:
        """
        Calculate Data Score based on AS-04 algorithm
        
        Data Score Calculation Rules:
        - Strong Accumulation: Both trends positive, R² > 0.7 → Score 8-10
        - Moderate Accumulation: One positive trend, R² > 0.5 → Score 6-7  
        - Neutral/Mixed: Conflicting signals or weak trends → Score 4-6
        - Distribution: Both trends negative, R² > 0.7 → Score 1-3
        - Insufficient Data: R² < 0.5 → Score 5 (neutral)
        
        Args:
            price_slope: Linear regression slope of price
            cvd_slope: Linear regression slope of CVD
            price_r_squared: R-squared value for price trend
            cvd_r_squared: R-squared value for CVD trend
            
        Returns:
            Data score (1-10 scale)
        """
        # Determine trend strength based on R-squared values
        price_strong = price_r_squared > 0.7
        price_moderate = price_r_squared > 0.5
        cvd_strong = cvd_r_squared > 0.7
        cvd_moderate = cvd_r_squared > 0.5
        
        # Determine trend directions
        price_positive = price_slope > 0
        cvd_positive = cvd_slope > 0
        
        # Insufficient data case (AS-04)
        if not price_moderate and not cvd_moderate:
            return 5.0  # Neutral score for weak trends
        
        # Strong Accumulation: Both trends positive with strong correlation
        if price_positive and cvd_positive:
            if price_strong and cvd_strong:
                return 10.0  # Perfect accumulation signal
            elif (price_strong or cvd_strong) and (price_moderate and cvd_moderate):
                return 9.0   # Strong accumulation
            elif price_moderate and cvd_moderate:
                return 8.0   # Good accumulation
            else:
                return 7.0   # Moderate accumulation
        
        # Moderate Accumulation: CVD positive, price flat/negative (classic accumulation divergence)
        elif cvd_positive and not price_positive:
            if cvd_strong:
                return 9.0   # Strong accumulation divergence
            elif cvd_moderate:
                return 8.0   # Good accumulation divergence
            else:
                return 6.0   # Weak accumulation signal
        
        # Moderate Accumulation: Price positive, CVD flat/negative (less ideal but still positive)
        elif price_positive and not cvd_positive:
            if price_strong and abs(cvd_slope) < abs(price_slope) * 0.5:  # CVD not strongly negative
                return 7.0   # Price momentum without CVD confirmation
            elif price_moderate:
                return 6.0   # Weak positive signal
            else:
                return 5.0   # Neutral
        
        # Distribution: Both trends negative
        elif not price_positive and not cvd_positive:
            if price_strong and cvd_strong:
                return 1.0   # Strong distribution
            elif (price_strong or cvd_strong) and (price_moderate and cvd_moderate):
                return 2.0   # Clear distribution
            elif price_moderate and cvd_moderate:
                return 3.0   # Moderate distribution
            else:
                return 4.0   # Weak negative signal
        
        # Mixed/Conflicting signals
        else:
            return 5.0  # Neutral for unclear signals
    
    @staticmethod
    def _classify_divergence(price_slope: float, cvd_slope: float) -> str:
        """
        Classify the type of divergence for reporting purposes
        
        Args:
            price_slope: Price trend slope
            cvd_slope: CVD trend slope
            
        Returns:
            Divergence classification string
        """
        if cvd_slope > 0 and price_slope <= 0:
            return "bullish_divergence"  # CVD up, price flat/down = accumulation
        elif cvd_slope < 0 and price_slope >= 0:
            return "bearish_divergence"  # CVD down, price flat/up = distribution
        elif cvd_slope > 0 and price_slope > 0:
            return "confluence_bullish"  # Both up = strong bull signal
        elif cvd_slope < 0 and price_slope < 0:
            return "confluence_bearish"  # Both down = strong bear signal
        else:
            return "neutral"  # Mixed or flat signals
    
    @staticmethod
    def _get_score_rationale(
        score: float,
        price_slope: float,
        cvd_slope: float,
        price_r_squared: float,
        cvd_r_squared: float
    ) -> str:
        """
        Generate human-readable rationale for the calculated score
        
        Args:
            score: Calculated data score
            price_slope: Price trend slope
            cvd_slope: CVD trend slope  
            price_r_squared: Price trend strength
            cvd_r_squared: CVD trend strength
            
        Returns:
            Score rationale string
        """
        price_dir = "rising" if price_slope > 0 else "falling"
        cvd_dir = "rising" if cvd_slope > 0 else "falling"
        
        price_strength = "strong" if price_r_squared > 0.7 else "moderate" if price_r_squared > 0.5 else "weak"
        cvd_strength = "strong" if cvd_r_squared > 0.7 else "moderate" if cvd_r_squared > 0.5 else "weak"
        
        if score >= 8:
            return f"Strong accumulation signal: {cvd_strength} {cvd_dir} CVD with {price_strength} {price_dir} price"
        elif score >= 6:
            return f"Moderate accumulation signal: {cvd_strength} {cvd_dir} CVD with {price_strength} {price_dir} price"
        elif score >= 4:
            return f"Neutral/mixed signals: {price_strength} {price_dir} price, {cvd_strength} {cvd_dir} CVD"
        else:
            return f"Distribution signal: {price_strength} {price_dir} price with {cvd_strength} {cvd_dir} CVD"
    
    @classmethod
    def analyze_csv_data(cls, csv_text: str) -> Dict[str, Any]:
        """
        Complete CSV analysis pipeline
        
        Performs parsing, validation, and accumulation signal calculation
        in a single operation with comprehensive error handling.
        
        Args:
            csv_text: Raw CSV text from user input
            
        Returns:
            Analysis results dictionary with score, metadata, and validation info
        """
        try:
            # Step 1: Parse and validate CSV
            df, validation_error = cls.parse_and_validate_csv(csv_text)
            
            if validation_error:
                return {
                    'success': False,
                    'error': validation_error,
                    'data_score': None,
                    'analysis_metadata': None,
                    'validation_errors': [validation_error],
                    'is_valid': False
                }
            
            # Step 2: Calculate accumulation signal
            try:
                data_score, analysis_metadata = cls.calculate_accumulation_signal(df)
                
                return {
                    'success': True,
                    'data_score': data_score,
                    'analysis_metadata': analysis_metadata,
                    'validation_errors': [],
                    'is_valid': True,
                    'processed_data': {
                        'total_periods': len(df),
                        'analysis_periods': analysis_metadata['periods_analyzed'],
                        'date_range': {
                            'start': df['time'].min().isoformat(),
                            'end': df['time'].max().isoformat()
                        }
                    }
                }
                
            except CSVValidationError as e:
                return {
                    'success': False,
                    'error': str(e),
                    'data_score': None,
                    'analysis_metadata': None,
                    'validation_errors': [str(e)],
                    'is_valid': False
                }
                
        except Exception as e:
            logger.error(f"CSV analysis pipeline failed: {str(e)}")
            return {
                'success': False,
                'error': f"Analysis failed: {str(e)}",
                'data_score': None,
                'analysis_metadata': None,
                'validation_errors': [str(e)],
                'is_valid': False
            }


class CSVFormatValidator:
    """
    Utility class for CSV format validation and preprocessing
    """
    
    @staticmethod
    def validate_csv_format_preview(csv_text: str, max_rows: int = 10) -> Dict[str, Any]:
        """
        Quick validation preview for frontend display
        
        Args:
            csv_text: Raw CSV text
            max_rows: Maximum rows to preview
            
        Returns:
            Validation preview results
        """
        try:
            df, error = CSVAnalyzer.parse_and_validate_csv(csv_text)
            
            if error:
                return {
                    'valid': False,
                    'error': error,
                    'preview': None
                }
            
            # Create preview
            preview_df = df.head(max_rows)
            preview = {
                'columns': list(df.columns),
                'total_rows': len(df),
                'preview_rows': len(preview_df),
                'sample_data': preview_df.to_dict('records'),
                'date_range': {
                    'start': df['time'].min().isoformat(),
                    'end': df['time'].max().isoformat()
                }
            }
            
            return {
                'valid': True,
                'error': None,
                'preview': preview
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Preview failed: {str(e)}",
                'preview': None
            }
    
    @staticmethod
    def get_csv_requirements() -> Dict[str, Any]:
        """
        Get CSV format requirements for frontend display
        
        Returns:
            Requirements specification
        """
        return {
            'required_columns': CSVAnalyzer.REQUIRED_COLUMNS,
            'minimum_periods': CSVAnalyzer.MINIMUM_PERIODS,
            'supported_formats': {
                'delimiters': ['comma (,)', 'semicolon (;)', 'tab'],
                'date_formats': ['YYYY-MM-DD', 'MM/DD/YYYY', 'DD.MM.YYYY', 'auto-detection'],
                'numeric_format': 'Decimal numbers (dots or commas as decimal separator)'
            },
            'column_descriptions': {
                'time': 'Date/timestamp for each data point',
                'close': 'Closing price for each period',
                'Volume Delta (Close)': 'Volume delta value (buying pressure - selling pressure)'
            },
            'data_source': 'TradingView CSV export with required indicators'
        }