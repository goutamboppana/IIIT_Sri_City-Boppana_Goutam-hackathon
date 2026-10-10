"""Tests for Module B: Stress Testing."""
import pytest
import numpy as np
import pandas as pd
from src.stress import (
    StressScenario, SCENARIOS, SECTOR_MAP,
    run_stress_test, list_scenarios, run_multiple_scenarios
)
from src.rebalance import DEFAULT_INDEX_CONSTITUENTS


class TestStressScenario:
    """Tests for StressScenario dataclass."""

    def test_get_shock_explicit(self):
        scenario = StressScenario(
            name="Test",
            description="Test",
            sector_shocks={"Technology": -0.3, "Energy": 0.1},
            default_shock=-0.15,
        )
        assert scenario.get_shock("Technology") == -0.3
        assert scenario.get_shock("Energy") == 0.1

    def test_get_shock_default(self):
        scenario = StressScenario(
            name="Test",
            description="Test",
            sector_shocks={"Technology": -0.3},
            default_shock=-0.15,
        )
        assert scenario.get_shock("Healthcare") == -0.15
        assert scenario.get_shock("Unknown") == -0.15


class TestPredefinedScenarios:
    """Tests for predefined scenarios."""

    def test_all_scenarios_exist(self):
        expected = ["market_selloff", "rate_shock", "geopolitical_energy", "credit_stress", "tech_shock"]
        assert set(SCENARIOS.keys()) == set(expected)

    def test_scenarios_have_required_fields(self):
        for key, scenario in SCENARIOS.items():
            assert scenario.name
            assert scenario.description
            assert isinstance(scenario.sector_shocks, dict)
            assert isinstance(scenario.default_shock, float)
            assert "SIMULATED" in scenario.description.upper() or "HYPOTHETICAL" in scenario.description.upper()

    def test_market_selloff_uniform(self):
        scenario = SCENARIOS["market_selloff"]
        # All sectors should get default shock
        assert scenario.get_shock("Technology") == -0.18
        assert scenario.get_shock("Financials") == -0.18
        assert scenario.get_shock("Energy") == -0.18

    def test_tech_shock_tech_heavier(self):
        scenario = SCENARIOS["tech_shock"]
        assert scenario.get_shock("Technology") < scenario.get_shock("Consumer Staples")
        assert scenario.get_shock("Technology") == -0.40


