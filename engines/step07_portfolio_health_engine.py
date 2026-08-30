from pathlib import Path
import csv
import math
from statistics import mean, pstdev

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config"
DATA = BASE / "data"
HIST = DATA / "historical"
STEP07 = BASE / "outputs" / "step07"
STEP07.mkdir(parents=True, exist_ok=True)

PORTFOLIO_SUMMARY = BASE / "portfolio_summary.csv"
INVESTED_SUMMARY = BASE / "outputs" / "portfolio" / "portfolio_invested_summary.csv"
PORTFOLIO_FILE = BASE / "portfolio.csv"
HISTORICAL_DATA = HIST / "historical_data.csv"

HEALTH_CONFIG = CONFIG / "portfolio_health_config.csv"
HEALTH_POLICY = CONFIG / "portfolio_health_policy.csv"
TARGET_POLICY = CONFIG / "portfolio_target_policy.csv"

OUT_SUMMARY = STEP07 / "portfolio_health_summary.csv"
OUT_COMPONENTS = STEP07 / "portfolio_health_components.csv"
OUT_CORR = STEP07 / "asset_correlation_matrix.csv"
OUT_ASSETS = STEP07 / "asset_health_metrics.csv"
OUT_POLICY = STEP07 / "target_policy_status.csv"

ASSET_RETURN_COL = {
    "Domestic_Equity": "RET_DOMESTIC",
    "Foreign_Equity": "RET_FOREIGN",
    "Bond": "RET_BOND",
    "Gold": "RET_GOLD",
}

