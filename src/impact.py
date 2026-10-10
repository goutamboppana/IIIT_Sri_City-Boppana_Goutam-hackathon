"""
Impact scoring module.

Event base severity weights (heuristic, not trained):
- Credit Event: 9 (highest - direct financial distress)
- Geopolitical: 8 (war, sanctions, trade wars)
- Macroeconomic: 7 (Fed, inflation, GDP - broad market impact)
- Merger/Acquisition: 7 (significant corporate action)
- Regulatory/Legal: 6 (lawsuits, investigations, regulatory risk)
- Earnings: 6 (fundamental performance signal)
- Management Change: 5 (leadership uncertainty)
- Dividend or Buyback: 4 (capital return signals)
- Product Launch: 4 (growth signal, but uncertain)
- Analyst Rating: 3 (opinion, not fact)
- Market Commentary: 2 (noise, opinions)
- Other: 1 (default/minimal)

Impact Score Formula (documented, deterministic, bounded [1, 10]):
  impact = round(base_severity × (0.5 + 0.5 × |sentiment|) × (0.5 + 0.5 × event_confidence))
  where:
    - base_severity: event-specific weight from EVENT_BASE
    - |sentiment|: absolute sentiment in [0, 1], amplifies impact for strong sentiment (either direction)
    - event_confidence: zero-shot classifier confidence in [0, 1], downweights uncertain classifications

This formula ensures:
- Strong sentiment (positive or negative) increases impact
- High-confidence classifications increase impact
- Neutral sentiment (0) with low confidence (0) gives minimum impact = round(base × 0.5 × 0.5)
- Result clipped to [1, 10] integer range
"""

EVENT_BASE = {
    "Credit Event": 9, "Geopolitical": 8, "Macroeconomic": 7,
    "Merger/Acquisition": 7, "Regulatory/Legal": 6, "Earnings": 6,
    "Management Change": 5, "Dividend or Buyback": 4, "Product Launch": 4,
    "Analyst Rating": 3, "Market Commentary": 2, "Other": 1,
}


def impact_score(event, sentiment, confidence):
    base = EVENT_BASE.get(event, 1)
    magnitude = 0.5 + 0.5 * abs(sentiment)   # strong sentiment, either direction, raises impact
    conf = 0.5 + 0.5 * confidence            # uncertain labels count for less
    return max(1, min(10, round(base * magnitude * conf)))