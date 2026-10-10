"""Module B: Portfolio Stress Testing

This module implements a practical, explainable stress-testing workflow that uses
the risk signals from the NLP engine to simulate adverse market scenarios.

Key Design Principles:
- Scenarios are explicitly defined and parameterized (not hidden black boxes)
- Uses portfolio holdings and weights consistently
- States assumed sector/asset exposures clearly
- Does NOT fabricate historical prices, returns, or correlations
- When genuine historical data is unavailable, uses explicit hypothetical shocks
- Results are labeled as SIMULATED, not historical backtests
- Methodology is transparent and documented

Scenario Types (configurable):
1. Broad Market Sell-off: Uniform equity drawdown
2. Interest Rate / Inflation Shock: Rate-sensitive sectors hit harder
3. Geopolitical / Energy Price Shock: Energy/defense up, others down
4. Credit / Financial Sector Stress: Banks/financials severely impacted
5. Technology Sector Shock: Tech-heavy drawdown
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class StressScenario:
    """Defines a stress scenario with explicit assumptions."""
    name: str
    description: str
    # Sector shocks: dict mapping sector -> return multiplier (e.g., -0.20 = -20%)
    sector_shocks: dict[str, float]
    # Default shock for sectors not explicitly listed
    default_shock: float
    # Whether this scenario uses historical data (if available) or hypothetical
    uses_historical: bool = False
    historical_source: Optional[str] = None

    def get_shock(self, sector: str) -> float:
        """Get shock for a sector, falling back to default."""
        return self.sector_shocks.get(sector, self.default_shock)


# Sector mapping for default index constituents
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "AMZN": "Technology",
    "NVDA": "Technology", "GOOGL": "Technology", "META": "Technology",
    "TSLA": "Consumer Discretionary",
    "JPM": "Financials", "GS": "Financials", "BAC": "Financials",
    "XOM": "Energy", "WMT": "Consumer Staples",
    "JNJ": "Healthcare", "PFE": "Healthcare",
    "BA": "Industrials",
}


# Predefined scenarios (all hypothetical/simulated unless noted)
SCENARIOS = {
    "market_selloff": StressScenario(
        name="Broad Market Sell-off",
        description=(
            "Simulates a broad equity market decline of 15-20%. "
            "All sectors decline proportionally. "
            "Based on historical bear market drawdowns (e.g., 2008, 2020). "
            "THIS IS A SIMULATED SCENARIO, NOT A BACKTEST."
        ),
        sector_shocks={},  # Uses default_shock for all
        default_shock=-0.18,
        uses_historical=False,
    ),
    "rate_shock": StressScenario(
        name="Interest Rate / Inflation Shock",
        description=(
            "Simulates a rapid rise in interest rates / inflation surprise. "
            "Rate-sensitive sectors (Financials, Utilities, REITs) affected differently. "
            "Financials may initially benefit from wider NIM but suffer from credit losses. "
            "THIS IS A SIMULATED SCENARIO, NOT A BACKTEST."
        ),
        sector_shocks={
            "Technology": -0.25,       # High duration, rate-sensitive
            "Consumer Discretionary": -0.22,
            "Financials": -0.10,       # Mixed: NIM benefit vs credit risk
            "Energy": -0.05,
            "Consumer Staples": -0.10,  # Defensive
            "Healthcare": -0.12,        # Moderate
            "Industrials": -0.18,
        },
        default_shock=-0.15,
        uses_historical=False,
    ),
    "geopolitical_energy": StressScenario(
        name="Geopolitical / Energy Price Shock",
        description=(
            "Simulates geopolitical crisis driving energy prices up 50%+. "
            "Energy sector rallies; broad market sells off on uncertainty. "
            "Defense/Industrials may be resilient. "
            "THIS IS A SIMULATED SCENARIO, NOT A BACKTEST."
        ),
        sector_shocks={
            "Technology": -0.20,
            "Consumer Discretionary": -0.25,
            "Financials": -0.15,
            "Energy": +0.15,           # Energy benefits from high prices
            "Consumer Staples": -0.08,  # Defensive
            "Healthcare": -0.10,        # Defensive
            "Industrials": -0.10,       # Defense spending may offset
        },
        default_shock=-0.15,
        uses_historical=False,
    ),
    "credit_stress": StressScenario(
        name="Credit / Financial Sector Stress",
        description=(
            "Simulates a credit crisis: rising defaults, tightening credit spreads. "
            "Financials severely impacted; high-yield corporates hit hard. "
            "Reminiscent of 2008 but not calibrated to it. "
            "THIS IS A SIMULATED SCENARIO, NOT A BACKTEST."
        ),
        sector_shocks={
            "Technology": -0.30,       # Growth stocks crushed in credit crunch
            "Consumer Discretionary": -0.35,
            "Financials": -0.40,       # Banks at epicenter
            "Energy": -0.20,
            "Consumer Staples": -0.15,  # Defensive but not immune
            "Healthcare": -0.15,
            "Industrials": -0.25,
        },
        default_shock=-0.25,
        uses_historical=False,
    ),
    "tech_shock": StressScenario(
        name="Technology Sector Shock",
        description=(
            "Simulates a tech-specific crash: valuation compression, AI bubble burst, "
            "regulatory crackdown on big tech. "
            "Non-tech sectors relatively resilient. "
            "THIS IS A SIMULATED SCENARIO, NOT A BACKTEST."
        ),
        sector_shocks={
            "Technology": -0.40,       # Epicenter
            "Consumer Discretionary": -0.20,  # Some overlap (AMZN, TSLA)
            "Financials": -0.10,
            "Energy": -0.05,
            "Consumer Staples": -0.05,  # Defensive
            "Healthcare": -0.08,
            "Industrials": -0.10,
        },
        default_shock=-0.10,
        uses_historical=False,
    ),
}


def run_stress_test(
    weights: pd.Series,
    tickers: list[str],
    scenario_name: str = "market_selloff",
    custom_shocks: Optional[dict[str, float]] = None,
    sector_map: Optional[dict[str, str]] = None,
) -> dict:
    """
    Run a stress test on the given portfolio.

    Args:
        weights: Portfolio weights (index=tickers, values sum to 1)
        tickers: List of tickers in the portfolio
        scenario_name: Name of predefined scenario, or "custom"
        custom_shocks: If scenario_name="custom", dict of sector->shock
        sector_map: Optional mapping ticker->sector (uses default if not provided)

    Returns:
        dict with keys:
            - scenario: StressScenario object
            - portfolio_return: float (weighted average return)
            - contrib_by_ticker: Series (ticker -> contribution to portfolio return)
            - contrib_by_sector: Series (sector -> contribution)
            - holdings_detail: DataFrame with ticker, weight, sector, shock, contrib
            - assumptions: dict of key assumptions
    """
    if sector_map is None:
        sector_map = SECTOR_MAP

    if scenario_name == "custom":
        if custom_shocks is None:
            raise ValueError("custom_shocks required for custom scenario")
        scenario = StressScenario(
            name="Custom Scenario",
            description="User-defined sector shocks.",
            sector_shocks=custom_shocks,
            default_shock=custom_shocks.get("default", -0.15),
            uses_historical=False,
        )
    else:
        scenario = SCENARIOS.get(scenario_name)
        if scenario is None:
            raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(SCENARIOS.keys())}")

    # Validate weights
    weights = weights.reindex(tickers).fillna(0.0)
    if abs(weights.sum() - 1.0) > 1e-6:
        weights = weights / weights.sum()

    # Compute per-holding shocks and contributions
    rows = []
    for ticker in tickers:
        w = weights.get(ticker, 0.0)
        sector = sector_map.get(ticker, "Other")
        shock = scenario.get_shock(sector)
        contrib = w * shock
        rows.append({
            "ticker": ticker,
            "weight": w,
            "sector": sector,
            "shock": shock,
            "contribution": contrib,
        })

    holdings = pd.DataFrame(rows)
    portfolio_return = holdings["contribution"].sum()
    contrib_by_ticker = holdings.set_index("ticker")["contribution"]
    contrib_by_sector = holdings.groupby("sector")["contribution"].sum()

    return {
        "scenario": scenario,
        "portfolio_return": portfolio_return,
        "contrib_by_ticker": contrib_by_ticker,
        "contrib_by_sector": contrib_by_sector,
        "holdings_detail": holdings,
        "assumptions": {
            "scenario_name": scenario.name,
            "scenario_description": scenario.description,
            "uses_historical_data": scenario.uses_historical,
            "historical_source": scenario.historical_source,
            "sector_mapping": sector_map,
            "weight_sum": float(weights.sum()),
            "n_holdings": int((weights > 0).sum()),
            "disclaimer": (
                "STRESS TEST RESULTS ARE SIMULATED ESTIMATES BASED ON EXPLICIT ASSUMPTIONS. "
                "THEY DO NOT REPRESENT ACTUAL HISTORICAL LOSSES OR PREDICT FUTURE PERFORMANCE. "
                "SCENARIOS ARE HYPOTHETICAL AND NOT CALIBRATED TO SPECIFIC HISTORICAL EPISODES."
            ),
        },
    }


def list_scenarios() -> list[dict]:
    """List available predefined scenarios."""
    return [
        {
            "key": key,
            "name": scenario.name,
            "description": scenario.description,
            "uses_historical": scenario.uses_historical,
        }
        for key, scenario in SCENARIOS.items()
    ]


def run_multiple_scenarios(
    weights: pd.Series,
    tickers: list[str],
    scenario_names: Optional[list[str]] = None,
    sector_map: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """Run multiple scenarios and return comparison DataFrame."""
    if scenario_names is None:
        scenario_names = list(SCENARIOS.keys())

    results = []
    for name in scenario_names:
        result = run_stress_test(weights, tickers, name, sector_map=sector_map)
        results.append({
            "Scenario": result["scenario"].name,
            "Portfolio Return": result["portfolio_return"],
            "Worst Sector": result["contrib_by_sector"].idxmin(),
            "Worst Sector Contribution": result["contrib_by_sector"].min(),
            "Best Sector": result["contrib_by_sector"].idxmax(),
            "Best Sector Contribution": result["contrib_by_sector"].max(),
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Quick demo
    tickers = DEFAULT_INDEX_CONSTITUENTS
    weights = pd.Series(1/len(tickers), index=tickers)

    print("Available Scenarios:")
    for s in list_scenarios():
        print(f"  {s['key']}: {s['name']}")

    print("\nRunning all scenarios on equal-weight portfolio:")
    comparison = run_multiple_scenarios(weights, tickers)
    print(comparison.to_string(index=False))

    print("\nDetailed: Market Sell-off")
    result = run_stress_test(weights, tickers, "market_selloff")
    print(f"Portfolio Return: {result['portfolio_return']:.2%}")
    print(f"By Sector:\n{result['contrib_by_sector'].to_string()}")
