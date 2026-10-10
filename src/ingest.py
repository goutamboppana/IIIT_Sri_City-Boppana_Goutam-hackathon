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

# Recognition universe: ~80 major US-listed companies across sectors.
# This is SEPARATE from the portfolio/index constituent universe.
# The risk engine recognizes all these companies; the rebalancer only uses its configured constituents.
COMPANIES = {
    # Technology & Semiconductors
    "apple": "AAPL", "microsoft": "MSFT", "amazon": "AMZN", "alphabet": "GOOGL",
    "google": "GOOGL", "meta": "META", "facebook": "META", "tesla": "TSLA",
    "nvidia": "NVDA", "netflix": "NFLX", "adobe": "ADBE", "salesforce": "CRM",
    "intel": "INTC", "amd": "AMD", "qualcomm": "QCOM", "broadcom": "AVGO",
    "texas instruments": "TXN", "micron": "MU", "lam research": "LRCX",
    "applied materials": "AMAT", "kla": "KLAC", "synopsys": "SNPS", "cadence": "CDNS",
    "oracle": "ORCL", "ibm": "IBM", "servicenow": "NOW", "workday": "WDAY",
    "palo alto networks": "PANW", "crowdstrike": "CRWD", "datadog": "DDOG",
    "snowflake": "SNOW", "mongodb": "MDB", "atlassian": "TEAM", "zoom": "ZM",
    "uber": "UBER", "airbnb": "ABNB", "shopify": "SHOP", "square": "SQ",
    "paypal": "PYPL", "block": "SQ",

    # Financial Services & Banks
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman sachs": "GS",
    "bank of america": "BAC", "wells fargo": "WFC", "citigroup": "C",
    "morgan stanley": "MS", "american express": "AXP", "visa": "V",
    "mastercard": "MA", "berkshire hathaway": "BRK.B", "blackrock": "BLK",
    "charles schwab": "SCHW", "fidelity": "FNF", "state street": "STT",
    "pnc": "PNC", "us bancorp": "USB", "truist": "TFC", "capital one": "COF",
    "discover": "DFS", "synchrony": "SYF", "ameriprise": "AMP",
    "northern trust": "NTRS", "t. rowe price": "TROW",

    # Healthcare & Pharmaceuticals
    "johnson & johnson": "JNJ", "pfizer": "PFE", "merck": "MRK",
    "abbvie": "ABBV", "eli lilly": "LLY", "bristol myers": "BMY",
    "amgen": "AMGN", "gilead": "GILD", "biogen": "BIIB", "regeneron": "REGN",
    "vertex": "VRTX", "moderna": "MRNA", "unitedhealth": "UNH",
    "cvs": "CVS", "cigna": "CI", "anthem": "ELV", "humana": "HUM",
    "mcKesson": "MCK", "cardinal health": "CAH", "medtronic": "MDT",
    "abbott": "ABT", "danaher": "DHR", "thermo fisher": "TMO",
    "intuitive surgical": "ISRG", "stryker": "SYK", "baxter": "BAX",

    # Consumer Goods & Retail
    "walmart": "WMT", "home depot": "HD", "costco": "COST",
    "target": "TGT", "lowes": "LOW", "nike": "NKE", "starbucks": "SBUX",
    "mcdonalds": "MCD", "pepsi": "PEP", "coca cola": "KO", "procter & gamble": "PG",
    "colgate": "CL", "kimberly clark": "KMB", "estee lauder": "EL",
    "loreal": "LRLCY", "philip morris": "PM", "altria": "MO",
    "monster beverage": "MNST", "kellogg": "K", "general mills": "GIS",
    "kraft heinz": "KHC", "conagra": "CAG", "tyson": "TSN", "hormel": "HRL",

    # Energy
    "exxon": "XOM", "chevron": "CVX", "conocophillips": "COP",
    "eog resources": "EOG", "pioneer natural": "PXD", "slb": "SLB",
    "halliburton": "HAL", "baker hughes": "BKR", "occidental": "OXY",
    "marathon": "MPC", "valero": "VLO", "phillips 66": "PSX",
    "kinder morgan": "KMI", "williams": "WMB", "oneok": "OKE",

    # Industrials
    "boeing": "BA", "caterpillar": "CAT", "deere": "DE",
    "honeywell": "HON", "3m": "MMM", "ge": "GE", "rtx": "RTX",
    "lockheed martin": "LMT", "northrop grumman": "NOC",
    "general dynamics": "GD", "l3harris": "LHX", "transdigm": "TDG",
    "united airlines": "UAL", "delta": "DAL", "american airlines": "AAL",
    "southwest": "LUV", "fedex": "FDX", "ups": "UPS",
    "union pacific": "UNP", "norfolk southern": "NSC", "csx": "CSX",
    "illinois tool works": "ITW", "parker hannifin": "PH", "emerson": "EMR",
    "eaton": "ETN", "te connect": "TEL", "rockwell": "ROK",
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
    "Amazon AWS revenue growth accelerates on AI demand",
    "Goldman Sachs sees recession risk rising to 35 percent",
    "Exxon posts record quarterly profit on high oil prices",
    "Walmart raises full-year guidance on strong consumer spending",
    "Johnson & Johnson talc litigation settlement advances",
    "AMD gains server CPU market share from Intel",
    "Visa and Mastercard face antitrust scrutiny over swipe fees",
    "UnitedHealth lowers profit forecast on Medicare costs",
    "Caterpillar warns of China slowdown impacting 2024 outlook",
    "Chevron acquires Hess in $53 billion all-stock deal",
]


