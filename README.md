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
| `impact` | 1 to 10 | Rule: event base severity x sentiment strength x classifier confidence |

Signals are written to `data/signals.csv` and `data/signals.json`.

**Module A, tactical index rebalancer** (`app.py`, `src/rebalance.py`): the index starts equal-weighted.
Each time step, a stock's net signal is the sum of `sentiment x impact / 10` over its new signals. Its weight is
multiplied by `exp(sensitivity x net_signal)`, partly pulled back toward equal weight (decay), clipped to a
floor and cap, and renormalized to 100%. Positive news raises a weight, negative news lowers it.

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

## Run it

Install and launch the dashboard (works without a GPU or torch):

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard reads `data/signals.csv` if you have run the engine, otherwise the bundled
`sample/signals_sample.csv`.

Run the engine yourself (needs torch; a GPU such as Colab's T4 is recommended):

```bash
# optional: live news
export NEWSAPI_KEY=your_key
# optional: Kaggle "Stock Tweets for Sentiment Analysis and Prediction" saved as data/stock_tweets.csv
python -m src.run_engine --n 500
```

Without a News API key the engine uses 10 built-in demo headlines. Without the Kaggle file it falls back to the
Hugging Face `zeroshot/twitter-financial-news-sentiment` tweets.

## Data sources

- Kaggle: Stock Tweets for Sentiment Analysis and Prediction (tweets for 25 tickers with dates)
- Hugging Face: `zeroshot/twitter-financial-news-sentiment` (used for testing the sentiment model)
- News API (optional live headlines)

## Results and limitations

- **Sentiment:** FinBERT off the shelf scored 70% accuracy and 0.63 macro-F1 on 300 validation tweets from the
  Hugging Face dataset. It rarely flips direction (bullish vs bearish); most errors are around the neutral boundary.
- **Event classification** is zero-shot and was checked by reading examples, not scored against labels.
  On the Kaggle tweets, about 65% of items land in `Other`, because most are short price chatter that fits none of the
  labels with enough confidence. It can also match on words, not meaning (for example, "EV tax credits" labeled as a
  credit event).
- **Impact score** is a transparent heuristic with hand-chosen weights, not a trained model. It rarely exceeds 7.
- The index is a mock one built from whichever tickers appear most in the signals. There is no price backtest.

## Project layout

```
src/ingest.py      two sources, ticker detection, relevance filter
src/engine.py      sentiment + event models, analyze()
src/impact.py      impact score rule
src/run_engine.py  runs the engine, writes signals
src/rebalance.py   Module A logic
app.py             Streamlit dashboard
notebooks/         EDA and model experiments
```