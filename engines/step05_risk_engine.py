from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config"
DATA = BASE / "data"
STEP04 = BASE / "outputs" / "step04"
STEP05 = BASE / "outputs" / "step05"
STEP05.mkdir(parents=True, exist_ok=True)

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def num(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))

def classify(score, bands):
    for lo, hi, label in bands:
        if lo <= score < hi:
            return label
    return "UNKNOWN"

def current_risk(indicator, value):
    if value is None:
        return 50.0

    refs = {
        "VIX": 10.0,
        "US_HY_SPREAD": 10.0,
        "FCI_TIGHTENING": 0.25,
        "US10Y": 10.0,
        "US_REAL10Y": 10.0,
        "USDKRW": 1.0,
    }

    ref = refs.get(indicator, 1.0)
    intensity = min(1.0, abs(value) / ref)
    direction = 1.0 if value > 0 else -1.0 if value < 0 else 0.0

    return clamp(
        50.0 + 50.0 * intensity * direction
    )

def avg_confidence(rows, indicator):
    vals = [
        num(r.get("Empirical_Confidence"))
        for r in rows
        if r.get("Indicator") == indicator
    ]
    vals = [v for v in vals if v is not None]

    return (
        sum(vals) / len(vals)
        if vals
        else 0.50
    )

def korean_comment(indicator, observed, adjusted):
    """
    간단한 Explainability용 한글 코멘트.
    예측 문구가 아니라 현재 위험점수가 왜 올라가거나 내려갔는지 설명한다.
    """

    direction = (
        "상승" if observed is not None and observed > 0
        else "하락" if observed is not None and observed < 0
        else "변화 없음"
    )

    impact = (
        "위험을 높였습니다"
        if adjusted > 52
        else "위험을 낮췄습니다"
        if adjusted < 48
        else "위험에 중립적으로 작용했습니다"
    )

    comments = {
        "VIX":
            (
                f"VIX가 {direction}했고, 현재 조정 위험점수 {adjusted:.2f}점 기준으로 "
                + ("시장 변동성 위험을 높였습니다." if adjusted > 52
                   else "시장 변동성 위험을 낮췄습니다." if adjusted < 48
                   else "시장 변동성 위험에 중립적으로 작용했습니다.")
            ),

        "US_HY_SPREAD":
            f"미국 하이일드 스프레드가 {direction}해 기업 신용위험과 자금조달 부담 변화를 반영하며 {impact}.",

        "FCI_TIGHTENING":
            f"금융여건지수가 {direction}해 금융시장 유동성과 자금조달 환경 변화를 반영하며 {impact}.",

        "US10Y":
            f"미국 10년물 금리가 {direction}해 할인율과 채권가격 부담 변화를 통해 포트폴리오 위험에 영향을 줬습니다.",

        "US_REAL10Y":
            f"미국 실질금리가 {direction}해 주식의 할인율과 금의 기회비용 변화가 위험점수에 반영됐습니다.",

        "USDKRW":
            f"원·달러 환율이 {direction}해 원화 약세·강세에 따른 해외자산 환산효과와 국내시장 부담이 반영됐습니다.",
    }

    return comments.get(
        indicator,
        f"{indicator}의 최근 변화와 장기 역사적 위치가 결합되어 현재 위험점수에 반영됐습니다."
    )

