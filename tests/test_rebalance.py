"""Lightweight unit tests for rebalancer.
No model downloads, no API calls."""
import pytest
import numpy as np
import pandas as pd
from src.rebalance import (
    load_signals, top_tickers, assign_steps, rebalance, _apply_limits,
    get_market_signals, _extract_ticker, _is_confident_match
)
from src.ingest import TickerMatch


class TestApplyLimits:
    """Tests for weight limit enforcement."""

    def test_clips_to_bounds(self):
        w = np.array([0.5, 0.3, 0.2])
        w_limited = _apply_limits(w, 0.1, 0.4)
        assert w_limited.max() <= 0.4 + 1e-9
        assert w_limited.min() >= 0.1 - 1e-9

    def test_renormalizes_to_one(self):
        w = np.array([0.5, 0.3, 0.2])
        w_limited = _apply_limits(w, 0.1, 0.4)
        assert abs(w_limited.sum() - 1.0) < 1e-9

    def test_feasible_bounds_for_small_index(self):
        # 15 stocks, max_weight=0.15 -> hi=0.15, lo=0.01
        w = np.full(15, 1/15)
        w_limited = _apply_limits(w, 0.01, 0.15)
        assert abs(w_limited.sum() - 1.0) < 1e-9


class TestTopTickers:
    """Tests for top_tickers selection."""

    def test_returns_most_frequent(self):
        df = pd.DataFrame({"ticker": ["AAPL"]*5 + ["TSLA"]*3 + ["MSFT"]*2})
        top = top_tickers(df, 2)
        assert top == ["AAPL", "TSLA"]


class TestAssignSteps:
    """Tests for time step assignment."""

    def test_replay_mode_for_undated(self):
        df = pd.DataFrame({
            "timestamp": [None]*10,
            "ticker": ["AAPL"]*10,
        })
        # Add ts column manually (simulating load_signals)
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, mode = assign_steps(df, n_steps=5)
        assert mode == "replay"
        assert "step" in df.columns
        assert df["step"].nunique() == 5

    def test_dated_mode(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "ticker": ["AAPL"]*10,
        })
        # Add ts column manually (simulating load_signals)
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, mode = assign_steps(df, freq="day")
        assert mode == "by day"
        assert df["step"].nunique() == 10


class TestRebalance:
    """Tests for the main rebalance function."""

    def make_signals(self, n=20):
        """Create synthetic signals for testing."""
        np.random.seed(42)
        tickers = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        data = []
        for i in range(n):
            t = np.random.choice(tickers)
            data.append({
                "timestamp": f"2024-01-{i%5+1:02d}T12:00:00Z",
                "ticker": t,
                "ticker_confidence": "high",
                "sentiment": np.random.uniform(-1, 1),
                "event": "Earnings",
                "event_confidence": 0.8,
                "impact": np.random.randint(1, 10),
                "text": f"Signal {i} for {t}",
            })
        return pd.DataFrame(data)

    def test_rebalance_outputs_correct_shape(self):
        df = self.make_signals(30)
        # Add ts column (simulating load_signals)
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, scores = rebalance(df, ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"])
        # Start row + 5 steps = 6 rows
        assert weights.shape == (6, 5)
        assert scores.shape == (6, 5)

    def test_weights_sum_to_one(self):
        df = self.make_signals(30)
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, _ = rebalance(df, ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"])
        assert np.allclose(weights.sum(axis=1), 1.0)

    def test_weights_within_bounds(self):
        df = self.make_signals(30)
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, _ = rebalance(df, ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"],
                               max_weight=0.3, min_weight=0.05)
        assert (weights <= 0.3 + 1e-9).all().all()
        assert (weights >= 0.05 - 1e-9).all().all()

    def test_positive_sentiment_increases_weight(self):
        # All positive sentiment for AAPL
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T12:00:00Z"]*5,
            "ticker": ["AAPL"]*5,
            "ticker_confidence": ["high"]*5,
            "sentiment": [0.8]*5,
            "event": ["Earnings"]*5,
            "event_confidence": [0.8]*5,
            "impact": [5]*5,
            "text": ["Good news"]*5,
        })
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, _ = rebalance(df, ["AAPL", "TSLA"], sensitivity=1.0, decay=0.0)
        # AAPL weight should increase
        assert weights.iloc[-1]["AAPL"] > weights.iloc[0]["AAPL"]

    def test_negative_sentiment_decreases_weight(self):
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T12:00:00Z"]*5,
            "ticker": ["AAPL"]*5,
            "ticker_confidence": ["high"]*5,
            "sentiment": [-0.8]*5,
            "event": ["Earnings"]*5,
            "event_confidence": [0.8]*5,
            "impact": [5]*5,
            "text": ["Bad news"]*5,
        })
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, _ = rebalance(df, ["AAPL", "TSLA"], sensitivity=1.0, decay=0.0)
        assert weights.iloc[-1]["AAPL"] < weights.iloc[0]["AAPL"]

    def test_no_signals_keeps_equal_weight(self):
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T12:00:00Z"],
            "ticker": ["TSLA"],
            "ticker_confidence": ["high"],
            "sentiment": [0.0],
            "event": ["Other"],
            "event_confidence": [0.1],
            "impact": [1],
            "text": ["Neutral"],
        })
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        weights, _ = rebalance(df, ["AAPL", "TSLA"], sensitivity=1.0, decay=0.0)
        # Both should stay at 0.5
        assert np.allclose(weights.iloc[-1], 0.5)

    def test_decay_pulls_toward_equal_weight(self):
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T12:00:00Z"]*5,
            "ticker": ["AAPL"]*5,
            "ticker_confidence": ["high"]*5,
            "sentiment": [0.8]*5,
            "event": ["Earnings"]*5,
            "event_confidence": [0.8]*5,
            "impact": [5]*5,
            "text": ["Good news"]*5,
        })
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        df, _ = assign_steps(df, freq="day")
        # With decay, weight should be pulled back
        weights_no_decay, _ = rebalance(df, ["AAPL", "TSLA"], sensitivity=1.0, decay=0.0)
        weights_with_decay, _ = rebalance(df, ["AAPL", "TSLA"], sensitivity=1.0, decay=0.5)
        # With decay, AAPL should be closer to 0.5
        assert abs(weights_with_decay.iloc[-1]["AAPL"] - 0.5) < abs(weights_no_decay.iloc[-1]["AAPL"] - 0.5)


