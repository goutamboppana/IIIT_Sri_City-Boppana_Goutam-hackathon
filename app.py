"""Module A dashboard. Run from the project root:  streamlit run app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.rebalance import load_signals, top_tickers, assign_steps, rebalance

st.set_page_config(page_title="Sentiment Index Rebalancer", layout="wide")
st.title("Tactical Index Rebalancer")
st.caption("Module A: stock weights adjust as the NLP risk engine's sentiment signals arrive.")

DEFAULT_PATH = Path(__file__).parent / "data" / "signals.csv"

# ---------- sidebar ----------
st.sidebar.header("Data")
upload = st.sidebar.file_uploader("Upload signals.csv (optional)", type="csv")
source = upload if upload is not None else DEFAULT_PATH
if upload is None and not DEFAULT_PATH.exists():
    st.error("No signals file found. Put signals.csv in the data/ folder, or upload one in the sidebar.")
    st.stop()

signals = load_signals(source)
if signals.empty:
    st.error("No signals with a ticker were found, so there is nothing to rebalance.")
    st.stop()

st.sidebar.header("Index")
all_tickers = signals["ticker"].value_counts().index.tolist()
default_tickers = top_tickers(signals, 15)
tickers = st.sidebar.multiselect("Stocks in the index", all_tickers, default=default_tickers)
if len(tickers) < 3:
    st.warning("Pick at least 3 stocks.")
    st.stop()

st.sidebar.header("Rebalancing rule")
sensitivity = st.sidebar.slider("Sensitivity", 0.1, 1.0, 0.5, 0.05,
                                help="How strongly sentiment moves a weight in one step.")
decay = st.sidebar.slider("Decay toward equal weight", 0.0, 0.5, 0.1, 0.05,
                          help="Fraction pulled back to the starting weight each step.")
max_weight = st.sidebar.slider("Max weight per stock", 0.05, 0.40, 0.15, 0.01, format="%.2f")
n_steps = st.sidebar.slider("Replay steps (when data has no real dates)", 5, 40, 20)

# ---------- compute ----------
signals, mode = assign_steps(signals, n_steps)
weights, scores = rebalance(signals, tickers, sensitivity, decay, max_weight)
used = signals[signals["ticker"].isin(tickers)]

change = (weights.iloc[-1] - weights.iloc[0]) * 100
c1, c2, c3, c4 = st.columns(4)
c1.metric("Signals used", len(used))
c2.metric("Time steps", len(weights) - 1, help=f"Grouping mode: {mode}")
c3.metric("Biggest gainer", change.idxmax(), f"{change.max():+.2f} pts")
c4.metric("Biggest loser", change.idxmin(), f"{change.min():+.2f} pts")

tab1, tab2, tab3, tab4 = st.tabs(["Weights over time", "Start vs now", "Replay a step", "How it works"])

with tab1:
    long = (weights * 100).reset_index(names="step").melt(
        id_vars="step", var_name="ticker", value_name="weight_pct")
    fig = px.area(long, x="step", y="weight_pct", color="ticker",
                  labels={"weight_pct": "Weight (%)", "step": ""})
    fig.update_layout(height=450, legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    lines = px.line(long, x="step", y="weight_pct", color="ticker",
                    labels={"weight_pct": "Weight (%)", "step": ""})
    lines.update_layout(height=350, legend_title_text="")
    st.plotly_chart(lines, width="stretch")

with tab2:
    cmp = pd.DataFrame({
        "Start": weights.iloc[0] * 100,
        "Now": weights.iloc[-1] * 100,
    })
    cmp["Change (pts)"] = cmp["Now"] - cmp["Start"]
    bar = px.bar(cmp.reset_index(names="ticker").melt(
        id_vars="ticker", value_vars=["Start", "Now"], var_name="when", value_name="weight_pct"),
        x="ticker", y="weight_pct", color="when", barmode="group",
        labels={"weight_pct": "Weight (%)", "ticker": ""})
    bar.update_layout(height=420, legend_title_text="")
    st.plotly_chart(bar, width="stretch")
    st.dataframe(cmp.sort_values("Change (pts)", ascending=False).round(2), width="stretch")

with tab3:
    idx = st.slider("Step", 0, len(weights) - 1, len(weights) - 1)
    label = weights.index[idx]
    st.subheader(label)
    left, right = st.columns([1, 1])
    with left:
        step_w = (weights.iloc[idx] * 100).rename("Weight (%)").round(2).to_frame()
        step_w["Sentiment score"] = scores.iloc[idx].round(2)
        st.dataframe(step_w.sort_values("Weight (%)", ascending=False), width="stretch")
    with right:
        if idx == 0:
            st.info("Start: equal weights, no signals yet.")
        else:
            step_sig = used[used["step_label"] == label][
                ["ticker", "sentiment", "event", "impact", "text"]]
            st.dataframe(step_sig, width="stretch", hide_index=True)

with tab4:
    st.markdown(f"""
**Each time step** the engine's signals are grouped by stock (grouping mode: *{mode}*), then:

1. **Score**: impact-weighted average sentiment of that stock's signals (0 if no news).
2. **Tilt**: `new = old × (1 + sensitivity × score)`. Positive sentiment raises a weight, negative lowers it.
3. **Decay**: a fraction of each weight is pulled back toward the equal-weight start, so old news fades.
4. **Limits**: weights are clipped to a floor and a cap, then renormalized so they sum to 100%.

The index starts equal-weighted. Signals come from `src/run_engine.py` (FinBERT sentiment, zero-shot event
classification, rule-based impact score).
""")