EXCHANGE_TAG = re.compile(r"\((?:NYSE|NASDAQ|NYSEARCA|AMEX)[:\s]+([A-Za-z.]{1,6})\)", re.IGNORECASE)
CASHTAG = re.compile(r"\$([A-Za-z]{1,5})\b")


@dataclass
class TickerMatch:
    ticker: str
    confidence: str  # "high", "medium", "low"
    method: str      # "exchange_tag", "cashtag", "company_name_with_finance", "company_name_alone"
    first_position: int = -1  # Character position of first mention in text


@dataclass
class TickerMatches:
    """Container for multiple ticker matches from a single text."""
    matches: list[TickerMatch]
    primary: Optional[TickerMatch] = None  # Best match if single attribution needed

    def __bool__(self):
        return bool(self.matches)

    def __iter__(self):
        return iter(self.matches)

    def get_primary(self) -> Optional[TickerMatch]:
        """Return the highest-confidence match for single-attribution use cases.

        Tie-breaking order:
        1. Highest confidence (high > medium > low)
        2. Earliest mention in text (first_position)
        3. Method priority (exchange_tag > cashtag > company_name_with_finance > company_name_alone)
        """
        if self.primary:
            return self.primary
        if not self.matches:
            return None

        conf_order = {"high": 0, "medium": 1, "low": 2}
        method_order = {"exchange_tag": 0, "cashtag": 1, "company_name_with_finance": 2, "company_name_alone": 3}

        # Sort by confidence, then first position, then method
        self.matches.sort(key=lambda m: (
            conf_order.get(m.confidence, 3),
            m.first_position if m.first_position >= 0 else float('inf'),
            method_order.get(m.method, 4)
        ))
        self.primary = self.matches[0]
        return self.primary


# Valid ticker pattern: 1-5 uppercase letters, optionally with . for share classes
VALID_TICKER = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")


