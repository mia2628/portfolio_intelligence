from pathlib import Path
import csv, sys

BASE=Path(__file__).resolve().parents[1]
P=BASE/"data"/"step11_5_coverage_summary.csv"

if not P.exists():
    print("FAIL: coverage summary 없음. step11_5_coverage_audit.py 먼저 실행")
    raise SystemExit(2)

with P.open("r",encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
r=rows[0]

print("="*78)
print("STEP 11.5 STRICT-27 GATE")
print("="*78)
print("Current ACTUAL    :",r["Current_ACTUAL"],"/",r["Total_Indicators"])
print("Strict LIVE_READY :",r["Strict_Live_Ready"],"/",r["Total_Indicators"])
print("STEP12 READY      :",r["STEP12_READY"])

if r["STEP12_READY"]!="YES":
    print()
    print("[BLOCK] exact/defined/licensed 27개 조건이 아직 충족되지 않았습니다.")
    print("STEP12 자동화는 아직 진행하지 않는 것이 안전합니다.")
    raise SystemExit(3)

print("PASS: 27개 전 지표 품질/출처 조건 충족")
