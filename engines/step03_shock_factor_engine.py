from pathlib import Path
import csv
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "data"

IMPACT_MATRIX_FILE = CONFIG_DIR / "impact_matrix.csv"
INDICATOR_CONFIG_FILE = CONFIG_DIR / "indicator_config.csv"
FACTOR_CONFIG_FILE = CONFIG_DIR / "factor_config.csv"
MARKET_INPUT_FILE = DATA_DIR / "step03_market_inputs.csv"
OUTPUT_FILE = OUTPUT_DIR / "step03_results.csv"

ASSETS = {
    "Domestic_Equity_Score": "국내주식",
    "Foreign_Equity_Score": "해외주식",
    "Bond_Score": "채권",
    "Gold_Score": "금",
}

SHOCK_MULTIPLIERS = {
    "NORMAL": 0.0,
    "MILD": 0.5,
    "STRONG": 1.0,
    "EXTREME": 1.5,
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_csv_dict(path, key):
    return {row[key]: row for row in read_csv(path)}


def classify_shock(value, mild, strong, extreme):
    x = abs(float(value))

    if x < mild:
        return "NORMAL"
    if x < strong:
        return "MILD"
    if x < extreme:
        return "STRONG"
    return "EXTREME"


def clamp(value, low, high):
    return max(low, min(high, value))


def load_all():
    matrix = read_csv_dict(IMPACT_MATRIX_FILE, "Indicator")
    indicator_cfg = read_csv_dict(INDICATOR_CONFIG_FILE, "Indicator")
    factor_cfg = read_csv_dict(FACTOR_CONFIG_FILE, "Factor_Group")
    market_inputs = read_csv(MARKET_INPUT_FILE)

    for indicator in matrix:
        if indicator not in indicator_cfg:
            raise ValueError(
                f"indicator_config.csv에 {indicator}가 없습니다."
            )

    return matrix, indicator_cfg, factor_cfg, market_inputs


def calculate_indicator_impacts(matrix, indicator_cfg, market_inputs):
    details = []

    for item in market_inputs:
        indicator = item["Indicator"]
        observed = float(item["Observed_Change"])

        if indicator not in matrix:
            raise KeyError(
                f"impact_matrix.csv에 {indicator}가 없습니다."
            )

        if indicator not in indicator_cfg:
            raise KeyError(
                f"indicator_config.csv에 {indicator}가 없습니다."
            )

        m = matrix[indicator]
        cfg = indicator_cfg[indicator]

        mild = float(cfg["Mild_Threshold"])
        strong = float(cfg["Strong_Threshold"])
        extreme = float(cfg["Extreme_Threshold"])

        shock_class = classify_shock(
            observed, mild, strong, extreme
        )
        shock_multiplier = SHOCK_MULTIPLIERS[shock_class]

        if observed > 0:
            direction = 1.0
        elif observed < 0:
            direction = -1.0
        else:
            direction = 0.0

        importance = float(m["Importance"])
        importance_weight = importance / 5.0

        impacts = {}

        for score_col, asset_name in ASSETS.items():
            base_score = float(m[score_col])

            raw_impact = (
                base_score
                * direction
                * shock_multiplier
                * importance_weight
            )

            impacts[asset_name] = raw_impact

        details.append({
            "Indicator": indicator,
            "Indicator_KR": m["Indicator_KR"],
            "Factor_Group": m["Factor_Group"],
            "Observed_Change": observed,
            "Shock_Class": shock_class,
            "Shock_Multiplier": shock_multiplier,
            "Importance": importance,
            "Impacts": impacts,
        })

    return details


def aggregate_factors(details, factor_cfg):
    grouped = defaultdict(list)

    for d in details:
        grouped[d["Factor_Group"]].append(d)

    factor_scores = {}

    for factor, items in grouped.items():
        cfg = factor_cfg[factor]
        factor_weight = float(cfg["Factor_Weight"])
        min_cap = float(cfg["Min_Cap"])
        max_cap = float(cfg["Max_Cap"])

        factor_scores[factor] = {}

        for asset_name in ASSETS.values():
            weighted_sum = 0.0
            total_weight = 0.0

            for d in items:
                indicator_weight = d["Importance"] / 5.0
                weighted_sum += (
                    d["Impacts"][asset_name] * indicator_weight
                )
                total_weight += indicator_weight

            if total_weight == 0:
                avg = 0.0
            else:
                avg = weighted_sum / total_weight

            weighted_factor = avg * factor_weight
            capped = clamp(
                weighted_factor,
                min_cap,
                max_cap
            )

            factor_scores[factor][asset_name] = capped

    return factor_scores


def aggregate_asset_environment(factor_scores):
    totals = defaultdict(float)
    counts = defaultdict(int)

    for factor, scores in factor_scores.items():
        for asset_name, score in scores.items():
            totals[asset_name] += score
            counts[asset_name] += 1

    final = {}

    for asset_name in ASSETS.values():
        if counts[asset_name] == 0:
            final[asset_name] = 0.0
        else:
            # Average across active factors so the score remains stable.
            final[asset_name] = (
                totals[asset_name] / counts[asset_name]
            )

    return final


def save_results(details, factor_scores, final_scores):
    rows = []

    for d in details:
        for asset_name, score in d["Impacts"].items():
            rows.append({
                "Level": "INDICATOR",
                "Name": d["Indicator"],
                "Factor_Group": d["Factor_Group"],
                "Asset": asset_name,
                "Score": round(score, 4),
                "Shock_Class": d["Shock_Class"],
                "Observed_Change": d["Observed_Change"],
            })

    for factor, scores in factor_scores.items():
        for asset_name, score in scores.items():
            rows.append({
                "Level": "FACTOR",
                "Name": factor,
                "Factor_Group": factor,
                "Asset": asset_name,
                "Score": round(score, 4),
                "Shock_Class": "",
                "Observed_Change": "",
            })

    for asset_name, score in final_scores.items():
        rows.append({
            "Level": "ASSET_ENVIRONMENT",
            "Name": "FINAL",
            "Factor_Group": "",
            "Asset": asset_name,
            "Score": round(score, 4),
            "Shock_Class": "",
            "Observed_Change": "",
        })

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Level","Name","Factor_Group","Asset",
                "Score","Shock_Class","Observed_Change"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)


