
from pathlib import Path
import io, requests, pandas as pd, numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "historical" / "historical_data.csv"
START = "2011-01-01"
END = "2026-07-31"

def fred_csv(series):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["Date", series]
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d[series] = pd.to_numeric(d[series], errors="coerce")
    return d.dropna(subset=["Date"])

def monthly_level(series, how="mean"):
    d = fred_csv(series).set_index("Date")
    s = d[series]
    if how == "last":
        s = s.resample("MS").last()
    else:
        s = s.resample("MS").mean()
    return s.loc[START:END]

def pct(s):
    return s.pct_change() * 100.0

def diff_bp(s):
    return s.diff() * 100.0

def main():
    idx = pd.date_range("2011-01-01","2026-07-01",freq="MS")
    out = pd.DataFrame(index=idx)

    # Rates
    gs10 = monthly_level("GS10")
    gs2 = monthly_level("GS2")
    fii10 = monthly_level("FII10")
    krbond = monthly_level("INTGSBKRM193N")
    kr10 = monthly_level("IRLTLT01KRM156N")
    fedfunds = monthly_level("FEDFUNDS")

    out["US10Y"] = diff_bp(gs10)
    out["US2Y"] = diff_bp(gs2)
    out["US_REAL10Y"] = diff_bp(fii10)
    out["US_10Y2Y_SPREAD"] = diff_bp(gs10-gs2)
    out["KR3Y"] = diff_bp(krbond)
    out["KR10Y"] = diff_bp(kr10)
    out["FED_HIKE_EXPECTATION"] = diff_bp(gs2-fedfunds)
    out["BOK_HIKE_EXPECTATION"] = diff_bp(krbond)

    # Inflation
    out["US_CPI"] = pct(monthly_level("CPIAUCSL"))
    out["US_CORE_CPI"] = pct(monthly_level("CPILFESL"))
    out["US_CORE_PCE"] = pct(monthly_level("PCEPILFE"))
    out["US_BREAKEVEN_10Y"] = diff_bp(monthly_level("T10YIE"))
    # KR_CPI intentionally left blank until BOK/OECD mapping is finalized.

    # FX / risk
    out["USDKRW"] = pct(monthly_level("EXKOUS"))
    out["DXY"] = pct(monthly_level("TWEXBGSMTH"))
    out["VIX"] = pct(monthly_level("VIXCLS"))
    # MOVE intentionally blank: no stable free 15y endpoint.
    out["US_HY_SPREAD"] = diff_bp(monthly_level("BAA10Y"))
    out["FCI_TIGHTENING"] = monthly_level("NFCI").diff()
    # GPR intentionally blank in this collector; external Excel endpoint varies.

    # Growth/labor
    out["US_ISM_MFG"] = pct(monthly_level("IPMAN"))
    out["US_UNEMPLOYMENT"] = monthly_level("UNRATE").diff()
    claims = monthly_level("ICSA")
    out["US_INITIAL_CLAIMS"] = claims.diff()/1000.0
    out["US_NFP_SURPRISE"] = monthly_level("PAYEMS").diff()

    exports = monthly_level("KORXTEXVA01NCMLM")
    out["KR_EXPORT_GROWTH"] = exports.pct_change(12)*100.0
    # KR semiconductor exports and central-bank gold buying need external sources.

    # Asset returns
    out["RET_DOMESTIC"] = pct(monthly_level("SPASTT01KRM661N"))
    try:
        out["RET_FOREIGN"] = pct(monthly_level("SPASTT01USM661N"))
    except Exception:
        out["RET_FOREIGN"] = np.nan

    # Approx Korean bond return proxy until actual bond holdings/duration are known.
    # y is in percent; delta yield in decimal = diff/100.
    duration = 6.0
    out["RET_BOND"] = (kr10.shift(1)/12.0) - duration*(kr10.diff())  # approximate percent return
    gold = monthly_level("GOLDPMGBD228NLBM")
    out["RET_GOLD"] = pct(gold)

    # Explicit blanks for columns requiring external/manual feeds.
    for c in ["KR_CPI","MOVE","GEOPOLITICAL_RISK","KR_SEMI_EXPORT_GROWTH","CB_GOLD_NET_BUYING"]:
        if c not in out:
            out[c] = np.nan

    out.index.name = "Date"
    out.reset_index().to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"saved: {OUT}")
    print("rows:", len(out))
    print("non-null counts:")
    print(out.notna().sum().sort_values())

if __name__ == "__main__":
    main()
