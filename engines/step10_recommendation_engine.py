from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
PORTFOLIO_INVESTED = BASE / "outputs" / "portfolio" / "portfolio_invested_summary.csv"
STEP05 = BASE / "outputs" / "step05"
STEP06 = BASE / "outputs" / "step06"
STEP07 = BASE / "outputs" / "step07"
STEP08 = BASE / "outputs" / "step08"
STEP09 = BASE / "outputs" / "step09"
STEP10 = BASE / "outputs" / "step10"
STEP10.mkdir(parents=True, exist_ok=True)

RISK_SUMMARY = STEP05 / "risk_summary.csv"
OPPORTUNITY = STEP06 / "opportunity_scores.csv"
HEALTH_SUMMARY = STEP07 / "portfolio_health_summary.csv"
ALLOC_SUMMARY = STEP08 / "monthly_allocation_summary.csv"
ALLOC_DETAIL = STEP08 / "monthly_allocation.csv"
REBAL_DECISION = STEP09 / "rebalancing_decision.csv"
REBAL_ACTIONS = STEP09 / "rebalancing_actions.csv"

OUT_SUMMARY = STEP10 / "recommendation_summary.csv"
OUT_DETAIL = STEP10 / "recommendation_detail.csv"

ASSET_KR = {
    "Domestic_Equity":"국내주식",
    "Foreign_Equity":"해외주식",
    "Bond":"채권",
    "Gold":"금",
}


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


def first_row(path):
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"{path} 가 비어 있습니다.")
    return rows[0]


def load_risk():
    r = first_row(RISK_SUMMARY)
    return {
        "score": num(r.get("Risk_Score"), num(r.get("Portfolio_Risk_Score"), 50.0)),
        "state": r.get("Risk_State", r.get("State", "UNKNOWN"))
    }


def load_opportunity():
    rows = read_csv(OPPORTUNITY)
    out = []
    for r in rows:
        a = r.get("Asset")
        s = num(r.get("Opportunity_Score"), 50.0)
        out.append((a, s))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def load_health():
    r = first_row(HEALTH_SUMMARY)
    return {
        "score": num(r.get("Portfolio_Health_Score"), 50.0),
        "state": r.get("Health_State", "UNKNOWN"),
        "comment": r.get("Korean_Comment", "")
    }


def load_allocation():
    summary = first_row(ALLOC_SUMMARY)
    details = read_csv(ALLOC_DETAIL)
    return summary, details


def load_rebalancing():
    decision = first_row(REBAL_DECISION)
    actions = read_csv(REBAL_ACTIONS)
    return decision, actions


def risk_message(score, state):
    if score >= 70:
        return f"현재 시장 위험도는 {score:.1f}점으로 높습니다. 신규투자는 평소보다 보수적으로 접근합니다."
    if score >= 55:
        return f"현재 시장 위험도는 {score:.1f}점으로 다소 높습니다. 분할매수와 자산분산을 우선합니다."
    if score >= 45:
        return f"현재 시장 위험도는 {score:.1f}점으로 중립권입니다. 특정 방향에 과도하게 베팅할 환경은 아닙니다."
    return f"현재 시장 위험도는 {score:.1f}점으로 비교적 낮습니다. 다만 기본 분산원칙은 유지합니다."


def opportunity_message(opps):
    if not opps:
        return "Opportunity 데이터가 없습니다."
    best_asset, best_score = opps[0]
    kr = ASSET_KR.get(best_asset, best_asset)
    return f"현재 신규자금 관점에서 가장 높은 상대매력도는 {kr} {best_score:.1f}점입니다."


def health_message(score, state):
    if score >= 80:
        return f"포트폴리오 건강도는 {score:.1f}점으로 매우 양호합니다."
    if score >= 65:
        return f"포트폴리오 건강도는 {score:.1f}점으로 전반적으로 양호합니다."
    if score >= 50:
        return f"포트폴리오 건강도는 {score:.1f}점으로 보통 수준이며 일부 구조 점검이 필요합니다."
    return f"포트폴리오 건강도는 {score:.1f}점으로 주의가 필요합니다."


def allocation_message(details):
    if not details:
        return "이번 달 신규자금 배분 결과가 없습니다."

    rows = sorted(
        details,
        key=lambda r: num(r.get("Allocation_Share_Pct"), 0.0),
        reverse=True
    )

    top = rows[:3]
    parts = []
    for r in top:
        asset = ASSET_KR.get(r.get("Asset"), r.get("Asset"))
        pct = num(r.get("Allocation_Share_Pct"), 0.0)
        krw = num(r.get("Allocation_KRW"))
        if krw is not None:
            parts.append(f"{asset} {pct:.1f}%({krw:,.0f}원)")
        else:
            parts.append(f"{asset} {pct:.1f}%")

    return "이번 달 신규자금은 " + ", ".join(parts) + " 순으로 배분하는 안이 제시되었습니다."


