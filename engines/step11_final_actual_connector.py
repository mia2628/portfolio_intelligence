from pathlib import Path
import argparse
import csv
import io
import re
import shutil
import requests

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config"
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)

MAPPING = CONFIG / "step11_actual_mapping.csv"
UNAVAILABLE = CONFIG / "step11_unavailable_indicators.csv"

STEP3_INPUT = DATA / "step03_market_inputs.csv"
STEP3_BACKUP = DATA / "step03_market_inputs_template.csv"
STEP3_ACTUAL = DATA / "step03_market_inputs_actual.csv"

AUDIT = DATA / "step11_current_market_data.csv"
DIAG = DATA / "step11_data_diagnostics.csv"

# Primary: Nasdaq Data Link's public FRED mirror.
NASDAQ_URL = "https://data.nasdaq.com/api/v3/datasets/FRED/{sid}.csv?order=asc"

# Secondary: FRED graph endpoint.
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

MIN_ACTUAL_TO_APPLY = 10


def read_csv(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def fnum(v):
    try:
        if v is None:
            return None
        s=str(v).strip().replace(",","")
        if s in ("",".","NA","N/A","null","None"):
            return None
        return float(s)
    except:
        return None


def parse_series_csv(text, sid):
    rows=list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise RuntimeError("EMPTY_CSV")

    headers=list(rows[0].keys())

    date_col=next(
        (x for x in ["Date","DATE","observation_date","date"] if x in headers),
        headers[0]
    )

    candidates=[h for h in headers if h != date_col]
    if not candidates:
        raise RuntimeError("NO_VALUE_COLUMN")

    value_col=(
        sid if sid in headers
        else "Value" if "Value" in headers
        else "VALUE" if "VALUE" in headers
        else candidates[0]
    )

    series=[]
    for r in rows:
        d=r.get(date_col)
        v=fnum(r.get(value_col))
        if d and v is not None:
            series.append((d,v))

    if len(series)<10:
        raise RuntimeError(f"TOO_FEW_OBSERVATIONS:{len(series)}")

    series.sort(key=lambda x:x[0])
    return series


def request_text(url):
    r=requests.get(
        url,
        timeout=45,
        headers={
            "User-Agent":"Mozilla/5.0 portfolio-intelligence/step11-final",
            "Accept":"text/csv,text/plain,*/*"
        }
    )
    r.raise_for_status()
    return r.text


def fetch_series(sid):
    errors=[]

    # Source 1: Nasdaq Data Link
    try:
        text=request_text(NASDAQ_URL.format(sid=sid))
        return parse_series_csv(text,sid), "NASDAQ_FRED"
    except Exception as e:
        errors.append("NASDAQ="+repr(e))

    # Source 2: FRED graph
    try:
        text=request_text(FRED_URL.format(sid=sid))
        return parse_series_csv(text,sid), "FRED_GRAPH"
    except Exception as e:
        errors.append("FRED="+repr(e))

    raise RuntimeError(" | ".join(errors))


def transform(series, mode, lookback):
    lag=max(1,int(lookback))
    if len(series)<=lag:
        raise RuntimeError("INSUFFICIENT_LOOKBACK")

    latest_date,latest=series[-1]
    ref_date,ref=series[-1-lag]

    if mode=="LEVEL_CHANGE":
        change=latest-ref
    elif mode=="PCT_CHANGE":
        if ref==0:
            raise RuntimeError("ZERO_REFERENCE")
        change=(latest/ref-1.0)*100.0
    else:
        raise RuntimeError("UNKNOWN_TRANSFORM:"+mode)

    return {
        "Latest_Date":latest_date,
        "Latest_Value":latest,
        "Reference_Date":ref_date,
        "Reference_Value":ref,
        "Observed_Change":change,
    }


def write_csv(path, rows, fields):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def build_all_rows(actual_by_indicator):
    output=[]

    # Stable ordering: all mapped actual indicators first.
    for m in read_csv(MAPPING):
        ind=m["Indicator"]
        if ind in actual_by_indicator:
            output.append({
                "Indicator":ind,
                "Observed_Change":round(actual_by_indicator[ind]["Observed_Change"],8)
            })
        else:
            # Failed live collection must be neutral, never old test data.
            output.append({"Indicator":ind,"Observed_Change":0.0})

    # Known unavailable indicators are explicitly neutral.
    for u in read_csv(UNAVAILABLE):
        output.append({"Indicator":u["Indicator"],"Observed_Change":0.0})

    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument(
        "--apply",
        action="store_true",
        help="검증 통과 시 실제 2컬럼 파일을 data/step03_market_inputs.csv에 적용"
    )
    args=ap.parse_args()

    actual={}
    audit=[]
    diag=[]

    for m in read_csv(MAPPING):
        ind=m["Indicator"]
        sid=m["Series_ID"]
        mode=m["Transform"]
        lag=int(float(m["Lookback_Obs"]))

        try:
            series,source=fetch_series(sid)
            x=transform(series,mode,lag)

            actual[ind]=x

            audit.append({
                "Indicator":ind,
                "Status":"ACTUAL",
                "Source":source,
                "Series_ID":sid,
                "Transform":mode,
                "Output_Unit":m["Output_Unit"],
                "Observation_Date":x["Latest_Date"],
                "Current_Value":round(x["Latest_Value"],8),
                "Reference_Date":x["Reference_Date"],
                "Reference_Value":round(x["Reference_Value"],8),
                "Observed_Change":round(x["Observed_Change"],8),
            })

            diag.append({
                "Indicator":ind,
                "Status":"ACTUAL",
                "Message":"OK via "+source
            })

        except Exception as e:
            audit.append({
                "Indicator":ind,
                "Status":"ERROR",
                "Source":"",
                "Series_ID":sid,
                "Transform":mode,
                "Output_Unit":m["Output_Unit"],
                "Observation_Date":"",
                "Current_Value":"",
                "Reference_Date":"",
                "Reference_Value":"",
                "Observed_Change":"",
            })

            diag.append({
                "Indicator":ind,
                "Status":"ERROR",
                "Message":str(e)[:1000]
            })

    for u in read_csv(UNAVAILABLE):
        diag.append({
            "Indicator":u["Indicator"],
            "Status":"UNAVAILABLE",
            "Message":u["Reason"]
        })

    actual_count=sum(1 for d in diag if d["Status"]=="ACTUAL")
    error_count=sum(1 for d in diag if d["Status"]=="ERROR")
    unavailable_count=sum(1 for d in diag if d["Status"]=="UNAVAILABLE")

    all_step3=build_all_rows(actual)

    write_csv(
        AUDIT,audit,
        [
            "Indicator","Status","Source","Series_ID","Transform","Output_Unit",
            "Observation_Date","Current_Value","Reference_Date","Reference_Value",
            "Observed_Change"
        ]
    )

    write_csv(
        DIAG,diag,
        ["Indicator","Status","Message"]
    )

    # Canonical STEP3 file is EXACTLY the schema already proven by the user's engine.
    write_csv(
        STEP3_ACTUAL,
        all_step3,
        ["Indicator","Observed_Change"]
    )

    print("="*78)
    print("STEP 11 - FINAL ACTUAL DATA CONNECTION")
    print("="*78)
    print(f"ACTUAL      : {actual_count}")
    print(f"ERROR       : {error_count}")
    print(f"UNAVAILABLE : {unavailable_count}")
    print()

    for a in audit:
        if a["Status"]=="ACTUAL":
            print(
                f"{a['Indicator']:<22} "
                f"Observed_Change={a['Observed_Change']:>12} "
                f"| {a['Output_Unit']:<5} "
                f"| {a['Source']:<12} "
                f"| {a['Observation_Date']}"
            )

    if error_count:
        print()
        print("ERROR DETAILS")
        for d in diag:
            if d["Status"]=="ERROR":
                print(f"- {d['Indicator']}: {d['Message']}")

    print()
    print("STEP3 canonical output")
    print("Columns : Indicator | Observed_Change")
    print(f"Rows    : {len(all_step3)}")
    print(f"File    : {STEP3_ACTUAL}")

    if args.apply:
        if actual_count < MIN_ACTUAL_TO_APPLY:
            print()
            print("[STOP] 실제 수집 성공 지표가 충분하지 않습니다.")
            print(
                f"ACTUAL {actual_count} < minimum {MIN_ACTUAL_TO_APPLY}. "
                "기존 STEP3 입력은 변경하지 않습니다."
            )
            raise SystemExit(2)

        if STEP3_INPUT.exists() and not STEP3_BACKUP.exists():
            shutil.copy2(STEP3_INPUT, STEP3_BACKUP)
            print()
            print(f"Backup  : {STEP3_BACKUP}")

        shutil.copy2(STEP3_ACTUAL,STEP3_INPUT)

        print()
        print("[APPLIED]")
        print("data/step03_market_inputs.csv를 실제 데이터 버전으로 교체했습니다.")
        print("기존 테스트 입력은 step03_market_inputs_template.csv에 보존됩니다.")
    else:
        print()
        print("[VALIDATION ONLY]")
        print("기존 data/step03_market_inputs.csv는 변경하지 않았습니다.")
        print("검증 후 --apply 또는 GitHub Actions에서 적용합니다.")


if __name__=="__main__":
    main()
