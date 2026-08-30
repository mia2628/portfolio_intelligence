from pathlib import Path
import csv
import sys

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config"
DATA = BASE / "data"
HIST = DATA / "historical"
STEP04 = BASE / "outputs" / "step04"
STEP05 = BASE / "outputs" / "step05"
STEP06 = BASE / "outputs" / "step06"
STEP06.mkdir(parents=True, exist_ok=True)

PORTFOLIO_SUMMARY = BASE / "portfolio_summary.csv"
INVESTED_SUMMARY = BASE / "outputs" / "portfolio" / "portfolio_invested_summary.csv"
PORTFOLIO_FILE = BASE / "portfolio.csv"
STEP03_RESULTS = DATA / "step03_results.csv"
HISTORICAL_DATA = HIST / "historical_data.csv"
SIMILAR_EPISODES = STEP04 / "similar_episodes.csv"
STEP05_RISK = STEP05 / "risk_scores.csv"

OPP_CONFIG = CONFIG / "opportunity_config.csv"
ASSET_CONFIG = CONFIG / "opportunity_asset_config.csv"
TARGET_POLICY = CONFIG / "portfolio_target_policy.csv"

OUT_SCORES = STEP06 / "opportunity_scores.csv"
OUT_DETAILS = STEP06 / "opportunity_details.csv"
OUT_SUMMARY = STEP06 / "opportunity_summary.csv"
OUT_MACRO_DIAG = STEP06 / "macro_source_diagnostics.csv"

ASSETS = ["Domestic_Equity", "Foreign_Equity", "Bond", "Gold"]

ASSET_ALIASES = {
    "Domestic_Equity": ["Domestic_Equity", "Domestic Equity", "국내주식"],
    "Foreign_Equity": ["Foreign_Equity", "Foreign Equity", "해외주식"],
    "Bond": ["Bond", "채권", "채권형"],
    "Gold": ["Gold", "금"],
}

MACRO_SCORE_CANDIDATES = [
    "Asset_Macro_Environment",
    "Macro_Environment_Score",
    "Macro_Environment",
    "Final_Macro_Score",
    "Final_Score",
    "Macro_Score",
    "Score",
]

FACTOR_SCORE_CANDIDATES = [
    "Weighted_Factor_Score",
    "Factor_Score",
    "Weighted_Score",
    "Score",
]


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


def classify(score):
    if score < 35: return "LOW"
    if score < 45: return "BELOW_AVERAGE"
    if score < 55: return "NEUTRAL"
    if score < 70: return "ATTRACTIVE"
    if score < 85: return "HIGH"
    return "VERY_HIGH"


def normalize_macro(raw):
    """
    STEP3 structural/macro score is expected to be on -5..+5.
    Mapping:
      -5 -> 0
       0 -> 50
      +5 -> 100

    If STEP3 already outputs 0..100, preserve it.

    No ambiguous auto-conversion beyond these ranges.
    """
    if raw is None:
        return None, "MISSING"

    if -5.000001 <= raw <= 5.000001:
        return clamp(50.0 + raw * 10.0), "STEP3_-5_TO_5"

    if 0.0 <= raw <= 100.0:
        return raw, "STEP3_0_TO_100"

    return None, "UNSUPPORTED_SCALE"


def canonical_asset(value):
    if value is None:
        return None
    s = str(value).strip()

    for canonical, aliases in ASSET_ALIASES.items():
        if s in aliases:
            return canonical

    norm = s.lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in ASSET_ALIASES.items():
        if norm == canonical.lower():
            return canonical
        for alias in aliases:
            if norm == alias.lower().replace(" ", "_").replace("-", "_"):
                return canonical
    return None


def first_numeric(row, names):
    for name in names:
        if name in row:
            v = num(row.get(name))
            if v is not None:
                return v, name
    return None, None


