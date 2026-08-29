from pathlib import Path
import csv, math
from collections import defaultdict

BASE=Path(__file__).resolve().parents[1]; CFG=BASE/"config"; DATA=BASE/"data"
IMPACT=CFG/"impact_matrix.csv"; FACTOR_CFG=CFG/"factor_config.csv"
INPUT=DATA/"step03_market_inputs.csv"; DIAG=DATA/"step11_data_diagnostics.csv"
HIST=DATA/"historical"/"historical_data.csv"
OUT=DATA/"step03_results.csv"; COV=DATA/"step03_factor_coverage.csv"
SUM=DATA/"step03_coverage_summary.csv"; EXC=DATA/"step03_excluded_indicators.csv"

ASSETS={"Domestic_Equity_Score":"국내주식","Foreign_Equity_Score":"해외주식","Bond_Score":"채권","Gold_Score":"금"}
MULT={"NORMAL":0.0,"MILD":0.5,"STRONG":1.0,"EXTREME":1.5}

# Empirical magnitude cutoffs: same transformed series vs its own history.
P_MILD=.50; P_STRONG=.75; P_EXTREME=.90
MIN_HISTORY=24

def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def dct(p,k):return {r[k]:r for r in read(p)}
def fnum(v):
    try:
        s=str(v).strip().replace(",","")
        return None if s in ("",".","NA","N/A","None","null") else float(s)
    except:return None
def clamp(v,a,b):return max(a,min(b,v))
def conf(w,c):return math.sqrt(w*c) if w>0 and c>0 else 0.0
def label(x):return "HIGH" if x>=.8 else "MEDIUM" if x>=.6 else "LOW" if x>=.4 else "VERY_LOW" if x>0 else "NONE"

def percentile_rank_abs(value, history):
    vals=sorted(abs(x) for x in history if x is not None)
    if len(vals)<MIN_HISTORY:return None
    x=abs(value)
    return sum(v<=x for v in vals)/len(vals)

def shock_from_percentile(p):
    if p is None:return "UNRATED"
    if p<P_MILD:return "NORMAL"
    if p<P_STRONG:return "MILD"
    if p<P_EXTREME:return "STRONG"
    return "EXTREME"

def factor_relevance(matrix):
    rel=defaultdict(lambda:defaultdict(bool))
    for _,m in matrix.items():
        f=m["Factor_Group"]
        for col,a in ASSETS.items():
            if float(m[col])!=0: rel[f][a]=True
    return rel

