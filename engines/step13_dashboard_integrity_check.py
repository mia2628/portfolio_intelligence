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


# Trend integrity
TREND=BASE/"docs"/"data"/"trend.json"
if not TREND.exists():
    fail("trend.json missing")
t=json.loads(TREND.read_text(encoding="utf-8"))
pts=t.get("points") or []
summary=t.get("summary") or {}

dates=[str(p.get("date") or "").strip() for p in pts]
if any(not d for d in dates):
    fail("blank trend date detected")
if len(dates)!=len(set(dates)):
    fail("duplicate trend dates detected")
if "7" not in summary or "30" not in summary:
    fail("7/30 trend summaries missing")
if len(pts)<1:
    fail("trend points missing")
print(f"Trend points  : {len(pts)}")
print(f"Trend 7D      : {summary['7'].get('points')} points")
print(f"Trend 30D     : {summary['30'].get('points')} points")
print("PASS: trend.json contains 7/30-day summaries.")

