from pathlib import Path
import io
import requests
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "historical" / "historical_data.csv"

START = "2011-01-01"
END = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")


def fred_csv(series):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] FRED download failed: {series} -> {e}")
        return pd.DataFrame(columns=["Date", series])

    try:
        d = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        print(f"[WARN] CSV parse failed: {series} -> {e}")
        return pd.DataFrame(columns=["Date", series])

    if d.shape[1] < 2:
        print(f"[WARN] Unexpected FRED format: {series}")
        return pd.DataFrame(columns=["Date", series])

    d = d.iloc[:, :2]
    d.columns = ["Date", series]

    d["Date"] = pd.to_datetime(
        d["Date"],
        errors="coerce"
    )

    d[series] = pd.to_numeric(
        d[series],
        errors="coerce"
    )

    return d.dropna(subset=["Date"])


def monthly_level(series, how="mean"):
    d = fred_csv(series)

    if d.empty:
        idx = pd.date_range(
            START,
            END,
            freq="MS"
        )
        return pd.Series(
            np.nan,
            index=idx,
            name=series
        )

    d = d.set_index("Date")
    s = d[series]

    if how == "last":
        s = s.resample("MS").last()
    else:
        s = s.resample("MS").mean()

    idx = pd.date_range(
        START,
        END,
        freq="MS"
    )

    return s.reindex(idx)


def pct(s):
    return s.pct_change() * 100.0


def diff_bp(s):
    return s.diff() * 100.0


def safe_assign(out, column, func):
    try:
        out[column] = func()
        print(
            f"[OK] {column}: "
            f"{out[column].notna().sum()} non-null rows"
        )
    except Exception as e:
        print(f"[WARN] {column} failed -> {e}")
        out[column] = np.nan


