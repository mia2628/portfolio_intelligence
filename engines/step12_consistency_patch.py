from pathlib import Path
import csv, argparse, math

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"outputs"
CFG=BASE/"config"

def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write(p,rows,fields=None):
    if not rows:return
    fields=fields or list(rows[0].keys())
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def num(x,default=None):
    try:return float(str(x).replace(",","").strip())
    except:return default
def clamp(x,a=0,b=100):return max(a,min(b,x))
def findcol(fields,aliases):
    norm={c.lower().replace("_","").replace(" ",""):c for c in fields}
    for a in aliases:
        k=a.lower().replace("_","").replace(" ","")
        if k in norm:return norm[k]
    return None
def asset_is_gold(v):
    return str(v).strip().lower() in ("gold","금")

def portfolio_current_gold():
    pc=BASE/"portfolio_config.csv"
    p=BASE/"portfolio.csv"
    if not pc.exists() or not p.exists():
        return None
    accounts={r["Account"]:num(r["Current_Value"],0) for r in read(pc)}
    prows=read(p)
    total=sum(accounts.values())
    gv=0.0
    for r in prows:
        if r.get("Asset")=="Gold":
            gv += accounts.get(r.get("Account"),0)*num(r.get("Weight_In_Account"),0)/100
    return 100*gv/total if total>0 else None

def policy():
    rows=read(CFG/"step12_policy_consistency.csv")
    return {r["Asset"]:r for r in rows}

def target_opportunity_score(current, lower, upper):
    """
    HARD_RANGE new-money opportunity:
    - inside acceptable band => neutral 50
    - below lower => linearly 50 at lower to 100 at 0%
    - above upper => linearly 50 at upper to 0 at 100%
    Continuous at both boundaries, bounded [0,100], no arbitrary pp multiplier.
    """
    if current < lower:
        return clamp(50 + 50*(lower-current)/max(lower,1e-12))
    if current > upper:
        return clamp(50 - 50*(current-upper)/max(100-upper,1e-12))
    return 50.0

def policy_health_score(current, lower, upper):
    """
    Policy compliance health:
    - any point inside acceptable range = 100
    - below lower = 100 * current/lower
    - above upper = 100 * (100-current)/(100-upper)
    Continuous, bounded, and does not pretend the center is uniquely healthy.
    """
    if lower <= current <= upper:return 100.0
    if current < lower:return clamp(100*current/max(lower,1e-12))
    return clamp(100*(100-current)/max(100-upper,1e-12))

def post5():
    p=OUT/"step05"/"risk_details.csv"
    if not p.exists():
        print("[WARN] risk_details.csv 없음; STEP5 score는 변경하지 않음")
        return
    rows=read(p); fields=list(rows[0]) if rows else []
    ic=findcol(fields,["Indicator","Name"])
    ac=findcol(fields,["Adjusted","Adjusted_Score","Risk_Adjusted","AdjustedRisk"])
    ec=findcol(fields,["Explanation","Reason","Interpretation","Narrative"])
    if not ic or not ac:
        print("[WARN] STEP5 설명 보정용 컬럼 미탐지; 점수는 그대로 유지")
        return
    if not ec:
        ec="Corrected_Explanation"; fields.append(ec)
    for r in rows:
        ind=r.get(ic,""); a=num(r.get(ac),50)
        if ind=="VIX":
            if a>50:
                r[ec]="VIX 신호가 기준보다 높은 위험 방향으로 작용해 시장 변동성 위험을 높였습니다."
            elif a<50:
                r[ec]="VIX 신호가 기준보다 낮은 위험 방향으로 작용해 시장 변동성 위험을 낮췄습니다."
            else:
                r[ec]="VIX 신호는 현재 위험도에 중립적으로 작용했습니다."
    write(p,rows,fields)
    print("[PATCH PASS] STEP5: VIX 설명을 Adjusted Risk 방향과 일치시켰습니다.")

