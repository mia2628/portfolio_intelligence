from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
p = BASE / "data" / "step03_market_inputs.csv"

if not p.exists():
    print("FAIL: step03_market_inputs.csv 없음")
    raise SystemExit(1)

with p.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

headers = list(rows[0].keys()) if rows else []

print("="*78)
print("STEP11 AUTOMATIC CONNECTION CHECK")
print("="*78)
print("Columns :", " | ".join(headers))
print("Rows    :", len(rows))

if headers != ["Indicator","Observed_Change"]:
    print("FAIL: schema mismatch")
    raise SystemExit(2)

nonzero = sum(
    1 for r in rows
    if abs(float(r.get("Observed_Change") or 0.0)) > 1e-12
)

print("Non-zero actual signals:", nonzero)

if nonzero < 8:
    print("FAIL: 실제 신호가 너무 적습니다.")
    raise SystemExit(3)

print("PASS: STEP4 -> STEP11 -> STEP3 자동 연결 정상")
