from pathlib import Path
import csv, json, math
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
DASH=BASE/"docs"/"data"/"dashboard.json"
HISTORY=BASE/"data"/"dashboard_history.csv"
TREND=BASE/"docs"/"data"/"trend.json"

FIELDS=[
    "date","generated_at",
    "risk","health",
    "opportunity_asset","opportunity_score"
]

def fnum(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None

def load_rows():
    if not HISTORY.exists():
        return []
    with HISTORY.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def write_rows(rows):
    HISTORY.parent.mkdir(parents=True,exist_ok=True)
    with HISTORY.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k,"") for k in FIELDS})

def direction(delta, eps=0.05):
    if delta is None: return "NO_DATA"
    if delta > eps: return "UP"
    if delta < -eps: return "DOWN"
    return "FLAT"

def metric_summary(points,key):
    vals=[(p["date"],p.get(key)) for p in points if p.get(key) is not None]
    if not vals:
        return {"current":None,"delta":None,"direction":"NO_DATA","min":None,"max":None,"avg":None}
    first=vals[0][1]
    last=vals[-1][1]
    delta=round(last-first,2) if len(vals)>=2 else 0.0
    nums=[v for _,v in vals]
    return {
        "current":round(last,2),
        "delta":delta,
        "direction":direction(delta),
        "min":round(min(nums),2),
        "max":round(max(nums),2),
        "avg":round(sum(nums)/len(nums),2),
    }

def period_summary(points,days):
    pts=points[-days:]
    opp_assets={}
    for p in pts:
        a=p.get("opportunity_asset")
        if a:
            opp_assets[a]=opp_assets.get(a,0)+1
    dominant=max(opp_assets,key=opp_assets.get) if opp_assets else None
    return {
        "days_requested":days,
        "points":len(pts),
        "from":pts[0]["date"] if pts else None,
        "to":pts[-1]["date"] if pts else None,
        "risk":metric_summary(pts,"risk"),
        "health":metric_summary(pts,"health"),
        "opportunity":metric_summary(pts,"opportunity_score"),
        "dominant_opportunity_asset":dominant,
    }

if not DASH.exists():
    raise SystemExit("dashboard.json missing")

d=json.loads(DASH.read_text(encoding="utf-8"))
today=datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
generated=d.get("meta",{}).get("generated_at") or datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
opps=d.get("opportunity") or []
top=opps[0] if opps else {}

row={
    "date":today,
    "generated_at":generated,
    "risk":d.get("risk",{}).get("score"),
    "health":d.get("health",{}).get("score"),
    "opportunity_asset":top.get("asset",""),
    "opportunity_score":top.get("score"),
}

rows=load_rows()
# Same-day rerun replaces the canonical row for that KST date.
rows=[r for r in rows if r.get("date")!=today]
rows.append(row)
rows=sorted(rows,key=lambda r:r.get("date",""))[-365:]
write_rows(rows)

points=[]
for r in rows:
    points.append({
        "date":r.get("date"),
        "generated_at":r.get("generated_at"),
        "risk":fnum(r.get("risk")),
        "health":fnum(r.get("health")),
        "opportunity_asset":r.get("opportunity_asset") or None,
        "opportunity_score":fnum(r.get("opportunity_score")),
    })

payload={
    "meta":{
        "generated_at":datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "history_rows":len(points),
        "retention_days":365,
        "same_day_policy":"REPLACE",
        "version":"STEP13_TREND_v9",
    },
    "points":points,
    "summary":{
        "7":period_summary(points,7),
        "30":period_summary(points,30),
    }
}

TREND.parent.mkdir(parents=True,exist_ok=True)
TREND.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("="*86)
print("STEP13 TREND SNAPSHOT v9")
print("="*86)
print("Trend date      :",today)
print("History rows    :",len(points))
for days in (7,30):
    s=payload["summary"][str(days)]
    print(f"{days}-day points   :",s["points"])
    print(f"{days}-day Risk     :",s["risk"])
    print(f"{days}-day Health   :",s["health"])
    print(f"{days}-day Opp      :",s["opportunity"])
print("PASS: daily snapshot + 7/30-day trend summaries generated.")
