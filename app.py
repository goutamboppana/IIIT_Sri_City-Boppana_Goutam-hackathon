"""Module A dashboard. Run from the project root:  streamlit run app.py"""
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.rebalance import load_signals, top_tickers, assign_steps, rebalance, get_market_signals

UP, DOWN, GREY = "#1D9E75", "#D85A30", "#C8C6BD"
ROOT = Path(__file__).parent
DEFAULT_PATH = ROOT / "data" / "signals.csv"
SAMPLE_PATH = ROOT / "sample" / "signals_sample.csv"

st.set_page_config(page_title="Sentiment Index Rebalancer", layout="wide")


def style(fig, height=400):
    fig.update_layout(template="simple_white", height=height, showlegend=False,
                      margin=dict(l=0, r=0, t=10, b=0), font=dict(size=13))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEECE6", zeroline=False)
    return fig


def format_timestamp(ts_str):
    """Format timestamp for display."""
    try:
        dt = pd.to_datetime(ts_str, utc=True, format="mixed")
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(ts_str)


# ---------- Sidebar: Data Source ----------
st.sidebar.header("Data Source")
upload = st.sidebar.file_uploader("Upload signals.csv", type="csv")
if upload is not None:
    source = upload
    source_label = "Uploaded file"
elif DEFAULT_PATH.exists():
    source = DEFAULT_PATH
    source_label = "data/signals.csv (local run)"
elif SAMPLE_PATH.exists():
    source = SAMPLE_PATH
    source_label = "sample/signals_sample.csv (bundled)"
    st.sidebar.info("Using bundled sample signals. Run `python -m src.run_engine` to generate fresh signals.")
else:
    st.error("No signals file found. Run `python -m src.run_engine --n 500`, or upload a signals.csv in the sidebar.")
    st.stop()

# ---------- Load Signals ----------
try:
    signals = load_signals(source)
except Exception as e:
    st.error(f"Failed to load signals: {e}")
    st.stop()

if signals.empty:
    st.error("No signals found in the data file.")
    st.stop()

# ---------- Data Freshness & Ingestion Stats ----------
st.sidebar.header("Data Info")
try:
    ts_col = pd.to_datetime(signals["timestamp"], errors="coerce", utc=True, format="mixed")
    valid_ts = ts_col.dropna()
    if not valid_ts.empty:
        latest = valid_ts.max()
        oldest = valid_ts.min()
        age_hours = (datetime.now(timezone.utc) - latest.to_pydatetime()).total_seconds() / 3600
        st.sidebar.metric("Latest Signal", format_timestamp(latest))
        st.sidebar.metric("Data Span", f"{(latest - oldest).days} days")
        if age_hours < 24:
            st.sidebar.success(f"Fresh ({age_hours:.1f} hrs old)")
        elif age_hours < 168:
            st.sidebar.warning(f"Stale ({age_hours/24:.1f} days old)")
        else:
            st.sidebar.error(f"Very stale ({age_hours/24:.1f} days old)")
except Exception:
    st.sidebar.info("Timestamp parsing unavailable")

# Source breakdown
if "source" in signals.columns:
    source_counts = signals["source"].value_counts()
    st.sidebar.caption("Sources:")
    for src, cnt in source_counts.items():
        st.sidebar.caption(f"  {src}: {cnt}")

# Ticker confidence breakdown
if "ticker_confidence" in signals.columns:
    conf_counts = signals["ticker_confidence"].value_counts()
    st.sidebar.caption("Ticker Confidence:")
    for conf, cnt in conf_counts.items():
        st.sidebar.caption(f"  {conf}: {cnt}")

# Market-wide signals count
market_sigs = get_market_signals(signals)
st.sidebar.caption(f"Market-wide signals: {len(market_sigs)}")

# ---------- Sidebar: Index Settings ----------
st.sidebar.header("Index Settings")
all_tickers = signals["ticker"].dropna().unique().tolist()
default_tickers = top_tickers(signals, 15)
tickers = st.sidebar.multiselect("Stocks in Index", all_tickers, default=default_tickers)
if len(tickers) < 3:
    st.warning("Select at least 3 stocks.")
    st.stop()

sensitivity = st.sidebar.slider("Sensitivity", 0.1, 3.0, 1.5, 0.1,
                                help="How strongly news moves a weight in one step.")