class TestRunStressTest:
    """Tests for run_stress_test function."""

    def make_equal_weights(self, tickers=None):
        if tickers is None:
            tickers = DEFAULT_INDEX_CONSTITUENTS
        return pd.Series(1/len(tickers), index=tickers)

    def test_basic_run(self):
        weights = self.make_equal_weights()
        result = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "market_selloff")

        assert "scenario" in result
        assert "portfolio_return" in result
        assert "contrib_by_ticker" in result
        assert "contrib_by_sector" in result
        assert "holdings_detail" in result
        assert "assumptions" in result

        # Portfolio return should equal default shock for uniform weights
        assert abs(result["portfolio_return"] - (-0.18)) < 0.001

    def test_weights_sum_to_one(self):
        weights = self.make_equal_weights()
        result = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "market_selloff")
        assert abs(result["assumptions"]["weight_sum"] - 1.0) < 1e-6

    def test_contributions_sum_to_portfolio_return(self):
        weights = self.make_equal_weights()
        result = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "rate_shock")

        ticker_contrib_sum = result["contrib_by_ticker"].sum()
        sector_contrib_sum = result["contrib_by_sector"].sum()
        portfolio_return = result["portfolio_return"]

        assert abs(ticker_contrib_sum - portfolio_return) < 1e-9
        assert abs(sector_contrib_sum - portfolio_return) < 1e-9

    def test_holdings_detail_structure(self):
        weights = self.make_equal_weights()
        result = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "market_selloff")

        holdings = result["holdings_detail"]
        assert len(holdings) == len(DEFAULT_INDEX_CONSTITUENTS)
        assert set(holdings.columns) == {"ticker", "weight", "sector", "shock", "contribution"}
        assert (holdings["weight"] >= 0).all()

    def test_custom_scenario(self):
        weights = self.make_equal_weights(["AAPL", "MSFT", "JPM"])
        custom_shocks = {"Technology": -0.5, "Financials": -0.2, "default": -0.1}
        result = run_stress_test(weights, ["AAPL", "MSFT", "JPM"], "custom", custom_shocks=custom_shocks)

        # Check custom shocks applied
        tech_contrib = result["contrib_by_sector"].get("Technology", 0)
        fin_contrib = result["contrib_by_sector"].get("Financials", 0)
        assert tech_contrib < fin_contrib  # Tech hit harder

    def test_custom_scenario_requires_shocks(self):
        weights = self.make_equal_weights()
        with pytest.raises(ValueError):
            run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "custom")

    def test_unknown_scenario_raises(self):
        weights = self.make_equal_weights()
        with pytest.raises(ValueError):
            run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "nonexistent")

    def test_non_equal_weights(self):
        # Concentrated in tech
        weights = pd.Series({"AAPL": 0.5, "MSFT": 0.3, "JPM": 0.2})
        result = run_stress_test(weights, ["AAPL", "MSFT", "JPM"], "tech_shock")

        # Should be worse than equal-weight due to tech concentration
        eq_weights = pd.Series(1/3, index=["AAPL", "MSFT", "JPM"])
        eq_result = run_stress_test(eq_weights, ["AAPL", "MSFT", "JPM"], "tech_shock")
        assert result["portfolio_return"] < eq_result["portfolio_return"]

    def test_assumptions_include_disclaimer(self):
        weights = self.make_equal_weights()
        result = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, "market_selloff")

        assert "disclaimer" in result["assumptions"]
        assert "SIMULATED" in result["assumptions"]["disclaimer"]
        assert "NOT REPRESENT ACTUAL" in result["assumptions"]["disclaimer"]


class TestListScenarios:
    """Tests for list_scenarios."""

    def test_returns_list(self):
        scenarios = list_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 5

        for s in scenarios:
            assert "key" in s
            assert "name" in s
            assert "description" in s
            assert "uses_historical" in s


class TestRunMultipleScenarios:
    """Tests for run_multiple_scenarios."""

    def make_equal_weights(self, tickers=None):
        if tickers is None:
            tickers = DEFAULT_INDEX_CONSTITUENTS
        return pd.Series(1/len(tickers), index=tickers)

    def test_returns_dataframe(self):
        weights = self.make_equal_weights()
        df = run_multiple_scenarios(weights, DEFAULT_INDEX_CONSTITUENTS)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == [
            "Scenario", "Portfolio Return", "Worst Sector",
            "Worst Sector Contribution", "Best Sector", "Best Sector Contribution"
        ]

    def test_portfolio_returns_match_individual(self):
        weights = self.make_equal_weights()
        multi = run_multiple_scenarios(weights, DEFAULT_INDEX_CONSTITUENTS)

        for _, row in multi.iterrows():
            scenario_key = row["Scenario"].lower().replace(" ", "_").replace("/", "_")
            # Find matching scenario
            for key, scenario in SCENARIOS.items():
                if scenario.name == row["Scenario"]:
                    individual = run_stress_test(weights, DEFAULT_INDEX_CONSTITUENTS, key)
                    assert abs(row["Portfolio Return"] - individual["portfolio_return"]) < 1e-9
                    break


class TestSectorMap:
    """Tests for sector mapping."""

    def test_default_constituents_have_sectors(self):
        for ticker in DEFAULT_INDEX_CONSTITUENTS:
            assert ticker in SECTOR_MAP, f"{ticker} missing from SECTOR_MAP"

    def test_sectors_are_strings(self):
        for sector in SECTOR_MAP.values():
            assert isinstance(sector, str)
            assert len(sector) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