def action_message(decision, actions):
    situation = decision.get("Situation_Message", "").strip()
    if situation:
        return situation

    d = decision.get("Decision", "")
    if d == "NEW_MONEY_CORRECTION":
        return "기존 자산은 매도하지 않고 신규자금으로 정책범위 이탈을 우선 보정합니다."
    if d == "REBALANCE_REQUIRED":
        return "정책범위 이탈이 커서 기존 자산 일부의 매도·재배분을 검토할 단계입니다."
    if d == "REVIEW_ONLY":
        return "정기점검 시점이지만 강제 리밸런싱은 필요하지 않습니다."
    if d == "HOLD":
        return "현재는 별도 조치 없이 기존 구조를 유지해도 됩니다."
    return decision.get("Reason", "현재 상황을 점검합니다.")


def final_recommendation(risk, opps, health, allocation_details, decision):
    best_asset, best_score = opps[0] if opps else ("", 50.0)
    best_kr = ASSET_KR.get(best_asset, best_asset)

    d = decision.get("Decision", "")

    if d == "REBALANCE_REQUIRED":
        return (
            "현재는 기존 자산을 그대로 유지하는 단계가 아니라, "
            "정책범위를 벗어난 자산을 중심으로 일부 매도·재배분을 검토할 시점입니다."
        )

    if d == "NEW_MONEY_CORRECTION":
        return (
            f"현재 포트폴리오 전체 구조는 유지하되, 신규자금으로 정책이탈 자산을 먼저 보정하고 "
            f"남는 자금은 STEP6 상대매력도에 따라 {best_kr} 등 유연자산에 분산 배분하는 것이 적절합니다."
        )

    if health["score"] < 50:
        return (
            "현재는 시장예측보다 포트폴리오 구조 개선이 우선입니다. "
            "신규자금은 집중도를 낮추고 분산효과를 높이는 방향으로 사용합니다."
        )

    if risk["score"] >= 70:
        return (
            "시장 위험도가 높으므로 기존 보유자산의 급격한 변경은 피하고, "
            "신규자금은 분할매수와 방어적 배분을 우선합니다."
        )

    return (
        f"현재는 강제 리밸런싱보다 기존 구조 유지가 우선이며, "
        f"신규자금은 {best_kr} 등 상대매력도가 높은 자산에 완만하게 기울여 배분합니다."
    )


def main():
    required = [
        RISK_SUMMARY,
        OPPORTUNITY,
        HEALTH_SUMMARY,
        ALLOC_SUMMARY,
        ALLOC_DETAIL,
        REBAL_DECISION,
        REBAL_ACTIONS,
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        print("STEP 10 실행 불가 - 필수 파일 누락")
        for p in missing:
            print(" -", p)
        raise SystemExit(1)

    risk = load_risk()
    opps = load_opportunity()
    health = load_health()
    alloc_summary, alloc_details = load_allocation()
    decision, actions = load_rebalancing()

    msg_risk = risk_message(risk["score"], risk["state"])
    msg_opp = opportunity_message(opps)
    msg_health = health_message(health["score"], health["state"])
    msg_alloc = allocation_message(alloc_details)
    msg_action = action_message(decision, actions)
    final = final_recommendation(risk, opps, health, alloc_details, decision)

    summary = [{
        "Risk_Score": round(risk["score"],2),
        "Risk_State": risk["state"],
        "Best_Opportunity_Asset": opps[0][0] if opps else "",
        "Best_Opportunity_Score": round(opps[0][1],2) if opps else "",
        "Portfolio_Health_Score": round(health["score"],2),
        "Portfolio_Health_State": health["state"],
        "Rebalancing_Decision": decision.get("Decision",""),
        "Action_Level": decision.get("Action_Level",""),
        "Situation_Message": msg_action,
        "Final_Recommendation": final,
    }]

    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    detail_rows = [
        {"Section":"시장위험","Message":msg_risk},
        {"Section":"신규자금 기회","Message":msg_opp},
        {"Section":"포트폴리오 건강","Message":msg_health},
        {"Section":"이번 달 배분","Message":msg_alloc},
        {"Section":"현재상황","Message":msg_action},
        {"Section":"최종권고","Message":final},
    ]

    with OUT_DETAIL.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        w.writeheader()
        w.writerows(detail_rows)

    print("="*78)
    print("STEP 10 - RECOMMENDATION / EXPLAINABILITY ENGINE")
    print("="*78)
    print()
    if PORTFOLIO_INVESTED.exists():
        pr=read_csv(PORTFOLIO_INVESTED)
        print("[현재 포트폴리오 - 투자원금 기준]")
        for r in sorted(pr,key=lambda x:float(x.get("Portfolio_Weight_Pct",0)),reverse=True):
            print(
                f"→ {r.get('Asset_KR',r.get('Asset'))}: "
                f"{float(r.get('Invested_Amount_KRW',0)):,.0f}원 "
                f"({float(r.get('Portfolio_Weight_Pct',0)):.2f}%)"
            )
        print()

    print("[현재 시장]")
    print("→", msg_risk)
    print()
    print("[신규자금 기회]")
    print("→", msg_opp)
    print()
    print("[포트폴리오 건강]")
    print("→", msg_health)
    print()
    print("[이번 달 배분]")
    print("→", msg_alloc)
    print()
    print("[현재상황]")
    print("→", msg_action)
    print()
    print("[최종 권고]")
    print("→", final)
    print()
    print("Generated:")
    print(" - outputs/step10/recommendation_summary.csv")
    print(" - outputs/step10/recommendation_detail.csv")


if __name__ == "__main__":
    main()
