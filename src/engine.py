"""Core NLP risk engine: text in -> structured risk signal out.

Models load lazily (on first use), so importing this file does not need torch.

Event Taxonomy (12 categories + "Other"):
- Earnings: Quarterly results, guidance, EPS, revenue
- Analyst Rating: Upgrades, downgrades, price target changes
- Management Change: CEO/CFO departures, board changes, executive appointments
- Dividend or Buyback: Dividend announcements, share repurchase programs
- Merger/Acquisition: M&A deals, acquisitions, takeovers, strategic investments
- Product Launch: New products, services, technology announcements
- Macroeconomic: Fed policy, inflation, GDP, unemployment, interest rates
- Geopolitical: Wars, sanctions, trade disputes, political instability
- Regulatory/Legal: Lawsuits, investigations, regulatory actions, compliance
- Credit Event: Defaults, bankruptcies, debt restructuring, rating changes
- Market Commentary: General market analysis, technical analysis, opinions
- Other: Catch-all for low-confidence classifications

Impact Score Formula (documented, deterministic):
  base_severity[event] × (0.5 + 0.5 × |sentiment|) × (0.5 + 0.5 × event_confidence)
  Clipped to [1, 10] integer.
"""
import re
import logging

from src.impact import impact_score, EVENT_BASE

EVENT_LABELS = [
    "Earnings", "Analyst Rating", "Management Change", "Dividend or Buyback",
    "Merger/Acquisition", "Product Launch", "Macroeconomic", "Geopolitical",
    "Regulatory/Legal", "Credit Event", "Market Commentary",
]
OTHER_THRESHOLD = 0.3   # below this confidence, the event becomes "Other"
HYPOTHESIS = "This financial news is about {}."

# Fail loudly if engine labels and impact weights ever drift apart
assert set(EVENT_LABELS) | {"Other"} == set(EVENT_BASE), "Label mismatch between engine and impact"

_sentiment_model = None
_event_model = None

_logger = logging.getLogger(__name__)


def clean(text):
    text = re.sub(r"https?://\S+", "", str(text))
    return text.replace("…", "").strip()


def _device():
    import torch
    return 0 if torch.cuda.is_available() else -1


def _get_sentiment_model():
    global _sentiment_model
    if _sentiment_model is None:
        from transformers import pipeline
        _sentiment_model = pipeline(
            "text-classification", model="ProsusAI/finbert", top_k=None, device=_device()
        )
    return _sentiment_model


def _get_event_model():
    global _event_model
    if _event_model is None:
        from transformers import pipeline
        _event_model = pipeline(
            "zero-shot-classification", model="facebook/bart-large-mnli", device=_device()
        )
    return _event_model


def sentiment_scores(texts, batch_size=16):
    """FinBERT: score = P(positive) - P(negative), in [-1, 1]."""
    outs = _get_sentiment_model()(list(texts), batch_size=batch_size, truncation=True)
    scores = []
    for o in outs:
        if isinstance(o, dict):          # guard for single-dict outputs
            o = [o]
        probs = {x["label"]: x["score"] for x in o}
        score = probs.get("positive", 0.0) - probs.get("negative", 0.0)
        # Clamp to [-1, 1] for safety
        score = max(-1.0, min(1.0, score))
        scores.append(round(score, 3))
    return scores


def classify_events(texts, batch_size=8):
    """Zero-shot NLI: returns (label, confidence) per text; weak guesses become 'Other'.

    Note: confidence is the raw model score (not calibrated probability).
    """
    res = _get_event_model()(
        list(texts),
        candidate_labels=EVENT_LABELS,
        hypothesis_template=HYPOTHESIS,
        batch_size=batch_size,
    )
    if isinstance(res, dict):
        res = [res]
    results = []
    for r in res:
        label, score = r["labels"][0], r["scores"][0]
        if score < OTHER_THRESHOLD:
            label = "Other"
        results.append((label, round(score, 3)))
    return results


def analyze_batch(texts):
    """Analyze many texts at once (much faster than a loop of analyze())."""
    texts = list(texts)
    cleaned = [clean(t) for t in texts]
    sentiments = sentiment_scores(cleaned)
    events = classify_events(cleaned)
    out = []
    for text, s, (event, conf) in zip(texts, sentiments, events):
        out.append({
            "text": text,
            "sentiment": s,
            "event": event,
            "event_confidence": conf,
            "impact": impact_score(event, s, conf),
        })
    return out


def analyze(text):
    return analyze_batch([text])[0]
