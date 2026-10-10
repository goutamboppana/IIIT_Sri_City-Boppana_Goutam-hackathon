"""Run the full engine: ingest two sources, analyze, write structured signals.

Usage (from the project root):
    python -m src.run_engine --n 100
    python -m src.run_engine --validate
"""
import argparse
import sys

from src.ingest import load_all, DATA
from src.engine import analyze_batch
from src.schema import SignalSchema, validate_signals_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="items to pull from each source")
    ap.add_argument("--validate", action="store_true", help="validate existing signals.csv and exit")
    args = ap.parse_args()

    path = DATA / "signals.csv"

    if args.validate:
        # Validation-only mode: check existing file and exit
        if not path.exists():
            print(f"Validation failed: {path} does not exist.", file=sys.stderr)
            sys.exit(1)

        valid, errors = validate_signals_file(str(path))

        if valid:
            print(f"[OK] Schema validation passed for {path}")
        else:
            print("[FAIL] Schema validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # Normal generation mode
    df = load_all(args.n)

    results = analyze_batch(df["text"].tolist())

    out = df.copy()
    out["sentiment"] = [r["sentiment"] for r in results]
    out["event"] = [r["event"] for r in results]
    out["event_confidence"] = [r["event_confidence"] for r in results]
    out["impact"] = [r["impact"] for r in results]

    # Validate schema before writing
    errors = SignalSchema.validate_full(out)
    if errors:
        print("Schema validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    DATA.mkdir(exist_ok=True)
    out.to_csv(path, index=False)
    out.to_json(DATA / "signals.json", orient="records", indent=2)

    print(f"\nWrote {len(out)} signals to {path} and signals.json")
    print("\nEvent counts:\n", out["event"].value_counts().to_string())
    print("\nTop 5 by impact:")
    print(out.sort_values("impact", ascending=False)
             .head(5)[["source", "ticker", "sentiment", "event", "impact", "text"]]
             .to_string(index=False, max_colwidth=60))


if __name__ == "__main__":
    main()