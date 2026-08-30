from pathlib import Path
import json, hashlib

BASE=Path(__file__).resolve().parents[1]
DASH=BASE/"docs"/"data"/"dashboard.json"
CFG=BASE/"config"/"step13_dashboard_config.json"
OUT=BASE/"outputs"/"step13"
OUT.mkdir(parents=True,exist_ok=True)

def load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def main():
    d=load(DASH); c=load(CFG)
    ac=c.get("alerts",{})
    alerts=[]

    risk=d.get("risk",{}).get("score")
    health=d.get("health",{}).get("score")
    conf=d.get("confidence",{}).get("score")
    gp=d.get("health",{}).get("gold_policy") or {}
    rb=d.get("rebalance",{})

    if risk is not None and risk >= float(ac.get("risk_high",65)):
        alerts.append({"key":"RISK_HIGH","severity":"HIGH","title":"시장 위험도 상승",
                       "message":f"현재 Risk Score {risk:.1f}점입니다."})
    if health is not None and health < float(ac.get("health_low",50)):
        alerts.append({"key":"HEALTH_LOW","severity":"HIGH","title":"포트폴리오 건강도 저하",
                       "message":f"현재 Health Score {health:.1f}점입니다."})
    if conf is not None and conf < float(ac.get("data_confidence_low",60)):
        alerts.append({"key":"DATA_CONFIDENCE_LOW","severity":"MEDIUM","title":"데이터 신뢰도 저하",
                       "message":f"현재 Data Coverage Confidence {conf:.1f}점입니다."})
    if ac.get("gold_policy_breach",True) and gp.get("status") in ("BELOW_RANGE","ABOVE_RANGE"):
        cur=gp.get("current"); lo=gp.get("lower"); hi=gp.get("upper")
        alerts.append({"key":"GOLD_POLICY_BREACH","severity":"MEDIUM","title":"금 정책범위 이탈",
                       "message":f"현재 금 비중 {cur:.2f}% / 정책범위 {lo:.0f}~{hi:.0f}% ({gp.get('status')})"})
    if rb.get("available") and rb.get("action_level")=="HIGH":
        alerts.append({"key":"REBALANCE_HIGH","severity":"HIGH","title":"리밸런싱 우선조치",
                       "message":rb.get("reason") or rb.get("decision","")})

    signature="|".join(sorted(a["key"] for a in alerts)) or "NONE"
    sig=hashlib.sha256(signature.encode()).hexdigest()[:12]
    result={"active":alerts,"count":len(alerts),"signature":sig}
    (OUT/"alerts.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return result

if __name__=="__main__":
    main()
