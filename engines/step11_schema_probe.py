from pathlib import Path
import csv
BASE=Path(__file__).resolve().parents[1]
p=BASE/"data"/"step03_market_inputs.csv"
if not p.exists():
    print("파일 없음:",p)
    raise SystemExit(1)
with p.open("r",encoding="utf-8-sig",newline="") as f:
    r=csv.reader(f)
    header=next(r,[])
print("="*78)
print("STEP3 INPUT SCHEMA")
print("="*78)
print("Columns:", " | ".join(header))
print("Column count:",len(header))
