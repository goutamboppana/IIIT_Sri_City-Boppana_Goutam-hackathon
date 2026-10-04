"""Module A dashboard. Run from the project root:  streamlit run app.py"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.rebalance import load_signals, top_tickers, assign_steps, rebalance

UP, DOWN, GREY = "#1D9E75", "#D85A30", "#C8C6BD"
ROOT = Path(__file__).parent
DEFAULT_PATH = ROOT / "data" / "signals.csv"            # your own run (git-ignored)
SAMPLE_PATH = ROOT / "sample" / "signals_sample.csv"    # committed sample so anyone can run the demo

st.set_page_config(page_title="Sentiment index rebalancer", layout="wide")


def style(fig, height=400):
    fig.update_layout(template="simple_white", height=height, showlegend=False,
                      margin=dict(l=0, r=0, t=10, b=0), font=dict(size=13))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEECE6", zeroline=False)
    return fig


# ---------- sidebar ----------
st.sidebar.header("Settings")
upload = st.sidebar.file_uploader("Signals file (optional)", type="csv")
if upload is not None:
    source = upload
elif DEFAULT_PATH.exists():
    source = DEFAULT_PATH
elif SAMPLE_PATH.exists():
    source = SAMPLE_PATH
    st.sidebar.info("Using the bundled sample signals.")
else:
    st.error("No signals file found. Run src/run_engine.py, or upload a signals.csv in the sidebar.")
    st.stop()

signals = load_signals(source)
if signals.empty:
    st.error("No signals with a ticker were found, so there is nothing to rebalance.")
    st.stop()

all_tickers = signals["ticker"].value_counts().index.tolist()
tickers = st.sidebar.multiselect("Stocks in the index", all_tickers, default=top_tickers(signals, 15))
if len(tickers) < 3:
    st.warning("Pick at least 3 stocks.")
    st.stop()

sensitivity = st.sidebar.slider("Sensitivity", 0.1, 3.0, 1.5, 0.1,
                                help="How strongly news moves a weight in one step.")
decay = st.sidebar.slider("Decay", 0.0, 0.5, 0.05, 0.05,
                          help="Share of each weight pulled back toward equal weight every step.")
max_weight = st.sidebar.slider("Max weight per stock", 0.05, 0.40, 0.15, 0.01, format="%.2f")
_, probe_mode = assign_steps(signals)
if probe_mode == "replay":
    freq = "auto"
    n_steps = st.sidebar.slider("Replay steps", 5, 40, 20,
                                help="This file has no usable dates, so signals are replayed in file order.")
else:
    n_steps = 20
    freq = st.sidebar.selectbox("Time step", ["Auto", "Day", "Week", "Month"],
                                help="How dated signals are grouped into rebalancing steps.").lower()

# ---------- compute ----------
signals, mode = assign_steps(signals, n_steps, freq)
weights, scores = rebalance(signals, tickers, sensitivity, decay, max_weight)
used = signals[signals["ticker"].isin(tickers)]
change = (weights.iloc[-1] - weights.iloc[0]) * 100

st.title("Sentiment-driven index rebalancer")
st.markdown(
    f"{len(tickers)} stocks, {len(used)} signals, {len(weights) - 1} time steps ({mode}).  "
    f"Biggest gain: **{change.idxmax()}** ({change.max():+.2f} pts).  "
    f"Biggest drop: **{change.idxmin()}** ({change.min():+.2f} pts)."
)

tab1, tab2, tab3 = st.tabs(["Overview", "Over time", "Replay a step"])

# ---------- overview: who moved ----------
with tab1:
    left, right = st.columns([3, 2])
    with left:
        st.caption("Change in weight, start to now (percentage points)")
        d = change.sort_values().rename("pts").rename_axis("ticker").reset_index()
        d["dir"] = np.where(d["pts"] >= 0, "Up", "Down")
        fig = px.bar(d, x="pts", y="ticker", orientation="h", color="dir",
                     color_discrete_map={"Up": UP, "Down": DOWN},
                     labels={"pts": "", "ticker": ""})
        fig.update_traces(hovertemplate="%{y}: %{x:+.2f} pts<extra></extra>")
        fig.add_vline(x=0, line_color="#999", line_width=1)
        st.plotly_chart(style(fig, 80 + 28 * len(tickers)), width="stretch")
    with right:
        st.caption("Weights (%)")
        tbl = pd.DataFrame({"Start": weights.iloc[0] * 100, "Now": weights.iloc[-1] * 100})
        tbl["Change"] = tbl["Now"] - tbl["Start"]
        st.dataframe(tbl.sort_values("Change", ascending=False).round(2), width="stretch")

# ---------- over time: highlight the movers, grey out the rest ----------
with tab2:
    delta = (weights - weights.iloc[0]) * 100
    final = delta.iloc[-1].sort_values()
    movers = list(dict.fromkeys(list(final.index[:3]) + list(final.index[-3:])))
    show = st.multiselect("Highlighted stocks (the rest stay grey)", tickers, default=movers)
    st.caption("Change in weight vs the equal-weight start (percentage points)")

    x = list(delta.index)
    fig = go.Figure()
    for t in tickers:
        if t not in show:
            fig.add_trace(go.Scatter(x=x, y=delta[t], mode="lines", line=dict(color=GREY, width=1),
                                     hovertemplate=f"%{{x}}<br>{t}: %{{y:.2f}} pts<extra></extra>"))
    for t in show:
        c = UP if delta[t].iloc[-1] >= 0 else DOWN
        fig.add_trace(go.Scatter(x=x, y=delta[t], mode="lines", line=dict(color=c, width=2.5),
                                 hovertemplate=f"%{{x}}<br>{t}: %{{y:.2f}} pts<extra></extra>"))
        fig.add_trace(go.Scatter(x=[x[-1]], y=[delta[t].iloc[-1]], mode="text", text=[f"  {t}"],
                                 textposition="middle right", textfont=dict(color=c),
                                 hoverinfo="skip", cliponaxis=False))
    fig.add_hline(y=0, line_color="#999", line_width=1)
    fig.update_xaxes(type="category", nticks=8)
    style(fig, 450)
    fig.update_layout(margin=dict(l=0, r=70, t=10, b=0))
    st.plotly_chart(fig, width="stretch")

# ---------- replay one step ----------
with tab3:
    idx = st.slider("Step", 0, len(weights) - 1, len(weights) - 1)
    label = weights.index[idx]
    left, right = st.columns(2)
    with left:
        st.caption(f"Weights at: {label}")
        step_w = (weights.iloc[idx] * 100).rename("Weight (%)").round(2).to_frame()
        step_w["Net signal"] = scores.iloc[idx].round(2)
        st.dataframe(step_w.sort_values("Weight (%)", ascending=False), width="stretch")
    with right:
        st.caption("Signals that arrived in this step")
        if idx == 0:
            st.info("Start: equal weights, no signals yet.")
        else:
            step_sig = used[used["step_label"] == label][["ticker", "sentiment", "event", "impact", "text"]]
            st.dataframe(step_sig, width="stretch", hide_index=True)

with st.expander("How the rebalancing works"):
    st.markdown("""
Each time step, signals are grouped by stock, then:

1. **Net signal**: sum of sentiment x impact/10 over that stock's signals (0 if no news), so more and stronger news moves a weight more.
2. **Tilt**: `new = old x exp(sensitivity x net signal)`. Positive news raises a weight, negative lowers it.
3. **Decay**: part of each weight is pulled back toward the equal-weight start, so old news fades.
4. **Limits**: weights are clipped to a floor and cap, then renormalized to sum to 100%.

Signals come from `src/run_engine.py`: FinBERT sentiment, zero-shot event class, rule-based impact score.
""")