decay = st.sidebar.slider("Decay", 0.0, 0.5, 0.05, 0.05,
                          help="Share of each weight pulled back toward equal weight every step.")
max_weight = st.sidebar.slider("Max Weight per Stock", 0.05, 0.40, 0.15, 0.01, format="%.2f")
min_weight = st.sidebar.slider("Min Weight per Stock", 0.005, 0.10, 0.01, 0.005, format="%.3f")

_, probe_mode = assign_steps(signals)
if probe_mode == "replay":
    freq = "auto"
    n_steps = st.sidebar.slider("Replay Steps", 5, 40, 20,
                                help="No usable dates; signals replayed in file order.")
else:
    n_steps = 20
    freq = st.sidebar.selectbox("Time Step", ["Auto", "Day", "Week", "Month"],
                                help="How dated signals are grouped.").lower()

# ---------- Compute Rebalancing ----------
signals, mode = assign_steps(signals, n_steps, freq)
weights, scores = rebalance(signals, tickers, sensitivity, decay, max_weight, min_weight)
used = signals[signals["ticker"].isin(tickers)]
change = (weights.iloc[-1] - weights.iloc[0]) * 100

# ---------- Title & Summary ----------
st.title("Sentiment-Driven Index Rebalancer")
st.caption(f"Data source: {source_label}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Stocks in Index", len(tickers))
with col2:
    st.metric("Signals Used", len(used))
with col3:
    st.metric("Time Steps", len(weights) - 1)
with col4:
    st.metric("Mode", mode)

st.markdown(
    f"Biggest gain: **{change.idxmax()}** ({change.max():+.2f} pts).  "
    f"Biggest drop: **{change.idxmin()}** ({change.min():+.2f} pts)."
)

# ---------- Tabs ----------
tab_overview, tab_signals, tab_market, tab_time, tab_replay, tab_method = st.tabs([
    "Portfolio Overview", "Stock Signals", "Market Signals", "Weights Over Time", "Replay Step", "Methodology"
])

# ---- Tab 1: Portfolio Overview ----
with tab_overview:
    st.subheader("Weight Changes (Start → Now)")
    left, right = st.columns([3, 2])
    with left:
        d = change.sort_values().rename("pts").rename_axis("ticker").reset_index()
        d["dir"] = np.where(d["pts"] >= 0, "Up", "Down")
        fig = px.bar(d, x="pts", y="ticker", orientation="h", color="dir",
                     color_discrete_map={"Up": UP, "Down": DOWN},
                     labels={"pts": "Change (pp)", "ticker": ""})
        fig.update_traces(hovertemplate="%{y}: %{x:+.2f} pp<extra></extra>")
        fig.add_vline(x=0, line_color="#999", line_width=1)
        st.plotly_chart(style(fig, 80 + 28 * len(tickers)), width="stretch")
    with right:
        st.caption("Weights (%)")
        tbl = pd.DataFrame({"Start": weights.iloc[0] * 100, "Now": weights.iloc[-1] * 100})
        tbl["Change (pp)"] = tbl["Now"] - tbl["Start"]
        st.dataframe(tbl.sort_values("Change (pp)", ascending=False).round(2), width="stretch")
    
    # Sentiment summary for selected stocks
    st.subheader("Sentiment Summary (Selected Stocks)")
    sent_summary = used.groupby("ticker").agg(
        n_signals=("sentiment", "count"),
        avg_sentiment=("sentiment", "mean"),
        avg_impact=("impact", "mean"),
        net_signal=("sentiment", lambda s: (s * used.loc[s.index, "impact"] / 10).sum())
    ).reindex(tickers).fillna(0).round(3)
    sent_summary["net_signal"] = sent_summary["net_signal"].clip(-2, 2)
    st.dataframe(sent_summary.sort_values("net_signal", ascending=False), width="stretch")

