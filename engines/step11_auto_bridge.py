from pathlib import Path
import argparse, csv, shutil

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
HISTORICAL = DATA / "historical" / "historical_data.csv"

MAPPING = BASE / "config" / "step11_historical_bridge_mapping.csv"
STEP3_INPUT = DATA / "step03_market_inputs.csv"
STEP3_BACKUP = DATA / "step03_market_inputs_template.csv"
STEP3_ACTUAL = DATA / "step03_market_inputs_actual.csv"

OUT_CURRENT = DATA / "step11_current_market_data.csv"
OUT_DIAG = DATA / "step11_data_diagnostics.csv"

MIN_ACTUAL = 10

ALL_INDICATORS = [
    "US10Y","US2Y","US_REAL10Y","US_10Y2Y_SPREAD",
    "KR3Y","KR10Y","FED_HIKE_EXPECTATION","BOK_HIKE_EXPECTATION",
    "US_CPI","US_CORE_CPI","US_CORE_PCE","US_BREAKEVEN_10Y","KR_CPI",
    "USDKRW","DXY","VIX","MOVE","US_HY_SPREAD","FCI_TIGHTENING",
    "GEOPOLITICAL_RISK","US_ISM_MFG","US_UNEMPLOYMENT","US_INITIAL_CLAIMS",
    "US_NFP_SURPRISE","KR_EXPORT_GROWTH","KR_SEMI_EXPORT_GROWTH",
    "CB_GOLD_NET_BUYING"
]

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def to_float(v):
    try:
        s = str(v).strip().replace(",", "")
        if s in ("", ".", "NA", "N/A", "None", "null"):
            return None
        return float(s)
    except:
        return None

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def find_column(headers, candidates):
    for c in candidates:
        if c in headers:
            return c
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None

def extract_series(rows, column):
    date_col = next(
        (c for c in ["Date","DATE","date","Month","MONTH","observation_date"] if c in rows[0]),
        None
    )
    out = []
    for i, r in enumerate(rows):
        v = to_float(r.get(column))
        if v is None:
            continue
        d = r.get(date_col) if date_col else str(i)
        out.append((d, v))
    return out

def observed_change(series, mode, lag):
    lag = max(1, int(lag))
    if len(series) <= lag:
        raise ValueError("insufficient observations")
    latest_date, latest = series[-1]
    ref_date, ref = series[-1-lag]

    if mode == "LEVEL_CHANGE":
        change = latest - ref
    elif mode == "PCT_CHANGE":
        if ref == 0:
            raise ValueError("zero reference")
        change = (latest / ref - 1.0) * 100.0
    else:
        raise ValueError("unknown transform")

    return latest_date, latest, ref_date, ref, change

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not HISTORICAL.exists():
        print("[STOP] historical_data.csv가 없습니다.")
        print("STEP4 collector가 먼저 정상 실행되어야 합니다.")
        raise SystemExit(1)

    rows = read_csv(HISTORICAL)
    if not rows:
        raise SystemExit("[STOP] historical_data.csv가 비어 있습니다.")

    headers = list(rows[0].keys())
    actual = {}
    audit = []
    diag = []

    for m in read_csv(MAPPING):
        indicator = m["Indicator"]
        candidates = [x.strip() for x in m["Candidate_Columns"].split(";") if x.strip()]
        col = find_column(headers, candidates)

        if not col:
            diag.append({
                "Indicator": indicator,
                "Status": "UNAVAILABLE",
                "Source_Column": "",
                "Message": "column not found"
            })
            continue

        try:
            s = extract_series(rows, col)
            d1, v1, d0, v0, ch = observed_change(
                s, m["Transform"], int(float(m["Lookback_Obs"]))
            )
            actual[indicator] = ch
            audit.append({
                "Indicator": indicator,
                "Status": "ACTUAL",
                "Source": "STEP4_HISTORICAL",
                "Source_Column": col,
                "Observation_Date": d1,
                "Current_Value": round(v1, 8),
                "Reference_Date": d0,
                "Reference_Value": round(v0, 8),
                "Observed_Change": round(ch, 8),
                "Output_Unit": m["Output_Unit"]
            })
            diag.append({
                "Indicator": indicator,
                "Status": "ACTUAL",
                "Source_Column": col,
                "Message": "OK"
            })
        except Exception as e:
            diag.append({
                "Indicator": indicator,
                "Status": "ERROR",
                "Source_Column": col,
                "Message": str(e)[:500]
            })

    step3_rows = [
        {"Indicator": ind, "Observed_Change": round(actual.get(ind, 0.0), 8)}
        for ind in ALL_INDICATORS
    ]

    write_csv(
        OUT_CURRENT, audit,
        ["Indicator","Status","Source","Source_Column","Observation_Date",
         "Current_Value","Reference_Date","Reference_Value","Observed_Change","Output_Unit"]
    )
    write_csv(
        OUT_DIAG, diag,
        ["Indicator","Status","Source_Column","Message"]
    )
    write_csv(
        STEP3_ACTUAL, step3_rows,
        ["Indicator","Observed_Change"]
    )

    ac = sum(d["Status"] == "ACTUAL" for d in diag)
    er = sum(d["Status"] == "ERROR" for d in diag)
    un = len(ALL_INDICATORS) - ac - er

    print("="*78)
    print("STEP 11 - AUTOMATIC STEP4 -> STEP3 BRIDGE")
    print("="*78)
    print(f"Historical rows : {len(rows)}")
    print(f"ACTUAL          : {ac}")
    print(f"ERROR           : {er}")
    print(f"UNAVAILABLE     : {un}")
    print()

    for a in audit:
        print(
            f"{a['Indicator']:<22} "
            f"{a['Observed_Change']:>12} {a['Output_Unit']:<5} "
            f"| {a['Source_Column']:<22} | {a['Observation_Date']}"
        )

    if args.apply:
        if ac < MIN_ACTUAL:
            print()
            print(f"[STOP] ACTUAL {ac} < minimum {MIN_ACTUAL}")
            print("기존 STEP3 입력파일은 변경하지 않습니다.")
            raise SystemExit(2)

        if STEP3_INPUT.exists() and not STEP3_BACKUP.exists():
            shutil.copy2(STEP3_INPUT, STEP3_BACKUP)
            print(f"Backup : {STEP3_BACKUP}")

        shutil.copy2(STEP3_ACTUAL, STEP3_INPUT)
        print()
        print("[APPLIED]")
        print("data/step03_market_inputs.csv가 실제 최신 데이터로 갱신되었습니다.")
    else:
        print("[VALIDATION ONLY]")

if __name__ == "__main__":
    main()