def load_macro_scores_strict():
    """
    Read STEP3 results in three defensible schemas:

    A. Asset-level long format
       Asset | Macro_Environment_Score

    B. Factor-level long format
       Asset | Factor_Group | Factor_Score
       -> simple mean of available factor scores for each asset
          because STEP3 has already applied factor weights/caps upstream.

    C. Wide format
       one row / columns like Domestic_Equity, Foreign_Equity, Bond, Gold
       or Domestic_Equity_Score, ...

    IMPORTANT:
    Missing assets are NOT silently assigned 50.
    Diagnostics are written and STEP6 stops.
    """
    if not STEP03_RESULTS.exists():
        raise FileNotFoundError(
            f"STEP3 결과가 없습니다: {STEP03_RESULTS}"
        )

    rows = read_csv(STEP03_RESULTS)
    if not rows:
        raise ValueError("step03_results.csv가 비어 있습니다.")

    headers = list(rows[0].keys())
    macro_raw = {}
    source_detail = {}

    # ---------- A: Asset-level long format ----------
    asset_col = None
    for candidate in ["Asset", "Asset_Class", "Asset_Name"]:
        if candidate in headers:
            asset_col = candidate
            break

    if asset_col:
        for r in rows:
            asset = canonical_asset(r.get(asset_col))
            if not asset:
                continue

            raw, score_col = first_numeric(r, MACRO_SCORE_CANDIDATES)
            if raw is not None:
                macro_raw[asset] = raw
                source_detail[asset] = f"LONG:{score_col}"

    # ---------- B: Factor-level long format ----------
    if asset_col and len(macro_raw) < len(ASSETS):
        factor_group_col = None
        for candidate in ["Factor_Group", "Factor", "Group"]:
            if candidate in headers:
                factor_group_col = candidate
                break

        if factor_group_col:
            by_asset = {a: [] for a in ASSETS}
            factor_col_used = None

            for r in rows:
                asset = canonical_asset(r.get(asset_col))
                if not asset:
                    continue
                raw, score_col = first_numeric(r, FACTOR_SCORE_CANDIDATES)
                if raw is not None:
                    by_asset[asset].append(raw)
                    factor_col_used = score_col

            for asset, vals in by_asset.items():
                if asset not in macro_raw and vals:
                    macro_raw[asset] = sum(vals) / len(vals)
                    source_detail[asset] = f"FACTOR_AGG:{factor_col_used};N={len(vals)}"

    # ---------- C: Wide format ----------
    if len(macro_raw) < len(ASSETS):
        # Search every row because some STEP3 files contain summary rows later.
        for asset in ASSETS:
            if asset in macro_raw:
                continue

            candidate_cols = []
            for alias in ASSET_ALIASES[asset]:
                candidate_cols.extend([
                    alias,
                    f"{alias}_Score",
                    f"{alias}_Macro",
                    f"{alias}_Macro_Score",
                    f"{alias}_Macro_Environment",
                ])

            found = False
            for r in rows:
                for col in candidate_cols:
                    if col in r:
                        raw = num(r.get(col))
                        if raw is not None:
                            macro_raw[asset] = raw
                            source_detail[asset] = f"WIDE:{col}"
                            found = True
                            break
                if found:
                    break

    # Normalize + diagnostics
    scores = {}
    diagnostics = []

    for asset in ASSETS:
        raw = macro_raw.get(asset)
        normalized, scale = normalize_macro(raw)

        if normalized is not None:
            status = "ACTUAL"
            scores[asset] = normalized
        else:
            status = "MISSING" if raw is None else "INVALID_SCALE"

        diagnostics.append({
            "Asset": asset,
            "Raw_STEP3_Macro": "" if raw is None else round(raw, 6),
            "Normalized_Macro_0_100": "" if normalized is None else round(normalized, 2),
            "Source": source_detail.get(asset, ""),
            "Scale_Detection": scale,
            "Status": status,
        })

    with OUT_MACRO_DIAG.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(diagnostics[0].keys()))
        w.writeheader()
        w.writerows(diagnostics)

    missing = [d["Asset"] for d in diagnostics if d["Status"] != "ACTUAL"]

    print()
    print("Macro source check")
    print("-" * 78)
    for d in diagnostics:
        mark = "✓" if d["Status"] == "ACTUAL" else "✗"
        print(
            f"{d['Asset']:<18} : {mark} {d['Status']:<13} "
            f"Raw={str(d['Raw_STEP3_Macro']):<10} "
            f"Macro={str(d['Normalized_Macro_0_100']):<8} "
            f"{d['Source']}"
        )
    print("-" * 78)

    if missing:
        print()
        print("[STOP] STEP3 실제 Macro 값을 읽지 못한 자산이 있습니다.")
        print("       50점으로 임의 대체하지 않고 STEP6을 중단합니다.")
        print("       확인 파일: outputs/step06/macro_source_diagnostics.csv")
        print("       누락 자산 :", ", ".join(missing))
        raise SystemExit(2)

    return scores


