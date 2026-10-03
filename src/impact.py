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