def print_results(details, factor_scores, final_scores):
    print()
    print("=" * 86)
    print("PORTFOLIO INTELLIGENCE SYSTEM - STEP 03")
    print("Shock & Factor Engine")
    print("=" * 86)

    for d in details:
        print()
        print(
            f"[{d['Indicator']}] {d['Indicator_KR']} | "
            f"변화={d['Observed_Change']:+.3f} | "
            f"Shock={d['Shock_Class']} | "
            f"Multiplier={d['Shock_Multiplier']:.1f} | "
            f"Factor={d['Factor_Group']}"
        )

        for asset_name, score in d["Impacts"].items():
            print(f"  {asset_name:<8}: {score:+.2f}")

    print()
    print("-" * 86)
    print("FACTOR SCORES")
    print("-" * 86)

    for factor, scores in factor_scores.items():
        print(f"[{factor}]")
        for asset_name, score in scores.items():
            print(f"  {asset_name:<8}: {score:+.2f}")

    print()
    print("-" * 86)
    print("ASSET MACRO ENVIRONMENT")
    print("-" * 86)

    for asset_name, score in final_scores.items():
        print(f"{asset_name:<8}: {score:+.2f}")

    print()
    print(f"상세 결과 저장: {OUTPUT_FILE.name}")
    print("=" * 86)


def main():
    matrix, indicator_cfg, factor_cfg, market_inputs = load_all()

    details = calculate_indicator_impacts(
        matrix,
        indicator_cfg,
        market_inputs,
    )

    factor_scores = aggregate_factors(
        details,
        factor_cfg,
    )

    final_scores = aggregate_asset_environment(
        factor_scores
    )

    save_results(
        details,
        factor_scores,
        final_scores,
    )

    print_results(
        details,
        factor_scores,
        final_scores,
    )


if __name__ == "__main__":
    main()
