"""Data ingestion: pulls text from two sources and applies cleaning + relevance filtering.

Source 1 (news):   NewsAPI if NEWSAPI_KEY is set, else a small built-in sample of headlines.
Source 2 (tweets): data/stock_tweets.csv (Kaggle) if present, else the Hugging Face
                   finance-tweets dataset.
"""
import os
import re
import difflib
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

DATA = Path(__file__).resolve().parent.parent / "data"

# Mock index: 15 large caps. Company-name keyword -> ticker.
COMPANIES = {
    "apple": "AAPL", "microsoft": "MSFT", "amazon": "AMZN", "alphabet": "GOOGL",
    "google": "GOOGL", "meta": "META", "facebook": "META", "tesla": "TSLA",
    "nvidia": "NVDA", "jpmorgan": "JPM", "goldman sachs": "GS",
    "bank of america": "BAC", "exxon": "XOM", "walmart": "WMT",
    "johnson & johnson": "JNJ", "pfizer": "PFE", "boeing": "BA",
}

# Company names sorted by length (longest first) to match "bank of america" before "america"
COMPANY_NAMES_SORTED = sorted(COMPANIES.keys(), key=len, reverse=True)

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
CASHTAG = re.compile(r"\$([A-Za-z]{1,5})\b")


@dataclass
class TickerMatch:
    ticker: str
    confidence: str  # "high", "medium", "low"
    method: str      # "exchange_tag", "cashtag", "company_name_with_finance", "company_name_alone"


def find_ticker(text: str) -> Optional[TickerMatch]:
    """
    Find ticker with confidence level.
    Priority: exchange tag > cashtag > company name with finance context > company name alone.
    Returns None if no match.
    """
    s = str(text)
    
    # 1. Exchange tag (highest confidence)
    m = EXCHANGE_TAG.search(s)
    if m:
        return TickerMatch(m.group(1).upper(), "high", "exchange_tag")
    
    # 2. Cashtag (high confidence)
    m = CASHTAG.search(s)
    if m:
        return TickerMatch(m.group(1).upper(), "high", "cashtag")
    
    low = s.lower()
    
    # 3. Company name WITH finance context (medium confidence)
    for name in COMPANY_NAMES_SORTED:
        if re.search(rf"\b{re.escape(name)}\b", low):
            # Require at least one finance word in the same text
            if FINANCE_WORDS.search(s):
                return TickerMatch(COMPANIES[name], "medium", "company_name_with_finance")
    
    # 4. Company name alone (low confidence) - only for tweets where cashtags are common
    # For news, we skip this to avoid false positives like "Tesla, Inc. reserved for PyPI package"
    return None


def is_relevant(text: str, ticker_match: Optional[TickerMatch]) -> bool:
    """
    Stricter relevance: require either a confident ticker match OR finance words.
    Low-confidence company-name-only matches are NOT considered relevant on their own.
    """
    if ticker_match and ticker_match.confidence in ("high", "medium"):
        return True
    return bool(FINANCE_WORDS.search(str(text)))


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text_similarity(a: str, b: str) -> float:
    """Quick similarity check using difflib.SequenceMatcher."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


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
        except Exception:
            print("NewsAPI failed; using sample headlines instead.")
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
    
    # Find tickers with confidence
    ticker_matches = [find_ticker(x) for x in df["text"]]
    df["ticker_match"] = ticker_matches
    df["ticker"] = [m.ticker if m else None for m in ticker_matches]
    df["ticker_confidence"] = [m.confidence if m else None for m in ticker_matches]
    df["ticker_method"] = [m.method if m else None for m in ticker_matches]
    
    df["timestamp"] = df["timestamp"].fillna(_now()).astype(str)
    
    before = len(df)
    
    # Track rejection reasons
    rejection_reasons = []
    
    # Filter: minimum text length
    keep = df["text"].str.len() >= 15
    rejection_reasons.extend(["short_text"] * (~keep).sum())
    df = df[keep].copy()
    
    # Filter: relevance
    keep = [is_relevant(x, t) for x, t in zip(df["text"], df["ticker_match"])]
    rejection_reasons.extend(["irrelevant"] * (~pd.Series(keep)).sum())
    df = df[keep].copy()
    
    # Near-duplicate detection (keep first occurrence)
    # Use first 100 chars for speed
    texts_short = df["text"].str[:100].tolist()
    is_dup = [False] * len(texts_short)
    for i in range(len(texts_short)):
        if is_dup[i]:
            continue
        for j in range(i + 1, len(texts_short)):
            if not is_dup[j] and _text_similarity(texts_short[i], texts_short[j]) > 0.85:
                is_dup[j] = True
    rejection_reasons.extend(["near_duplicate"] * sum(is_dup))
    # Use boolean array aligned with df index
    df = df[~np.array(is_dup)].copy()
    
    # Exact duplicate removal (fallback)
    df = df.drop_duplicates(subset="text").reset_index(drop=True)
    
    kept = len(df)
    print(f"Ingested {before} items, kept {kept} after filtering "
          f"(rejected: {before - kept} - "
          f"short: {rejection_reasons.count('short_text')}, "
          f"irrelevant: {rejection_reasons.count('irrelevant')}, "
          f"near_dup: {rejection_reasons.count('near_duplicate')}) "
          f"(sources: {', '.join(sorted(df['source'].unique()))})")
    
    return df[["source", "timestamp", "ticker", "ticker_confidence", "ticker_method", "text"]]