def main():

    current_month_start = pd.Timestamp.today().normalize().replace(day=1)
    idx = pd.date_range(
        START,
        current_month_start,
        freq="MS"
    )

    out = pd.DataFrame(index=idx)

    print("=" * 80)
    print("STEP 04 HISTORICAL DATA COLLECTOR")
    print("=" * 80)

    # ---------------------------------------------------------
    # RATE DATA
    # ---------------------------------------------------------

    gs10 = monthly_level("GS10")
    gs2 = monthly_level("GS2")
    fii10 = monthly_level("FII10")
    krbond = monthly_level("INTGSBKRM193N")
    kr10 = monthly_level("IRLTLT01KRM156N")
    fedfunds = monthly_level("FEDFUNDS")

    out["US10Y"] = diff_bp(gs10)
    out["US2Y"] = diff_bp(gs2)
    out["US_REAL10Y"] = diff_bp(fii10)
    out["US_10Y2Y_SPREAD"] = diff_bp(
        gs10 - gs2
    )

    out["KR3Y"] = diff_bp(krbond)
    out["KR10Y"] = diff_bp(kr10)

    out["FED_HIKE_EXPECTATION"] = diff_bp(
        gs2 - fedfunds
    )

    out["BOK_HIKE_EXPECTATION"] = diff_bp(
        krbond
    )

    # ---------------------------------------------------------
    # INFLATION DATA
    # ---------------------------------------------------------

    safe_assign(
        out,
        "US_CPI",
        lambda: pct(
            monthly_level("CPIAUCSL")
        )
    )

    safe_assign(
        out,
        "US_CORE_CPI",
        lambda: pct(
            monthly_level("CPILFESL")
        )
    )

    safe_assign(
        out,
        "US_CORE_PCE",
        lambda: pct(
            monthly_level("PCEPILFE")
        )
    )

    safe_assign(
        out,
        "US_BREAKEVEN_10Y",
        lambda: diff_bp(
            monthly_level("T10YIE")
        )
    )

    # Korea CPI:
    # leave blank until BOK/OECD source is finalized
    out["KR_CPI"] = np.nan

    # ---------------------------------------------------------
    # FX / RISK DATA
    # ---------------------------------------------------------

    safe_assign(
        out,
        "USDKRW",
        lambda: pct(
            monthly_level("EXKOUS")
        )
    )

    safe_assign(
        out,
        "DXY",
        lambda: pct(
            monthly_level("TWEXBGSMTH")
        )
    )

    safe_assign(
        out,
        "VIX",
        lambda: pct(
            monthly_level("VIXCLS")
        )
    )

    # MOVE:
    # no stable free long-history endpoint here yet
    out["MOVE"] = np.nan

    safe_assign(
        out,
        "US_HY_SPREAD",
        lambda: diff_bp(
            monthly_level("BAA10Y")
        )
    )

    safe_assign(
        out,
        "FCI_TIGHTENING",
        lambda: monthly_level(
            "NFCI"
        ).diff()
    )

    # Geopolitical Risk:
    # external dataset to be added separately
    out["GEOPOLITICAL_RISK"] = np.nan

    # ---------------------------------------------------------
    # GROWTH / LABOR DATA
    # ---------------------------------------------------------

    safe_assign(
        out,
        "US_ISM_MFG",
        lambda: pct(
            monthly_level("IPMAN")
        )
    )

    safe_assign(
        out,
        "US_UNEMPLOYMENT",
        lambda: monthly_level(
            "UNRATE"
        ).diff()
    )

    safe_assign(
        out,
        "US_INITIAL_CLAIMS",
        lambda: monthly_level(
            "ICSA"
        ).diff() / 1000.0
    )

    safe_assign(
        out,
        "US_NFP_SURPRISE",
        lambda: monthly_level(
            "PAYEMS"
        ).diff()
    )

    safe_assign(
        out,
        "KR_EXPORT_GROWTH",
        lambda: monthly_level(
            "KORXTEXVA01NCMLM"
        ).pct_change(12) * 100.0
    )

    # Korea semiconductor exports:
    # Korea Customs data will be added separately
    out["KR_SEMI_EXPORT_GROWTH"] = np.nan

    # ---------------------------------------------------------
    # GOLD-SPECIFIC DATA
    # ---------------------------------------------------------

    # Central-bank gold net buying:
    # quarterly WGC data will be added separately
    out["CB_GOLD_NET_BUYING"] = np.nan

    # ---------------------------------------------------------
    # ASSET RETURN SERIES
    # ---------------------------------------------------------

    safe_assign(
        out,
        "RET_DOMESTIC",
        lambda: pct(
            monthly_level(
                "SPASTT01KRM661N"
            )
        )
    )

    safe_assign(
        out,
        "RET_FOREIGN",
        lambda: pct(
            monthly_level(
                "SPASTT01USM661N"
            )
        )
    )

    # Korean bond return proxy:
    # return ≈ carry/12 - duration * yield_change
    # Duration is provisional until actual bond holdings are known.
    duration = 6.0

    safe_assign(
        out,
        "RET_BOND",
        lambda: (
            kr10.shift(1) / 12.0
            - duration * kr10.diff()
        )
    )

    # GOLD RETURN
    #
    # Previous FRED ID:
    # GOLDPMGBD228NLBM
    # is no longer available via fredgraph.
    #
    # Use ID7108 as a temporary long-history gold-price proxy.
    # This is NOT spot gold itself; it is a historical gold-related
    # price index proxy for STEP 4 calibration.
    safe_assign(
        out,
        "RET_GOLD",
        lambda: pct(
            monthly_level("ID7108")
        )
    )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    out.index.name = "Date"

    out.reset_index().to_csv(
        OUT,
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("=" * 80)
    print(f"SAVED: {OUT}")
    print(f"ROWS : {len(out)}")
    print("=" * 80)

    print()
    print("NON-NULL COUNTS")
    print("-" * 80)

    print(
        out.notna()
        .sum()
        .sort_values(
            ascending=False
        )
    )

    print()
    print(
        "NOTE: KR_CPI, MOVE, GEOPOLITICAL_RISK, "
        "KR_SEMI_EXPORT_GROWTH, CB_GOLD_NET_BUYING "
        "remain blank until their dedicated collectors are added."
    )


if __name__ == "__main__":
    main()