def find_tickers(text: str) -> TickerMatches:
    """
    Find ALL tickers mentioned in text with confidence levels.
    Priority: exchange tag > cashtag > company name with finance context > company name alone.
    Finance context is scoped to the same sentence as the company mention.
    Returns TickerMatches container with all matches and a primary match.
    """
    s = str(text)
    all_matches = []

    # 1. Exchange tags (highest confidence)
    for m in EXCHANGE_TAG.finditer(s):
        ticker = m.group(1).upper()
        if VALID_TICKER.match(ticker):
            all_matches.append(TickerMatch(ticker, "high", "exchange_tag", m.start()))

    # 2. Cashtags (high confidence)
    for m in CASHTAG.finditer(s):
        ticker = m.group(1).upper()
        if VALID_TICKER.match(ticker) and ticker in COMPANIES.values():
            all_matches.append(TickerMatch(ticker, "high", "cashtag", m.start()))

    low = s.lower()

    # Split text into sentences for finance-context scoping
    # Simple sentence splitter: split on .!? followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', s)
    sentence_spans = []  # (start_char, end_char, sentence_text)
    pos = 0
    for sent in sentences:
        start = s.find(sent, pos)
        if start == -1:
            start = pos
        end = start + len(sent)
        sentence_spans.append((start, end, sent))
        pos = end

    # For each sentence, check if it has finance words
    sentence_has_finance = []
    for _, _, sent in sentence_spans:
        sentence_has_finance.append(bool(FINANCE_WORDS.search(sent)))

    # 3. Company names with finance context (medium confidence)
    # Check each company name against each sentence
    for name in COMPANY_NAMES_SORTED:
        ticker = COMPANIES[name]
        # Skip if already matched via exchange_tag or cashtag
        if any(m.ticker == ticker for m in all_matches):
            continue

        # Find all occurrences of company name in text
        pattern = rf"\b{re.escape(name)}\b"
        for match in re.finditer(pattern, low):
            match_start = match.start()
            match_end = match.end()

            # Find which sentence this mention falls in
            for i, (sent_start, sent_end, _) in enumerate(sentence_spans):
                if sent_start <= match_start < sent_end:
                    # Check if this sentence has finance words
                    if sentence_has_finance[i]:
                        all_matches.append(TickerMatch(ticker, "medium", "company_name_with_finance", match_start))
                    break

    # 4. Company names alone (low confidence) - only if cashtags present in text
    # This helps with tweets where $TICKER is common but company name appears without finance words
    cashtag_present = bool(CASHTAG.search(s))
    if cashtag_present:
        for name in COMPANY_NAMES_SORTED:
            ticker = COMPANIES[name]
            if any(m.ticker == ticker for m in all_matches):
                continue
            pattern = rf"\b{re.escape(name)}\b"
            for match in re.finditer(pattern, low):
                all_matches.append(TickerMatch(ticker, "low", "company_name_alone", match.start()))
                break  # Only need first mention for low confidence

    # Deduplicate by ticker, keeping highest confidence (and earliest position for same confidence)
    seen = {}
    for m in all_matches:
        if m.ticker not in seen:
            seen[m.ticker] = m
        else:
            existing = seen[m.ticker]
            conf_order = {"high": 0, "medium": 1, "low": 2}
            if conf_order[m.confidence] < conf_order[existing.confidence]:
                seen[m.ticker] = m
            elif conf_order[m.confidence] == conf_order[existing.confidence]:
                # Same confidence: keep earliest mention
                if m.first_position >= 0 and (existing.first_position < 0 or m.first_position < existing.first_position):
                    seen[m.ticker] = m

    unique_matches = list(seen.values())
    return TickerMatches(unique_matches)


# Backward compatibility: find_ticker returns primary match only
def find_ticker(text: str) -> Optional[TickerMatch]:
    """Backward compatible single-ticker match (returns primary)."""
    return find_tickers(text).get_primary()