def load_weights():
    rows = read_csv(OPP_CONFIG)
    d = {r["Component"]: num(r["Weight"], 0.0) for r in rows}
    total = sum(d.values())
    if total <= 0:
        raise ValueError("Opportunity weight 합계가 0입니다.")
    return {k: v / total for k, v in d.items()}


def pick_num(row, names):
    for n in names:
        if n in row:
            v = num(row.get(n))
            if v is not None:
                return v
    return None


def load_portfolio_weights():
    result = {}

    # Canonical current composition for decisions: invested-principal basis.
    # Market valuation snapshot is intentionally not used for daily weight updates.
    if INVESTED_SUMMARY.exists():
        rows = read_csv(INVESTED_SUMMARY)
        for r in rows:
            asset = canonical_asset(r.get("Asset"))
            if not asset:
                continue
            current = pick_num(r, ["Portfolio_Weight_Pct","Portfolio_Weight"])
            result[asset] = {"Current_Weight":current,"Target_Weight":None}
        if result:
            return result

    if PORTFOLIO_SUMMARY.exists():
        rows = read_csv(PORTFOLIO_SUMMARY)
        for r in rows:
            asset = canonical_asset(r.get("Asset"))
            if not asset:
                continue
            current = pick_num(r, [
                "Portfolio_Weight_Pct", "Portfolio_Weight",
                "Current_Portfolio_Weight", "Current_Weight",
                "Weight_Pct", "Weight"
            ])
            target = pick_num(r, [
                "Target_Weight_Pct", "Target_Weight", "Target"
            ])
            result[asset] = {
                "Current_Weight": current,
                "Target_Weight": target
            }
        if result:
            return result

    rows = read_csv(PORTFOLIO_FILE)
    for r in rows:
        asset = canonical_asset(r.get("Asset"))
        if not asset:
            continue
        current = pick_num(r, [
            "Portfolio_Weight_Pct", "Portfolio_Weight",
            "Current_Weight", "Weight_Pct", "Weight"
        ])
        target = pick_num(r, [
            "Target_Weight_Pct", "Target_Weight", "Target"
        ])
        result[asset] = {
            "Current_Weight": current,
            "Target_Weight": target
        }

    return result


def load_target_policy():
    """Canonical portfolio policy. HARD_RANGE overrides stale Target_Weight fields."""
    rows = read_csv(TARGET_POLICY)
    result = {}
    for r in rows:
        asset = canonical_asset(r.get("Asset"))
        if not asset:
            continue
        result[asset] = {
            "Policy_Type": (r.get("Policy_Type") or "").strip().upper(),
            "Target": num(r.get("Target_Pct")),
            "Lower": num(r.get("Lower_Bound_Pct")),
            "Upper": num(r.get("Upper_Bound_Pct")),
        }
    return result


