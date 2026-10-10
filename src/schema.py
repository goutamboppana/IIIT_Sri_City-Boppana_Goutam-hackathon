"""Signal schema definition and validation."""
from typing import Any, Optional
from dataclasses import dataclass, fields
import pandas as pd


@dataclass
class SignalSchema:
    """Expected schema for risk signals."""
    source: str                    # e.g., "newsapi", "sample_headlines", "kaggle_stock_tweets", "hf_finance_tweets"
    timestamp: str                 # ISO 8601 UTC timestamp
    ticker: Optional[str]          # Primary stock ticker (e.g., "AAPL") or None for market-wide
    ticker_confidence: Optional[str]  # "high", "medium", or None
    ticker_method: Optional[str]   # "exchange_tag", "cashtag", "company_name_with_finance", or None
    all_tickers: Optional[str]     # Pipe-separated list of all matched tickers
    all_ticker_confidences: Optional[str]  # Pipe-separated confidences
    all_ticker_methods: Optional[str]      # Pipe-separated methods
    text: str                      # Original text content
    sentiment: Optional[float]     # FinBERT score in [-1, 1]
    event: Optional[str]           # Event category (e.g., "Earnings", "Other")
    event_confidence: Optional[float]  # Classifier confidence in [0, 1]
    impact: Optional[int]          # Impact score in [1, 10]

    # Columns required for raw ingested data (before engine)
    INGEST_REQUIRED = ["source", "timestamp", "ticker", "ticker_confidence", "ticker_method",
                       "all_tickers", "all_ticker_confidences", "all_ticker_methods", "text"]
    # Columns required for full signals (after engine)
    FULL_REQUIRED = INGEST_REQUIRED + ["sentiment", "event", "event_confidence", "impact"]

    # Valid values
    VALID_SOURCES = {"newsapi", "sample_headlines", "kaggle_stock_tweets", "hf_finance_tweets"}
    VALID_CONFIDENCE = {"high", "medium"}
    VALID_METHODS = {"exchange_tag", "cashtag", "company_name_with_finance"}

    @classmethod
    def validate_ingest(cls, df: pd.DataFrame) -> list[str]:
        """Validate ingested data (before engine). Returns list of errors."""
        errors = []
        
        # Check required columns
        missing = set(cls.INGEST_REQUIRED) - set(df.columns)
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        if errors:
            return errors
        
        # Check source values
        invalid_sources = set(df["source"].unique()) - cls.VALID_SOURCES
        if invalid_sources:
            errors.append(f"Invalid source values: {invalid_sources}")
        
        # Check ticker_confidence
        conf_vals = set(df["ticker_confidence"].dropna().unique()) - cls.VALID_CONFIDENCE
        if conf_vals:
            errors.append(f"Invalid ticker_confidence values: {conf_vals}")
        
        # Check ticker_method
        method_vals = set(df["ticker_method"].dropna().unique()) - cls.VALID_METHODS
        if method_vals:
            errors.append(f"Invalid ticker_method values: {method_vals}")
        
        # Check timestamp format
        try:
            pd.to_datetime(df["timestamp"], utc=True, format="mixed")
        except Exception as e:
            errors.append(f"Invalid timestamp format: {e}")
        
        # Check text not empty
        if df["text"].str.len().min() < 1:
            errors.append("Empty text found")
        
        return errors

    @classmethod
    def validate_full(cls, df: pd.DataFrame) -> list[str]:
        """Validate full signals (after engine). Returns list of errors."""
        errors = cls.validate_ingest(df)
        
        # Check additional required columns
        missing = set(cls.FULL_REQUIRED) - set(df.columns)
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        if "sentiment" in df.columns:
            # Check sentiment bounds
            out_of_bounds = df["sentiment"].dropna()
            out_of_bounds = out_of_bounds[(out_of_bounds < -1.0) | (out_of_bounds > 1.0)]
            if len(out_of_bounds) > 0:
                errors.append(f"Sentiment out of bounds [-1, 1]: {len(out_of_bounds)} rows")
        
        if "event_confidence" in df.columns:
            out_of_bounds = df["event_confidence"].dropna()
            out_of_bounds = out_of_bounds[(out_of_bounds < 0.0) | (out_of_bounds > 1.0)]
            if len(out_of_bounds) > 0:
                errors.append(f"Event confidence out of bounds [0, 1]: {len(out_of_bounds)} rows")
        
        if "impact" in df.columns:
            out_of_bounds = df["impact"].dropna()
            out_of_bounds = out_of_bounds[(out_of_bounds < 1) | (out_of_bounds > 10)]
            if len(out_of_bounds) > 0:
                errors.append(f"Impact out of bounds [1, 10]: {len(out_of_bounds)} rows")
        
        return errors


def validate_signals_file(path: str, full: bool = True) -> tuple[bool, list[str]]:
    """Validate a signals CSV file. Returns (is_valid, errors)."""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return False, [f"Failed to read CSV: {e}"]
    
    if full:
        errors = SignalSchema.validate_full(df)
    else:
        errors = SignalSchema.validate_ingest(df)
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        valid, errors = validate_signals_file(sys.argv[1])
        if valid:
            print("[OK] Schema validation passed")
        else:
            print("[FAIL] Schema validation failed:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
    else:
        print("Usage: python -m src.schema <signals.csv>")