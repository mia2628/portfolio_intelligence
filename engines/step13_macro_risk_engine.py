from pathlib import Path
import io, json, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

def build_session():
    retry=Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=3,
        status_forcelist=[429,500,502,503,504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session=requests.Session()
    session.mount("https://",HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent":"portfolio-intelligence/1.0"})
    return session

def fetch_fred(series_id):
    """
    FRED public CSV with retries.
    Connect/read timeout are separated so a slow FRED response does not
    immediately kill the entire scheduled job.
    """
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    session=build_session()
    last=None
    for attempt in range(1,4):
        try:
            r=session.get(url,timeout=(15,75))
            r.raise_for_status()
            df=pd.read_csv(io.StringIO(r.text))
            date_col="DATE" if "DATE" in df.columns else df.columns[0]
            val_col=[c for c in df.columns if c!=date_col][0]
            df=df.rename(columns={date_col:"date",val_col:"value"})
            df["date"]=pd.to_datetime(df["date"],errors="coerce")
            df["value"]=pd.to_numeric(df["value"],errors="coerce")
            df=df.dropna(subset=["date","value"]).sort_values("date")
            cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
            df=df[df["date"]>=cutoff].copy()
            if len(df)<MIN_OBS:
                raise RuntimeError(f"too few FRED observations: {len(df)}")
            return df
        except Exception as e:
            last=e
            print(f"WARN: FRED {series_id} attempt {attempt}/3 failed: {e}")
            if attempt<3:
                time.sleep(5*attempt)
    raise RuntimeError(f"FRED {series_id} failed after retries: {last}")

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

def load_local_fallback(key):
    """
    Use existing repository historical data if FRED is temporarily unavailable.
    This keeps the chart operational during external-source outages.
    """
    candidates=[
        BASE/"data"/"historical"/"historical_data.csv",
        BASE/"data"/"historical_data.csv",
    ]
    aliases={
        "US10Y":["US10Y","US_10Y","US10Y_YIELD","DGS10"],
        "VIX":["VIX","VIXCLS"],
        "HY_SPREAD":["US_HY_SPREAD","HY_SPREAD","BAMLH0A0HYM2"],
        "USDKRW":["USDKRW","USD_KRW","DEXKOUS"],
    }
    for p in candidates:
        if not p.exists():
            continue
        try:
            df=pd.read_csv(p)
            date_candidates=[c for c in ["date","DATE","Date","observation_date"] if c in df.columns]
            if not date_candidates:
                continue
            col=next((c for c in aliases[key] if c in df.columns),None)
            if not col:
                continue
            x=df[[date_candidates[0],col]].copy()
            x.columns=["date","value"]
            x["date"]=pd.to_datetime(x["date"],errors="coerce")
            x["value"]=pd.to_numeric(x["value"],errors="coerce")
            x=x.dropna().sort_values("date")
            cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
            x=x[x["date"]>=cutoff]
            if len(x)>=MIN_OBS:
                print(f"FALLBACK: {key} loaded from {p} ({len(x)} rows)")
                return x
        except Exception as e:
            print(f"WARN: local fallback {p} / {key}: {e}")
    return None

def load_previous_macro_series(key):
    """
    Last-resort fallback from existing macro_risk.json.
    This contains normalized points only, so it cannot rebuild raw FRED values.
    It is used only to preserve the previous published chart when fresh rebuild fails.
    """
    return None

frames={}
errors={}
source_used={}
for key,meta in SERIES.items():
    try:
        frames[key]=fetch_fred(meta["fred_id"])
        source_used[key]="FRED"
    except Exception as e:
        errors[key]=str(e)
        fb=load_local_fallback(key)
        if fb is not None:
            frames[key]=fb
            source_used[key]="LOCAL_FALLBACK"

if len(frames)<3:
    # Do not destroy the currently published chart during a temporary FRED outage.
    if OUT.exists():
        try:
            prev=json.loads(OUT.read_text(encoding="utf-8"))
            if (prev.get("points") or []) and prev.get("current",{}).get("score") is not None:
                print("="*86)
                print("STEP13 MACRO RISK v10.2")
                print("="*86)
                print("WARN: fresh macro rebuild unavailable; preserving previous macro_risk.json.")
                print("Available fresh sources:",list(frames))
                print("Errors:",errors)
                print("PASS_WITH_STALE_DATA: previous valid macro chart retained.")
                raise SystemExit(0)
        except SystemExit:
            raise
        except Exception:
            pass
    raise SystemExit(f"FAIL: insufficient macro sources after retry/fallback: {errors}")

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
        "source_used":source_used,
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
print("Source mix       :",source_used)
print("Latest date      :",payload["current"]["date"])
print("Macro Tension    :",payload["current"]["score"],payload["current"]["state"])
print("Display points   :",len(points))
for k in SERIES:
    print(f"{k:16}: raw={latest_raw[k]['value']} norm={latest_norm[k]}")
if errors:
    print("Source warnings  :",errors)
print("PASS: macro risk composite generated.")
