from pathlib import Path
import csv, json, math
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"outputs"
DOCS=BASE/"docs"/"data"
CFG=BASE/"config"/"step13_dashboard_config.json"

def read_csv(path):
    if not path.exists(): return []
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def read_json(path, default=None):
    if not path.exists(): return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default

def num(v, default=None):
    try:
        if v is None or str(v).strip()=="": return default
        return float(str(v).replace(",","").replace("%","").strip())
    except Exception:
        return default

def pick(row, names, default=None):
    for n in names:
        if n in row:
            v=row.get(n)
            if v is not None and str(v).strip()!="":
                return v
    return default

def first(path):
    rows=read_csv(path)
    return rows[0] if rows else {}

def label(score, kind="generic"):
    if score is None: return "UNKNOWN"
    if kind=="risk":
        return "LOW" if score<40 else "NEUTRAL" if score<60 else "HIGH" if score<75 else "VERY_HIGH"
    if kind=="health":
        return "WEAK" if score<50 else "FAIR" if score<65 else "GOOD" if score<80 else "STRONG"
    if kind=="opportunity":
        return "LOW" if score<45 else "NEUTRAL" if score<55 else "ATTRACTIVE" if score<70 else "STRONG"
    return "NEUTRAL"

def portfolio_data(expose_amounts):
    rows=read_csv(OUT/"portfolio"/"portfolio_invested_summary.csv")
    items=[]
    total=0
    for r in rows:
        amt=num(r.get("Invested_Amount_KRW"),0) or 0
        wt=num(pick(r,["Portfolio_Weight_Pct","Portfolio_Weight"]),0) or 0
        total=max(total, num(r.get("Total_Invested_Amount_KRW"),0) or 0)
        items.append({
            "asset":r.get("Asset",""),
            "name":r.get("Asset_KR") or r.get("Asset",""),
            "weight":round(wt,2),
            "amount":round(amt) if expose_amounts else None,
        })
    items.sort(key=lambda x:x["weight"],reverse=True)
    if total<=0:
        total=sum((x["amount"] or 0) for x in items) if expose_amounts else 0
    return items, (round(total) if expose_amounts else None)

def risk_data():
    s=first(OUT/"step05"/"risk_summary.csv")
    scores=read_csv(OUT/"step05"/"risk_scores.csv")
    details=read_csv(OUT/"step05"/"risk_details.csv")
    portfolio=None
    for r in scores:
        if str(r.get("Asset","")).upper()=="PORTFOLIO":
            portfolio=num(pick(r,["Risk_Score","Score","Adjusted_Risk_Score"]))
            break
    if portfolio is None:
        portfolio=num(pick(s,["Portfolio_Risk_Score","Portfolio_Risk","Risk_Score","Score"]))

    cons=[]
    for r in details:
        ind=pick(r,["Indicator","Name"],"")
        adj=num(pick(r,["Adjusted","Adjusted_Score","Adjusted_Risk","Risk_Adjusted"]))
        contribution=num(pick(r,["Contribution","Weighted_Contribution","Risk_Contribution"]),0)
        expl=pick(r,["Explanation","Reason","Interpretation","Narrative"],"")
        if ind:
            cons.append({
                "indicator":ind,
                "adjusted":None if adj is None else round(adj,2),
                "contribution":round(abs(contribution or 0),4),
                "explanation":expl,
            })
    cons.sort(key=lambda x:x["contribution"],reverse=True)
    return {"score":portfolio,"label":label(portfolio,"risk"),"contributors":cons[:3]}

def opportunity_data():
    rows=read_csv(OUT/"step06"/"opportunity_scores.csv")
    details=read_csv(OUT/"step06"/"opportunity_details.csv")
    dmap={r.get("Asset"):r for r in details}
    items=[]
    for r in rows:
        a=r.get("Asset","")
        score=num(pick(r,["Opportunity_Score","Score","Opportunity"]))
        dr=dmap.get(a,{})
        items.append({
            "asset":a,
            "score":None if score is None else round(score,2),
            "label":label(score,"opportunity"),
            "components":{
                "target":num(pick(dr,["Target_Gap_Score","Target_Score","Target"])),
                "macro":num(pick(dr,["Macro_Score","Macro"])),
                "risk_adj":num(pick(dr,["Risk_Adjusted_Score","RiskAdj","Risk_Adjusted"])),
                "history":num(pick(dr,["Historical_Score","History_Score","History"])),
                "drawdown":num(pick(dr,["Drawdown_Score","Drawdown"])),
            },
            "explanation":pick(dr,["Explanation","Reason","Comment","Narrative"],"")
        })
    items.sort(key=lambda x:(x["score"] is not None,x["score"] or -999),reverse=True)
    return items

