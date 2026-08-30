from pathlib import Path
import io, json, math, re
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
    "US10Y":[
        "US10Y","US_10Y","US10Y_YIELD","US_10Y_YIELD","DGS10",
        "US10YTREASURY","US10YTREASURYYIELD","UST10Y","UST_10Y"
    ],
    "VIX":[
        "VIX","VIXCLS","CBOEVIX","CBOE_VIX","VIX_INDEX"
    ],
    "HY_SPREAD":[
        "US_HY_SPREAD","USHYSPREAD","HY_SPREAD","HYSPREAD",
        "BAMLH0A0HYM2","HIGH_YIELD_SPREAD","US_HIGH_YIELD_SPREAD"
    ],
    "USDKRW":[
        "USDKRW","USD_KRW","DEXKOUS","USD/KRW","KRWUSD",
        "USDKRW_EXCHANGE_RATE","USD_KRW_EXCHANGE_RATE"
    ],
}

DATE_CANDIDATES=[
    "date","DATE","Date","observation_date","timestamp","datetime",
    "asof_date","base_date","trade_date"
]
INDICATOR_CANDIDATES=[
    "indicator","Indicator","indicator_id","indicator_code","series",
    "series_id","metric","Metric","name","Name","symbol","ticker"
]
VALUE_CANDIDATES=[
    "value","Value","VALUE","current_value","close","Close",
    "price","rate","score","observation"
]

LOOKBACK_DAYS=900
ROLLING_OBS=252
MIN_OBS=60
DISPLAY_DAYS=120
PLOT_POINTS=90

def norm_name(v):
    return re.sub(r"[^A-Z0-9]","",str(v).upper())

NORM_ALIASES={k:{norm_name(x) for x in vals} for k,vals in ALIASES.items()}

def identify_indicator(label):
    n=norm_name(label)
    for key,aliases in NORM_ALIASES.items():
        if n in aliases:
            return key
    # conservative fuzzy fallbacks
    if "VIX" in n:
        return "VIX"
    if ("HY" in n or "HIGHYIELD" in n) and "SPREAD" in n:
        return "HY_SPREAD"
    if "USDKRW" in n or ("USD" in n and "KRW" in n):
        return "USDKRW"
    if ("10Y" in n or "10YEAR" in n) and ("US" in n or "TREAS" in n or "UST" in n):
        return "US10Y"
    return None

def clean_series(df,date_col,value_col):
    x=df[[date_col,value_col]].copy()
    x.columns=["date","value"]
    x["date"]=pd.to_datetime(x["date"],errors="coerce")
    x["value"]=pd.to_numeric(x["value"],errors="coerce")
    x=x.dropna(subset=["date","value"]).sort_values("date")
    cutoff=pd.Timestamp(datetime.now(KST).date()-timedelta(days=LOOKBACK_DAYS))
    x=x[x["date"]>=cutoff]
    x=x.drop_duplicates(subset=["date"],keep="last")
    return x

