"""Data ingestion: pulls text from two sources and applies cleaning + relevance filtering.

Source 1 (news):   NewsAPI if NEWSAPI_KEY is set, else a small built-in sample of headlines.
Source 2 (tweets): data/stock_tweets.csv (Kaggle) if present, else the Hugging Face
                   finance-tweets dataset.
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# Mock index: 15 large caps. Company-name keyword -> ticker.
COMPANIES = {
    "apple": "AAPL", "microsoft": "MSFT", "amazon": "AMZN", "alphabet": "GOOGL",
    "google": "GOOGL", "meta": "META", "facebook": "META", "tesla": "TSLA",
    "nvidia": "NVDA", "jpmorgan": "JPM", "goldman sachs": "GS",
    "bank of america": "BAC", "exxon": "XOM", "walmart": "WMT",
    "johnson & johnson": "JNJ", "pfizer": "PFE", "boeing": "BA",
}

FINANCE_WORDS = re.compile(
    r"\b(earnings|revenue|profit|guidance|downgrade|upgrade|merger|acquisition|acquire[sd]?|"
    r"stocks?|shares|dividend|buyback|rates?|inflation|fed|bonds?|debt|default|lawsuit|"
    r"sanctions?|tariffs?|ipo|price target|analyst|ceo|cfo|quarter|q[1-4]|market|oil|bank|"
    r"economy|recession|gdp|yield)\b",
    re.IGNORECASE,
)

# Illustrative demo headlines used ONLY when no NewsAPI key is set.
SAMPLE_HEADLINES = [
    "Apple raises quarterly dividend and expands share buyback program",
    "Tesla shares fall after analyst downgrade over weak delivery outlook",
    "JPMorgan beats earnings expectations on strong trading revenue",
    "Fed signals further interest rate hikes as inflation stays elevated",
    "Boeing faces new regulatory probe over safety inspections",
    "Microsoft announces acquisition of a cybersecurity startup",
    "Oil prices jump as geopolitical tensions escalate in the Middle East",
    "Bank of America warns of rising credit card defaults",
    "Nvidia unveils new AI chip, shares rally",
    "Pfizer CFO to step down at the end of the quarter",
]


EXCHANGE_TAG = re.compile(r"\((?:NYSE|NASDAQ|NYSEARCA|AMEX)[:\s]+([A-Za-z.]{1,6})\)", re.IGNORECASE)


def find_ticker(text):
    """Exchange tag (NYSE:CORR), then cashtag ($AAPL), then company name. None if nothing found."""
    m = EXCHANGE_TAG.search(str(text))
    if m:
        return m.group(1).upper()
    m = re.search(r"\$([A-Za-z]{1,5})\b", str(text))
    if m:
        return m.group(1).upper()
    low = str(text).lower()
    for name, ticker in COMPANIES.items():
        if re.search(rf"\b{re.escape(name)}\b", low):
            return ticker
    return None


def is_relevant(text, ticker):
    return ticker is not None or bool(FINANCE_WORDS.search(str(text)))


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_news(n=50):
    key = os.environ.get("NEWSAPI_KEY")
    if key:
        try:
            import requests
            q = '(Apple OR Microsoft OR Amazon OR Tesla OR Nvidia OR JPMorgan OR "Goldman Sachs" OR Exxon OR Boeing OR Pfizer)'
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": q, "language": "en", "sortBy": "publishedAt",
                        "pageSize": min(n, 100), "apiKey": key},
                timeout=20,
            )
            r.raise_for_status()
            rows = []
            for a in r.json().get("articles", []):
                text = ". ".join(x for x in [a.get("title"), a.get("description")] if x)
                rows.append({"text": text, "timestamp": a.get("publishedAt") or _now(), "ticker": None})
            if rows:
                df = pd.DataFrame(rows)
                df["source"] = "newsapi"
                return df
        except Exception as e:
            print(f"NewsAPI failed ({e}); using sample headlines instead.")
    df = pd.DataFrame({"text": SAMPLE_HEADLINES, "timestamp": _now(), "ticker": None})
    df["source"] = "sample_headlines"
    return df.head(n)


def load_tweets(n=100, seed=1):
    path = DATA / "stock_tweets.csv"
    if path.exists():
        df = pd.read_csv(path).rename(
            columns={"Tweet": "text", "Date": "timestamp", "Stock Name": "ticker"}
        )[["text", "timestamp", "ticker"]]
        source = "kaggle_stock_tweets"
    else:
        from datasets import load_dataset
        df = load_dataset("zeroshot/twitter-financial-news-sentiment")["validation"].to_pandas()[["text"]]
        df["timestamp"] = None
        df["ticker"] = None
        source = "hf_finance_tweets"
    df = df.sample(min(n, len(df)), random_state=seed).copy()
    df["source"] = source
    return df


def load_all(n_each=100):
    df = pd.concat([load_news(n_each), load_tweets(n_each)], ignore_index=True)
    df["text"] = df["text"].astype(str).str.strip()
    df["ticker"] = [t if isinstance(t, str) and t else find_ticker(x)
                    for t, x in zip(df["ticker"], df["text"])]
    df["timestamp"] = df["timestamp"].fillna(_now()).astype(str)

    before = len(df)
    df = df[df["text"].str.len() >= 15]
    df = df[[is_relevant(x, t) for x, t in zip(df["text"], df["ticker"])]]
    df = df.drop_duplicates(subset="text").reset_index(drop=True)
    print(f"Ingested {before} items, kept {len(df)} after filtering "
          f"(sources: {', '.join(sorted(df['source'].unique()))})")
    return df[["source", "timestamp", "ticker", "text"]]