def main():

    risk_config = CONFIG / "risk_config.csv"
    asset_sens = CONFIG / "asset_risk_sensitivity.csv"
    state_bands = CONFIG / "risk_state_bands.csv"
    market_inputs = DATA / "step03_market_inputs.csv"
    percentiles = STEP04 / "percentile_results.csv"
    confidence = STEP04 / "empirical_confidence.csv"

    required = [
        risk_config,
        asset_sens,
        state_bands,
        market_inputs,
        percentiles,
        confidence,
    ]

    missing = [
        p for p in required
        if not p.exists()
    ]

    if missing:
        print(
            "STEP 05 실행 불가 - 필수 파일 누락"
        )

        for p in missing:
            print(" -", p)

        raise SystemExit(1)

    bands = [
        (
            num(r["Lower_Bound"]),
            num(r["Upper_Bound"]),
            r["Risk_State"],
        )
        for r in read_csv(state_bands)
    ]

    cfg = [
        r for r in read_csv(risk_config)
        if num(r.get("Enabled"), 0) == 1
    ]

    market = {
        r["Indicator"]:
        num(r.get("Observed_Change"))
        for r in read_csv(market_inputs)
    }

    hist = {
        r["Indicator"]:
        num(r.get("Historical_Percentile"))
        for r in read_csv(percentiles)
    }

    conf_rows = read_csv(confidence)

    total_weight = sum(
        num(r["Base_Weight"], 0.0)
        for r in cfg
    )

    if total_weight <= 0:
        raise ValueError(
            "활성 Risk Weight 합계가 0입니다."
        )

    details = []
    weighted_sum = 0.0

    for r in cfg:

        ind = r["Indicator"]
        weight = num(
            r["Base_Weight"],
            0.0
        )

        obs = market.get(ind)
        hp = hist.get(ind)

        cur = current_risk(
            ind,
            obs
        )

        hist_risk = (
            50.0
            if hp is None
            else clamp(hp)
        )

        conf = avg_confidence(
            conf_rows,
            ind
        )

        blended = (
            0.60 * cur
            + 0.40 * hist_risk
        )

        adjusted = (
            50.0
            + (blended - 50.0) * conf
        )

        norm_w = (
            weight / total_weight
        )

        contribution = (
            adjusted * norm_w
        )

        weighted_sum += (
            adjusted * weight
        )

        comment = korean_comment(
            ind,
            obs,
            adjusted
        )

        details.append({
            "Indicator": ind,
            "Risk_Block": r["Risk_Block"],
            "Observed_Change": (
                ""
                if obs is None
                else obs
            ),
            "Historical_Percentile": (
                ""
                if hp is None
                else hp
            ),
            "Empirical_Confidence":
                round(conf, 4),
            "Current_Risk":
                round(cur, 2),
            "Historical_Risk":
                round(hist_risk, 2),
            "Blended_Risk":
                round(blended, 2),
            "Adjusted_Risk":
                round(adjusted, 2),
            "Raw_Weight":
                round(weight, 4),
            "Normalized_Weight":
                round(norm_w, 4),
            "Weighted_Contribution":
                round(contribution, 4),
            "Signal_Status":
                (
                    "MISSING_CURRENT"
                    if obs is None
                    else (
                        "MISSING_HISTORY"
                        if hp is None
                        else "OK"
                    )
                ),
            "Korean_Comment": comment,
        })

    portfolio_risk = (
        weighted_sum / total_weight
    )

    sensitivities = {
        r["Asset"]:
        num(
            r["Risk_Sensitivity"],
            1.0
        )
        for r in read_csv(asset_sens)
    }

    scores = [{
        "Asset": "PORTFOLIO",
        "Risk_Score":
            round(portfolio_risk, 2),
        "Risk_State":
            classify(
                portfolio_risk,
                bands
            ),
        "Risk_Sensitivity":
            1.00,
    }]

    for asset, sens in sensitivities.items():

        score = clamp(
            50.0
            + (
                portfolio_risk - 50.0
            ) * sens
        )

        scores.append({
            "Asset": asset,
            "Risk_Score":
                round(score, 2),
            "Risk_State":
                classify(
                    score,
                    bands
                ),
            "Risk_Sensitivity":
                round(sens, 2),
        })

    ok_count = sum(
        1 for r in details
        if r["Signal_Status"] == "OK"
    )

    missing_current = sum(
        1 for r in details
        if r["Signal_Status"] == "MISSING_CURRENT"
    )

    missing_history = sum(
        1 for r in details
        if r["Signal_Status"] == "MISSING_HISTORY"
    )

    top3 = sorted(
        details,
        key=lambda x:
            x["Weighted_Contribution"],
        reverse=True
    )[:3]

    summary = [{
        "Portfolio_Risk_Score":
            round(portfolio_risk, 2),
        "Portfolio_Risk_State":
            classify(
                portfolio_risk,
                bands
            ),
        "Active_Indicators":
            len(details),
        "OK_Signals":
            ok_count,
        "Missing_Current":
            missing_current,
        "Missing_History":
            missing_history,

        "Top_Risk_Contributor_1":
            (
                top3[0]["Indicator"]
                if len(top3) > 0
                else ""
            ),

        "Top_Risk_Contributor_1_Comment":
            (
                top3[0]["Korean_Comment"]
                if len(top3) > 0
                else ""
            ),

        "Top_Risk_Contributor_2":
            (
                top3[1]["Indicator"]
                if len(top3) > 1
                else ""
            ),

        "Top_Risk_Contributor_2_Comment":
            (
                top3[1]["Korean_Comment"]
                if len(top3) > 1
                else ""
            ),

        "Top_Risk_Contributor_3":
            (
                top3[2]["Indicator"]
                if len(top3) > 2
                else ""
            ),

        "Top_Risk_Contributor_3_Comment":
            (
                top3[2]["Korean_Comment"]
                if len(top3) > 2
                else ""
            ),
    }]

    with (
        STEP05 / "risk_details.csv"
    ).open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.DictWriter(
            f,
            fieldnames=
                list(details[0].keys())
        )

        w.writeheader()
        w.writerows(details)

    with (
        STEP05 / "risk_scores.csv"
    ).open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.DictWriter(
            f,
            fieldnames=[
                "Asset",
                "Risk_Score",
                "Risk_State",
                "Risk_Sensitivity",
            ]
        )

        w.writeheader()
        w.writerows(scores)

    with (
        STEP05 / "risk_summary.csv"
    ).open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.DictWriter(
            f,
            fieldnames=
                list(summary[0].keys())
        )

        w.writeheader()
        w.writerows(summary)

    print("=" * 76)
    print(
        "STEP 05 - RISK ENGINE "
        "v3 EXPLAINABLE"
    )
    print("=" * 76)

    for r in scores:
        print(
            f"{r['Asset']:<18} "
            f"{r['Risk_Score']:>6.2f} "
            f"/ 100 "
            f"{r['Risk_State']}"
        )

    print()

    print(
        f"Active indicators : "
        f"{len(details)}"
    )

    print(
        f"OK signals        : "
        f"{ok_count}"
    )

    print(
        f"Missing current   : "
        f"{missing_current}"
    )

    print(
        f"Missing history   : "
        f"{missing_history}"
    )

    print()

    print(
        "Top risk contributors:"
    )

    for i, r in enumerate(
        top3,
        start=1
    ):
        print(
            f"{i}. "
            f"{r['Indicator']} "
            f"(Adjusted="
            f"{r['Adjusted_Risk']}, "
            f"Contribution="
            f"{r['Weighted_Contribution']})"
        )

        print(
            f"   → "
            f"{r['Korean_Comment']}"
        )

    print()

    print("Generated:")
    print(
        " - outputs/step05/"
        "risk_scores.csv"
    )
    print(
        " - outputs/step05/"
        "risk_details.csv"
    )
    print(
        " - outputs/step05/"
        "risk_summary.csv"
    )


if __name__ == "__main__":
    main()