def target_policy_score(current, policy_row, fallback_target=None):
    """
    Opportunity Target component.

    HARD_RANGE:
      current < lower:
        50 + 50*(lower-current)/lower
      lower <= current <= upper:
        50
      current > upper:
        50 - 50*(current-upper)/(100-upper)

    Meaning:
    - 50 = no policy-driven new-money tilt.
    - Below lower -> progressively stronger buy priority.
    - Above upper -> progressively lower buy priority.
    - Continuous and bounded in [0,100].

    FLEXIBLE:
    - neutral 50, because no numeric target is intentionally imposed.

    Fallback:
    - only for legacy policies without an explicit policy row.
    """
    if current is None:
        return 50.0, None, None, None, None

    if policy_row:
        ptype = policy_row.get("Policy_Type", "")
        target = policy_row.get("Target")
        lower = policy_row.get("Lower")
        upper = policy_row.get("Upper")

        if ptype == "FLEXIBLE":
            return 50.0, None, target, lower, upper

        if ptype == "HARD_RANGE" and lower is not None and upper is not None:
            if current < lower:
                score = 50.0 + 50.0 * (lower-current) / max(lower, 1e-12)
            elif current > upper:
                score = 50.0 - 50.0 * (current-upper) / max(100.0-upper, 1e-12)
            else:
                score = 50.0
            gap_to_target = None if target is None else target-current
            return clamp(score), gap_to_target, target, lower, upper

    if fallback_target is None or fallback_target <= 0:
        return 50.0, None, fallback_target, None, None

    gap = fallback_target-current
    ratio = gap/fallback_target
    return clamp(50.0+40.0*ratio), gap, fallback_target, None, None


def load_risk_scores():
    return {
        canonical_asset(r.get("Asset")): num(r.get("Risk_Score"), 50.0)
        for r in read_csv(STEP05_RISK)
        if canonical_asset(r.get("Asset")) is not None
    }


ASSET_RET_COL = {
    "Domestic_Equity": "RET_DOMESTIC",
    "Foreign_Equity": "RET_FOREIGN",
    "Bond": "RET_BOND",
    "Gold": "RET_GOLD",
}


def compute_drawdown_scores():
    result = {a: 50.0 for a in ASSET_RET_COL}
    if not HISTORICAL_DATA.exists():
        return result

    rows = read_csv(HISTORICAL_DATA)

    for asset, col in ASSET_RET_COL.items():
        wealth = 1.0
        peak = 1.0
        had = False

        for r in rows:
            ret = num(r.get(col))
            if ret is None:
                continue
            had = True
            wealth *= 1.0 + ret / 100.0
            peak = max(peak, wealth)

        if not had or peak <= 0:
            continue

        dd = wealth / peak - 1.0
        dd_pct = abs(min(dd, 0.0)) * 100.0

        # 0% DD=45, 10%=60, 20%=75, 30%+=90
        result[asset] = clamp(
            45.0 + min(45.0, dd_pct * 1.5)
        )

    return result


def similar_episode_scores():
    result = {a: 50.0 for a in ASSET_RET_COL}

    if not SIMILAR_EPISODES.exists():
        return result

    rows = read_csv(SIMILAR_EPISODES)

    for asset in ASSET_RET_COL:
        col = f"{asset}_Forward_Avg_Return"
        vals = [num(r.get(col)) for r in rows]
        vals = [v for v in vals if v is not None]

        if vals:
            avg_ret = sum(vals) / len(vals)
            result[asset] = clamp(
                50.0 + avg_ret * 5.0,
                35.0,
                65.0
            )

    return result


