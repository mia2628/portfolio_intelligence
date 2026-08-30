from pathlib import Path
import io, json, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"docs"/"data"/"macro_risk.json"
KST=ZoneInfo("Asia/Seoul")

SERIES={
    "US10Y":{"fred_id":"DGS10","name":"미국 10년물","unit":"%"},
    "VIX":{"fred_id":"VIXCLS","name":"VIX","unit":""},
    "HY_SPREAD":{"fred_id":"BAMLH0A0HYM2","name":"하이일드 스프레드","unit":"%p"},
    "USDKRW":{"fred_id":"DEXKOUS","name":"USD/KRW","unit":"원"},
}
ALIASES={
    "US10Y":["US10Y","US_10Y","US10Y_YIELD","DGS10"],
    "VIX":["VIX","VIXCLS"],
    "HY_SPREAD":["US_HY_SPREAD","HY_SPREAD","BAMLH0A0HYM2"],
    "USDKRW":["USDKRW","USD_KRW","DEXKOUS"],
}
LOOKBACK_DAYS=900
ROLLING_OBS=252
MIN_OBS=60
DISPLAY_DAYS=120
PLOT_POINTS=90

def load_local_series(key):
    candidates=[BASE/"data"/"historical"/"historical_data.csv", BASE/"data"/"historical_data.csv"]
    for p in candidates:
        if not p.exists():
            continue
        try:
            df=pd.read_csv(p)
            date_col=next((c for c in ["date","DATE","Date","observation_date"] if c in df.columns),None)
            val_col=next((c for c in ALIASES[key] if c in df.columns),None)
            if not date_col or not val_col:
                continue
            x=df[[date_col,val_col]].copy()
            x.columns=["date","value"]
            x["date"]=pd.to_datetime(x["date"],errors="coerce")
            x["value"]=pd.to_numeric(x["value"],errors="coerce")
            x=x.dropna().sort_values("date")
            cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
            x=x[x["date"]>=cutoff]
            if len(x)>=MIN_OBS:
                return x, str(p)
        except Exception as e:
            print(f"WARN local {key}: {e}")
    return None, None

def fetch_fred_once(key):
    sid=SERIES[key]["fred_id"]
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    r=requests.get(url,timeout=(5,12),headers={"User-Agent":"portfolio-intelligence/1.0"})
    r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    date_col="DATE" if "DATE" in df.columns else df.columns[0]
    val_col=next(c for c in df.columns if c!=date_col)
    df=df.rename(columns={date_col:"date",val_col:"value"})
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df["value"]=pd.to_numeric(df["value"],errors="coerce")
    df=df.dropna().sort_values("date")
    cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
    df=df[df["date"]>=cutoff]
    if len(df)<MIN_OBS:
        raise RuntimeError(f"{key}: too few observations {len(df)}")
    return key,df

def rolling_percentile(values,window=ROLLING_OBS,min_obs=MIN_OBS):
    out=[]
    arr=list(values)
    for i,v in enumerate(arr):
        if v is None or not math.isfinite(float(v)):
            out.append(None); continue
        start=max(0,i-window+1)
        hist=[x for x in arr[start:i+1] if x is not None and math.isfinite(float(x))]
        if len(hist)<min_obs:
            out.append(None); continue
        less=sum(x<v for x in hist)
        equal=sum(x==v for x in hist)
        out.append(round(100.0*(less+0.5*equal)/len(hist),2))
    return out

def preserve_previous(reason,errors):
    if OUT.exists():
        try:
            prev=json.loads(OUT.read_text(encoding="utf-8"))
            if (prev.get("points") or []) and prev.get("current",{}).get("score") is not None:
                print("="*86)
                print("STEP13 MACRO RISK v10.3 FAST")
                print("="*86)
                print("WARN:",reason)
                print("Errors:",errors)
                print("PASS_WITH_STALE_DATA: previous valid macro_risk.json retained.")
                raise SystemExit(0)
        except SystemExit:
            raise
        except Exception:
            pass
    raise SystemExit(f"FAIL: {reason}; no valid previous macro_risk.json")

frames={}
source_used={}
errors={}

