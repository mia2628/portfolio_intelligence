from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
root=BASE/"data"
print("="*86)
print("STEP13 LOCAL DATA SCHEMA DIAGNOSTIC")
print("="*86)
if not root.exists():
    raise SystemExit("data/ missing")
for p in sorted(root.rglob("*.csv")):
    try:
        if p.stat().st_size > 50_000_000:
            continue
        df=pd.read_csv(p,nrows=5)
        cols=[str(c) for c in df.columns]
        interesting=any(
            x in " ".join(cols).upper()
            for x in ["VIX","US10","HY","SPREAD","USD","KRW","INDICATOR","SERIES"]
        ) or "histor" in p.name.lower()
        if interesting:
            print(f"{p}:")
            print("  columns =",cols)
    except Exception as e:
        print(f"{p}: READ ERROR {e}")
print("PASS: schema diagnostic completed.")
