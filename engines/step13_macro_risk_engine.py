from pathlib import Path
import io, json, math, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

BASE=Path(__file__).resolve().parents[1]
HIST=BASE/"data"/"historical"/"historical_data.csv"
STEP3=BASE/"data"/"step03_market_inputs.csv"
OUT=BASE/"docs"/"data"/"macro_risk.json"
KST=ZoneInfo("Asia/Seoul")

KEYS=["US10Y","VIX","US_HY_SPREAD","USDKRW"]
DISPLAY={
    "US10Y":{"name":"미국 10년물 변화","unit":"bp"},
    "VIX":{"name":"VIX 변화","unit":"%"},
    "US_HY_SPREAD":{"name":"하이일드 스프레드 변화","unit":"bp"},
    "USDKRW":{"name":"USD/KRW 변화","unit":"%"},
}

MIN_OBS=60
ROLLING_OBS=120
PLOT_POINTS=90

def numeric(s):
    return pd.to_numeric(s,errors="coerce")

def read_hist_text(text):
    df=pd.read_csv(io.StringIO(text))
    if "Date" not in df.columns:
        return None
    df["Date"]=pd.to_datetime(df["Date"],errors="coerce")
    df=df.dropna(subset=["Date"]).sort_values("Date")
    for k in KEYS:
        if k in df.columns:
            df[k]=numeric(df[k])
    return df

def valid_score(df):
    if df is None or df.empty:
        return 0,{}
    counts={k:int(df[k].notna().sum()) if k in df.columns else 0 for k in KEYS}
    good=sum(v>=MIN_OBS for v in counts.values())
    return good,counts

def current_file_candidate():
    if not HIST.exists():
        return None,None
    try:
        text=HIST.read_text(encoding="utf-8-sig")
        df=read_hist_text(text)
        good,counts=valid_score(df)
        if good>=3:
            return df,{"source":"CURRENT_FILE","counts":counts}
    except Exception as e:
        print("WARN current historical_data:",e)
    return None,None

def git_history_candidate():
    """
    Find the newest committed historical_data.csv that contains
    at least 3 of the 4 macro series with >= MIN_OBS valid rows.
    No network access is required.
    """
    path="data/historical/historical_data.csv"
    try:
        p=subprocess.run(
            ["git","log","--format=%H","--",path],
            cwd=BASE,check=True,text=True,capture_output=True,timeout=20
        )
        commits=[x.strip() for x in p.stdout.splitlines() if x.strip()]
    except Exception as e:
        print("WARN git log:",e)
        return None,None

    for sha in commits[:80]:
        try:
            p=subprocess.run(
                ["git","show",f"{sha}:{path}"],
                cwd=BASE,check=True,text=True,capture_output=True,timeout=10
            )
            df=read_hist_text(p.stdout)
            good,counts=valid_score(df)
            if good>=3:
                return df,{
                    "source":"GIT_LAST_KNOWN_GOOD",
                    "commit":sha[:12],
                    "counts":counts,
                }
        except Exception:
            continue
    return None,None

def load_step3_current():
    vals={}
    if not STEP3.exists():
        return vals
    try:
        d=pd.read_csv(STEP3)
        if not {"Indicator","Observed_Change"}.issubset(d.columns):
            return vals
        for _,r in d.iterrows():
            k=str(r["Indicator"])
            if k in KEYS:
                v=pd.to_numeric(pd.Series([r["Observed_Change"]]),errors="coerce").iloc[0]
                if pd.notna(v):
                    vals[k]=float(v)
    except Exception as e:
        print("WARN step03 current:",e)
    return vals

def percentile(values,current):
    a=[float(x) for x in values if pd.notna(x)]
    if not a or current is None:
        return None
    less=sum(x<current for x in a)
    equal=sum(x==current for x in a)
    return round(100*(less+0.5*equal)/len(a),2)

def rolling_percentile(series,window=ROLLING_OBS):
    vals=list(series)
    out=[]
    for i,v in enumerate(vals):
        if pd.isna(v):
            out.append(None); continue
        h=[float(x) for x in vals[max(0,i-window+1):i+1] if pd.notna(x)]
        if len(h)<24:
            out.append(None); continue
        less=sum(x<float(v) for x in h)
        equal=sum(x==float(v) for x in h)
        out.append(round(100*(less+0.5*equal)/len(h),2))
    return out

