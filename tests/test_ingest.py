"""Lightweight unit tests for ingestion and ticker matching.
No model downloads, no API calls."""
import pytest
import pandas as pd
from src.ingest import (
    find_ticker, find_tickers, is_relevant, load_all, TickerMatch, TickerMatches,
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


class TestFindTickers:
    """Tests for multi-ticker find_tickers function."""

    def test_single_ticker_returns_matches(self):
        matches = find_tickers("$AAPL beats earnings")
        assert len(matches.matches) == 1
        assert matches.matches[0].ticker == "AAPL"
        assert matches.matches[0].confidence == "high"
        assert matches.matches[0].method == "cashtag"

    def test_multiple_cashtags(self):
        matches = find_tickers("$AAPL and $MSFT both rose")
        assert len(matches.matches) == 2
        tickers = {m.ticker for m in matches.matches}
        assert tickers == {"AAPL", "MSFT"}

    def test_multiple_companies_with_finance_context(self):
        matches = find_tickers("Apple and Microsoft both beat earnings expectations")
        assert len(matches.matches) == 2
        tickers = {m.ticker for m in matches.matches}
        assert tickers == {"AAPL", "MSFT"}

    def test_exchange_tag_and_cashtag_combined(self):
        matches = find_tickers("Apple (NASDAQ: AAPL) and $MSFT rose")
        assert len(matches.matches) == 2
        methods = {m.method for m in matches.matches}
        assert "exchange_tag" in methods
        assert "cashtag" in methods

    def test_primary_returns_highest_confidence(self):
        matches = find_tickers("Microsoft mentions $AAPL stake")
        primary = matches.get_primary()
        assert primary is not None
        assert primary.ticker == "AAPL"  # cashtag beats company name
        assert primary.confidence == "high"

    def test_no_duplicate_tickers(self):
        # Same company via cashtag and name should deduplicate
        matches = find_tickers("Apple ($AAPL) beats earnings")
        assert len(matches.matches) == 1
        assert matches.matches[0].ticker == "AAPL"
        assert matches.matches[0].confidence == "high"  # cashtag wins

    def test_unknown_cashtag_not_matched(self):
        matches = find_tickers("$XYZABC is a fake ticker")
        # Unknown ticker not in COMPANIES should not match
        assert len(matches.matches) == 0

    def test_invalid_ticker_syntax_rejected(self):
        matches = find_tickers("$TOOLONGTICKER not valid")
        assert len(matches.matches) == 0

    def test_netflix_primary_over_incidental_jnj(self):
        """Netflix is the subject; J&J mentioned incidentally → NFLX should be primary."""
        text = "Netflix shares climb on subscriber data; Johnson & Johnson also mentioned"
        matches = find_tickers(text)
        primary = matches.get_primary()
        assert primary is not None, "Should have a primary match"
        assert primary.ticker == "NFLX", f"Expected NFLX primary, got {primary.ticker}"
        # JNJ should still be matched but not primary
        tickers = {m.ticker for m in matches.matches}
        assert "JNJ" in tickers, "JNJ should still be detected"
        # NFLX should have higher or equal confidence
        nflx_match = next(m for m in matches.matches if m.ticker == "NFLX")
        jnj_match = next(m for m in matches.matches if m.ticker == "JNJ")
        # Both should be medium (same confidence), but NFLX should win tiebreak
        assert nflx_match.confidence == jnj_match.confidence == "medium"

    def test_finance_context_scoped_to_sentence(self):
        """Finance word in separate sentence should not upgrade unrelated company."""
        text = "Apple announced new iPhone. Fed raises rates today."
        matches = find_tickers(text)
        apple_match = next((m for m in matches if m.ticker == "AAPL"), None)
        # Apple appears in first sentence without finance words
        # Fed raises rates is in second sentence
        # Apple should NOT get medium confidence from distant finance word
        assert apple_match is None or apple_match.confidence == "low", \
            f"Apple should not get medium confidence from distant finance word, got {apple_match.confidence if apple_match else None}"

    def test_anker_amazon_deal_rejected(self):
        """Product deal article without finance words → irrelevant."""
        text = "Anker EufyCam 40% off on Amazon Prime Day"
        matches = find_tickers(text)
        assert not is_relevant(text, matches), "Product deal without finance words should be irrelevant"

    def test_amazon_revenue_attributed_to_amazon(self):
        """Amazon revenue article with Anker mention → AMZN primary."""
        text = "Amazon revenue boosted by Anker camera sales on Prime Day"
        matches = find_tickers(text)
        primary = matches.get_primary()
        assert primary is not None
        assert primary.ticker == "AMZN", f"Expected AMZN primary, got {primary.ticker}"

    def test_multi_company_no_arbitrary_primary_by_name_length(self):
        """Multi-company financial news should not pick primary by longest name."""
        text = "Nvidia and AMD both beat earnings expectations"
        matches = find_tickers(text)
        primary = matches.get_primary()
        # Both have same confidence (medium), same method
        # Should not deterministically pick one based on name length
        # Acceptable: primary is None (ambiguous) or tiebreak by first mention
        tickers = {m.ticker for m in matches.matches}
        assert tickers == {"NVDA", "AMD"}
        # If a primary is chosen, it should be the first-mentioned company
        if primary is not None:
            # Nvidia appears first in text
            assert primary.ticker == "NVDA", \
                f"Expected first-mentioned NVDA as primary, got {primary.ticker}"


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
        expected_cols = ["source", "timestamp", "ticker", "ticker_confidence", "ticker_method",
                         "all_tickers", "all_ticker_confidences", "all_ticker_methods", "text"]
        assert list(df.columns) == expected_cols

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

    def test_all_tickers_column_present(self):
        df = load_all(n_each=10)
        assert "all_tickers" in df.columns
        assert "all_ticker_confidences" in df.columns
        assert "all_ticker_methods" in df.columns


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