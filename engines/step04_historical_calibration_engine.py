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
DIAGNOSTIC_OUT = OUTPUT_DIR / "step04_diagnostics.csv"

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
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    denx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    deny = math.sqrt(sum((b - my) ** 2 for b in ys))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def ols_beta_r2(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None, None, len(pairs)

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    mx, my = mean(xs), mean(ys)
    varx = sum((a - mx) ** 2 for a in xs)

    if varx == 0:
        return None, None, len(pairs)

    beta = sum((a - mx) * (b - my) for a, b in pairs) / varx
    alpha = my - beta * mx

    yhat = [alpha + beta * a for a in xs]
    sst = sum((b - my) ** 2 for b in ys)
    sse = sum((b - h) ** 2 for b, h in zip(ys, yhat))

    r2 = None if sst == 0 else 1 - sse / sst
    return beta, r2, len(pairs)


def direction_consistency(x, y):
    pairs = [
        (a, b)
        for a, b in zip(x, y)
        if a not in (None, 0) and b not in (None, 0)
    ]
    if not pairs:
        return None

    same = sum(
        1
        for a, b in pairs
        if (a > 0 and b > 0) or (a < 0 and b < 0)
    )
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


def resolve_indicator_column(indicator_row, data_columns):
    """
    Prefer mapping CSV column.
    If it does not exist, fall back to the Indicator name itself.
    This fixes differences between the original STEP4 template
    (e.g. US_CORE_CPI_SURPRISE) and the current collector
    (e.g. US_CORE_CPI).
    """
    requested = indicator_row.get("Historical_Column", "")
    indicator = indicator_row.get("Indicator", "")

    if requested in data_columns:
        return requested, "MAPPED"

    if indicator in data_columns:
        return indicator, "FALLBACK_TO_INDICATOR"

    # Compatibility aliases for collector v2
    aliases = {
        "US_CPI": "US_CPI",
        "US_CORE_CPI": "US_CORE_CPI",
        "US_CORE_PCE": "US_CORE_PCE",
        "KR_CPI": "KR_CPI",
        "US_ISM_MFG": "US_ISM_MFG",
        "US_UNEMPLOYMENT": "US_UNEMPLOYMENT",
        "US_INITIAL_CLAIMS": "US_INITIAL_CLAIMS",
        "US_NFP_SURPRISE": "US_NFP_SURPRISE",
        "KR_EXPORT_GROWTH": "KR_EXPORT_GROWTH",
        "KR_SEMI_EXPORT_GROWTH": "KR_SEMI_EXPORT_GROWTH",
    }

    alias = aliases.get(indicator)
    if alias in data_columns:
        return alias, "ALIAS"

    return None, "MISSING"


def resolve_asset_column(asset_row, data_columns):
    requested = asset_row.get("Historical_Return_Column", "")
    if requested in data_columns:
        return requested
    return None


def write_rows(path, fieldnames, rows):
    """
    Always create the CSV, even when there are zero data rows.
    This makes STEP4 completion easy to verify and prevents
    silent missing-file behavior.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        if rows:
            w.writerows(rows)


def main():
    if not HIST_DATA.exists():
        raise FileNotFoundError(
            f"historical_data.csv가 없습니다: {HIST_DATA}"
        )

    cfg = read_config()
    min_obs = int(float(cfg.get("Min_Observations", 36)))
    rolling_months = int(float(cfg.get("Rolling_Window_Months", 36)))
    k = int(float(cfg.get("Similar_Episode_Count", 5)))
    forward_months = int(float(cfg.get("Forward_Return_Months", 3)))

    data = read_csv(HIST_DATA)
    if not data:
        raise ValueError("historical_data.csv가 비어 있습니다.")

    data_columns = set(data[0].keys())
    indicator_map = read_csv(INDICATOR_MAP)
    asset_map = read_csv(ASSET_MAP)

    diagnostics = []

    # Resolve indicator columns against actual historical_data.csv
    resolved_indicators = []
    for ind in indicator_map:
        resolved_col, status = resolve_indicator_column(ind, data_columns)
        nonnull = 0

        if resolved_col:
            nonnull = sum(
                1
                for r in data
                if safe_float(r.get(resolved_col)) is not None
            )

        diagnostics.append({
            "Type": "INDICATOR",
            "Name": ind["Indicator"],
            "Requested_Column": ind.get("Historical_Column", ""),
            "Resolved_Column": resolved_col or "",
            "Status": status,
            "NonNull_Count": nonnull,
        })

        if resolved_col and nonnull >= 3:
            item = dict(ind)
            item["_Resolved_Column"] = resolved_col
            resolved_indicators.append(item)

    # Resolve asset return columns
    resolved_assets = []
    for asset in asset_map:
        col = resolve_asset_column(asset, data_columns)
        nonnull = 0

        if col:
            nonnull = sum(
                1
                for r in data
                if safe_float(r.get(col)) is not None
            )

        diagnostics.append({
            "Type": "ASSET",
            "Name": asset["Asset"],
            "Requested_Column": asset.get("Historical_Return_Column", ""),
            "Resolved_Column": col or "",
            "Status": "OK" if col else "MISSING",
            "NonNull_Count": nonnull,
        })

        if col and nonnull >= 3:
            item = dict(asset)
            item["_Resolved_Column"] = col
            resolved_assets.append(item)

    regression_rows = []
    rolling_rows = []
    confidence_rows = []
    percentile_rows = []
    similar_rows = []

    # 1. Full-sample regressions + rolling betas
    for ind in resolved_indicators:
        indicator = ind["Indicator"]
        col = ind["_Resolved_Column"]
        x = [safe_float(r.get(col)) for r in data]

        # Percentile result is independent of asset returns
        current = next((v for v in reversed(x) if v is not None), None)
        pr = percentile_rank(x, current)
        zs = zscore(current, x)

        percentile_rows.append({
            "Indicator": indicator,
            "Historical_Column": col,
            "Latest_Value": "" if current is None else current,
            "Historical_Percentile": "" if pr is None else round(pr, 2),
            "Z_Score": "" if zs is None else round(zs, 4),
            "N": sum(v is not None for v in x),
        })

        for asset in resolved_assets:
            asset_name = asset["Asset"]
            ret_col = asset["_Resolved_Column"]
            y = [safe_float(r.get(ret_col)) for r in data]

            beta, r2, n = ols_beta_r2(x, y)
            corr = pearson(x, y)
            consistency = direction_consistency(x, y)

            regression_rows.append({
                "Indicator": indicator,
                "Asset": asset_name,
                "Indicator_Column": col,
                "Return_Column": ret_col,
                "Beta": "" if beta is None else round(beta, 8),
                "R2": "" if r2 is None else round(r2, 6),
                "Correlation": "" if corr is None else round(corr, 6),
                "Direction_Consistency": (
                    "" if consistency is None else round(consistency, 6)
                ),
                "N": n,
            })

            # Rolling beta: require enough paired observations inside each window
            if len(data) >= rolling_months:
                for end in range(rolling_months, len(data) + 1):
                    subx = x[end - rolling_months:end]
                    suby = y[end - rolling_months:end]
                    rb, rr2, rn = ols_beta_r2(subx, suby)

                    if rb is None or rn < max(12, rolling_months // 2):
                        continue

                    rolling_rows.append({
                        "End_Date": data[end - 1]["Date"],
                        "Indicator": indicator,
                        "Asset": asset_name,
                        "Rolling_Beta": round(rb, 8),
                        "Rolling_R2": (
                            "" if rr2 is None else round(rr2, 6)
                        ),
                        "N": rn,
                    })

            # Empirical confidence
            if (
                n >= min_obs
                and beta is not None
                and r2 is not None
                and consistency is not None
            ):
                direction_strength = abs(consistency - 0.5) * 2.0
                r2_strength = max(0.0, min(1.0, r2))

                # Rolling sign stability
                rb_vals = [
                    r["Rolling_Beta"]
                    for r in rolling_rows
                    if r["Indicator"] == indicator
                    and r["Asset"] == asset_name
                ]

                if rb_vals:
                    pos = sum(1 for b in rb_vals if float(b) > 0)
                    neg = sum(1 for b in rb_vals if float(b) < 0)
                    stability = max(pos, neg) / len(rb_vals)
                else:
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
                "N": n,
            })

    # 2. Similar historical episodes
    usable = []
    for ind in resolved_indicators:
        col = ind["_Resolved_Column"]
        vals = [safe_float(r.get(col)) for r in data]
        latest = next((v for v in reversed(vals) if v is not None), None)

        if latest is None:
            continue

        if sum(v is not None for v in vals) < min_obs:
            continue

        usable.append((ind["Indicator"], col, vals, latest))

    distances = []

    if usable:
        # Determine latest row that has at least one usable indicator
        latest_data_idx = None
        for idx in range(len(data) - 1, -1, -1):
            if any(safe_float(data[idx].get(col)) is not None for _, col, _, _ in usable):
                latest_data_idx = idx
                break

        if latest_data_idx is not None:
            for idx, row in enumerate(data):
                if idx == latest_data_idx:
                    continue

                comps = []

                for _, col, vals, latest in usable:
                    v = safe_float(row.get(col))
                    if v is None:
                        continue

                    z_now = zscore(latest, vals)
                    z_then = zscore(v, vals)

                    if z_now is None or z_then is None:
                        continue

                    comps.append((z_now - z_then) ** 2)

                # Require at least 3 comparable indicators
                if len(comps) >= 3:
                    dist = math.sqrt(sum(comps) / len(comps))
                    distances.append((dist, idx, len(comps)))

    distances.sort(key=lambda x: x[0])

    for rank, (dist, idx, compared_count) in enumerate(distances[:k], start=1):
        item = {
            "Rank": rank,
            "Date": data[idx]["Date"],
            "Distance": round(dist, 6),
            "Compared_Indicators": compared_count,
        }

        for asset in resolved_assets:
            asset_name = asset["Asset"]
            col = asset["_Resolved_Column"]
            vals = []

            for j in range(
                idx + 1,
                min(idx + 1 + forward_months, len(data))
            ):
                v = safe_float(data[j].get(col))
                if v is not None:
                    vals.append(v)

            item[f"{asset_name}_Forward_Avg_Return"] = (
                "" if not vals else round(mean(vals), 6)
            )

        similar_rows.append(item)

    # 3. Always write all expected STEP4 outputs
    write_rows(
        REGRESSION_OUT,
        [
            "Indicator","Asset","Indicator_Column","Return_Column",
            "Beta","R2","Correlation","Direction_Consistency","N"
        ],
        regression_rows,
    )

    write_rows(
        ROLLING_OUT,
        ["End_Date","Indicator","Asset","Rolling_Beta","Rolling_R2","N"],
        rolling_rows,
    )

    write_rows(
        PERCENTILE_OUT,
        [
            "Indicator","Historical_Column","Latest_Value",
            "Historical_Percentile","Z_Score","N"
        ],
        percentile_rows,
    )

    similar_fields = [
        "Rank","Date","Distance","Compared_Indicators"
    ] + [
        f"{a['Asset']}_Forward_Avg_Return"
        for a in resolved_assets
    ]

    write_rows(
        SIMILAR_OUT,
        similar_fields,
        similar_rows,
    )

    write_rows(
        CONFIDENCE_OUT,
        ["Indicator","Asset","Empirical_Confidence","N"],
        confidence_rows,
    )

    write_rows(
        DIAGNOSTIC_OUT,
        [
            "Type","Name","Requested_Column","Resolved_Column",
            "Status","NonNull_Count"
        ],
        diagnostics,
    )

    print("=" * 84)
    print("STEP 04 - Historical Calibration Engine v2")
    print("=" * 84)
    print(f"Historical rows       : {len(data)}")
    print(f"Resolved indicators   : {len(resolved_indicators)}")
    print(f"Resolved assets       : {len(resolved_assets)}")
    print(f"Regression rows       : {len(regression_rows)}")
    print(f"Rolling beta rows     : {len(rolling_rows)}")
    print(f"Percentile rows       : {len(percentile_rows)}")
    print(f"Similar episodes      : {len(similar_rows)}")
    print(f"Confidence rows       : {len(confidence_rows)}")
    print()
    print("Generated files:")
    print(" - regression_results.csv")
    print(" - rolling_beta.csv")
    print(" - percentile_results.csv")
    print(" - similar_episodes.csv")
    print(" - empirical_confidence.csv")
    print(" - step04_diagnostics.csv")
    print("=" * 84)

    if len(rolling_rows) == 0:
        print(
            "[WARN] rolling_beta.csv는 생성됐지만 데이터 행이 0개입니다. "
            "step04_diagnostics.csv에서 자산 수익률 NonNull_Count를 확인하세요."
        )

    if len(similar_rows) == 0:
        print(
            "[WARN] similar_episodes.csv는 생성됐지만 데이터 행이 0개입니다. "
            "비교 가능한 지표가 3개 미만인지 diagnostics를 확인하세요."
        )


if __name__ == "__main__":
    main()