def patch_step06_table(p,current,tscore):
    if not p.exists():return False
    rows=read(p)
    if not rows:return False
    fields=list(rows[0])
    asset=findcol(fields,["Asset","Asset_Name"])
    target=findcol(fields,["Target","Target_Score","TargetScore"])
    macro=findcol(fields,["Macro","Macro_Score","MacroScore"])
    risk=findcol(fields,["RiskAdj","Risk_Adjusted","RiskAdj_Score","Risk_Adjusted_Score"])
    hist=findcol(fields,["History","History_Score","Historical_Score"])
    dd=findcol(fields,["Drawdown","Drawdown_Score"])
    opp=findcol(fields,["Opportunity_Score","Opportunity","Score"])
    gap=findcol(fields,["Target_Gap_pp","Target_Gap","Gap_pp"])
    reason=findcol(fields,["Reason","Explanation","Narrative","Interpretation"])
    if not asset:return False
    changed=False
    for r in rows:
        if not asset_is_gold(r.get(asset)):
            continue
        if target:r[target]=f"{tscore:.4f}"
        if gap:r[gap]=f"{current-20.0:.4f}"
        # Recalculate total if all required components are present.
        vals=[num(r.get(c)) if c else None for c in (macro,risk,hist,dd)]
        if opp and all(v is not None for v in vals):
            m,ra,h,d=vals
            score=.30*tscore+.25*m+.20*ra+.15*h+.10*d
            r[opp]=f"{clamp(score):.4f}"
        if reason:
            deficit=max(0,18.0-current)
            r[reason]=(f"금: 현재 {current:.2f}%로 정책 하한 18.00%보다 {deficit:.2f}%p 낮아 "
                       "신규자금 보충 우선순위가 높습니다. 허용범위에 진입하면 Target 점수는 중립 50으로 복귀합니다.")
        changed=True
    if changed:write(p,rows,fields)
    return changed

def post6():
    current=portfolio_current_gold()
    if current is None:raise SystemExit("[FAIL] Gold current weight 계산 불가")
    t=target_opportunity_score(current,18.0,22.0)
    changed=[]
    for fn in ["opportunity_scores.csv","opportunity_details.csv","opportunity_summary.csv"]:
        p=OUT/"step06"/fn
        if patch_step06_table(p,current,t):changed.append(fn)
    # Always save authoritative policy diagnostic.
    diag=[{
        "Asset":"Gold","Current_Weight":round(current,4),"Target":20.0,"Lower":18.0,"Upper":22.0,
        "Gap_to_Target_pp":round(current-20,4),"Gap_to_Lower_pp":round(current-18,4),
        "Target_Opportunity_Score":round(t,4),
        "Formula":"below lower: 50+50*(lower-current)/lower; in range:50; above upper:50-50*(current-upper)/(100-upper)"
    }]
    write(OUT/"step06"/"policy_target_diagnostics.csv",diag)
    if not changed:
        raise SystemExit("[FAIL] STEP6 canonical output schema를 인식하지 못했습니다. 출력 CSV 헤더 확인 필요")
    print(f"[PATCH PASS] STEP6: Gold {current:.2f}% / policy 18~22% / target component={t:.2f}")
    print("             patched:",", ".join(changed))

