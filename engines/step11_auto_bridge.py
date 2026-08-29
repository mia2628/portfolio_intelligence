from pathlib import Path
import argparse, csv, shutil
from datetime import datetime

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/"data"
HIST=DATA/"historical"/"historical_data.csv"
STEP3=DATA/"step03_market_inputs.csv"
BACKUP=DATA/"step03_market_inputs_template.csv"
ACTUAL=DATA/"step03_market_inputs_actual.csv"
CURRENT=DATA/"step11_current_market_data.csv"
DIAG=DATA/"step11_data_diagnostics.csv"

ALL=[
"US10Y","US2Y","US_REAL10Y","US_10Y2Y_SPREAD","KR3Y","KR10Y",
"FED_HIKE_EXPECTATION","BOK_HIKE_EXPECTATION","US_CPI","US_CORE_CPI",
"US_CORE_PCE","US_BREAKEVEN_10Y","KR_CPI","USDKRW","DXY","VIX","MOVE",
"US_HY_SPREAD","FCI_TIGHTENING","GEOPOLITICAL_RISK","US_ISM_MFG",
"US_UNEMPLOYMENT","US_INITIAL_CLAIMS","US_NFP_SURPRISE","KR_EXPORT_GROWTH",
"KR_SEMI_EXPORT_GROWTH","CB_GOLD_NET_BUYING"
]

MIN_ACTUAL=10
MAX_STALE_MONTHS=3

def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def fnum(v):
    try:
        s=str(v).strip().replace(",","")
        return None if s in ("",".","NA","N/A","None","null") else float(s)
    except:return None

def parse_date(s):
    try:return datetime.strptime(str(s)[:10],"%Y-%m-%d")
    except:return None

def month_gap(a,b):
    return (b.year-a.year)*12+(b.month-a.month)

def write(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");args=ap.parse_args()
    if not HIST.exists():raise SystemExit("[STOP] historical_data.csv 없음")
    rows=read(HIST)
    if not rows:raise SystemExit("[STOP] historical_data.csv 비어 있음")

    dataset_dates=[parse_date(r.get("Date")) for r in rows if parse_date(r.get("Date"))]
    dataset_latest=max(dataset_dates) if dataset_dates else datetime.today()

    actual=[]; diag=[]; step3=[]
    for ind in ALL:
        found=None
        for r in reversed(rows):
            v=fnum(r.get(ind))
            d=parse_date(r.get("Date"))
            if v is not None and d:
                found=(d,v);break

        if found is None:
            status="UNAVAILABLE"; value=0.0; obs_date=""; age=""
            msg="historical_data에 유효값 없음"
        else:
            d,v=found; age=month_gap(d,dataset_latest)
            if age>MAX_STALE_MONTHS:
                status="STALE"; value=0.0
                msg=f"latest value is {age} months old"
            else:
                status="ACTUAL"; value=v
                msg="OK: STEP4에서 이미 변환된 최신값을 직접 사용"
            obs_date=d.strftime("%Y-%m-%d")

        if status=="ACTUAL":
            actual.append({"Indicator":ind,"Observed_Change":round(value,8),
                           "Observation_Date":obs_date,"Age_Months":age,"Status":status})
        diag.append({"Indicator":ind,"Status":status,"Observation_Date":obs_date,
                     "Age_Months":age,"Message":msg})
        # Canonical file keeps every indicator, but STEP3 will use diagnostics to exclude non-ACTUAL.
        step3.append({"Indicator":ind,"Observed_Change":round(value,8) if status=="ACTUAL" else 0.0})

    write(CURRENT,actual,["Indicator","Observed_Change","Observation_Date","Age_Months","Status"])
    write(DIAG,diag,["Indicator","Status","Observation_Date","Age_Months","Message"])
    write(ACTUAL,step3,["Indicator","Observed_Change"])

    ac=sum(x["Status"]=="ACTUAL" for x in diag)
    er=sum(x["Status"] in ("ERROR","STALE") for x in diag)
    un=sum(x["Status"]=="UNAVAILABLE" for x in diag)

    print("="*78);print("STEP 11 - VALIDATED LATEST-SIGNAL BRIDGE");print("="*78)
    print(f"Historical rows : {len(rows)}")
    print(f"ACTUAL          : {ac}")
    print(f"STALE/ERROR     : {er}")
    print(f"UNAVAILABLE     : {un}")
    print("→ STEP4 값은 이미 변화량이므로 STEP11에서 재차분하지 않습니다.")

    if args.apply:
        if ac<MIN_ACTUAL:
            print(f"[STOP] ACTUAL {ac} < {MIN_ACTUAL}; 기존 STEP3 입력 유지")
            raise SystemExit(2)
        if STEP3.exists() and not BACKUP.exists():shutil.copy2(STEP3,BACKUP)
        shutil.copy2(ACTUAL,STEP3)
        print("[APPLIED] step03_market_inputs.csv 갱신")
    else: print("[VALIDATION ONLY]")

if __name__=="__main__":main()