def health_data():
    s=first(OUT/"step07"/"portfolio_health_summary.csv")
    comps=read_csv(OUT/"step07"/"portfolio_health_components.csv")
    score=num(pick(s,["Portfolio_Health_Score","Portfolio_Health","Health_Score","Score"]))
    component_items=[]
    for r in comps:
        component_items.append({
            "name":r.get("Component",""),
            "score":num(pick(r,["Score","Component_Score","Value"])),
            "effective_weight":num(pick(r,["Effective_Weight","Weight"])),
            "status":r.get("Status","SCORED"),
        })
    gold=None
    for r in read_csv(OUT/"step07"/"target_policy_status.csv"):
        if r.get("Asset")=="Gold":
            gold={
                "current":num(pick(r,["Current_Weight","Current_Weight_Pct"])),
                "target":num(pick(r,["Target_Pct","Target"])),
                "lower":num(pick(r,["Lower_Bound_Pct","Lower"])),
                "upper":num(pick(r,["Upper_Bound_Pct","Upper"])),
                "status":r.get("Status",""),
            }
            break
    return {
        "score":score,
        "label":label(score,"health"),
        "components":component_items,
        "gold_policy":gold,
        "comment":pick(s,["Korean_Comment","Comment","Explanation"],"")
    }

def allocation_data():
    rows=read_csv(OUT/"step08"/"monthly_allocation.csv")
    items=[]
    for r in rows:
        alloc=num(r.get("Allocation_KRW"),0) or 0
        share=num(r.get("Allocation_Share_Pct"),0) or 0
        if alloc==0 and share==0 and r.get("Allocation_Eligible")=="NO":
            continue
        items.append({
            "asset":r.get("Asset",""),
            "share":round(share,2),
            "amount":round(alloc),
            "scenario_weight":num(r.get("Scenario_Weight_Pct")),
            "current_weight":num(r.get("Current_Weight_Pct")),
        })
    items.sort(key=lambda x:x["share"],reverse=True)
    scenario_total=sum(x["amount"] for x in items)
    return {"available":bool(rows),"input_amount":scenario_total if rows else None,"items":items}

def rebalance_data():
    r=first(OUT/"step09"/"rebalancing_decision.csv")
    if not r:return {"available":False}
    return {
        "available":True,
        "decision":pick(r,["Decision","Rebalancing_Decision"],""),
        "action_level":pick(r,["Action_Level","Level"],""),
        "reason":pick(r,["Reason","Decision_Reason"],""),
        "calendar_due":str(pick(r,["Calendar_Due","CalendarDue"],"")).lower()=="true",
        "threshold_trigger":str(pick(r,["Threshold_Trigger","ThresholdTrigger"],"")).lower()=="true",
        "gold_weight":num(pick(r,["Gold_Weight_Pct","Gold_Weight"])),
        "gold_source":pick(r,["Gold_Weight_Source"],""),
    }

def recommendation_data():
    s=first(OUT/"step10"/"recommendation_summary.csv")
    d=read_csv(OUT/"step10"/"recommendation_detail.csv")
    sections=[]
    for r in d:
        title=pick(r,["Section","Category","Title"],"")
        text=pick(r,["Text","Recommendation","Message","Detail"],"")
        if title or text: sections.append({"title":title,"text":text})
    # flexible summary aliases
    final=pick(s,["Final_Recommendation","Recommendation","Final","Korean_Recommendation"],"")
    situation=pick(s,["Current_Situation","Situation","Current_Status"],"")
    return {"final":final,"situation":situation,"sections":sections}

def confidence_data():
    p=OUT/"step11"/"coverage_summary.csv"
    rows=read_csv(p)
    if rows:
        r=rows[0]
        return {
            "score":num(pick(r,["Data_Confidence_Score","Confidence_Score","DataConfidence"])),
            "label":pick(r,["Data_Confidence_Label","Confidence_Label"],""),
            "actual":num(pick(r,["Actual_Indicators","Actual"])),
            "total":num(pick(r,["Total_Indicators","Total"])),
        }
    # fallback from step03 diagnostics if present
    return {"score":None,"label":"UNKNOWN","actual":None,"total":None}

def build():
    config=read_json(CFG,{})
    expose=bool(config.get("privacy",{}).get("expose_amounts",False))
    portfolio,total=portfolio_data(expose)

    data={
        "meta":{
            "generated_at":datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
            "basis":"INVESTED_PRINCIPAL",
            "privacy_amounts":expose,
            "version":"STEP13_v1",
        },
        "portfolio":{"items":portfolio,"total_invested":total},
        "risk":risk_data(),
        "opportunity":opportunity_data(),
        "health":health_data(),
        "allocation":allocation_data(),
        "rebalance":rebalance_data(),
        "recommendation":recommendation_data(),
        "confidence":confidence_data(),
    }
    DOCS.mkdir(parents=True,exist_ok=True)
    (DOCS/"dashboard.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    (OUT/"step13").mkdir(parents=True,exist_ok=True)
    (OUT/"step13"/"dashboard.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print("="*84)
    print("STEP13 DASHBOARD EXPORT")
    print("="*84)
    print("Generated :",data["meta"]["generated_at"])
    print("Basis     : INVESTED_PRINCIPAL")
    print("Amounts   :","VISIBLE" if expose else "HIDDEN")
    print("Portfolio :",len(portfolio),"assets")
    print("Risk      :",data["risk"]["score"],data["risk"]["label"])
    print("Health    :",data["health"]["score"],data["health"]["label"])
    print("Scenario  :","AVAILABLE" if data["allocation"]["available"] else "NONE")
    print("Saved     : docs/data/dashboard.json")
    return data

if __name__=="__main__":
    build()
