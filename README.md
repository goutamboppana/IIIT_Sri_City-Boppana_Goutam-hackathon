# AI/NLP Risk Engine + Tactical Index Rebalancer

An NLP engine that reads financial text (news headlines and stock tweets) and turns it into structured
risk signals, plus a dashboard that uses those signals to rebalance a mock stock index (Module A).

## What it does

**Risk engine** (`src/`): for each piece of text it outputs

| Field | Meaning | How it is produced |
|---|---|---|
| `sentiment` | -1.0 to 1.0 | FinBERT: P(positive) - P(negative) |
| `event` | Earnings, Analyst Rating, Credit Event, Geopolitical, ... or `Other` | Zero-shot classification (`facebook/bart-large-mnli`); confidence under 0.3 becomes `Other` |
| `event_confidence` | 0 to 1 | Score of the winning label |
| `impact` | 1 to 10 | Rule: event base severity × sentiment strength × classifier confidence |

Signals are written to `data/signals.csv` and `data/signals.json`.

**Module A, tactical index rebalancer** (`app.py`, `src/rebalance.py`): the index starts equal-weighted.
Each time step, a stock's net signal is the sum of `sentiment × impact / 10` over its new signals (only high/medium confidence ticker matches).
Its weight is multiplied by `exp(sensitivity × net_signal)`, partly pulled back toward equal weight (decay), clipped to a
floor and cap, and renormalized to 100%. Positive news raises a weight, negative news lowers it.
Market-wide signals (no confident ticker) are retained for aggregate risk view but do not drive individual stock weights.

## Architecture

```
News (NewsAPI / sample headlines) --+
                                    +--> clean + ticker detection + relevance filter
Tweets (Kaggle stock tweets) -------+                |
                                                      v
                               FinBERT sentiment + zero-shot event class
                                                      |
                                            impact score (rule)
                                                      |
                                        data/signals.csv / .json
                                                      |
                              rebalancer --> Streamlit dashboard
```

### Data Quality Improvements
- **Ticker mapping**: Exchange tag → Cashtag ($AAPL) → Company name *with finance context* (reduces false positives like "Tesla, Inc. reserved for PyPI package")
- **Relevance filtering**: Requires confident ticker match OR finance keywords
- **Near-duplicate detection**: Drops articles with >85% text similarity
- **Rejection tracking**: Logs counts of rejected items by reason (short, irrelevant, near-duplicate)

## Run it

### Dashboard (no GPU required)
```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard reads `data/signals.csv` if you have run the engine, otherwise the bundled
`sample/signals_sample.csv`.

### Risk Engine (needs torch; GPU recommended)
```bash
# optional: live news
export NEWSAPI_KEY=your_key
# optional: Kaggle "Stock Tweets for Sentiment Analysis and Prediction" saved as data/stock_tweets.csv
python -m src.run_engine --n 500
```

Without a News API key the engine uses 10 built-in demo headlines. Without the Kaggle file it falls back to the
Hugging Face `zeroshot/twitter-financial-news-sentiment` tweets.

The engine now supports `--validate` flag to validate output schema before writing:
```bash
python -m src.run_engine --n 500 --validate
```

### Schema Validation
```bash
python -m src.schema data/signals.csv
```

### Tests (no model downloads, no API calls)
```bash
python -m pytest tests/ -v
```

## Data sources

- **News**: NewsAPI (live) or 10 built-in sample headlines (fallback)
- **Tweets**: Kaggle "Stock Tweets for Sentiment Analysis and Prediction" (if `data/stock_tweets.csv` exists) or Hugging Face `zeroshot/twitter-financial-news-sentiment` validation split

## Signal Schema

The output `signals.csv` contains:

| Column | Type | Description |
|---|---|---|
| `source` | string | Data source: `newsapi`, `sample_headlines`, `kaggle_stock_tweets`, `hf_finance_tweets` |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `ticker` | string/null | Stock ticker (e.g., `AAPL`) or empty for market-wide |
| `ticker_confidence` | string/null | `high` (exchange tag/cashtag), `medium` (company name + finance context), or empty |
| `ticker_method` | string/null | `exchange_tag`, `cashtag`, `company_name_with_finance`, or empty |
| `text` | string | Original text content |
| `sentiment` | float | FinBERT score in [-1, 1] |
| `event` | string | Event category (e.g., `Earnings`, `Other`) |
| `event_confidence` | float | Classifier confidence in [0, 1] |
| `impact` | int | Impact score in [1, 10] |

## Results and limitations

- **Sentiment:** FinBERT off the shelf scored 70% accuracy and 0.63 macro-F1 on 300 validation tweets from the
  Hugging Face dataset. It rarely flips direction (bullish vs bearish); most errors are around the neutral boundary.
- **Event classification** is zero-shot and was checked by reading examples, not scored against labels.
  On the Kaggle tweets, about 65% of items land in `Other`, because most are short price chatter that fits none of the
  labels with enough confidence. It can also match on words, not meaning (for example, "EV tax credits" labeled as a
  credit event).
- **Impact score** is a transparent heuristic with hand-chosen weights, not a trained model. It rarely exceeds 7.
- **Ticker mapping** is keyword-based; company name matching requires finance context to reduce false positives.
- The index is a mock one built from whichever tickers appear most in the signals. There is no price backtest.
- **No Module B yet** (strategic portfolio stress testing) - planned for future work.

## Project layout

```
src/ingest.py       two sources, ticker detection, relevance filter, near-dedup
src/engine.py       sentiment + event models, analyze()
src/impact.py       impact score rule
src/run_engine.py   runs the engine, writes signals, validates schema
src/rebalance.py    Module A logic (rebalancing + market signals)
src/schema.py       signal schema definition & validation
app.py              Streamlit dashboard (Module A)
tests/              lightweight unit tests (no models, no APIs)
notebooks/          EDA and model experiments
data/               generated signals (git-ignored) + raw tweet data
sample/             bundled sample signals for demo
```

## Security & Configuration

- API keys via environment variables (`NEWSAPI_KEY`)
- `.env` file supported via `python-dotenv` (git-ignored)
- `.env.example` provides template
- No secrets in logs or code

## Dashboard Features

- **Data freshness indicator** based on latest signal timestamp
- **Ingestion statistics** and source breakdowns
- **Sentiment summary** metrics (positive/negative/neutral)
- **Event category** and **impact severity** breakdowns
- **Searchable, filterable signal table** for stock-specific signals
- **Market-wide signals view** (unmapped/aggregate risk)
- **Portfolio weight comparison** (baseline vs adjusted)
- **Weight trajectories** over time with highlighted movers
- **Step-by-step replay** showing signals driving each rebalance
- **Methodology documentation** in-app