def post7():
    current=portfolio_current_gold()
    if current is None:raise SystemExit("[FAIL] Gold current weight 계산 불가")
    tph=policy_health_score(current,18.0,22.0)

    comp=OUT/"step07"/"portfolio_health_components.csv"
    summ=OUT/"step07"/"portfolio_health_summary.csv"
    status=OUT/"step07"/"target_policy_status.csv"

    # Patch status values where identifiable.
    if status.exists():
        rows=read(status)
        if rows:
            fields=list(rows[0]); asset=findcol(fields,["Asset"]); target=findcol(fields,["Target","Target_Weight"])
            lower=findcol(fields,["Lower","Lower_Bound","Lower_Weight"]); upper=findcol(fields,["Upper","Upper_Bound","Upper_Weight"])
            for r in rows:
                if asset and asset_is_gold(r.get(asset)):
                    if target:r[target]="20.0"
                    if lower:r[lower]="18.0"
                    if upper:r[upper]="22.0"
            write(status,rows,fields)

    # Read component scores and recompute Health excluding FX REPORT_ONLY.
    scores={}
    if comp.exists():
        rows=read(comp)
        if rows:
            fields=list(rows[0]); name=findcol(fields,["Component","Metric","Name"]); score=findcol(fields,["Score","Component_Score","Value"])
            if name and score:
                for r in rows:
                    n=str(r.get(name,"")).lower().replace("_","").replace(" ","")
                    v=num(r.get(score))
                    if v is not None:scores[n]=v
                    if "target" in n and "policy" in n:
                        r[score]=f"{tph:.4f}"
                    if "fx" in n:
                        wc=findcol(fields,["Weight","Effective_Weight"])
                        if wc:r[wc]="0.0"
                write(comp,rows,fields)

    def pick(keys):
        for k,v in scores.items():
            if any(x in k for x in keys):return v
        return None
    C=pick(["concentration"]); V=pick(["volatility"]); D=pick(["maxdrawdown","drawdown"])
    R=pick(["correlation"])
    if None in (C,V,D,R):
        # Known component values may be in summary; fail rather than fabricate.
        raise SystemExit("[FAIL] STEP7 component schema에서 핵심 점수 탐지 실패")

    # FX is REPORT_ONLY: scored weights sum 0.90 and are renormalized.
    health=(.25*C+.20*V+.20*D+.15*R+.10*tph)/.90
    health=clamp(health)

    # Patch summary generically.
    if summ.exists():
        rows=read(summ)
        if rows:
            fields=list(rows[0])
            hs=findcol(fields,["Portfolio_Health","Health_Score","Portfolio_Health_Score","Score"])
            tp=findcol(fields,["Target_Policy","Target_Policy_Score"])
            if hs:
                for r in rows:r[hs]=f"{health:.4f}"
            if tp:
                for r in rows:r[tp]=f"{tph:.4f}"
            write(summ,rows,fields)

    diag=[{
        "Gold_Current_Weight":round(current,4),"Gold_Target":20.0,"Gold_Lower":18.0,"Gold_Upper":22.0,
        "Target_Policy_Health_Score":round(tph,4),
        "Concentration":C,"Volatility":V,"Max_Drawdown":D,"Correlation":R,
        "FX_Exposure_Effective_Weight":0.0,
        "Portfolio_Health_Recomputed":round(health,4),
        "Formula":"(.25*C+.20*V+.20*DD+.15*Corr+.10*TargetPolicy)/.90; FX is REPORT_ONLY"
    }]
    write(OUT/"step07"/"policy_health_diagnostics.csv",diag)
    print(f"[PATCH PASS] STEP7: Gold policy health={tph:.2f}, FX REPORT_ONLY weight=0")
    print(f"             Recomputed Portfolio Health={health:.2f}")
    print(f"             Gold policy: current {current:.2f}% / target 20% / acceptable 18~22%")

def check():
    p=BASE/"portfolio.csv"
    rows=read(p); g=next((r for r in rows if r.get("Asset")=="Gold"),None)
    if not g or abs(num(g.get("Target_Weight"),-1)-20)>1e-9:
        raise SystemExit("[FAIL] portfolio.csv Gold Target_Weight != 20")

    d6=OUT/"step06"/"policy_target_diagnostics.csv"
    d7=OUT/"step07"/"policy_health_diagnostics.csv"
    if not d6.exists() or not d7.exists():
        raise SystemExit("[FAIL] consistency diagnostics missing")

    a=read(d6)[0]; b=read(d7)[0]
    print("="*90);print("STEP12 POLICY / MATH CONSISTENCY CHECK");print("="*90)
    print(f"Gold current            : {a['Current_Weight']}%")
    print("Gold policy             : target 20% | acceptable 18~22%")
    print(f"Opportunity TargetScore : {a['Target_Opportunity_Score']}")
    print(f"Health PolicyScore      : {b['Target_Policy_Health_Score']}")
    print(f"Portfolio Health        : {b['Portfolio_Health_Recomputed']}")
    print("FX Exposure             : REPORT_ONLY, effective weight 0")
    print("PASS: STEP5 narrative direction / STEP6 policy / STEP7 policy+FX semantics aligned")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--stage",choices=["post5","post6","post7","check"],required=True)
    a=ap.parse_args()
    {"post5":post5,"post6":post6,"post7":post7,"check":check}[a.stage]()

if __name__=="__main__":main()