def is_relevant(text: str, ticker_matches) -> bool:
    """
    Stricter relevance: require either a confident ticker match OR finance words.
    Low-confidence company-name-only matches are NOT considered relevant on their own.
    Accepts TickerMatch, TickerMatches, or None for backward compatibility.
    """
    if ticker_matches is None:
        return bool(FINANCE_WORDS.search(str(text)))

    # Handle TickerMatch (single) or TickerMatches (multiple)
    if isinstance(ticker_matches, TickerMatch):
        matches = [ticker_matches]
    elif isinstance(ticker_matches, TickerMatches):
        matches = list(ticker_matches)
    else:
        matches = []

    # High or medium confidence ticker match makes it relevant
    for m in matches:
        if m.confidence in ("high", "medium"):
            return True
    # Market-wide finance news is relevant even without ticker
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
            # Use a broad financial news query to capture expanded company universe
            # NewsAPI free tier: 100 results max per request, so we respect pageSize limit
            q = '(stock OR earnings OR revenue OR acquisition OR merger OR dividend OR buyback OR ' \
                'analyst OR upgrade OR downgrade OR Fed OR inflation OR rates OR oil OR economy)'
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

    # Find all tickers with confidence
    ticker_matches_list = [find_tickers(x) for x in df["text"]]
    df["ticker_matches"] = ticker_matches_list
    # Primary ticker for backward compatibility
    primary_matches = [tm.get_primary() for tm in ticker_matches_list]
    df["ticker"] = [m.ticker if m else None for m in primary_matches]
    df["ticker_confidence"] = [m.confidence if m else None for m in primary_matches]
    df["ticker_method"] = [m.method if m else None for m in primary_matches]
    # All tickers as pipe-separated string for multi-ticker support
    df["all_tickers"] = ["|".join(m.ticker for m in tm) if tm else "" for tm in ticker_matches_list]
    df["all_ticker_confidences"] = ["|".join(m.confidence for m in tm) if tm else "" for tm in ticker_matches_list]
    df["all_ticker_methods"] = ["|".join(m.method for m in tm) if tm else "" for tm in ticker_matches_list]

    df["timestamp"] = df["timestamp"].fillna(_now()).astype(str)

    before = len(df)

    # Track rejection reasons
    rejection_reasons = []
    rejection_details = []  # For inspectability

    # Filter: minimum text length
    short_mask = df["text"].str.len() < 15
    rejection_reasons.extend(["short_text"] * short_mask.sum())
    rejection_details.extend([("short_text", row["text"][:50]) for _, row in df[short_mask].iterrows()])
    df = df[~short_mask].copy()

    # Filter: relevance
    relevance_results = [(is_relevant(x, tm), x, tm) for x, tm in zip(df["text"], df["ticker_matches"])]
    keep = [r[0] for r in relevance_results]
    rejected_irrel = [(row["text"][:50], "no_ticker_no_finance") for i, r in enumerate(relevance_results) if not r[0] for _, row in [df.iloc[i:i+1].iterrows().__next__()]]
    rejection_reasons.extend(["irrelevant"] * (~pd.Series(keep)).sum())
    rejection_details.extend(rejected_irrel)
    df = df[keep].copy()

    # Near-duplicate detection (keep first occurrence)
    # Use first 100 chars for speed
    texts_short = df["text"].str[:100].tolist()
    is_dup = [False] * len(texts_short)
    dup_pairs = []
    for i in range(len(texts_short)):
        if is_dup[i]:
            continue
        for j in range(i + 1, len(texts_short)):
            if not is_dup[j] and _text_similarity(texts_short[i], texts_short[j]) > 0.85:
                is_dup[j] = True
                dup_pairs.append((i, j))
    rejection_reasons.extend(["near_duplicate"] * sum(is_dup))
    rejection_details.extend([("near_duplicate", df.iloc[j]["text"][:50]) for i, j in dup_pairs])
    # Use boolean array aligned with df index
    df = df[~np.array(is_dup)].copy()

    # Exact duplicate removal (fallback)
    exact_dups = df.duplicated(subset="text")
    rejection_reasons.extend(["exact_duplicate"] * exact_dups.sum())
    rejection_details.extend([("exact_duplicate", row["text"][:50]) for _, row in df[exact_dups].iterrows()])
    df = df[~exact_dups].copy()

    kept = len(df)

    # Build rejection summary for inspectability
    rejection_summary = {
        "short_text": rejection_reasons.count("short_text"),
        "irrelevant": rejection_reasons.count("irrelevant"),
        "near_duplicate": rejection_reasons.count("near_duplicate"),
        "exact_duplicate": rejection_reasons.count("exact_duplicate"),
    }

    print(f"Ingested {before} items, kept {kept} after filtering "
          f"(rejected: {before - kept} - "
          f"short: {rejection_summary['short_text']}, "
          f"irrelevant: {rejection_summary['irrelevant']}, "
          f"near_dup: {rejection_summary['near_duplicate']}, "
          f"exact_dup: {rejection_summary['exact_duplicate']}) "
          f"(sources: {', '.join(sorted(df['source'].unique()))})")

    # Attach rejection details to dataframe for inspection (as metadata)
    df.attrs["rejection_summary"] = rejection_summary
    df.attrs["rejection_details"] = rejection_details[:50]  # Limit stored details

    return df[["source", "timestamp", "ticker", "ticker_confidence", "ticker_method",
               "all_tickers", "all_ticker_confidences", "all_ticker_methods", "text"]]
