"""Lightweight tests for dashboard data loading logic."""
import pytest
import pandas as pd
import numpy as np
from src.rebalance import load_signals, assign_steps, rebalance, get_market_signals
import tempfile
import os


class TestDashboardDataLoading:
    """Tests for dashboard data processing."""

    def make_sample_signals(self):
        """Create sample signals similar to sample/signals_sample.csv"""
        return pd.DataFrame({
            "source": ["sample_headlines"]*5 + ["kaggle_stock_tweets"]*5,
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="D").astype(str),
            "ticker": ["AAPL", "TSLA", "JPM", None, "BA", "TSLA", "TSLA", "MSFT", "NIO", "TSLA"],
            "sentiment": [0.3, -0.9, 0.9, 0.5, -0.9, 0.4, 0.2, 0.0, -0.3, 0.9],
            "event": ["Dividend or Buyback", "Analyst Rating", "Earnings", "Macroeconomic",
                      "Regulatory/Legal", "Other", "Other", "Market Commentary", "Other", "Analyst Rating"],
            "event_confidence": [0.8, 0.6, 0.7, 0.3, 0.6, 0.1, 0.2, 0.3, 0.1, 0.5],
            "impact": [2, 2, 5, 4, 5, 1, 1, 1, 1, 2],
            "text": [f"Signal {i}" for i in range(10)],
        })

    def test_load_signals_from_csv(self):
        """Test that load_signals works with our sample structure."""
        df = self.make_sample_signals()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            fname = f.name
        try:
            loaded = load_signals(fname)
            assert len(loaded) == 10
            assert "ts" in loaded.columns
            # All timestamps should parse (None becomes NaT, but we have valid dates)
            assert loaded["ts"].notna().sum() == 10
        finally:
            os.unlink(fname)

    def test_assign_steps_with_dates(self):
        """Test assign_steps with dated signals."""
        df = self.make_sample_signals()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            fname = f.name
        try:
            signals = load_signals(fname)
            signals, mode = assign_steps(signals, n_steps=5)
            assert "step" in signals.columns
            assert mode.startswith("by ")
        finally:
            os.unlink(fname)

    def test_rebalance_runs_end_to_end(self):
        """Full integration test: load -> assign_steps -> rebalance"""
        df = self.make_sample_signals()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            fname = f.name
        try:
            signals = load_signals(fname)
            signals, mode = assign_steps(signals, n_steps=5)
            tickers = ["AAPL", "TSLA", "JPM", "BA", "MSFT", "NIO"]
            weights, scores = rebalance(signals, tickers)
            
            # Start row + number of unique steps
            n_steps = signals["step"].nunique()
            assert weights.shape[0] == n_steps + 1
            assert weights.shape[1] == 6  # 6 tickers
            assert np.allclose(weights.sum(axis=1), 1.0)
        finally:
            os.unlink(fname)

    def test_dashboard_metrics_calculation(self):
        """Test the metric calculations used in dashboard."""
        df = self.make_sample_signals()
        
        # Test sentiment summary logic
        used = df[df["ticker"].isin(["AAPL", "TSLA", "JPM"])].copy()
        sent_summary = used.groupby("ticker").agg(
            n_signals=("sentiment", "count"),
            avg_sentiment=("sentiment", "mean"),
            avg_impact=("impact", "mean"),
            net_signal=("sentiment", lambda s: (s * used.loc[s.index, "impact"] / 10).sum())
        ).fillna(0)
        
        assert "AAPL" in sent_summary.index
        assert "TSLA" in sent_summary.index
        assert sent_summary.loc["AAPL", "n_signals"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])