df,source=current_file_candidate()
if df is None:
    df,source=git_history_candidate()

if df is None:
    raise SystemExit(
        "FAIL: no valid historical_data.csv in current file or git history. "
        "This is a repository-data issue, not an external API timeout."
    )

print("="*86)
print("STEP13 MACRO DATA RECOVERY v10.5")
print("="*86)
print("Historical source :",source)

# Use only available validated macro columns.
available=[k for k in KEYS if k in df.columns and df[k].notna().sum()>=MIN_OBS]
if len(available)<3:
    raise SystemExit(f"FAIL: only {available} have enough history")

# Build normalized historical chart from the already-transformed STEP04 signals.
plot=df[["Date"]+available].copy()
for k in available:
    plot[k+"_N"]=rolling_percentile(plot[k])

norm_cols=[k+"_N" for k in available]
plot["MACRO_TENSION"]=plot[norm_cols].mean(axis=1,skipna=True)
plot.loc[plot[norm_cols].notna().sum(axis=1)<3,"MACRO_TENSION"]=float("nan")
plot=plot.dropna(subset=["MACRO_TENSION"]).tail(PLOT_POINTS)

# Overlay latest STEP3 transformed signals when available.
current=load_step3_current()
raw={}
norm={}
for k in KEYS:
    hist=df[k].dropna().tolist() if k in df.columns else []
    latest_current=current.get(k)
    if latest_current is None and hist:
        latest_current=float(hist[-1])
    raw[k]=latest_current
    norm[k]=percentile(hist,latest_current) if hist and latest_current is not None else None

active_norm=[v for v in norm.values() if v is not None]
macro_score=round(sum(active_norm)/len(active_norm),1) if len(active_norm)>=3 else None

def state(v):
    if v is None:return "NO_DATA"
    if v>=65:return "HIGH"
    if v>=45:return "ELEVATED"
    return "CALM"

points=[]
for _,r in plot.iterrows():
    points.append({
        "date":r["Date"].strftime("%Y-%m-%d"),
        "us10y":None if "US10Y_N" not in r or pd.isna(r.get("US10Y_N")) else round(float(r["US10Y_N"]),1),
        "vix":None if "VIX_N" not in r or pd.isna(r.get("VIX_N")) else round(float(r["VIX_N"]),1),
        "hy":None if "US_HY_SPREAD_N" not in r or pd.isna(r.get("US_HY_SPREAD_N")) else round(float(r["US_HY_SPREAD_N"]),1),
        "usdkrw":None if "USDKRW_N" not in r or pd.isna(r.get("USDKRW_N")) else round(float(r["USDKRW_N"]),1),
        "macro_tension":round(float(r["MACRO_TENSION"]),1),
    })

latest_raw={}
for k in KEYS:
    latest_raw[k]={
        "name":DISPLAY[k]["name"],
        "value":None if raw[k] is None else round(float(raw[k]),3),
        "unit":DISPLAY[k]["unit"],
        "source":"STEP3_CURRENT" if k in current else source["source"],
    }

payload={
    "meta":{
        "generated_at":datetime.now(KST).isoformat(timespec="seconds"),
        "source":"REPOSITORY_DATA_ONLY",
        "historical_source":source,
        "normalization":"percentile of STEP04 transformed macro signals; high = higher upward pressure",
        "display_points":len(points),
        "version":"STEP13_MACRO_v10_5",
        "external_network_required":False,
    },
    "current":{
        "score":macro_score,
        "state":state(macro_score),
        "date":datetime.now(KST).date().isoformat(),
        "raw":latest_raw,
        "normalized":norm,
    },
    "points":points,
}

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("Available series  :",available)
print("STEP3 current     :",current)
print("Macro Tension     :",macro_score,state(macro_score))
print("Display points    :",len(points))
print("External network  : NOT USED")
print("PASS: macro chart generated from repository data / git last-known-good history.")
