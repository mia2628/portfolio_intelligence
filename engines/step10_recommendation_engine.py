from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
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
    out.sort(key=lambda x:x[1], reverse=True)
    return out

def load_health():
    r = first_row(HEALTH_SUMMARY)
    return {
        "score": num(r.get("Portfolio_Health_Score"), 50.0),
        "state": r.get("Health_State", "UNKNOWN")
    }

def load_allocation():
    return first_row(ALLOC_SUMMARY), read_csv(ALLOC_DETAIL)

def load_rebalancing():
    return first_row(REBAL_DECISION), read_csv(REBAL_ACTIONS)

def risk_message(score):
    if score >= 70:
        return f"현재 시장 위험도는 {score:.1f}점으로 높습니다. 신규투자는 평소보다 보수적으로 접근합니다."
    if score >= 55:
        return f"현재 시장 위험도는 {score:.1f}점으로 다소 높습니다. 분할매수와 자산분산을 우선합니다."
    if score >= 45:
        return f"현재 시장 위험도는 {score:.1f}점으로 중립권입니다. 특정 방향에 과도하게 베팅할 환경은 아닙니다."
    return f"현재 시장 위험도는 {score:.1f}점으로 비교적 낮습니다. 기본 분산원칙은 유지합니다."

def opportunity_message(opps):
    if not opps:
        return "Opportunity 데이터가 없습니다."
    a,s = opps[0]
    return f"현재 신규자금 관점에서 가장 높은 상대매력도는 {ASSET_KR.get(a,a)} {s:.1f}점입니다."

def health_message(score):
    if score >= 80:
        return f"포트폴리오 건강도는 {score:.1f}점으로 매우 양호합니다."
    if score >= 65:
        return f"포트폴리오 건강도는 {score:.1f}점으로 전반적으로 양호합니다."
    if score >= 50:
        return f"포트폴리오 건강도는 {score:.1f}점으로 보통 수준이며 일부 구조 점검이 필요합니다."
    return f"포트폴리오 건강도는 {score:.1f}점으로 주의가 필요합니다."

def allocation_message(details):
    positive = [
        r for r in details
        if num(r.get("Allocation_KRW"),0.0) > 0
        or num(r.get("Allocation_Share_Pct"),0.0) > 0
    ]
    if not positive:
        return "이번 달 신규자금 배분 결과가 없습니다."

    positive.sort(
        key=lambda r:num(r.get("Allocation_Share_Pct"),0.0),
        reverse=True
    )

    parts=[]
    for r in positive:
        a=ASSET_KR.get(r.get("Asset"),r.get("Asset"))
        pct=num(r.get("Allocation_Share_Pct"),0.0)
        krw=num(r.get("Allocation_KRW"))
        parts.append(
            f"{a} {pct:.1f}%({krw:,.0f}원)"
            if krw is not None else
            f"{a} {pct:.1f}%"
        )

    return "이번 달 신규자금은 " + ", ".join(parts) + "로 배분하는 안이 제시되었습니다."

def build_current_situation(decision):
    d=decision.get("Decision","")
    gold=num(decision.get("Gold_Weight_Pct"))
    rng=decision.get("Gold_Range","")
    health=num(decision.get("Portfolio_Health"),50.0)
    due=str(decision.get("Calendar_Due","")).lower()=="true"

    when = "정기점검일이 도래했으며" if due else "아직 정기점검일 전이지만"

    if d=="NEW_MONEY_CORRECTION":
        return (
            f"{when}, 금 비중이 {gold:.2f}%로 정책범위 {rng}보다 낮습니다. "
            f"포트폴리오 건강도는 {health:.1f}점으로 비교적 양호하므로 "
            "기존자산 매도보다 신규자금으로 금을 우선 보충하는 단계입니다."
        )
    if d=="REBALANCE_REQUIRED":
        return (
            f"{when}, 금 비중이 {gold:.2f}%로 정책범위 {rng}를 초과했습니다. "
            "신규자금만으로 보정하기보다 일부 매도·재배분까지 검토할 단계입니다."
        )
    if d=="REVIEW_ONLY":
        return (
            f"6개월 정기점검일이 도래했지만 금 비중은 정책범위 {rng} 안이고 "
            "구조적 이상도 크지 않아 강제 리밸런싱은 필요하지 않습니다."
        )
    if d=="HOLD":
        return (
            f"정기점검일 전이며 금 비중도 정책범위 {rng} 안에 있습니다. "
            "현재는 별도 리밸런싱 없이 구조를 유지하는 단계입니다."
        )
    return decision.get("Reason","현재 포트폴리오 상태를 점검합니다.")

