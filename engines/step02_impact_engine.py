from pathlib import Path
import csv
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"

IMPACT_MATRIX_FILE = CONFIG_DIR / "impact_matrix.csv"
INDICATOR_CONFIG_FILE = CONFIG_DIR / "indicator_config.csv"

ASSETS = {
    "Domestic_Equity_Score": "국내주식",
    "Foreign_Equity_Score": "해외주식",
    "Bond_Score": "채권",
    "Gold_Score": "금",
}

# STEP 2 테스트용 시장방향.
# +1 = 상승/예상상회
# -1 = 하락/예상하회
#  0 = 중립
TEST_MARKET_SIGNALS = {
    "US10Y": 1,
    "US_REAL10Y": -1,
    "USDKRW": 1,
    "VIX": 1,
    "US_CORE_CPI": 1,
    "KR_EXPORT_GROWTH": -1,
}


def read_csv_as_dict(path, key):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row[key]: row for row in rows}


def load_files():
    matrix = read_csv_as_dict(IMPACT_MATRIX_FILE, "Indicator")
    indicator_config = read_csv_as_dict(INDICATOR_CONFIG_FILE, "Indicator")

    missing_cfg = set(matrix) - set(indicator_config)
    if missing_cfg:
        raise ValueError(
            "indicator_config.csv에 없는 지표: "
            + ", ".join(sorted(missing_cfg))
        )

    # Factor_Group consistency check
    mismatched = []
    for indicator in matrix:
        if matrix[indicator]["Factor_Group"] != indicator_config[indicator]["Factor_Group"]:
            mismatched.append(indicator)

    if mismatched:
        raise ValueError(
            "두 CSV의 Factor_Group이 일치하지 않는 지표: "
            + ", ".join(sorted(mismatched))
        )

    return matrix, indicator_config


def direction_label(signal):
    if signal > 0:
        return "상승/예상상회"
    if signal < 0:
        return "하락/예상하회"
    return "중립"


def calculate_directional_impact(matrix, market_signals):
    asset_totals = defaultdict(float)
    factor_asset_totals = defaultdict(lambda: defaultdict(float))
    details = []

    for indicator, signal in market_signals.items():
        if indicator not in matrix:
            raise KeyError(f"impact_matrix.csv에 {indicator}가 없습니다.")

        if signal not in (-1, 0, 1):
            raise ValueError(
                f"{indicator} 테스트 신호는 -1, 0, +1만 사용해야 합니다."
            )

        row = matrix[indicator]
        factor = row["Factor_Group"]
        importance = float(row["Importance"])

        detail = {
            "Indicator": indicator,
            "Indicator_KR": row["Indicator_KR"],
            "Factor_Group": factor,
            "Signal": signal,
            "Direction": direction_label(signal),
            "Importance": importance,
            "Asset_Impacts": {},
        }

        for score_col, asset_name in ASSETS.items():
            base_score = float(row[score_col])

            # STEP 2는 방향만 검증.
            # 상승/예상상회(+1) -> 기본점수
            # 하락/예상하회(-1) -> 부호 반전
            directional_score = base_score * signal

            detail["Asset_Impacts"][asset_name] = directional_score
            asset_totals[asset_name] += directional_score
            factor_asset_totals[factor][asset_name] += directional_score

        details.append(detail)

    return details, dict(asset_totals), factor_asset_totals


def print_results(details, totals, factor_totals):
    print()
    print("=" * 82)
    print("PORTFOLIO INTELLIGENCE SYSTEM - STEP 02 REVISED")
    print("Portfolio Impact Matrix Direction Validation")
    print("=" * 82)

    for item in details:
        print()
        print(
            f"[{item['Indicator']}] {item['Indicator_KR']} "
            f"→ {item['Direction']} | "
            f"Factor={item['Factor_Group']} | "
            f"중요도 {item['Importance']:.0f}/5"
        )

        for asset_name, score in item["Asset_Impacts"].items():
            print(f"  {asset_name:<8}: {score:+.1f}")

    print()
    print("-" * 82)
    print("Factor별 단순 방향점수 (STEP 3 중복계산 방지용 참고)")
    print("-" * 82)

    factor_order = [
        "RATE", "INFLATION", "FX", "RISK", "GROWTH", "GOLD_SPECIFIC"
    ]

    for factor in factor_order:
        if factor not in factor_totals:
            continue

        print(f"[{factor}]")
        for asset_name in ["국내주식", "해외주식", "채권", "금"]:
            score = factor_totals[factor].get(asset_name, 0.0)
            print(f"  {asset_name:<8}: {score:+.1f}")

    print()
    print("-" * 82)
    print("전체 단순 방향점수 합계")
    print("-" * 82)

    for asset_name in ["국내주식", "해외주식", "채권", "금"]:
        print(f"{asset_name:<8}: {totals.get(asset_name, 0.0):+.1f}")

    print()
    print("※ 이 값은 최종 Portfolio Score가 아닙니다.")
    print("※ STEP 2는 경제적 방향(+/-) 검증만 담당합니다.")
    print("※ STEP 3에서 변화크기(Shock)와 Factor 집계를 반영합니다.")
    print("※ 따라서 STEP 3부터는 모든 개별 지표 점수를 단순합산하지 않습니다.")
    print("=" * 82)


def main():
    matrix, indicator_config = load_files()

    details, totals, factor_totals = calculate_directional_impact(
        matrix,
        TEST_MARKET_SIGNALS,
    )

    print_results(details, totals, factor_totals)


if __name__ == "__main__":
    main()
