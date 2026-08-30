from pathlib import Path
import io, json, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"docs"/"data"/"macro_risk.json"
KST=ZoneInfo("Asia/Seoul")

SERIES={
    "US10Y":{
        "fred_id":"DGS10",
        "name":"미국 10년물",
        "unit":"%",
    },
    "VIX":{
        "fred_id":"VIXCLS",
        "name":"VIX",
        "unit":"",
    },
    "HY_SPREAD":{
        "fred_id":"BAMLH0A0HYM2",
        "name":"하이일드 스프레드",
        "unit":"%p",
    },
    "USDKRW":{
        "fred_id":"DEXKOUS",
        "name":"USD/KRW",
        "unit":"원",
    },
}

LOOKBACK_DAYS=900
ROLLING_OBS=252
MIN_OBS=60
DISPLAY_DAYS=120
PLOT_POINTS=90

def fetch_fred(series_id):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r=requests.get(url,timeout=30,headers={"User-Agent":"portfolio-intelligence/1.0"})
    r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    if "DATE" not in df.columns:
        # FRED occasionally returns "observation_date".
        date_col=df.columns[0]
    else:
        date_col="DATE"
    val_col=[c for c in df.columns if c!=date_col][0]
    df=df.rename(columns={date_col:"date",val_col:"value"})
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df["value"]=pd.to_numeric(df["value"],errors="coerce")
    df=df.dropna(subset=["date","value"]).sort_values("date")
    cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
    return df[df["date"]>=cutoff].copy()

def rolling_percentile(values, window=ROLLING_OBS, min_obs=MIN_OBS):
    out=[]
    arr=list(values)
    for i,v in enumerate(arr):
        start=max(0,i-window+1)
        hist=[x for x in arr[start:i+1] if x is not None and math.isfinite(float(x))]
        if len(hist)<min_obs:
            out.append(None)
            continue
        less=sum(x<v for x in hist)
        equal=sum(x==v for x in hist)
        pct=100.0*(less+0.5*equal)/len(hist)
        out.append(round(pct,2))
    return out

frames={}
errors={}
for key,meta in SERIES.items():
    try:
        frames[key]=fetch_fred(meta["fred_id"])
    except Exception as e:
        errors[key]=str(e)

if len(frames)<3:
    raise SystemExit(f"FAIL: insufficient macro sources: {errors}")

# union business dates
all_dates=sorted(set().union(*[set(df["date"]) for df in frames.values()]))
master=pd.DataFrame({"date":all_dates}).sort_values("date")

for key,df in frames.items():
    master=master.merge(df.rename(columns={"value":key}),on="date",how="left")

# Financial daily series have holidays/missing dates; forward-fill only over short gaps.
for key in frames:
    master[key]=master[key].ffill(limit=5)

# normalized stress percentile: high level = high tension for all four series
for key in frames:
    vals=[None if pd.isna(x) else float(x) for x in master[key]]
    master[key+"_N"]=rolling_percentile(vals)

norm_cols=[k+"_N" for k in frames]
master["MACRO_TENSION"]=master[norm_cols].mean(axis=1,skipna=True)
master.loc[master[norm_cols].notna().sum(axis=1)<3,"MACRO_TENSION"]=float("nan")

latest_valid=master.dropna(subset=["MACRO_TENSION"])
if latest_valid.empty:
    raise SystemExit("FAIL: no normalized macro tension data")

latest=latest_valid.iloc[-1]
display_cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=DISPLAY_DAYS))
plot=master[master["date"]>=display_cutoff].copy()
plot=plot.dropna(subset=["MACRO_TENSION"])

# limit to latest 90 observations for mobile legibility
plot=plot.tail(PLOT_POINTS)

def f(v,d=2):
    return None if pd.isna(v) else round(float(v),d)

def direction(v):
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
    raw=latest.get(key)
    norm=latest.get(key+"_N")
    latest_raw[key]={
        "name":meta["name"],
        "value":f(raw,3 if key!="USDKRW" else 2),
        "unit":meta["unit"],
        "fred_id":meta["fred_id"],
    }
    latest_norm[key]=f(norm,1)

payload={
    "meta":{
        "generated_at":datetime.now(KST).isoformat(timespec="seconds"),
        "source":"FRED",
        "normalization":"rolling percentile over up to 252 valid observations; high = higher tension",
        "display_points":len(points),
        "version":"STEP13_MACRO_v10",
        "errors":errors,
    },
    "current":{
        "score":f(latest["MACRO_TENSION"],1),
        "state":direction(f(latest["MACRO_TENSION"],1)),
        "date":latest["date"].strftime("%Y-%m-%d"),
        "raw":latest_raw,
        "normalized":latest_norm,
    },
    "points":points,
}

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("="*86)
print("STEP13 MACRO RISK v10")
print("="*86)
print("Source           : FRED")
print("Latest date      :",payload["current"]["date"])
print("Macro Tension    :",payload["current"]["score"],payload["current"]["state"])
print("Display points   :",len(points))
for k in SERIES:
    print(f"{k:16}: raw={latest_raw[k]['value']} norm={latest_norm[k]}")
if errors:
    print("Source warnings  :",errors)
print("PASS: macro risk composite generated.")
