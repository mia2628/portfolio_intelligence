from pathlib import Path
import csv
import argparse
from datetime import date, datetime
from calendar import monthrange

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config"
STEP07 = BASE / "outputs" / "step07"
STEP09 = BASE / "outputs" / "step09"
STEP09.mkdir(parents=True, exist_ok=True)

PORTFOLIO_SUMMARY = BASE / "portfolio_summary.csv"
INVESTED_SUMMARY = BASE / "outputs" / "portfolio" / "portfolio_invested_summary.csv"
HEALTH_SUMMARY = STEP07 / "portfolio_health_summary.csv"
HEALTH_COMPONENTS = STEP07 / "portfolio_health_components.csv"
TARGET_POLICY_STATUS = STEP07 / "target_policy_status.csv"
POLICY_FILE = CONFIG / "rebalancing_policy.csv"

OUT_DECISION = STEP09 / "rebalancing_decision.csv"
OUT_ACTIONS = STEP09 / "rebalancing_actions.csv"
OUT_STATE = STEP09 / "rebalancing_state.csv"

ASSET_ALIASES = {
    "Gold": ["Gold","금"],
    "Domestic_Equity": ["Domestic_Equity","국내주식"],
    "Foreign_Equity": ["Foreign_Equity","해외주식"],
    "Bond": ["Bond","채권","채권형"],
    "Cash": ["Cash","현금","유동성"],
    "Other": ["Other","기타"],
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


def canonical_asset(v):
    if v is None:
        return None
    s = str(v).strip()
    for k, vals in ASSET_ALIASES.items():
        if s in vals:
            return k
    return s


def load_policy():
    rows = read_csv(POLICY_FILE)
    return {r["Parameter"]: num(r.get("Value")) for r in rows}


def add_months(d, months):
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def parse_date(s):
    s = str(s).strip()

    # Accept:
    # 20260829
    # 2026-08-29
    # 2026/08/29
    formats = [
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValueError(
        "날짜 형식 오류: 20260829, 2026-08-29, 2026/08/29 중 하나로 입력하세요."
    )


def load_gold_weight():
    """
    Current Gold weight source priority:
    1) outputs/portfolio/portfolio_invested_summary.csv
       - canonical actual portfolio state
       - invested-principal basis
    2) legacy portfolio_summary.csv only as fallback
    """
    sources = [
        ("INVESTED_PRINCIPAL", INVESTED_SUMMARY),
        ("LEGACY_FALLBACK", PORTFOLIO_SUMMARY),
    ]

    for source_name, path in sources:
        if not path.exists():
            continue
        rows = read_csv(path)
        for r in rows:
            if canonical_asset(r.get("Asset")) == "Gold":
                for c in [
                    "Portfolio_Weight_Pct",
                    "Portfolio_Weight",
                    "Current_Portfolio_Weight",
                    "Current_Weight",
                    "Weight_Pct",
                    "Weight",
                ]:
                    if c in r:
                        v = num(r.get(c))
                        if v is not None:
                            return v, source_name

    raise ValueError(
        "portfolio_invested_summary.csv 및 legacy portfolio_summary.csv에서 "
        "Gold 현재비중을 찾지 못했습니다."
    )


def load_health():
    rows = read_csv(HEALTH_SUMMARY)
    if not rows:
        raise ValueError("STEP7 Health Summary가 비어 있습니다.")
    r = rows[0]

    health = num(r.get("Portfolio_Health_Score"), 50.0)

    comp = {}
    if HEALTH_COMPONENTS.exists():
        for x in read_csv(HEALTH_COMPONENTS):
            comp[x.get("Component","")] = num(x.get("Score"), 50.0)

    return {
        "Portfolio_Health": health,
        "Concentration": comp.get("Concentration", 50.0),
        "Correlation": comp.get("Correlation_Diversification", 50.0),
    }


def load_gold_policy_status():
    for r in read_csv(TARGET_POLICY_STATUS):
        if canonical_asset(r.get("Asset")) == "Gold":
            return {
                "Status": r.get("Status",""),
                "Target": num(r.get("Target_Pct"),20.0),
                "Lower": num(r.get("Lower_Bound_Pct"),18.0),
                "Upper": num(r.get("Upper_Bound_Pct"),22.0),
            }
    return {"Status":"", "Target":20.0, "Lower":18.0, "Upper":22.0}


def build_situation_message(
    calendar_due,
    gold_below,
    gold_above,
    structural_caution,
    gold_weight,
    lower,
    upper
):
    if gold_above:
        return (
            f"정기점검일 {'도래' if calendar_due else '전'}이지만, "
            f"금 비중이 {gold_weight:.2f}%로 정책 상한 {upper:.2f}%를 초과했습니다. "
            "현재 포트폴리오 구조도 함께 점검하면서 필요하면 일부 매도·재배분을 검토합니다."
        )

    if gold_below:
        if structural_caution:
            return (
                f"정기점검일 {'도래' if calendar_due else '전'}이지만, "
                f"금 비중이 {gold_weight:.2f}%로 정책 하한 {lower:.2f}%보다 낮고 "
                "포트폴리오 건강지표 일부도 주의수준입니다. "
                "기존자산 매도보다 신규자금으로 금을 보충하면서 구조를 함께 점검합니다."
            )
        return (
            f"정기점검일 {'도래' if calendar_due else '전'}이지만, "
            f"금 비중이 {gold_weight:.2f}%로 정책 하한 {lower:.2f}%보다 낮습니다. "
            "다만 전체 포트폴리오 구조는 비교적 양호하므로 매도 리밸런싱은 하지 않고, "
            "신규자금으로 금을 우선 보충합니다."
        )

    if structural_caution:
        return (
            f"금 비중은 정책범위 {lower:.0f}~{upper:.0f}% 안에 있지만, "
            "포트폴리오 건강지표 일부가 주의수준입니다. "
            "즉시 매매보다 구조 변화 여부를 먼저 점검합니다."
        )

    if calendar_due:
        return (
            f"6개월 정기점검일이 도래했지만 금 비중은 정책범위 {lower:.0f}~{upper:.0f}% 안이고 "
            "포트폴리오 구조도 큰 이상이 없습니다. 강제 리밸런싱 없이 현재 구조를 유지합니다."
        )

    return (
        f"아직 정기점검일 전이고 금 비중도 정책범위 {lower:.0f}~{upper:.0f}% 안이며 "
        "포트폴리오 구조도 큰 이상이 없습니다. 현재는 별도 조치 없이 유지합니다."
    )


def evaluate(
    current_date,
    last_rebalance_date,
    gold_weight,
    health,
    policy,
    gold_policy
):
    interval = int(policy.get("Review_Interval_Months") or 6)
    due_date = add_months(last_rebalance_date, interval)
    calendar_due = current_date >= due_date

    lower = gold_policy["Lower"]
    target = gold_policy["Target"]
    upper = gold_policy["Upper"]

    gold_below = gold_weight < lower
    gold_above = gold_weight > upper

    health_caution = health["Portfolio_Health"] < (policy.get("Health_Caution_Score") or 50.0)
    concentration_caution = health["Concentration"] < (policy.get("Concentration_Caution_Score") or 50.0)
    correlation_caution = health["Correlation"] < (policy.get("Correlation_Caution_Score") or 50.0)

    structural_caution = any([
        health_caution,
        concentration_caution,
        correlation_caution
    ])

    threshold_trigger = gold_below or gold_above or structural_caution

    if gold_above and (policy.get("Allow_Selling") or 0) >= 1:
        decision = "REBALANCE_REQUIRED"
        action_level = "HIGH"
        reason = "Gold가 허용상한 22%를 초과해 매도/재배분 검토가 필요합니다."
    elif gold_below:
        decision = "NEW_MONEY_CORRECTION"
        action_level = "MEDIUM"
        reason = "Gold가 허용하한 18% 미만이므로 매도 없이 신규자금으로 우선 보충합니다."
    elif structural_caution and calendar_due:
        decision = "STRUCTURAL_REVIEW"
        action_level = "MEDIUM"
        reason = "정기 점검 시점이며 포트폴리오 건강지표 일부가 주의수준입니다."
    elif structural_caution:
        decision = "WATCH"
        action_level = "LOW"
        reason = "정기 점검 전이지만 건강지표 일부가 주의수준이므로 관찰합니다."
    elif calendar_due:
        decision = "REVIEW_ONLY"
        action_level = "LOW"
        reason = "6개월 정기 점검 시점이지만 정책범위 이탈이 없어 강제 리밸런싱은 필요하지 않습니다."
    else:
        decision = "HOLD"
        action_level = "NONE"
        reason = "정기 점검 전이며 정책범위와 건강지표 모두 큰 이상이 없습니다."

    situation_message = build_situation_message(
        calendar_due=calendar_due,
        gold_below=gold_below,
        gold_above=gold_above,
        structural_caution=structural_caution,
        gold_weight=gold_weight,
        lower=lower,
        upper=upper,
    )

    actions = []

    if gold_below:
        actions.append({
            "Priority":1,
            "Action":"BUY_WITH_NEW_MONEY",
            "Asset":"Gold",
            "Reason":f"Gold {gold_weight:.2f}% < 하한 {lower:.2f}%",
            "Target":f"신규자금으로 먼저 {lower:.0f}% 하한을 향해 복구"
        })

    if gold_above:
        actions.append({
            "Priority":1,
            "Action":"CONSIDER_SELL_AND_REALLOCATE",
            "Asset":"Gold",
            "Reason":f"Gold {gold_weight:.2f}% > 상한 {upper:.2f}%",
            "Target":f"우선 {upper:.0f}% 이하, 필요시 중심 {target:.0f}% 근처로 복귀"
        })

    if concentration_caution:
        actions.append({
            "Priority":2,
            "Action":"REVIEW_CONCENTRATION",
            "Asset":"Portfolio",
            "Reason":f"Concentration Score {health['Concentration']:.2f}",
            "Target":"신규자금을 덜 집중된 자산으로 우선 배분"
        })

    if correlation_caution:
        actions.append({
            "Priority":2,
            "Action":"REVIEW_DIVERSIFICATION",
            "Asset":"Portfolio",
            "Reason":f"Correlation Score {health['Correlation']:.2f}",
            "Target":"동조화가 높은 자산군 비중 확대를 억제"
        })

    if not actions:
        actions.append({
            "Priority":1,
            "Action":"NO_FORCED_TRADE",
            "Asset":"Portfolio",
            "Reason":"명시적 정책범위 이탈 없음",
            "Target":"현재 구조 유지"
        })

    return {
        "Current_Date": current_date.isoformat(),
        "Last_Rebalance_Date": last_rebalance_date.isoformat(),
        "Next_Scheduled_Review": due_date.isoformat(),
        "Calendar_Due": calendar_due,
        "Threshold_Trigger": threshold_trigger,
        "Gold_Weight_Pct": round(gold_weight,2),
        "Gold_Weight_Source": gold_weight_source,
        "Gold_Range": f"{lower:.0f}~{upper:.0f}%",
        "Portfolio_Health": round(health["Portfolio_Health"],2),
        "Concentration_Score": round(health["Concentration"],2),
        "Correlation_Score": round(health["Correlation"],2),
        "Decision": decision,
        "Action_Level": action_level,
        "Reason": reason,
        "Situation_Message": situation_message,
        "Actions": actions,
    }


def save(result):
    decision_row = {k:v for k,v in result.items() if k != "Actions"}

    with OUT_DECISION.open("w",encoding="utf-8-sig",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(decision_row.keys()))
        w.writeheader()
        w.writerow(decision_row)

    with OUT_ACTIONS.open("w",encoding="utf-8-sig",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result["Actions"][0].keys()))
        w.writeheader()
        w.writerows(result["Actions"])

    state = [{
        "Last_Rebalance_Date":result["Last_Rebalance_Date"],
        "Next_Scheduled_Review":result["Next_Scheduled_Review"],
        "Decision":result["Decision"]
    }]

    with OUT_STATE.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(state[0].keys()))
        w.writeheader()
        w.writerows(state)