# ---- Tab 2: Stock Signals (Searchable/Filterable) ----
with tab_signals:
    st.subheader("All Signals for Selected Stocks")
    
    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        event_filter = st.multiselect("Event", sorted(used["event"].unique()), default=[])
    with fcol2:
        sent_filter = st.selectbox("Sentiment", ["All", "Positive (>0)", "Negative (<0)", "Neutral (≈0)"])
    with fcol3:
        impact_min = st.slider("Min Impact", 1, 10, 1)
    
    # Apply filters
    filtered = used.copy()
    if event_filter:
        filtered = filtered[filtered["event"].isin(event_filter)]
    if sent_filter == "Positive (>0)":
        filtered = filtered[filtered["sentiment"] > 0.1]
    elif sent_filter == "Negative (<0)":
        filtered = filtered[filtered["sentiment"] < -0.1]
    elif sent_filter == "Neutral (≈0)":
        filtered = filtered[filtered["sentiment"].between(-0.1, 0.1)]
    filtered = filtered[filtered["impact"] >= impact_min]
    
    # Search
    search = st.text_input("Search text", placeholder="Filter by keyword in signal text...")
    if search:
        filtered = filtered[filtered["text"].str.contains(search, case=False, na=False)]
    
    st.caption(f"Showing {len(filtered)} of {len(used)} signals")
    
    # Display table
    display_cols = ["timestamp", "ticker", "sentiment", "event", "event_confidence", "impact", "text"]
    available_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(
        filtered[available_cols].sort_values("timestamp", ascending=False)
        .rename(columns={"timestamp": "Time", "ticker": "Ticker", "sentiment": "Sentiment",
                         "event": "Event", "event_confidence": "Confidence", "impact": "Impact", "text": "Text"}),
        width="stretch", hide_index=True, height=500,
        column_config={
            "Text": st.column_config.TextColumn(width="large"),
            "Time": st.column_config.TextColumn(width="medium"),
        }
    )

# ---- Tab 3: Market-Wide Signals ----
with tab_market:
    st.subheader("Market-Wide Signals (No Confident Ticker Match)")
    st.caption("These signals affect aggregate market risk but not individual stock weights.")
    
    if market_sigs.empty:
        st.info("No market-wide signals in current dataset.")
    else:
        # Filters
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            m_event_filter = st.multiselect("Event", sorted(market_sigs["event"].unique()), default=[])
        with mcol2:
            m_impact_min = st.slider("Min Impact", 1, 10, 1, key="mkt_impact")
        
        m_filtered = market_sigs.copy()
        if m_event_filter:
            m_filtered = m_filtered[m_filtered["event"].isin(m_event_filter)]
        m_filtered = m_filtered[m_filtered["impact"] >= m_impact_min]
        
        m_search = st.text_input("Search market signals", placeholder="Filter by keyword...")
        if m_search:
            m_filtered = m_filtered[m_filtered["text"].str.contains(m_search, case=False, na=False)]
        
        st.caption(f"Showing {len(m_filtered)} of {len(market_sigs)} market signals")
        
        m_cols = ["timestamp", "sentiment", "event", "event_confidence", "impact", "source", "text"]
        m_avail = [c for c in m_cols if c in m_filtered.columns]
        st.dataframe(
            m_filtered[m_avail].sort_values("timestamp", ascending=False)
            .rename(columns={"timestamp": "Time", "sentiment": "Sentiment", "event": "Event",
                             "event_confidence": "Confidence", "impact": "Impact", "source": "Source", "text": "Text"}),
            width="stretch", hide_index=True, height=400,
            column_config={"Text": st.column_config.TextColumn(width="large")}
        )

