from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE / "config"
DATA_DIR = BASE / "data"
STEP04_DIR = BASE / "outputs" / "step04"
STEP05_DIR = BASE / "outputs" / "step05"
STEP05_DIR.mkdir(parents=True, exist_ok=True)

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def fnum(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))

def risk_from_change(indicator, value):
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
    return clamp(50.0 + 50.0 * intensity * direction)

def avg_conf(rows, indicator):
    vals = [fnum(r.get("Empirical_Confidence")) for r in rows if r.get("Indicator") == indicator]
    vals = [v for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else 0.50

def state(score):
    if score < 30: return "LOW"
    if score < 50: return "MODERATE_LOW"
    if score < 70: return "MODERATE_HIGH"
    if score < 85: return "HIGH"
    return "EXTREME"

def main():
    risk_cfg_file = CONFIG_DIR / "risk_config.csv"
    asset_sens_file = CONFIG_DIR / "asset_risk_sensitivity.csv"
    market_file = DATA_DIR / "step03_market_inputs.csv"
    percentile_file = STEP04_DIR / "percentile_results.csv"
    confidence_file = STEP04_DIR / "empirical_confidence.csv"

    required = [risk_cfg_file, asset_sens_file, market_file, percentile_file, confidence_file]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("STEP 05 실행 불가 - 필수 파일 누락")
        for p in missing: print(" -", p)
        raise SystemExit(1)

    risk_cfg = [r for r in read_csv(risk_cfg_file) if fnum(r.get("Enabled"),0)==1]
    market = {r["Indicator"]: fnum(r.get("Observed_Change")) for r in read_csv(market_file)}
    percentiles = {r["Indicator"]: fnum(r.get("Historical_Percentile")) for r in read_csv(percentile_file)}
    conf_rows = read_csv(confidence_file)

    details=[]; weighted_sum=0.0; total_weight=0.0
    for r in risk_cfg:
        ind=r["Indicator"]; weight=fnum(r["Base_Weight"],0.0)
        obs=market.get(ind); hp=percentiles.get(ind)
        current=risk_from_change(ind,obs)
        historical=50.0 if hp is None else clamp(hp)
        conf=avg_conf(conf_rows,ind)
        blended=0.60*current+0.40*historical
        adjusted=50.0+(blended-50.0)*conf
        weighted_sum += adjusted*weight; total_weight += weight
        details.append({
            "Indicator":ind,"Risk_Block":r["Risk_Block"],
            "Observed_Change":"" if obs is None else obs,
            "Historical_Percentile":"" if hp is None else hp,
            "Empirical_Confidence":round(conf,4),
            "Current_Risk":round(current,2),
            "Historical_Risk":round(historical,2),
            "Adjusted_Risk":round(adjusted,2),
            "Weight":weight
        })

    portfolio_risk = weighted_sum/total_weight if total_weight else 50.0
    sens={r["Asset"]:fnum(r["Risk_Sensitivity"],1.0) for r in read_csv(asset_sens_file)}
    scores=[{"Asset":"PORTFOLIO","Risk_Score":round(portfolio_risk,2),"Risk_State":state(portfolio_risk)}]
    for asset,s in sens.items():
        score=clamp(50.0+(portfolio_risk-50.0)*s)
        scores.append({"Asset":asset,"Risk_Score":round(score,2),"Risk_State":state(score)})

    with (STEP05_DIR/"risk_details.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=details[0].keys()); w.writeheader(); w.writerows(details)
    with (STEP05_DIR/"risk_scores.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["Asset","Risk_Score","Risk_State"]); w.writeheader(); w.writerows(scores)

    print("="*72)
    print("STEP 05 - RISK ENGINE")
    print("="*72)
    for r in scores:
        print(f"{r['Asset']:<18} {r['Risk_Score']:>6.2f} / 100 {r['Risk_State']}")
    print("Generated:")
    print(" - outputs/step05/risk_scores.csv")
    print(" - outputs/step05/risk_details.csv")

if __name__ == "__main__":
    main()
