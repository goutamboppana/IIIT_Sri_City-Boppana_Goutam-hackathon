"""Lightweight unit tests for ingestion and ticker matching.
No model downloads, no API calls."""
import pytest
import pandas as pd
from src.ingest import (
    find_ticker, is_relevant, load_all, TickerMatch,
    COMPANIES, FINANCE_WORDS, _text_similarity
)


class TestFindTicker:
    """Tests for ticker detection with confidence levels."""

    def test_exchange_tag_high_confidence(self):
        m = find_ticker("Apple Inc. (NASDAQ: AAPL) reports earnings")
        assert m is not None
        assert m.ticker == "AAPL"
        assert m.confidence == "high"
        assert m.method == "exchange_tag"

    def test_cashtag_high_confidence(self):
        m = find_ticker("$TSLA shares rise on delivery news")
        assert m is not None
        assert m.ticker == "TSLA"
        assert m.confidence == "high"
        assert m.method == "cashtag"

    def test_company_name_with_finance_context_medium(self):
        # Company name + finance word = medium confidence
        m = find_ticker("Apple raises dividend and expands buyback")
        assert m is not None
        assert m.ticker == "AAPL"
        assert m.confidence == "medium"
        assert m.method == "company_name_with_finance"

    def test_company_name_without_finance_context_returns_none(self):
        # Company name alone (no finance words) should return None for news
        m = find_ticker("kafka-helmsman added to PyPI. Reserved for Tesla, Inc.")
        assert m is None, "Should not match Tesla without finance context"

    def test_unknown_company_returns_none(self):
        m = find_ticker("RandomCorp announces new product")
        assert m is None

    def test_longest_company_name_matched_first(self):
        # "bank of america" should match before "america"
        m = find_ticker("Bank of America beats earnings")
        assert m is not None
        assert m.ticker == "BAC"

    def test_case_insensitive(self):
        m = find_ticker("MICROSOFT reports strong quarter")
        assert m is not None
        assert m.ticker == "MSFT"

    def test_ticker_from_cashtag_overrides_company_name(self):
        # $AAPL should win over "microsoft" in same text
        m = find_ticker("Microsoft buys $AAPL stake")
        assert m is not None
        assert m.ticker == "AAPL"
        assert m.method == "cashtag"


class TestIsRelevant:
    """Tests for relevance filtering."""

    def test_high_confidence_ticker_is_relevant(self):
        m = TickerMatch("AAPL", "high", "exchange_tag")
        assert is_relevant("Any text", m) is True

    def test_medium_confidence_ticker_is_relevant(self):
        m = TickerMatch("TSLA", "medium", "company_name_with_finance")
        assert is_relevant("Tesla beats earnings", m) is True

    def test_no_ticker_but_finance_words_is_relevant(self):
        assert is_relevant("Fed raises interest rates", None) is True
        assert is_relevant("Earnings beat expectations", None) is True

    def test_no_ticker_no_finance_words_not_relevant(self):
        assert is_relevant("Random text about nothing", None) is False

    def test_low_confidence_ticker_not_relevant(self):
        # Low confidence matches are treated as no match
        m = TickerMatch("TSLA", "low", "company_name_alone")
        assert is_relevant("Tesla mentioned in passing", m) is False


class TestTextSimilarity:
    """Tests for near-duplicate detection."""

    def test_identical_texts(self):
        assert _text_similarity("Apple reports earnings", "Apple reports earnings") == 1.0

    def test_similar_texts(self):
        sim = _text_similarity("Apple reports strong earnings", "Apple reports strong earnings today")
        assert sim > 0.85

    def test_different_texts(self):
        sim = _text_similarity("Apple reports earnings", "Tesla delivers cars")
        assert sim < 0.5


class TestLoadAll:
    """Tests for the main load_all function (uses sample data)."""

    def test_load_all_returns_dataframe(self):
        df = load_all(n_each=5)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert list(df.columns) == ["source", "timestamp", "ticker", "ticker_confidence", "ticker_method", "text"]

    def test_no_duplicate_texts(self):
        df = load_all(n_each=10)
        assert df["text"].duplicated().sum() == 0

    def test_min_text_length(self):
        df = load_all(n_each=10)
        assert (df["text"].str.len() >= 15).all()

    def test_ticker_confidence_values(self):
        df = load_all(n_each=10)
        valid_conf = {"high", "medium", None}
        assert set(df["ticker_confidence"].dropna().unique()).issubset(valid_conf)


class TestFinanceWordsRegex:
    """Tests for the finance words regex."""

    def test_matches_common_finance_terms(self):
        assert FINANCE_WORDS.search("earnings beat")
        assert FINANCE_WORDS.search("dividend announcement")
        assert FINANCE_WORDS.search("merger acquisition")
        assert FINANCE_WORDS.search("analyst upgrade")
        assert FINANCE_WORDS.search("Fed rate hike")

    def test_no_match_on_non_finance(self):
        assert not FINANCE_WORDS.search("random text about cats")
        assert not FINANCE_WORDS.search("weather is nice today")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])