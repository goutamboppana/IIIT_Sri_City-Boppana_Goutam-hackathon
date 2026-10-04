"""Module A: tactical index rebalancing driven by the engine's sentiment signals.

Runs on plain pandas/numpy, so it works on your laptop (no torch needed).

Rule, applied once per time step:
  1. For each stock, net signal = sum of (sentiment * impact / 10) over that step's signals
     (0 if no news). More and stronger news means a bigger signal, capped at +/-2.
  2. Tilt:   w_new = w_old * exp(sensitivity * net_signal)
  3. Decay:  pull a fraction of the weight back toward the equal-weight start,
             so one burst of news doesn't move the index forever.
  4. Limits: clip each weight to [min_weight, max_weight] and renormalize to 100%.
"""
import numpy as np
import pandas as pd

from src.ingest import find_ticker


def load_signals(source):
    """Read signals.csv (path or uploaded file), fill missing tickers from the text."""
    df = pd.read_csv(source)
    if "ticker" not in df.columns:
        df["ticker"] = None
    df["ticker"] = [
        t if isinstance(t, str) and t.strip() else find_ticker(x)
        for t, x in zip(df["ticker"], df["text"])
    ]
    df = df.dropna(subset=["ticker"]).copy()
    df["ticker"] = df["ticker"].str.upper()
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
    return df.reset_index(drop=True)


def top_tickers(df, n=15):
    return df["ticker"].value_counts().head(n).index.tolist()


def assign_steps(df, n_steps=20, freq="auto"):
    """Group signals into time steps.

    Dated data: one step per day, week or month (freq="auto" picks day for up to 60 distinct
    days, otherwise week). Undated data: replay the file in order, split into n_steps chunks.
    Returns (df with 'step' and 'step_label', mode) where mode is 'by day/week/month' or 'replay'.
    """
    df = df.copy()
    if df["ts"].notna().all() and df["ts"].dt.normalize().nunique() >= 5:
        df = df.sort_values("ts").reset_index(drop=True)
        days = df["ts"].dt.normalize()
        if freq == "auto":
            freq = "week" if days.nunique() > 60 else "day"
        if freq == "month":
            key = df["ts"].dt.to_period("M").dt.start_time
        elif freq == "week":
            key = df["ts"].dt.to_period("W").dt.start_time
        else:
            freq, key = "day", days
        order = {k: i for i, k in enumerate(sorted(key.unique()))}
        df["step"] = key.map(order)
        df["step_label"] = key.dt.strftime("%Y-%m-%d")
        return df, f"by {freq}"
    n = max(1, min(n_steps, len(df)))
    df["step"] = np.arange(len(df)) * n // len(df)
    df["step_label"] = "Step " + (df["step"] + 1).astype(str)
    return df, "replay"


def _apply_limits(w, lo, hi):
    for _ in range(50):
        w = np.clip(w, lo, hi)
        w = w / w.sum()
        if w.min() >= lo - 1e-9 and w.max() <= hi + 1e-9:
            break
    return w


def rebalance(df, tickers, sensitivity=0.5, decay=0.1, max_weight=0.15, min_weight=0.01):
    """df must already have 'step' and 'step_label' (see assign_steps).
    Returns (weights, scores): DataFrames with one row per step ('Start' first)."""
    n = len(tickers)
    w0 = np.full(n, 1.0 / n)
    hi = max(max_weight, 1.5 / n)      # keep the limits feasible for small indexes
    lo = min(min_weight, 0.5 / n)
    w = w0.copy()

    labels = df.drop_duplicates("step").sort_values("step").set_index("step")["step_label"]
    weight_rows = [pd.Series(w, index=tickers, name="Start")]
    score_rows = [pd.Series(0.0, index=tickers, name="Start")]

    for step, label in labels.items():
        sub = df[(df["step"] == step) & (df["ticker"].isin(tickers))].copy()
        sub["wx"] = sub["sentiment"] * sub["impact"] / 10.0
        score = sub.groupby("ticker")["wx"].sum().reindex(tickers).fillna(0.0).clip(-2, 2).values

        tilted = w * np.exp(sensitivity * score)
        tilted = tilted / tilted.sum()
        w = _apply_limits((1 - decay) * tilted + decay * w0, lo, hi)

        weight_rows.append(pd.Series(w, index=tickers, name=label))
        score_rows.append(pd.Series(score, index=tickers, name=label))

    return pd.DataFrame(weight_rows), pd.DataFrame(score_rows)