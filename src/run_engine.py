"""Run the full engine: ingest two sources, analyze, write structured signals.

Usage (from the project root):
    python -m src.run_engine --n 100
"""
import argparse
import sys

from src.ingest import load_all, DATA
from src.engine import analyze_batch
from src.schema import SignalSchema


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="items to pull from each source")
    ap.add_argument("--validate", action="store_true", help="validate output schema before writing")
    args = ap.parse_args()

    df = load_all(args.n)
    results = analyze_batch(df["text"].tolist())

    out = df.copy()
    out["sentiment"] = [r["sentiment"] for r in results]
    out["event"] = [r["event"] for r in results]
    out["event_confidence"] = [r["event_confidence"] for r in results]
    out["impact"] = [r["impact"] for r in results]

    # Validate schema
    errors = SignalSchema.validate_full(out)
    if errors:
        print("Schema validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        if args.validate:
            sys.exit(1)

    DATA.mkdir(exist_ok=True)
    out.to_csv(DATA / "signals.csv", index=False)
    out.to_json(DATA / "signals.json", orient="records", indent=2)

    print(f"\nWrote {len(out)} signals to {DATA / 'signals.csv'} and signals.json")
    print("\nEvent counts:\n", out["event"].value_counts().to_string())
    print("\nTop 5 by impact:")
    print(out.sort_values("impact", ascending=False)
             .head(5)[["source", "ticker", "sentiment", "event", "impact", "text"]]
             .to_string(index=False, max_colwidth=60))


if __name__ == "__main__":
    main()