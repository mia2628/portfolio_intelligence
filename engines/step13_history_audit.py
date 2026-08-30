from pathlib import Path
import csv
from collections import Counter

BASE=Path(__file__).resolve().parents[1]
P=BASE/"data"/"dashboard_history.csv"

if not P.exists():
    raise SystemExit("FAIL: dashboard_history.csv missing")

with P.open("r",encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))

blank=[r for r in rows if not (r.get("date") or "").strip()]
valid=[r for r in rows if (r.get("date") or "").strip()]
dates=[r["date"].strip() for r in valid]
dupes={d:c for d,c in Counter(dates).items() if c>1}

print("="*86)
print("STEP13 HISTORY AUDIT")
print("="*86)
print("CSV rows       :",len(rows))
print("Valid rows     :",len(valid))
print("Blank rows     :",len(blank))
print("Unique dates   :",len(set(dates)))
print("Duplicate dates:",dupes if dupes else "NONE")

if blank:
    raise SystemExit("FAIL: blank date rows remain in dashboard_history.csv")
if dupes:
    raise SystemExit("FAIL: duplicate date rows remain in dashboard_history.csv")

print("PASS: history contains only valid, unique daily rows.")
