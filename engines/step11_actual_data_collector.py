from pathlib import Path
import csv, io, statistics, requests
from datetime import datetime

BASE=Path(__file__).resolve().parents[1]
CONFIG=BASE/"config"
DATA=BASE/"data"
DATA.mkdir(parents=True,exist_ok=True)

SOURCE_CONFIG=CONFIG/"step11_data_sources.csv"
UNAVAILABLE_CONFIG=CONFIG/"step11_unavailable_indicators.csv"

OUT_CURRENT=DATA/"step11_current_market_data.csv"
OUT_DIAG=DATA/"step11_data_diagnostics.csv"
OUT_CANON=DATA/"step03_market_inputs_actual.csv"

FRED_URL="https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def fnum(v):
    try:
        if v is None or str(v).strip() in ("",".","NA","N/A"): return None
        return float(v)
    except: return None

def fetch_fred(sid):
    url=FRED_URL.format(sid=sid)
    try:
        r=requests.get(url,timeout=30,headers={"User-Agent":"portfolio-intelligence-step11/2.0"})
        r.raise_for_status()
    except requests.exceptions.SSLError as e:
        raise RuntimeError("SSL_ERROR: "+str(e))
    except requests.exceptions.ProxyError as e:
        raise RuntimeError("PROXY_ERROR: "+str(e))
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError("CONNECTION_ERROR: "+str(e))
    except requests.exceptions.Timeout as e:
        raise RuntimeError("TIMEOUT: "+str(e))
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP_ERROR {getattr(r,'status_code','?')}: {str(e)}")

    rows=list(csv.DictReader(io.StringIO(r.text)))
    if not rows: raise RuntimeError("EMPTY_RESPONSE")
    date_col="observation_date" if "observation_date" in rows[0] else list(rows[0])[0]
    value_col=sid if sid in rows[0] else [c for c in rows[0] if c!=date_col][0]
    out=[]
    for row in rows:
        v=fnum(row.get(value_col)); d=row.get(date_col)
        if v is not None and d: out.append((d,v))
    if len(out)<10: raise RuntimeError(f"TOO_FEW_OBS:{len(out)}")
    return out

def analyze(series,lag,zlook):
    vals=[v for _,v in series]; dates=[d for d,_ in series]
    lag=max(1,int(lag))
    if len(vals)<=lag: raise RuntimeError("INSUFFICIENT_FOR_LAG")
    latest=vals[-1]; prev=vals[-1-lag]; change=latest-prev

    deltas=[]
    start=max(lag,len(vals)-int(zlook)-lag)
    for i in range(start,len(vals)):
        if i-lag>=0: deltas.append(vals[i]-vals[i-lag])

    if len(deltas)>=10:
        mu=statistics.mean(deltas); sd=statistics.pstdev(deltas)
        z=(change-mu)/sd if sd>0 else 0.0
    else: z=0.0

    if abs(change)<=max(abs(latest)*1e-6,1e-12): direction=0
    else: direction=1 if change>0 else -1

    az=abs(z)
    shock="NORMAL" if az<0.5 else "MILD" if az<1 else "STRONG" if az<2 else "EXTREME"
    return dates[-1],latest,dates[-1-lag],prev,change,z,direction,shock,len(vals)

def write(path,rows,fields):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    actual=[]; diag=[]
    for c in read_csv(SOURCE_CONFIG):
        ind=c["Indicator"]; sid=c["Series_ID"]
        try:
            s=fetch_fred(sid)
            d,v,rd,rv,ch,z,direction,shock,n=analyze(
                s,int(c["Change_Lookback_Obs"]),int(c["Z_Lookback_Obs"])
            )
            actual.append({
                "Indicator":ind,"Direction":direction,"Shock_Level":shock,
                "Current_Value":round(v,8),"Observation_Date":d,
                "Reference_Value":round(rv,8),"Reference_Date":rd,
                "Change":round(ch,8),"Shock_Z":round(z,4),
                "Source":"FRED","Series_ID":sid,"Status":"ACTUAL"
            })
            diag.append({"Indicator":ind,"Status":"ACTUAL","Series_ID":sid,"Message":"OK"})
        except Exception as e:
            diag.append({"Indicator":ind,"Status":"ERROR","Series_ID":sid,"Message":str(e)[:500]})

    for c in read_csv(UNAVAILABLE_CONFIG):
        ind=c["Indicator"]
        # Canonical neutral row so no historical test signal can leak into STEP3.
        actual.append({
            "Indicator":ind,"Direction":0,"Shock_Level":"NORMAL",
            "Current_Value":"","Observation_Date":"",
            "Reference_Value":"","Reference_Date":"",
            "Change":"","Shock_Z":"","Source":"","Series_ID":"","Status":"UNAVAILABLE"
        })
        diag.append({"Indicator":ind,"Status":"UNAVAILABLE","Series_ID":"","Message":c["Reason"]})

    # Also add failed FRED rows as neutral canonical rows.
    have={r["Indicator"] for r in actual}
    for d in diag:
        if d["Status"]=="ERROR" and d["Indicator"] not in have:
            actual.append({
                "Indicator":d["Indicator"],"Direction":0,"Shock_Level":"NORMAL",
                "Current_Value":"","Observation_Date":"","Reference_Value":"","Reference_Date":"",
                "Change":"","Shock_Z":"","Source":"FRED","Series_ID":d["Series_ID"],"Status":"ERROR"
            })

    current=[r for r in actual if r["Status"]=="ACTUAL"]
    fields=["Indicator","Direction","Shock_Level","Current_Value","Observation_Date",
            "Reference_Value","Reference_Date","Change","Shock_Z","Source","Series_ID","Status"]
    write(OUT_CURRENT,current,fields)
    write(OUT_CANON,actual,fields)
    write(OUT_DIAG,diag,["Indicator","Status","Series_ID","Message"])

    ac=sum(x["Status"]=="ACTUAL" for x in diag)
    er=sum(x["Status"]=="ERROR" for x in diag)
    un=sum(x["Status"]=="UNAVAILABLE" for x in diag)

    print("="*78)
    print("STEP 11 - ACTUAL DATA COLLECTOR v2")
    print("="*78)
    print(f"ACTUAL      : {ac}")
    print(f"ERROR       : {er}")
    print(f"UNAVAILABLE : {un}")
    print()
    for x in diag:
        if x["Status"]=="ERROR":
            print(f"[ERROR] {x['Indicator']:<22} {x['Message']}")
    print()
    print("Canonical STEP3 input:")
    print(" - data/step03_market_inputs_actual.csv")
    print("※ 기존 step03_market_inputs.csv의 스키마와 무관하게 표준 컬럼으로 생성합니다.")
    print("※ 아직 STEP3가 이 파일을 읽도록 바꾸지는 마세요.")

if __name__=="__main__":
    main()