for key in SERIES:
    df,src=load_local_series(key)
    if df is not None:
        frames[key]=df
        source_used[key]=f"LOCAL:{src}"

missing=[k for k in SERIES if k not in frames]
if missing:
    print("Missing local series -> short parallel FRED fetch:",missing)
    with ThreadPoolExecutor(max_workers=min(4,len(missing))) as ex:
        futs={ex.submit(fetch_fred_once,k):k for k in missing}
        for fut in as_completed(futs):
            key=futs[fut]
            try:
                k,df=fut.result()
                frames[k]=df
                source_used[k]="FRED"
            except Exception as e:
                errors[key]=str(e)
                print(f"WARN: {key} FRED fallback failed: {e}")

if len(frames)<3:
    preserve_previous("fewer than 3 macro sources available",errors)

all_dates=sorted(set().union(*[set(df["date"]) for df in frames.values()]))
master=pd.DataFrame({"date":all_dates}).sort_values("date")
for key,df in frames.items():
    master=master.merge(df.rename(columns={"value":key}),on="date",how="left")
for key in frames:
    master[key]=master[key].ffill(limit=5)

for key in frames:
    vals=[None if pd.isna(x) else float(x) for x in master[key]]
    master[key+"_N"]=rolling_percentile(vals)

norm_cols=[k+"_N" for k in frames]
master["MACRO_TENSION"]=master[norm_cols].mean(axis=1,skipna=True)
master.loc[master[norm_cols].notna().sum(axis=1)<3,"MACRO_TENSION"]=float("nan")

latest_valid=master.dropna(subset=["MACRO_TENSION"])
if latest_valid.empty:
    preserve_previous("no normalized macro tension rows",errors)

latest=latest_valid.iloc[-1]
display_cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=DISPLAY_DAYS))
plot=master[master["date"]>=display_cutoff].dropna(subset=["MACRO_TENSION"]).tail(PLOT_POINTS)

def f(v,d=2):
    return None if pd.isna(v) else round(float(v),d)
def state(v):
    if v is None:return "NO_DATA"
    if v>=65:return "HIGH"
    if v>=45:return "ELEVATED"
    return "CALM"

points=[]
for _,r in plot.iterrows():
    points.append({
        "date":r["date"].strftime("%Y-%m-%d"),
        "us10y":f(r.get("US10Y_N"),1),
        "vix":f(r.get("VIX_N"),1),
        "hy":f(r.get("HY_SPREAD_N"),1),
        "usdkrw":f(r.get("USDKRW_N"),1),
        "macro_tension":f(r.get("MACRO_TENSION"),1),
    })

latest_raw={}
latest_norm={}
for key,meta in SERIES.items():
    latest_raw[key]={
        "name":meta["name"],
        "value":f(latest.get(key),3 if key!="USDKRW" else 2) if key in frames else None,
        "unit":meta["unit"],
        "fred_id":meta["fred_id"],
    }
    latest_norm[key]=f(latest.get(key+"_N"),1) if key in frames else None

payload={
    "meta":{
        "generated_at":datetime.now(KST).isoformat(timespec="seconds"),
        "source":"LOCAL_FIRST_WITH_FRED_FALLBACK",
        "source_used":source_used,
        "normalization":"rolling percentile over up to 252 valid observations; high = higher tension",
        "display_points":len(points),
        "version":"STEP13_MACRO_v10_3",
        "errors":errors,
    },
    "current":{
        "score":f(latest["MACRO_TENSION"],1),
        "state":state(f(latest["MACRO_TENSION"],1)),
        "date":latest["date"].strftime("%Y-%m-%d"),
        "raw":latest_raw,
        "normalized":latest_norm,
    },
    "points":points,
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("="*86)
print("STEP13 MACRO RISK v10.3 FAST")
print("="*86)
print("Source mix       :",source_used)
print("Latest date      :",payload["current"]["date"])
print("Macro Tension    :",payload["current"]["score"],payload["current"]["state"])
print("Display points   :",len(points))
if errors: print("Source warnings  :",errors)
print("PASS: macro risk composite generated without long retry loops.")
