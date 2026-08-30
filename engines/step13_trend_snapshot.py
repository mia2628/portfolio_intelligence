from pathlib import Path
import csv,json
from datetime import datetime
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parents[1]
DASH=BASE/"docs"/"data"/"dashboard.json"
HISTORY=BASE/"data"/"dashboard_history.csv"
TREND=BASE/"docs"/"data"/"trend.json"
FIELDS=["Date_KST","Generated_At","Risk_Score","Health_Score","Best_Opportunity_Asset","Best_Opportunity_Score","Gold_Weight_Pct","Data_Confidence_Score"]
def read_csv(p):
    if not p.exists():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_csv(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
def n(v):
    try:return float(v)
    except:return None
def main():
    d=json.loads(DASH.read_text(encoding="utf-8"))
    now=datetime.now(ZoneInfo("Asia/Seoul"));date=now.strftime("%Y-%m-%d")
    opp=(d.get("opportunity") or [{}])[0];gold=d.get("health",{}).get("gold_policy") or {}
    row={"Date_KST":date,"Generated_At":d.get("meta",{}).get("generated_at",now.isoformat(timespec="seconds")),
         "Risk_Score":d.get("risk",{}).get("score",""),"Health_Score":d.get("health",{}).get("score",""),
         "Best_Opportunity_Asset":opp.get("asset",""),"Best_Opportunity_Score":opp.get("score",""),
         "Gold_Weight_Pct":gold.get("current",""),"Data_Confidence_Score":d.get("confidence",{}).get("score","")}
    rows=[r for r in read_csv(HISTORY) if r.get("Date_KST")!=date];rows.append(row)
    rows=sorted(rows,key=lambda r:r.get("Date_KST",""))[-365:];write_csv(HISTORY,rows)
    pts=[{"date":r["Date_KST"],"risk":n(r["Risk_Score"]),"health":n(r["Health_Score"]),
          "opportunity_asset":r["Best_Opportunity_Asset"],"opportunity_score":n(r["Best_Opportunity_Score"]),
          "gold_weight":n(r["Gold_Weight_Pct"]),"confidence":n(r["Data_Confidence_Score"])} for r in rows[-30:]]
    TREND.parent.mkdir(parents=True,exist_ok=True)
    TREND.write_text(json.dumps({"generated_at":now.isoformat(timespec="seconds"),"window_days":30,"points":pts},ensure_ascii=False,indent=2),encoding="utf-8")
    print("="*84);print("STEP13 TREND SNAPSHOT");print("="*84)
    print("Date        :",date);print("History rows:",len(rows));print("Trend points:",len(pts))
    print("Saved       : data/dashboard_history.csv");print("Saved       : docs/data/trend.json")
if __name__=="__main__":main()