class TestExtractTicker:
    """Tests for ticker extraction helper."""

    def test_extracts_from_tickermatch(self):
        m = TickerMatch("AAPL", "high", "exchange_tag")
        assert _extract_ticker(m) == "AAPL"

    def test_extracts_from_string(self):
        assert _extract_ticker("  aapl  ") == "AAPL"

    def test_returns_none_for_none(self):
        assert _extract_ticker(None) is None


class TestIsConfidentMatch:
    """Tests for confidence checking."""

    def test_high_confidence(self):
        m = TickerMatch("AAPL", "high", "exchange_tag")
        assert _is_confident_match(m) is True

    def test_medium_confidence(self):
        m = TickerMatch("TSLA", "medium", "company_name_with_finance")
        assert _is_confident_match(m) is True

    def test_low_confidence(self):
        m = TickerMatch("TSLA", "low", "company_name_alone")
        assert _is_confident_match(m) is False

    def test_none(self):
        assert _is_confident_match(None) is False

    def test_legacy_string(self):
        assert _is_confident_match("AAPL") is True
        assert _is_confident_match("") is False


class TestGetMarketSignals:
    """Tests for market-wide signal extraction."""

    def test_returns_low_confidence_signals(self):
        df = pd.DataFrame({
            "ticker": ["AAPL", "TSLA", "MSFT"],
            "ticker_confidence": ["high", "medium", "low"],
            "text": ["a", "b", "c"],
        })
        market = get_market_signals(df)
        assert len(market) == 1
        assert market.iloc[0]["ticker"] == "MSFT"

    def test_returns_no_ticker_signals(self):
        df = pd.DataFrame({
            "ticker": ["AAPL", None, "TSLA"],
            "ticker_confidence": ["high", None, "high"],
            "text": ["a", "b", "c"],
        })
        market = get_market_signals(df)
        assert len(market) == 1
        # NaN in ticker column for the middle row
        assert pd.isna(market.iloc[0]["ticker"])


class TestLoadSignals:
    """Tests for load_signals with mock CSV."""

    def test_loads_csv_and_parses_timestamps(self, tmp_path):
        csv = tmp_path / "test_signals.csv"
        df = pd.DataFrame({
            "source": ["newsapi", "sample_headlines"],
            "timestamp": ["2024-01-01T12:00:00Z", "2024-01-02T12:00:00Z"],
            "ticker": ["AAPL", "TSLA"],
            "sentiment": [0.5, -0.3],
            "event": ["Earnings", "Analyst Rating"],
            "event_confidence": [0.8, 0.6],
            "impact": [5, 3],
            "text": ["Apple beats", "Tesla downgraded"],
        })
        df.to_csv(csv, index=False)
        
        loaded = load_signals(csv)
        assert len(loaded) == 2
        assert "ts" in loaded.columns
        assert loaded["ts"].notna().all()

    def test_handles_missing_ticker_column(self, tmp_path):
        csv = tmp_path / "test_signals.csv"
        df = pd.DataFrame({
            "source": ["newsapi"],
            "timestamp": ["2024-01-01T12:00:00Z"],
            "sentiment": [0.5],
            "event": ["Earnings"],
            "event_confidence": [0.8],
            "impact": [5],
            "text": ["Apple beats earnings"],
        })
        df.to_csv(csv, index=False)
        
        loaded = load_signals(csv)
        assert "ticker" in loaded.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])