# ---- Tab 4: Weights Over Time ----
with tab_time:
    st.subheader("Weight Trajectories")
    delta = (weights - weights.iloc[0]) * 100
    final = delta.iloc[-1].sort_values()
    movers = list(dict.fromkeys(list(final.index[:3]) + list(final.index[-3:])))
    show = st.multiselect("Highlighted Stocks", tickers, default=movers)
    st.caption("Change in weight vs equal-weight start (percentage points)")
    
    x = list(delta.index)
    fig = go.Figure()
    for t in tickers:
        if t not in show:
            fig.add_trace(go.Scatter(x=x, y=delta[t], mode="lines", line=dict(color=GREY, width=1),
                                     hovertemplate=f"%{{x}}<br>{t}: %{{y:.2f}} pp<extra></extra>"))
    for t in show:
        c = UP if delta[t].iloc[-1] >= 0 else DOWN
        fig.add_trace(go.Scatter(x=x, y=delta[t], mode="lines", line=dict(color=c, width=2.5),
                                 hovertemplate=f"%{{x}}<br>{t}: %{{y:.2f}} pp<extra></extra>"))
        fig.add_trace(go.Scatter(x=[x[-1]], y=[delta[t].iloc[-1]], mode="text", text=[f"  {t}"],
                                 textposition="middle right", textfont=dict(color=c),
                                 hoverinfo="skip", cliponaxis=False))
    fig.add_hline(y=0, line_color="#999", line_width=1)
    fig.update_xaxes(type="category", nticks=8)
    style(fig, 450)
    fig.update_layout(margin=dict(l=0, r=70, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    
    # Event breakdown driving weight changes
    st.subheader("Event Breakdown by Step")
    step_event = used.groupby(["step_label", "event"]).size().unstack(fill_value=0)
    if not step_event.empty:
        fig2 = px.bar(step_event, barmode="stack", labels={"value": "Signals", "step_label": "Step"})
        style(fig2, 300)
        st.plotly_chart(fig2, width="stretch")

# ---- Tab 5: Replay a Step ----
with tab_replay:
    st.subheader("Step Detail")
    idx = st.slider("Step", 0, len(weights) - 1, len(weights) - 1)
    label = weights.index[idx]
    left, right = st.columns(2)
    with left:
        st.caption(f"Weights at: {label}")
        step_w = (weights.iloc[idx] * 100).rename("Weight (%)").round(2).to_frame()
        step_w["Net Signal"] = scores.iloc[idx].round(2)
        st.dataframe(step_w.sort_values("Weight (%)", ascending=False), width="stretch")
    with right:
        st.caption("Signals Driving This Step")
        if idx == 0:
            st.info("Start: equal weights, no signals yet.")
        else:
            step_sig = used[used["step_label"] == label].copy()
            if step_sig.empty:
                st.info("No stock-specific signals in this step.")
            else:
                step_sig["contribution"] = (step_sig["sentiment"] * step_sig["impact"] / 10).round(3)
                display = step_sig[["ticker", "sentiment", "event", "impact", "contribution", "text"]]
                display = display.rename(columns={"ticker": "Ticker", "sentiment": "Sentiment",
                                                  "event": "Event", "impact": "Impact",
                                                  "contribution": "Weight Δ", "text": "Text"})
                st.dataframe(display.sort_values("Weight Δ", ascending=False), width="stretch", hide_index=True,
                             column_config={"Text": st.column_config.TextColumn(width="large")})

# ---- Tab 6: Methodology ----
with tab_method:
    st.subheader("How It Works")
    st.markdown("""
### Data Pipeline
1. **Ingestion** (`src/ingest.py`): News (NewsAPI or sample) + Tweets (Kaggle or HF dataset)
2. **Ticker Mapping**: Exchange tag → Cashtag → Company name *with finance context* (reduces false positives)
3. **Relevance Filter**: Requires confident ticker match OR finance keywords
4. **Near-Duplicate Removal**: Drops articles with >85% text similarity
5. **Risk Engine** (`src/engine.py`): FinBERT sentiment + Zero-shot event classification (BART-MNLI)
6. **Impact Score** (`src/impact.py`): `base_severity × (0.5+0.5×|sentiment|) × (0.5+0.5×confidence)`, bounded [1,10]

### Rebalancing Logic (Module A)
For each time step:
1. **Net Signal** per stock = Σ(sentiment × impact/10), capped at ±2
2. **Tilt**: `weight_new = weight_old × exp(sensitivity × net_signal)`
3. **Decay**: Pull toward equal-weight: `weight = (1-decay)×tilted + decay×equal_weight`
4. **Limits**: Clip to [min_weight, max_weight], renormalize to 100%

### Signal Classification
- **Sentiment**: FinBERT, score = P(positive) - P(negative) ∈ [-1, 1]
- **Event**: Zero-shot (BART-MNLI), 12 categories + "Other" if confidence < 0.3
- **Impact**: Rule-based heuristic (not a trained model)

### Limitations
- Event classification is zero-shot; ~65% of tweets land in "Other"
- Impact scores are heuristic, not calibrated to real losses
- Index is mock; no price backtest or transaction costs
- Ticker mapping is keyword-based; may misattribute
""")

# ---------- Footer ----------
st.markdown("---")
st.caption("S&P Global AI/NLP Risk Engine Hackathon • Module A: Tactical Index Rebalancer")