def explain(asset, mscore, risk_raw, hscore, dscore, gap, current=None, lower=None, upper=None):
    kr = {
        "Domestic_Equity": "국내주식",
        "Foreign_Equity": "해외주식",
        "Bond": "채권",
        "Gold": "금",
    }.get(asset, asset)

    reasons = []

    if current is not None and lower is not None and upper is not None:
        if current < lower:
            reasons.append(
                f"현재 {current:.1f}%로 정책 하한 {lower:.1f}%보다 {lower-current:.1f}%p 낮아 신규자금 보충 우선순위가 높습니다"
            )
        elif current > upper:
            reasons.append(
                f"현재 {current:.1f}%로 정책 상한 {upper:.1f}%보다 {current-upper:.1f}%p 높아 추가매수 우선순위가 낮습니다"
            )
        else:
            reasons.append(f"현재 비중이 정책 허용범위 {lower:.0f}~{upper:.0f}% 안에 있습니다")
    elif gap is not None:
        if gap > 0:
            reasons.append(f"목표비중보다 {abs(gap):.1f}%p 낮아 보충 요인이 있습니다")
        elif gap < 0:
            reasons.append(f"목표비중보다 {abs(gap):.1f}%p 높아 추가매수 필요성이 낮습니다")

    if mscore >= 58:
        reasons.append("현재 거시환경이 비교적 우호적입니다")
    elif mscore <= 42:
        reasons.append("현재 거시환경이 비우호적입니다")

    if dscore >= 60:
        reasons.append("고점 대비 낙폭이 있어 분할매수 매력이 높아졌습니다")

    if hscore >= 55:
        reasons.append("유사한 과거 국면 이후 수익흐름이 상대적으로 우호적이었습니다")
    elif hscore <= 45:
        reasons.append("유사한 과거 국면 이후 수익흐름은 다소 불리했습니다")

    if risk_raw >= 60:
        reasons.append("현재 위험도가 높아 기회점수를 낮췄습니다")
    elif risk_raw <= 45:
        reasons.append("현재 위험 부담이 낮아 기회점수에 도움이 됐습니다")

    if not reasons:
        reasons.append("정책·거시환경·위험·과거 국면이 전반적으로 중립적입니다")

    return f"{kr}: " + ", ".join(reasons[:2]) + "."