def main():
    matrix=dct(IMPACT,"Indicator"); fc=dct(FACTOR_CFG,"Factor_Group")
    inputs=read(INPUT); diag={r["Indicator"]:(r.get("Status") or "").upper() for r in read(DIAG)}
    hist=read(HIST)

    hist_by={}
    for ind in matrix:
        hist_by[ind]=[fnum(r.get(ind)) for r in hist if fnum(r.get(ind)) is not None]

    details=[]; excluded=[]
    for x in inputs:
        ind=x["Indicator"].strip()
        if diag.get(ind)!="ACTUAL":
            excluded.append({"Indicator":ind,"Status":diag.get(ind,"NO_STATUS"),"Reason":"실제 최신값이 아니므로 계산 제외"});continue
        if ind not in matrix:
            excluded.append({"Indicator":ind,"Status":"CONFIG_MISSING","Reason":"impact_matrix 누락"});continue
        obs=float(x["Observed_Change"])
        p=percentile_rank_abs(obs,hist_by.get(ind,[]))
        sc=shock_from_percentile(p)
        if sc=="UNRATED":
            excluded.append({"Indicator":ind,"Status":"INSUFFICIENT_HISTORY","Reason":"Shock 분류용 역사자료 24개월 미만"});continue
        direction=1 if obs>0 else -1 if obs<0 else 0
        impacts={a:float(matrix[ind][col])*direction*MULT[sc] for col,a in ASSETS.items()}
        details.append({"Indicator":ind,"Factor_Group":matrix[ind]["Factor_Group"],"Observed_Change":obs,
                        "Shock_Class":sc,"Shock_Percentile":p,"Importance":float(matrix[ind]["Importance"]),"Impacts":impacts})

    if not details:raise RuntimeError("사용 가능한 ACTUAL 지표가 없습니다.")

    all_imp=defaultdict(float); all_cnt=defaultdict(int)
    for _,m in matrix.items():
        f=m["Factor_Group"];all_imp[f]+=float(m["Importance"]);all_cnt[f]+=1

    grouped=defaultdict(list)
    for d in details:grouped[d["Factor_Group"]].append(d)

    fs={}; cov={}
    for f,cfg in fc.items():
        items=grouped.get(f,[]); ai=sum(i["Importance"] for i in items)
        wc=ai/all_imp[f] if all_imp[f] else 0; cc=len(items)/all_cnt[f] if all_cnt[f] else 0; cf=conf(wc,cc)
        cov[f]={"Available":len(items),"Total":all_cnt[f],"WeightedCoverage":wc,"CountCoverage":cc,
                "Confidence":cf,"Label":label(cf),"FactorWeight":float(cfg["Factor_Weight"])}
        fs[f]={}
        for a in ASSETS.values():
            if ai<=0:fs[f][a]=None
            else:
                # Importance exactly once; available weights sum to 1.
                signal=sum(i["Impacts"][a]*i["Importance"] for i in items)/ai
                fs[f][a]=clamp(signal,float(cfg["Min_Cap"]),float(cfg["Max_Cap"]))

    rel=factor_relevance(matrix)
    raw={}; adjusted={}; aconf={}
    for a in ASSETS.values():
        intended=sum(cov[f]["FactorWeight"] for f in cov if rel[f][a])
        raw_num=raw_den=adj_num=0.0
        for f,scores in fs.items():
            if not rel[f][a]:continue
            s=scores[a]
            if s is None:continue
            fw=cov[f]["FactorWeight"];cf=cov[f]["Confidence"]
            raw_num+=s*fw;raw_den+=fw
            adj_num+=s*fw*cf
        raw[a]=raw_num/raw_den if raw_den else 0.0
        # Critical correction: denominator is intended relevant factor weight,
        # so incomplete confidence shrinks decision score toward neutral.
        adjusted[a]=adj_num/intended if intended else 0.0
        aconf[a]=sum(cov[f]["FactorWeight"]*cov[f]["Confidence"] for f in cov if rel[f][a])/intended if intended else 0.0

    rows=[]
    for d in details:
        for a,s in d["Impacts"].items():
            rows.append({"Level":"INDICATOR","Name":d["Indicator"],"Factor_Group":d["Factor_Group"],"Asset":a,
                         "Score":round(s,4),"Shock_Class":d["Shock_Class"],"Observed_Change":d["Observed_Change"],
                         "Shock_Percentile":round(d["Shock_Percentile"]*100,2),"Coverage":"","Confidence":"",
                         "Confidence_Label":"","Raw_Score":""})
    for f,scores in fs.items():
        c=cov[f]
        for a,s in scores.items():
            rows.append({"Level":"FACTOR","Name":f,"Factor_Group":f,"Asset":a,"Score":"" if s is None else round(s,4),
                         "Shock_Class":"","Observed_Change":"","Shock_Percentile":"","Coverage":round(c["WeightedCoverage"],4),
                         "Confidence":round(c["Confidence"],4),"Confidence_Label":c["Label"],"Raw_Score":""})
    for a in ASSETS.values():
        rows.append({"Level":"ASSET_ENVIRONMENT","Name":"FINAL","Factor_Group":"","Asset":a,"Score":round(adjusted[a],4),
                     "Shock_Class":"","Observed_Change":"","Shock_Percentile":"","Coverage":"","Confidence":round(aconf[a],4),
                     "Confidence_Label":label(aconf[a]),"Raw_Score":round(raw[a],4)})
    fields=["Level","Name","Factor_Group","Asset","Score","Shock_Class","Observed_Change","Shock_Percentile",
            "Coverage","Confidence","Confidence_Label","Raw_Score"]
    with OUT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

    cr=[]
    for f,c in cov.items():
        cr.append({"Factor_Group":f,"Available_Indicators":c["Available"],"Total_Indicators":c["Total"],
                   "Count_Coverage_Pct":round(c["CountCoverage"]*100,2),"Weighted_Coverage_Pct":round(c["WeightedCoverage"]*100,2),
                   "Data_Confidence_Score":round(c["Confidence"]*100,2),"Data_Confidence_Label":c["Label"],
                   "Factor_Weight":c["FactorWeight"]})
    with COV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(cr[0]));w.writeheader();w.writerows(cr)

    actual=len({d["Indicator"] for d in details});total=len(matrix)
    wi=sum(d["Importance"] for d in details);ti=sum(float(m["Importance"]) for m in matrix.values())
    wc=wi/ti;cc=actual/total;oc=conf(wc,cc)
    sr={"Actual_Indicators":actual,"Total_Indicators":total,"Count_Coverage_Pct":round(cc*100,2),
        "Weighted_Coverage_Pct":round(wc*100,2),"Data_Confidence_Score":round(oc*100,2),
        "Data_Confidence_Label":label(oc),"Shock_Method":"EMPIRICAL_ABS_PERCENTILE_50_75_90",
        "Scoring_Mode":"AVAILABLE_ONLY_RENORMALIZED_WITH_CONFIDENCE_SHRINKAGE","Missing_As_Zero":"NO"}
    with SUM.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(sr));w.writeheader();w.writerow(sr)
    with EXC.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["Indicator","Status","Reason"]);w.writeheader();w.writerows(excluded)

    print("="*94);print("STEP 03 - VALIDATED COVERAGE-AWARE ENGINE v2");print("="*94)
    print(f"실제 사용지표 : {actual}/{total}")
    for f,c in cov.items():
        print(f"{f:<15} {c['Available']}/{c['Total']} | Coverage={c['WeightedCoverage']*100:5.1f}% | DataConfidence={c['Confidence']*100:5.1f}% ({c['Label']})")
    print()
    for a in ASSETS.values():
        print(f"{a:<8} Raw={raw[a]:+6.2f} | Decision={adjusted[a]:+6.2f} | DataConfidence={aconf[a]*100:5.1f}% ({label(aconf[a])})")
    print("→ STEP4 최신 변환값 직접 사용")
    print("→ Shock는 동일 지표 역사적 절대변화 percentile로 분류")
    print("→ Importance 1회 적용 + ACTUAL 내부 재정규화")
    print("→ 부족한 정보는 최종 Decision 점수를 중립(0) 방향으로 축소")
    print("→ Confidence는 통계적 확률이 아니라 Data Coverage Confidence")

if __name__=="__main__":main()