def main():
    required = [
        PORTFOLIO_SUMMARY,
        HEALTH_SUMMARY,
        TARGET_POLICY_STATUS,
        POLICY_FILE
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        print("STEP 09 실행 불가 - 필수 파일 누락")
        for p in missing:
            print(" -",p)
        raise SystemExit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--last-rebalance", type=str, help="마지막 리밸런싱/기준일 YYYY-MM-DD")
    parser.add_argument("--date", type=str, help="점검일 YYYY-MM-DD (생략 시 오늘)")
    args = parser.parse_args()

    current_date = parse_date(args.date) if args.date else date.today()

    if args.last_rebalance:
        last_rebalance = parse_date(args.last_rebalance)
    else:
        text = input("마지막 리밸런싱 또는 기준일을 입력하세요 (예: 20260829): ").strip()
        last_rebalance = parse_date(text)

    policy = load_policy()
    gold_weight, gold_weight_source = load_gold_weight()
    health = load_health()
    gold_policy = load_gold_policy_status()

    result = evaluate(
        current_date,
        last_rebalance,
        gold_weight,
        health,
        policy,
        gold_policy
    )

    save(result)

    print("="*78)
    print("STEP 09 - 6-MONTH REBALANCING ENGINE v4 INVESTED-STATE")
    print("="*78)
    print(f"점검일            : {result['Current_Date']}")
    print(f"마지막 기준일     : {result['Last_Rebalance_Date']}")
    print(f"다음 정기점검일   : {result['Next_Scheduled_Review']}")
    print(f"정기점검 도래     : {result['Calendar_Due']}")
    print(f"Threshold Trigger : {result['Threshold_Trigger']}")
    print()
    print(f"Gold 비중         : {result['Gold_Weight_Pct']:.2f}%")
    print(f"Gold 비중 기준    : {result.get('Gold_Weight_Source','UNKNOWN')}")
    print(f"Gold 정책범위     : {result['Gold_Range']}")
    print(f"Portfolio Health  : {result['Portfolio_Health']:.2f}")
    print(f"Concentration     : {result['Concentration_Score']:.2f}")
    print(f"Correlation       : {result['Correlation_Score']:.2f}")
    print()
    print(f"Decision          : {result['Decision']}")
    print(f"Action Level      : {result['Action_Level']}")
    print(f"Reason            : {result['Reason']}")
    print()
    print("현재상황")
    print(f"→ {result['Situation_Message']}")
    print()
    print("권고조치")
    for a in result["Actions"]:
        print(
            f"{a['Priority']}. {a['Action']} | "
            f"{a['Asset']} | {a['Reason']} | {a['Target']}"
        )
    print()
    print("원칙")
    print("→ 6개월이 됐다고 무조건 사고팔지 않습니다.")
    print("→ Gold 18% 미만은 STEP8 신규자금으로 먼저 보정합니다.")
    print("→ Gold 22% 초과처럼 명확한 정책이탈일 때만 매도를 검토합니다.")
    print("→ FLEXIBLE 자산은 임의 목표비중을 만들지 않습니다.")
    print()
    print("Generated:")
    print(" - outputs/step09/rebalancing_decision.csv")
    print(" - outputs/step09/rebalancing_actions.csv")
    print(" - outputs/step09/rebalancing_state.csv")


if __name__ == "__main__":
    main()