def main():
    required = [
        PORTFOLIO_FILE,
        STEP03_RESULTS,
        STEP05_RISK,
        OPP_CONFIG,
        ASSET_CONFIG,
        TARGET_POLICY,
        HISTORICAL_DATA,
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        print("STEP 06 v4 실행 불가 - 필수 파일 누락")
        for p in missing:
            print(" -", p)
        raise SystemExit(1)

    weights = load_weights()

    # This is now strict: no silent neutral fallback.
    macro = load_macro_scores_strict()

    portfolio = load_portfolio_weights()
    target_policy = load_target_policy()
    risk = load_risk_scores()
    historical = similar_episode_scores()
    drawdown = compute_drawdown_scores()

    assets = [
        canonical_asset(r.get("Asset"))
        for r in read_csv(ASSET_CONFIG)
        if num(r.get("Enabled"), 0) == 1
    ]
    assets = [a for a in assets if a]

    details = []

    for asset in assets:
        p = portfolio.get(asset, {})
        current = p.get("Current_Weight")
        fallback_target = p.get("Target_Weight")

        tscore, gap, target, lower, upper = target_policy_score(
            current,
            target_policy.get(asset),
            fallback_target
        )
        mscore = macro[asset]
        risk_raw = risk.get(asset, 50.0)
        rscore = clamp(100.0 - risk_raw)
        hscore = historical.get(asset, 50.0)
        dscore = drawdown.get(asset, 50.0)

        comp = {
            "Target_Gap": tscore,
            "Macro_Environment": mscore,
            "Risk_Adjustment": rscore,
            "Historical_Context": hscore,
            "Drawdown": dscore,
        }

        final = sum(
            comp[k] * weights[k]
            for k in weights
        )

        comment = explain(
            asset, mscore, risk_raw,
            hscore, dscore, gap,
            current=current, lower=lower, upper=upper
        )

        details.append({
            "Asset": asset,
            "Current_Weight": "" if current is None else round(current, 4),
            "Target_Weight": "" if target is None else round(target, 4),
            "Lower_Bound_Pct": "" if lower is None else round(lower, 4),
            "Upper_Bound_Pct": "" if upper is None else round(upper, 4),
            "Target_Gap": "" if gap is None else round(gap, 4),
            "Target_Gap_Score": round(tscore, 2),
            "Macro_Environment_Score": round(mscore, 2),
            "Macro_Source": "STEP3_ACTUAL",
            "Risk_Score": round(risk_raw, 2),
            "Risk_Adjustment_Score": round(rscore, 2),
            "Historical_Context_Score": round(hscore, 2),
            "Drawdown_Score": round(dscore, 2),
            "Opportunity_Score": round(final, 2),
            "Opportunity_State": classify(final),
            "Korean_Comment": comment,
        })

    ranking = sorted(
        details,
        key=lambda r: r["Opportunity_Score"],
        reverse=True
    )

    with OUT_DETAILS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(details[0].keys()))
        w.writeheader()
        w.writerows(details)

    with OUT_SCORES.open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "Asset", "Opportunity_Score",
            "Opportunity_State", "Korean_Comment"
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ranking:
            w.writerow({k: r[k] for k in fields})

    summary = [{
        "Rank_1": ranking[0]["Asset"],
        "Rank_1_Score": ranking[0]["Opportunity_Score"],
        "Rank_2": ranking[1]["Asset"],
        "Rank_2_Score": ranking[1]["Opportunity_Score"],
        "Rank_3": ranking[2]["Asset"],
        "Rank_3_Score": ranking[2]["Opportunity_Score"],
        "Rank_4": ranking[3]["Asset"],
        "Rank_4_Score": ranking[3]["Opportunity_Score"],
        "Macro_Normalization": "PASS_ALL_STEP3_ACTUAL",
        "Target_Policy_Method": "HARD_RANGE_CONTINUOUS_V2",
        "Opportunity_Formula": "0.30*Target+0.25*Macro+0.20*RiskAdj+0.15*History+0.10*Drawdown",
        "Note": "신규자금 상대적 매력도이며 매도 또는 리밸런싱 신호가 아닙니다.",
    }]

    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    print()
    print("=" * 78)
    print("STEP 06 - OPPORTUNITY ENGINE v5 POLICY INTEGRATED")
    print("=" * 78)
    print("점수 의미 (50 = 중립)")
    print("Target    : 목표비중 대비 부족/초과")
    print("Macro     : STEP3 실제 거시환경의 우호/비우호")
    print("RiskAdj   : 현재 위험도를 반대로 조정한 점수")
    print("History   : 과거 유사국면 이후 수익흐름")
    print("Drawdown  : 고점 대비 낙폭에 따른 분할매수 매력")
    print("-" * 78)

    for i, r in enumerate(ranking, 1):
        print(
            f"{i}. {r['Asset']:<18} "
            f"{r['Opportunity_Score']:>6.2f} / 100 "
            f"{r['Opportunity_State']}"
        )
        print(f"   → {r['Korean_Comment']}")
        print(
            f"      Target={r['Target_Gap_Score']:.2f} | "
            f"Macro={r['Macro_Environment_Score']:.2f} ✓ | "
            f"RiskAdj={r['Risk_Adjustment_Score']:.2f} | "
            f"History={r['Historical_Context_Score']:.2f} | "
            f"Drawdown={r['Drawdown_Score']:.2f}"
        )

    print()
    print("Macro normalization : PASS - all assets loaded from STEP3 actual results")
    print()
    print("Generated:")
    print(" - outputs/step06/opportunity_scores.csv")
    print(" - outputs/step06/opportunity_details.csv")
    print(" - outputs/step06/opportunity_summary.csv")
    print(" - outputs/step06/macro_source_diagnostics.csv")


if __name__ == "__main__":
    main()