ASSET_ALIASES = {
    "Domestic_Equity": ["Domestic_Equity","Domestic Equity","국내주식"],
    "Foreign_Equity": ["Foreign_Equity","Foreign Equity","해외주식"],
    "Bond": ["Bond","채권","채권형"],
    "Cash": ["Cash","유동성","현금"],
    "Other": ["Other","기타"],
    "Gold": ["Gold","금"],
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


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def canonical_asset(value):
    if value is None:
        return None
    s = str(value).strip()
    for canonical, aliases in ASSET_ALIASES.items():
        if s in aliases:
            return canonical
    n = s.lower().replace(" ","_").replace("-","_")
    for canonical, aliases in ASSET_ALIASES.items():
        if n == canonical.lower():
            return canonical
        for alias in aliases:
            if n == alias.lower().replace(" ","_").replace("-","_"):
                return canonical
    return None


def pick_num(row, names):
    for n in names:
        if n in row:
            v = num(row.get(n))
            if v is not None:
                return v
    return None


def load_portfolio():
    result = {}

    # Prefer actual invested-principal state. Evaluation amounts are snapshots only.
    if INVESTED_SUMMARY.exists():
        rows = read_csv(INVESTED_SUMMARY)
        for r in rows:
            asset = canonical_asset(r.get("Asset"))
            if not asset:
                continue
            current = pick_num(r, ["Portfolio_Weight_Pct","Portfolio_Weight"])
            result[asset] = {"Current_Weight":current}
        if result:
            return result

    if PORTFOLIO_SUMMARY.exists():
        rows = read_csv(PORTFOLIO_SUMMARY)
        for r in rows:
            asset = canonical_asset(r.get("Asset"))
            if not asset:
                continue
            current = pick_num(r, [
                "Portfolio_Weight_Pct","Portfolio_Weight",
                "Current_Portfolio_Weight","Current_Weight",
                "Weight_Pct","Weight"
            ])
            result[asset] = {"Current_Weight": current}
        if result:
            return result

    rows = read_csv(PORTFOLIO_FILE)
    for r in rows:
        asset = canonical_asset(r.get("Asset"))
        if not asset:
            continue
        current = pick_num(r, [
            "Portfolio_Weight_Pct","Portfolio_Weight",
            "Current_Weight","Weight_Pct","Weight"
        ])
        result[asset] = {"Current_Weight": current}

    return result


def load_policy():
    rows = read_csv(HEALTH_POLICY)
    return {r["Parameter"]: num(r.get("Value")) for r in rows}


def load_component_weights():
    rows = read_csv(HEALTH_CONFIG)
    d = {r["Component"]: num(r["Weight"],0.0) for r in rows}
    total = sum(d.values())
    if total <= 0:
        raise ValueError("Portfolio Health weight 합계가 0입니다.")
    return {k:v/total for k,v in d.items()}


def paired_corr(x, y):
    pairs = [(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(pairs) < 12:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((a-mx)**2 for a in xs))
    sy = math.sqrt(sum((b-my)**2 for b in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((a-mx)*(b-my) for a,b in pairs)/(sx*sy)


def portfolio_return_series(rows, portfolio):
    assets = []
    weights = []

    for asset, col in ASSET_RETURN_COL.items():
        w = portfolio.get(asset, {}).get("Current_Weight")
        if w is not None and w > 0:
            assets.append((asset,col))
            weights.append(w)

    total = sum(weights)
    if total <= 0:
        return [], []

    norm = [w/total for w in weights]
    dates = []
    rets = []

    for row in rows:
        vals = []
        valid = True
        for (_,col) in assets:
            v = num(row.get(col))
            if v is None:
                valid = False
                break
            vals.append(v)

        if not valid:
            continue

        pr = sum(v*w for v,w in zip(vals,norm))
        dates.append(row.get("Date",""))
        rets.append(pr)

    return dates, rets


def annualized_vol(monthly_returns):
    vals = [v for v in monthly_returns if v is not None]
    if len(vals) < 12:
        return None
    return pstdev(vals) * math.sqrt(12)


def max_drawdown(monthly_returns):
    if not monthly_returns:
        return None
    wealth = 1.0
    peak = 1.0
    mdd = 0.0
    for r in monthly_returns:
        wealth *= 1.0 + r/100.0
        peak = max(peak, wealth)
        dd = wealth/peak - 1.0
        mdd = min(mdd, dd)
    return mdd * 100.0


def score_concentration(portfolio):
    ws = [
        p["Current_Weight"]/100.0
        for p in portfolio.values()
        if p.get("Current_Weight") is not None and p["Current_Weight"] > 0
    ]
    if len(ws) <= 1:
        return 0.0, 1.0, 1.0

    s = sum(ws)
    ws = [w/s for w in ws]
    hhi = sum(w*w for w in ws)
    n = len(ws)

    min_hhi = 1.0/n
    score = 100.0 * (1.0 - hhi) / (1.0 - min_hhi)
    effective_n = 1.0/hhi if hhi > 0 else float(n)

    return clamp(score), hhi, effective_n


def score_volatility(vol_pct):
    if vol_pct is None:
        return 50.0
    if vol_pct <= 8: return 90.0
    if vol_pct <= 12: return 80.0 - (vol_pct-8)*2.5
    if vol_pct <= 18: return 70.0 - (vol_pct-12)*2.5
    if vol_pct <= 25: return 55.0 - (vol_pct-18)*2.5
    if vol_pct <= 35: return 37.5 - (vol_pct-25)*1.75
    return 20.0


def score_drawdown(mdd_pct):
    if mdd_pct is None:
        return 50.0
    d = abs(min(mdd_pct,0.0))
    return clamp(100.0 - 2.0*d)


def build_correlations(rows):
    series = {
        asset: [num(r.get(col)) for r in rows]
        for asset,col in ASSET_RETURN_COL.items()
    }

    matrix = {}
    for a in ASSET_RETURN_COL:
        matrix[a] = {}
        for b in ASSET_RETURN_COL:
            if a == b:
                matrix[a][b] = 1.0
            else:
                matrix[a][b] = paired_corr(series[a],series[b])
    return matrix


def score_correlation(matrix, portfolio):
    pairs = []
    assets = list(ASSET_RETURN_COL.keys())

    for i in range(len(assets)):
        for j in range(i+1,len(assets)):
            a,b = assets[i],assets[j]
            wa = portfolio.get(a,{}).get("Current_Weight")
            wb = portfolio.get(b,{}).get("Current_Weight")
            c = matrix.get(a,{}).get(b)

            if wa is None or wb is None or wa <= 0 or wb <= 0 or c is None:
                continue

            pairs.append((c,wa*wb))

    if not pairs:
        return 50.0, None

    den = sum(w for _,w in pairs)
    avg_corr = sum(c*w for c,w in pairs)/den if den > 0 else None

    if avg_corr is None:
        return 50.0, None

    score = clamp(80.0 - 60.0 * avg_corr)
    return score, avg_corr


def score_target_policy(portfolio):
    """
    Policy logic:
    - HARD_RANGE: evaluate numeric compliance.
    - FLEXIBLE: treated as intentionally unconstrained, not missing.
    - Policy Coverage therefore measures whether every held asset has an explicit policy,
      not whether every asset has a numeric target.
    """
    rows = read_csv(TARGET_POLICY)

    policy_map = {}
    for r in rows:
        asset = canonical_asset(r.get("Asset"))
        if not asset:
            continue
        policy_map[asset] = r

    status_rows = []
    hard_scores = []
    held_assets = [
        a for a,p in portfolio.items()
        if p.get("Current_Weight") is not None and p["Current_Weight"] > 0
    ]

    policy_defined_count = 0

    for asset in held_assets:
        current = portfolio[asset]["Current_Weight"]
        pol = policy_map.get(asset)

        if pol is None:
            status_rows.append({
                "Asset":asset,
                "Current_Weight":round(current,4),
                "Policy_Type":"UNDEFINED",
                "Target_Pct":"",
                "Lower_Bound_Pct":"",
                "Upper_Bound_Pct":"",
                "Status":"UNDEFINED",
                "Policy_Score":50.0,
                "Comment":"정책이 정의되지 않았습니다.",
            })
            continue

        policy_defined_count += 1
        ptype = pol.get("Policy_Type","").strip().upper()

        if ptype == "FLEXIBLE":
            status_rows.append({
                "Asset":asset,
                "Current_Weight":round(current,4),
                "Policy_Type":"FLEXIBLE",
                "Target_Pct":"",
                "Lower_Bound_Pct":"",
                "Upper_Bound_Pct":"",
                "Status":"FLEXIBLE",
                "Policy_Score":50.0,
                "Comment":"고정 목표 없이 유연하게 운용하는 자산입니다.",
            })
            continue

        if ptype == "HARD_RANGE":
            target = num(pol.get("Target_Pct"))
            lower = num(pol.get("Lower_Bound_Pct"))
            upper = num(pol.get("Upper_Bound_Pct"))

            if target is None or lower is None or upper is None:
                score = 50.0
                status = "INVALID_POLICY"
                comment = "정책 범위 설정값을 확인해야 합니다."
            else:
                if lower <= current <= upper:
                    status = "IN_RANGE"
                    score = 100.0
                    comment = "허용범위 안에 있어 정책상 정상입니다."
                elif current < lower:
                    status = "BELOW_RANGE"
                    gap = lower-current
                    score = clamp(100.0 * current / max(lower, 1e-12))
                    comment = f"허용하한 {lower:.1f}%보다 {gap:.1f}%p 낮아 신규자금으로 보충이 필요합니다."
                else:
                    status = "ABOVE_RANGE"
                    gap = current-upper
                    score = clamp(100.0 * (100.0-current) / max(100.0-upper, 1e-12))
                    comment = f"허용상한 {upper:.1f}%보다 {gap:.1f}%p 높아 추가매수를 억제할 필요가 있습니다."

            hard_scores.append(score)

            status_rows.append({
                "Asset":asset,
                "Current_Weight":round(current,4),
                "Policy_Type":"HARD_RANGE",
                "Target_Pct":target if target is not None else "",
                "Lower_Bound_Pct":lower if lower is not None else "",
                "Upper_Bound_Pct":upper if upper is not None else "",
                "Status":status,
                "Policy_Score":round(score,2),
                "Comment":comment,
            })

    coverage = (
        policy_defined_count/len(held_assets)
        if held_assets else 0.0
    )

    # Target-policy component reflects only explicit HARD_RANGE constraints.
    # FLEXIBLE assets are not penalized, and full policy coverage is reported separately.
    target_policy_score = (
        sum(hard_scores)/len(hard_scores)
        if hard_scores else 50.0
    )

    return target_policy_score, coverage, status_rows


def fx_exposure(portfolio, policy):
    ratios = {
        "Domestic_Equity": policy.get("Domestic_Equity_FX_Exposure_Ratio") or 0.0,
        "Foreign_Equity": policy.get("Foreign_Equity_FX_Exposure_Ratio") if policy.get("Foreign_Equity_FX_Exposure_Ratio") is not None else 1.0,
        "Bond": policy.get("Bond_FX_Exposure_Ratio") or 0.0,
        "Gold": policy.get("Gold_FX_Exposure_Ratio") if policy.get("Gold_FX_Exposure_Ratio") is not None else 1.0,
    }

    exposure = 0.0
    for asset,ratio in ratios.items():
        w = portfolio.get(asset,{}).get("Current_Weight")
        if w is not None:
            exposure += w*ratio

    lo = policy.get("FX_Target_Min_Pct")
    hi = policy.get("FX_Target_Max_Pct")

    if lo is None or hi is None or hi < lo:
        return exposure, 50.0, "REPORT_ONLY"

    if lo <= exposure <= hi:
        return exposure, 100.0, "IN_RANGE"

    distance = lo-exposure if exposure < lo else exposure-hi
    score = clamp(100.0 - 5.0*distance)

    return exposure, score, "OUT_OF_RANGE"


def health_state(score):
    if score >= 80: return "EXCELLENT"
    if score >= 65: return "GOOD"
    if score >= 50: return "FAIR"
    if score >= 35: return "CAUTION"
    return "WEAK"


def main():
    required = [
        PORTFOLIO_FILE,
        HISTORICAL_DATA,
        HEALTH_CONFIG,
        HEALTH_POLICY,
        TARGET_POLICY,
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        print("STEP 07 실행 불가 - 필수 파일 누락")
        for p in missing:
            print(" -",p)
        raise SystemExit(1)

    portfolio = load_portfolio()
    policy = load_policy()
    weights = load_component_weights()
    hist_rows = read_csv(HISTORICAL_DATA)

    concentration_score, hhi, effective_n = score_concentration(portfolio)

    _, port_rets = portfolio_return_series(hist_rows, portfolio)
    vol = annualized_vol(port_rets)
    mdd = max_drawdown(port_rets)

    vol_score = score_volatility(vol)
    dd_score = score_drawdown(mdd)

    corr_matrix = build_correlations(hist_rows)
    corr_score, avg_corr = score_correlation(corr_matrix, portfolio)

    target_policy_score, policy_coverage, target_status_rows = score_target_policy(portfolio)

    fx_pct, fx_score, fx_status = fx_exposure(portfolio, policy)

    components = {
        "Concentration":concentration_score,
        "Volatility":vol_score,
        "Max_Drawdown":dd_score,
        "Correlation_Diversification":corr_score,
        "Target_Drift":target_policy_score,
        "FX_Exposure":fx_score,
    }

    # REPORT_ONLY means no contribution to Portfolio Health.
    # Remaining scored component weights are renormalized to sum to 1.
    effective_weights = dict(weights)
    if fx_status == "REPORT_ONLY":
        effective_weights["FX_Exposure"] = 0.0

    scored_weight_sum = sum(
        effective_weights.get(k, 0.0)
        for k in components
    )
    if scored_weight_sum <= 0:
        raise ValueError("Portfolio Health 유효 weight 합계가 0입니다.")

    effective_weights = {
        k: effective_weights.get(k, 0.0) / scored_weight_sum
        for k in components
    }

    final = sum(
        components[k] * effective_weights[k]
        for k in components
    )

    component_rows = [
        {
            "Component":k,
            "Score":round(v,2),
            "Configured_Weight":round(weights.get(k,0.0),4),
            "Effective_Weight":round(effective_weights[k],4),
            "Weighted_Contribution":round(v*effective_weights[k],4),
            "Status":"REPORT_ONLY" if k=="FX_Exposure" and fx_status=="REPORT_ONLY" else "SCORED",
        }
        for k,v in components.items()
    ]

    with OUT_COMPONENTS.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(component_rows[0].keys()))
        w.writeheader()
        w.writerows(component_rows)

    with OUT_POLICY.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(target_status_rows[0].keys()))
        w.writeheader()
        w.writerows(target_status_rows)

    corr_fields = ["Asset"] + list(ASSET_RETURN_COL.keys())
    corr_rows = []
    for a in ASSET_RETURN_COL:
        row={"Asset":a}
        for b in ASSET_RETURN_COL:
            c=corr_matrix[a][b]
            row[b]="" if c is None else round(c,4)
        corr_rows.append(row)

    with OUT_CORR.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=corr_fields)
        w.writeheader()
        w.writerows(corr_rows)

    asset_rows=[]
    for asset,col in ASSET_RETURN_COL.items():
        vals=[num(r.get(col)) for r in hist_rows]
        vals=[v for v in vals if v is not None]
        avol=annualized_vol(vals)
        amdd=max_drawdown(vals)

        asset_rows.append({
            "Asset":asset,
            "Current_Weight":portfolio.get(asset,{}).get("Current_Weight",""),
            "Annualized_Volatility_Pct":"" if avol is None else round(avol,2),
            "Max_Drawdown_Pct":"" if amdd is None else round(amdd,2),
        })

    with OUT_ASSETS.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(asset_rows[0].keys()))
        w.writeheader()
        w.writerows(asset_rows)

    gold_status = next(
        (r for r in target_status_rows if r["Asset"]=="Gold"),
        None
    )

    comments=[]

    if concentration_score >= 65:
        comments.append("자산 집중도는 비교적 안정적입니다")

    if avg_corr is not None and avg_corr < 0.3:
        comments.append("자산 간 상관관계가 낮아 분산효과가 양호합니다")

    if gold_status:
        comments.append(
            f"금 정책: 현재 {gold_status['Current_Weight']:.1f}% / "
            f"목표 {gold_status['Target_Pct']}% / "
            f"허용범위 {gold_status['Lower_Bound_Pct']}~{gold_status['Upper_Bound_Pct']}% "
            f"→ {gold_status['Status']}"
        )

    summary=[{
        "Portfolio_Health_Score":round(final,2),
        "Health_State":health_state(final),
        "HHI":round(hhi,4),
        "Effective_Number_of_Assets":round(effective_n,2),
        "Portfolio_Annualized_Volatility_Pct":"" if vol is None else round(vol,2),
        "Portfolio_Max_Drawdown_Pct":"" if mdd is None else round(mdd,2),
        "Weighted_Average_Correlation":"" if avg_corr is None else round(avg_corr,4),
        "Policy_Coverage_Pct":round(policy_coverage*100,2),
        "Target_Policy_Score":round(target_policy_score,2),
        "Gold_Status":gold_status["Status"] if gold_status else "",
        "Estimated_FX_Exposure_Pct":round(fx_pct,2),
        "FX_Status":fx_status,
        "FX_Effective_Weight":round(effective_weights.get("FX_Exposure",0.0),4),
        "Target_Policy_Method":"HARD_RANGE_COMPLIANCE_V2",
        "Health_Formula":"weighted scored components; REPORT_ONLY components excluded and remaining weights renormalized",
        "Korean_Comment":" / ".join(comments[:3]),
    }]

    with OUT_SUMMARY.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    print("="*78)
    print("STEP 07 - PORTFOLIO HEALTH ENGINE v2 POLICY INTEGRATED")
    print("="*78)
    print(f"Portfolio Health : {final:.2f} / 100  {health_state(final)}")
    print()
    print("구성점수")
    print(f"Concentration    : {concentration_score:.2f}")
    print(f"Volatility       : {vol_score:.2f}")
    print(f"Max Drawdown     : {dd_score:.2f}")
    print(f"Correlation      : {corr_score:.2f}")
    print(f"Target Policy    : {target_policy_score:.2f}")
    print(f"FX Exposure      : {fx_score:.2f} ({fx_status}, EffectiveWeight={effective_weights.get('FX_Exposure',0.0):.4f})")
    print()
    print("핵심지표")
    print(f"HHI              : {hhi:.4f}")
    print(f"Effective Assets : {effective_n:.2f}")
    print(f"Ann. Volatility  : {'' if vol is None else f'{vol:.2f}%'}")
    print(f"Max Drawdown     : {'' if mdd is None else f'{mdd:.2f}%'}")
    print(f"Avg Correlation  : {'' if avg_corr is None else f'{avg_corr:.4f}'}")
    print(f"Policy Coverage  : {policy_coverage*100:.1f}%")
    print(f"FX Exposure      : {fx_pct:.2f}%")
    print()
    print("Target Policy")
    for r in target_status_rows:
        if r["Asset"] == "Gold":
            print(
                f"Gold              : 현재 {r['Current_Weight']:.2f}% | "
                f"목표 {r['Target_Pct']}% | "
                f"허용 {r['Lower_Bound_Pct']}~{r['Upper_Bound_Pct']}% | "
                f"{r['Status']}"
            )
        elif r["Policy_Type"] == "FLEXIBLE":
            print(f"{r['Asset']:<18}: FLEXIBLE")
    print()
    print("해석")
    for c in comments[:3]:
        print(f"→ {c}")
    print()
    print("Generated:")
    print(" - outputs/step07/portfolio_health_summary.csv")
    print(" - outputs/step07/portfolio_health_components.csv")
    print(" - outputs/step07/asset_correlation_matrix.csv")
    print(" - outputs/step07/asset_health_metrics.csv")
    print(" - outputs/step07/target_policy_status.csv")


if __name__ == "__main__":
    main()
