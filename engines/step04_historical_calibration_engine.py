from pathlib import Path
import csv
import math
from statistics import mean, pstdev

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "historical"
OUTPUT_DIR = BASE_DIR / "outputs" / "step04"

HIST_CONFIG = CONFIG_DIR / "historical_config.csv"
INDICATOR_MAP = CONFIG_DIR / "historical_indicator_mapping.csv"
ASSET_MAP = CONFIG_DIR / "historical_asset_mapping.csv"
HIST_DATA = DATA_DIR / "historical_data.csv"

REGRESSION_OUT = OUTPUT_DIR / "regression_results.csv"
ROLLING_OUT = OUTPUT_DIR / "rolling_beta.csv"
PERCENTILE_OUT = OUTPUT_DIR / "percentile_results.csv"
SIMILAR_OUT = OUTPUT_DIR / "similar_episodes.csv"
CONFIDENCE_OUT = OUTPUT_DIR / "empirical_confidence.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_config():
    return {r["Parameter"]: r["Value"] for r in read_csv(HIST_CONFIG)}


def safe_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def pearson(x, y):
    pairs = [(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    num = sum((a-mx)*(b-my) for a,b in pairs)
    denx = math.sqrt(sum((a-mx)**2 for a in xs))
    deny = math.sqrt(sum((b-my)**2 for b in ys))
    if denx == 0 or deny == 0:
        return None
    return num/(denx*deny)


def ols_beta_r2(x, y):
    pairs = [(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None, None, len(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    varx = sum((a-mx)**2 for a in xs)
    if varx == 0:
        return None, None, len(pairs)
    beta = sum((a-mx)*(b-my) for a,b in pairs) / varx
    alpha = my - beta*mx
    yhat = [alpha + beta*a for a in xs]
    sst = sum((b-my)**2 for b in ys)
    sse = sum((b-h)**2 for b,h in zip(ys,yhat))
    r2 = None if sst == 0 else 1 - sse/sst
    return beta, r2, len(pairs)


def direction_consistency(x, y):
    pairs = [(a,b) for a,b in zip(x,y) if a not in (None,0) and b not in (None,0)]
    if not pairs:
        return None
    same = sum(1 for a,b in pairs if (a > 0 and b > 0) or (a < 0 and b < 0))
    return same / len(pairs)


def percentile_rank(series, value):
    vals = sorted(v for v in series if v is not None)
    if not vals or value is None:
        return None
    count = sum(1 for v in vals if v <= value)
    return 100.0 * count / len(vals)


def zscore(value, series):
    vals = [v for v in series if v is not None]
    if len(vals) < 2 or value is None:
        return None
    sd = pstdev(vals)
    if sd == 0:
        return 0.0
    return (value - mean(vals)) / sd


def main():
    if not HIST_DATA.exists():
        print("="*78)
        print("STEP 04 - Historical Calibration Engine")
        print("="*78)
        print("historical_data.csv가 아직 없습니다.")
        print("data/historical/historical_data_template.csv를 복사하여")
        print("historical_data.csv로 이름을 바꾼 뒤 과거 데이터를 채워주세요.")
        print("실제 API 자동수집은 STEP 11에서 연결합니다.")
        return

    cfg = read_config()
    min_obs = int(float(cfg["Min_Observations"]))
    rolling_months = int(float(cfg["Rolling_Window_Months"]))

    data = read_csv(HIST_DATA)
    indicator_map = read_csv(INDICATOR_MAP)
    asset_map = read_csv(ASSET_MAP)

    regression_rows = []
    confidence_rows = []
    rolling_rows = []

    # Full-sample regression/correlation for every indicator-asset pair
    for ind in indicator_map:
        indicator = ind["Indicator"]
        col = ind["Historical_Column"]
        x = [safe_float(r.get(col)) for r in data]

        for asset in asset_map:
            asset_name = asset["Asset"]
            ret_col = asset["Historical_Return_Column"]
            y = [safe_float(r.get(ret_col)) for r in data]

            beta, r2, n = ols_beta_r2(x, y)
            corr = pearson(x, y)
            consistency = direction_consistency(x, y)

            regression_rows.append({
                "Indicator": indicator,
                "Asset": asset_name,
                "Beta": "" if beta is None else round(beta, 8),
                "R2": "" if r2 is None else round(r2, 6),
                "Correlation": "" if corr is None else round(corr, 6),
                "Direction_Consistency": "" if consistency is None else round(consistency, 6),
                "N": n,
            })

            # Simple empirical confidence v1
            if n >= min_obs and beta is not None and r2 is not None and consistency is not None:
                direction_strength = abs(consistency - 0.5) * 2.0
                r2_strength = max(0.0, min(1.0, r2))
                # Rolling stability placeholder will be refined below
                stability = 0.5
                conf = (
                    0.50 * direction_strength
                    + 0.25 * r2_strength
                    + 0.25 * stability
                )
                conf = max(0.0, min(1.0, conf))
            else:
                conf = 0.0

            confidence_rows.append({
                "Indicator": indicator,
                "Asset": asset_name,
                "Empirical_Confidence": round(conf, 4),
            })

            # Rolling beta
            if len(data) >= rolling_months:
                for end in range(rolling_months, len(data)+1):
                    subx = x[end-rolling_months:end]
                    suby = y[end-rolling_months:end]
                    rb, rr2, rn = ols_beta_r2(subx, suby)
                    if rb is None:
                        continue
                    rolling_rows.append({
                        "End_Date": data[end-1]["Date"],
                        "Indicator": indicator,
                        "Asset": asset_name,
                        "Rolling_Beta": round(rb, 8),
                        "Rolling_R2": "" if rr2 is None else round(rr2, 6),
                        "N": rn,
                    })

    # Current percentile uses latest non-null historical observation for each indicator
    percentile_rows = []
    for ind in indicator_map:
        indicator = ind["Indicator"]
        col = ind["Historical_Column"]
        vals = [safe_float(r.get(col)) for r in data]
        current = next((v for v in reversed(vals) if v is not None), None)
        pr = percentile_rank(vals, current)
        zs = zscore(current, vals)
        percentile_rows.append({
            "Indicator": indicator,
            "Latest_Value": "" if current is None else current,
            "Historical_Percentile": "" if pr is None else round(pr, 2),
            "Z_Score": "" if zs is None else round(zs, 4),
        })

    # Similar historical episodes based on standardized indicator distance.
    usable_inds = []
    for ind in indicator_map:
        col = ind["Historical_Column"]
        vals = [safe_float(r.get(col)) for r in data]
        latest = next((v for v in reversed(vals) if v is not None), None)
        if latest is None:
            continue
        usable_inds.append((ind["Indicator"], col, vals, latest))

    distances = []
    if usable_inds:
        for idx, row in enumerate(data[:-1]):  # exclude latest row itself
            comps = []
            for indicator, col, vals, latest in usable_inds:
                v = safe_float(row.get(col))
                if v is None:
                    continue
                z_now = zscore(latest, vals)
                z_then = zscore(v, vals)
                if z_now is None or z_then is None:
                    continue
                comps.append((z_now-z_then)**2)
            if comps:
                dist = math.sqrt(sum(comps)/len(comps))
                distances.append((dist, idx))

    distances.sort(key=lambda x: x[0])
    k = int(float(cfg["Similar_Episode_Count"]))
    forward_months = int(float(cfg["Forward_Return_Months"]))
    similar_rows = []

    for rank, (dist, idx) in enumerate(distances[:k], start=1):
        item = {
            "Rank": rank,
            "Date": data[idx]["Date"],
            "Distance": round(dist, 6),
        }

        for asset in asset_map:
            asset_name = asset["Asset"]
            col = asset["Historical_Return_Column"]
            vals = []
            for j in range(idx+1, min(idx+1+forward_months, len(data))):
                v = safe_float(data[j].get(col))
                if v is not None:
                    vals.append(v)
            item[f"{asset_name}_Forward_Avg_Return"] = (
                "" if not vals else round(mean(vals), 6)
            )
        similar_rows.append(item)

    # Write outputs
    def write_dicts(path, rows):
        if not rows:
            return
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_dicts(REGRESSION_OUT, regression_rows)
    write_dicts(ROLLING_OUT, rolling_rows)
    write_dicts(PERCENTILE_OUT, percentile_rows)
    write_dicts(SIMILAR_OUT, similar_rows)
    write_dicts(CONFIDENCE_OUT, confidence_rows)

    print("="*78)
    print("STEP 04 - Historical Calibration Engine")
    print("="*78)
    print(f"Historical rows     : {len(data)}")
    print(f"Regression results  : {len(regression_rows)}")
    print(f"Rolling beta rows   : {len(rolling_rows)}")
    print(f"Similar episodes    : {len(similar_rows)}")
    print("Outputs saved to outputs/step04/")
    print("="*78)


if __name__ == "__main__":
    main()