def final_recommendation(risk, opps, health, alloc_summary, alloc_details, decision):
    d=decision.get("Decision","")
    contribution=num(alloc_summary.get("Monthly_Contribution_KRW"),0.0)
    policy_gold=num(alloc_summary.get("Gold_Policy_First_KRW"),0.0)

    positive = [
        r for r in alloc_details
        if num(r.get("Allocation_KRW"),0.0) > 0
    ]
    gold_alloc = next(
        (num(r.get("Allocation_KRW"),0.0) for r in alloc_details if r.get("Asset")=="Gold"),
        0.0
    )

    all_to_gold = contribution > 0 and gold_alloc >= contribution - 1

    if d=="REBALANCE_REQUIRED":
        return (
            "현재는 신규자금 배분만으로 해결하기보다 정책범위를 초과한 자산의 "
            "일부 매도·재배분을 검토하는 것이 우선입니다."
        )

    if d=="NEW_MONEY_CORRECTION":
        if all_to_gold:
            return (
                f"현재는 금 비중이 정책 하한에 크게 못 미치므로 이번 달 신규자금 "
                f"{contribution:,.0f}원은 전액 금 보충에 사용하는 것이 우선입니다. "
                "기존 보유자산은 매도하지 않습니다."
            )
        else:
            non_gold_positive = [
                r for r in positive if r.get("Asset")!="Gold"
            ]
            if non_gold_positive:
                return (
                    "신규자금으로 금 정책이탈을 먼저 보정한 뒤 남는 자금은 "
                    "STEP6 Opportunity를 이용해 국내주식·해외주식·채권 등 FLEXIBLE 자산에 "
                    "완만하게 분산 배분합니다. 기존 보유자산은 매도하지 않습니다."
                )
            return (
                "신규자금은 금 정책이탈 보정에 우선 사용하고, 기존 보유자산은 매도하지 않습니다."
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

    best_asset = opps[0][0] if opps else ""
    return (
        f"강제 리밸런싱보다 기존 구조 유지가 우선이며, 신규자금은 "
        f"{ASSET_KR.get(best_asset,best_asset)} 등 상대매력도가 높은 자산으로 완만하게 기울여 배분합니다."
    )

def main():
    required=[
        RISK_SUMMARY,OPPORTUNITY,HEALTH_SUMMARY,
        ALLOC_SUMMARY,ALLOC_DETAIL,
        REBAL_DECISION,REBAL_ACTIONS
    ]
    missing=[p for p in required if not p.exists()]
    if missing:
        print("STEP 10 실행 불가 - 필수 파일 누락")
        for p in missing:
            print(" -",p)
        raise SystemExit(1)

    risk=load_risk()
    opps=load_opportunity()
    health=load_health()
    alloc_summary,alloc_details=load_allocation()
    decision,actions=load_rebalancing()

    msg_risk=risk_message(risk["score"])
    msg_opp=opportunity_message(opps)
    msg_health=health_message(health["score"])
    msg_alloc=allocation_message(alloc_details)
    msg_situation=build_current_situation(decision)
    final=final_recommendation(
        risk,opps,health,alloc_summary,alloc_details,decision
    )

    summary=[{
        "Risk_Score":round(risk["score"],2),
        "Risk_State":risk["state"],
        "Best_Opportunity_Asset":opps[0][0] if opps else "",
        "Best_Opportunity_Score":round(opps[0][1],2) if opps else "",
        "Portfolio_Health_Score":round(health["score"],2),
        "Portfolio_Health_State":health["state"],
        "Rebalancing_Decision":decision.get("Decision",""),
        "Action_Level":decision.get("Action_Level",""),
        "Current_Situation":msg_situation,
        "Final_Recommendation":final
    }]

    with OUT_SUMMARY.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

    detail=[
        {"Section":"현재 시장","Message":msg_risk},
        {"Section":"신규자금 기회","Message":msg_opp},
        {"Section":"포트폴리오 건강","Message":msg_health},
        {"Section":"이번 달 배분","Message":msg_alloc},
        {"Section":"현재상황","Message":msg_situation},
        {"Section":"최종 권고","Message":final},
    ]

    with OUT_DETAIL.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(detail[0].keys()))
        w.writeheader(); w.writerows(detail)

    print("="*78)
    print("STEP 10 - RECOMMENDATION / EXPLAINABILITY ENGINE v2")
    print("="*78)
    print()
    for title,msg in [
        ("현재 시장",msg_risk),
        ("신규자금 기회",msg_opp),
        ("포트폴리오 건강",msg_health),
        ("이번 달 배분",msg_alloc),
        ("현재상황",msg_situation),
        ("최종 권고",final),
    ]:
        print(f"[{title}]")
        print("→",msg)
        print()

if __name__=="__main__":
    main()
