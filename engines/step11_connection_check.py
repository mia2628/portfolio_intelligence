from pathlib import Path
import csv
import sys

BASE=Path(__file__).resolve().parents[1]
p=BASE/"data"/"step03_market_inputs.csv"

if not p.exists():
    print("FAIL: file missing:",p)
    raise SystemExit(1)

with p.open("r",encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))

headers=list(rows[0].keys()) if rows else []

print("="*78)
print("STEP 11 -> STEP 3 CONNECTION CHECK")
print("="*78)
print("Columns :", " | ".join(headers))
print("Rows    :",len(rows))

if headers != ["Indicator","Observed_Change"]:
    print("FAIL: STEP3 input schema mismatch")
    raise SystemExit(2)

if len(rows)<20:
    print("FAIL: too few indicator rows")
    raise SystemExit(3)

nonzero=sum(
    1 for r in rows
    if float(r.get("Observed_Change") or 0)!=0
)

print("Non-zero:",nonzero)

if nonzero<10:
    print("FAIL: actual non-zero signals are too few")
    raise SystemExit(4)

print("PASS: STEP11 actual data is connected to STEP3 canonical input.")
