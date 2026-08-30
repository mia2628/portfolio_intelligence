from pathlib import Path
import json, sys

BASE=Path(__file__).resolve().parents[1]
P=BASE/"docs"/"data"/"dashboard.json"

PLACEHOLDERS=[
    "STEP13 데이터가 아직 생성되지 않았습니다.",
    "STEP13 데이터가 아직 생성되지 않았습니다",
]

def fail(msg):
    print(f"FAIL: {msg}")
    raise SystemExit(1)

if not P.exists():
    fail("dashboard.json missing")

d=json.loads(P.read_text(encoding="utf-8"))

risk=d.get("risk",{}).get("score")
health=d.get("health",{}).get("score")
portfolio=d.get("portfolio",{}).get("items") or []
opps=d.get("opportunity") or []
final=str(d.get("recommendation",{}).get("final") or "").strip()

if risk is None: fail("Risk score missing")
if health is None: fail("Health score missing")
if len(portfolio)<4: fail(f"Portfolio assets insufficient: {len(portfolio)}")
if not opps or opps[0].get("score") is None: fail("Opportunity missing")
if not final: fail("TODAY'S ACTION recommendation missing")
if any(x in final for x in PLACEHOLDERS): fail("Placeholder recommendation detected")

meta=d.get("meta",{})
if meta.get("basis")!="INVESTED_PRINCIPAL": fail("Unexpected portfolio basis")

print("="*86)
print("STEP13 DASHBOARD INTEGRITY CHECK")
print("="*86)
print(f"Risk        : {risk}")
print(f"Health      : {health}")
print(f"Portfolio   : {len(portfolio)} assets")
print(f"Opportunity : {opps[0].get('asset')} {opps[0].get('score')}")
print(f"Action      : {final[:120]}")
print(f"Rec source  : {d.get('recommendation',{}).get('source','UNKNOWN')}")
print("PASS: dashboard.json contains live, non-placeholder STEP13 data.")