def discover_local_sources():
    """
    Search data/**/*.csv and support:
    A) WIDE: date + one column per indicator
    B) LONG: date + indicator/series/name + value
    """
    found={}
    diagnostics=[]

    data_root=BASE/"data"
    if not data_root.exists():
        return found, diagnostics

    # Prefer historical-looking files, but inspect all reasonably sized CSVs.
    files=sorted(data_root.rglob("*.csv"), key=lambda p:(
        0 if "histor" in p.name.lower() else 1,
        len(str(p))
    ))

    for p in files:
        try:
            if p.stat().st_size > 50_000_000:
                continue
            df=pd.read_csv(p)
            if df.empty:
                continue
        except Exception as e:
            diagnostics.append(f"SKIP {p}: {e}")
            continue

        cols=list(df.columns)
        date_col=next((c for c in DATE_CANDIDATES if c in cols),None)
        if not date_col:
            # Last-resort: find a column containing 'date'
            date_col=next((c for c in cols if "date" in str(c).lower()),None)
        if not date_col:
            continue

        # ---------- WIDE format ----------
        for c in cols:
            if c==date_col:
                continue
            key=identify_indicator(c)
            if key and key not in found:
                try:
                    x=clean_series(df,date_col,c)
                    if len(x)>=MIN_OBS:
                        found[key]=(x,f"{p} [WIDE:{c}]")
                except Exception:
                    pass

        # ---------- LONG format ----------
        ind_col=next((c for c in INDICATOR_CANDIDATES if c in cols),None)
        val_col=next((c for c in VALUE_CANDIDATES if c in cols and c!=date_col),None)

        # Infer common long-format columns if exact candidate names differ.
        if not ind_col:
            for c in cols:
                if c==date_col:
                    continue
                sample=df[c].dropna().astype(str).head(100)
                if sample.empty:
                    continue
                matches=sum(identify_indicator(v) is not None for v in sample)
                if matches>=1:
                    ind_col=c
                    break

        if ind_col and not val_col:
            numeric_candidates=[]
            for c in cols:
                if c in {date_col,ind_col}:
                    continue
                conv=pd.to_numeric(df[c],errors="coerce")
                ratio=conv.notna().mean()
                if ratio>=0.5:
                    numeric_candidates.append((ratio,c))
            if numeric_candidates:
                val_col=max(numeric_candidates)[1]

        if ind_col and val_col:
            for key in SERIES:
                if key in found:
                    continue
                mask=df[ind_col].astype(str).map(identify_indicator)==key
                if not mask.any():
                    continue
                try:
                    x=clean_series(df.loc[mask],[date_col][0],val_col)
                    if len(x)>=MIN_OBS:
                        found[key]=(x,f"{p} [LONG:{ind_col}={key}, value={val_col}]")
                except Exception:
                    pass

        if len(found)==4:
            break

    return found, diagnostics

def fetch_fred_once(key):
    sid=SERIES[key]["fred_id"]
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    r=requests.get(url,timeout=(5,12),headers={"User-Agent":"portfolio-intelligence/1.0"})
    r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    date_col="DATE" if "DATE" in df.columns else df.columns[0]
    val_col=next(c for c in df.columns if c!=date_col)
    x=clean_series(df,date_col,val_col)
    if len(x)<MIN_OBS:
        raise RuntimeError(f"{key}: too few observations {len(x)}")
    return key,x

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

def previous_is_valid():
    if not OUT.exists():
        return False
    try:
        d=json.loads(OUT.read_text(encoding="utf-8"))
        return bool(d.get("points")) and d.get("current",{}).get("score") is not None
    except Exception:
        return False

frames={}
source_used={}
errors={}

local,diagnostics=discover_local_sources()
for key,(df,src) in local.items():
    frames[key]=df
    source_used[key]=f"LOCAL:{src}"

print("="*86)
print("STEP13 MACRO LOCAL DISCOVERY v10.4")
print("="*86)
print("Detected local macro series:",sorted(frames))
for k,v in source_used.items():
    print(f"{k:16}: {v}")

missing=[k for k in SERIES if k not in frames]

# Only missing series use short parallel FRED fallback.
if missing:
    print("Missing after local autodetect -> short parallel FRED:",missing)
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
    if previous_is_valid():
        print("PASS_WITH_STALE_DATA: previous valid macro_risk.json retained.")
        raise SystemExit(0)
    raise SystemExit(
        "FAIL: fewer than 3 macro sources after local auto-detection and FRED fallback. "
        f"Detected={sorted(frames)}, errors={errors}"
    )

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
    if previous_is_valid():
        print("PASS_WITH_STALE_DATA: no fresh normalized row; previous macro chart retained.")
        raise SystemExit(0)
    raise SystemExit("FAIL: no normalized macro tension row")

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
        "source":"LOCAL_AUTODETECT_WITH_FRED_FALLBACK",
        "source_used":source_used,
        "normalization":"rolling percentile over up to 252 valid observations; high = higher tension",
        "display_points":len(points),
        "version":"STEP13_MACRO_v10_4",
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
print("STEP13 MACRO RISK v10.4")
print("="*86)
print("Source mix       :",source_used)
print("Latest date      :",payload["current"]["date"])
print("Macro Tension    :",payload["current"]["score"],payload["current"]["state"])
print("Display points   :",len(points))
if errors:
    print("Source warnings  :",errors)
print("PASS: macro risk composite generated.")
