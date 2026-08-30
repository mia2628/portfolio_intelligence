from pathlib import Path
import csv, sys

BASE=Path(__file__).resolve().parents[1]
INV=BASE/"outputs"/"portfolio"/"portfolio_invested_summary.csv"
STEP8=BASE/"outputs"/"step08"/"monthly_allocation.csv"
STEP9=BASE/"outputs"/"step09"/"rebalancing_decision.csv"

def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def num(x):
    try:return float(x)
    except:return 0.0

print("="*92)
print("STEP12 STEP8/STEP9 FINAL CONSISTENCY CHECK")
print("="*92)

inv=read(INV)
expected_total=sum(num(r.get("Invested_Amount_KRW")) for r in inv)
gold=next(r for r in inv if r.get("Asset")=="Gold")
expected_gold=num(gold.get("Portfolio_Weight_Pct"))

a8=read(STEP8)
actual_assets={r.get("Asset") for r in a8}
required={"Bond","Domestic_Equity","Foreign_Equity","Cash","Other","Gold"}
missing=required-actual_assets
if missing:
    raise SystemExit(f"FAIL STEP8 missing assets: {sorted(missing)}")

step8_current_total=sum(num(r.get("Current_Invested_KRW")) for r in a8)
step8_scenario_total=sum(num(r.get("Scenario_Invested_KRW")) for r in a8)
contribution=sum(num(r.get("Allocation_KRW")) for r in a8)

if abs(step8_current_total-expected_total)>2:
    raise SystemExit(f"FAIL STEP8 current total: {step8_current_total} != {expected_total}")

if abs(step8_scenario_total-(expected_total+contribution))>2:
    raise SystemExit("FAIL STEP8 scenario total does not equal current + contribution")

d9=read(STEP9)
if not d9:
    raise SystemExit("FAIL STEP9 decision output empty")
r=d9[0]
g9=num(r.get("Gold_Weight_Pct"))
source=r.get("Gold_Weight_Source","")

if abs(g9-expected_gold)>0.02:
    raise SystemExit(f"FAIL STEP9 Gold: {g9} != invested-state {expected_gold}")
if source!="INVESTED_PRINCIPAL":
    raise SystemExit(f"FAIL STEP9 source: {source}")

print(f"Invested total       : {expected_total:,.0f} KRW")
print(f"STEP8 current total  : {step8_current_total:,.0f} KRW")
print(f"STEP8 scenario total : {step8_scenario_total:,.0f} KRW")
print(f"STEP9 Gold weight    : {g9:.2f}%")
print(f"STEP9 Gold source    : {source}")
print("PASS: STEP8 includes Cash/Other in denominator and STEP9 reads invested-state Gold directly.")
