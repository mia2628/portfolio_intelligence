from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
REG = BASE / "config" / "step11_5_indicator_source_registry.csv"
DIAG = BASE / "data" / "step11_data_diagnostics.csv"
OUT = BASE / "data" / "step11_5_coverage_report.csv"
SUMMARY = BASE / "data" / "step11_5_coverage_summary.csv"

def read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def current_status_map():
    if not DIAG.exists():
        return {}
    rows=read(DIAG)
    out={}
    for r in rows:
        ind=(r.get("Indicator") or "").strip()
        st=(r.get("Status") or "").strip().upper()
        if ind: out[ind]=st
    return out

def source_readiness(r, live_status):
    exactness=r["Exactness"]
    cred=r["Credential_or_License"]
    impl=r["Implementation"].lower()

    # Current pipeline proves data is already arriving.
    if live_status == "ACTUAL":
        # Still distinguish known proxy/licensing definition issues.
        if exactness in ("EXACT","DERIVED_EXACT","EXACT_EOD","EXACT_SERIES",
                         "EXACT_FOR_REFERENCE","DERIVED_EXACT_IF_HS_BASKET_FIXED",
                         "EXACT_REPORTED_DELAYED"):
            return "LIVE_READY"
        if exactness in ("EXACT_IF_DEFINED","EXACT_IF_CONSENSUS_DEFINED","DEFINITION_REQUIRED"):
            return "LIVE_BUT_DEFINITION_CHECK"
        if "LICENSE" in exactness or "PERMISSION" in exactness:
            return "LIVE_LICENSE_CHECK"
        return "LIVE_REVIEW"

    if r["Cost"] in ("LICENSED","PAID","PAID_FOR_CONSENSUS","PAID_OR_DERIVED"):
        return "LICENSE_OR_PAID_REQUIRED"
    if exactness == "DEFINITION_REQUIRED":
        return "DEFINITION_REQUIRED"
    if "Add " in r["Implementation"] or cred not in ("NONE","NONE_OR_DOWNLOAD_SESSION"):
        return "CONNECTOR_REQUIRED"
    return "NOT_LIVE"

def main():
    reg=read(REG)
    live=current_status_map()
    rows=[]

    for r in reg:
        ind=r["Indicator"]
        st=live.get(ind,"NO_CURRENT_STATUS")
        ready=source_readiness(r,st)
        rows.append({
            "Indicator":ind,
            "Factor_Group":r["Factor_Group"],
            "Current_Data_Status":st,
            "Source_Readiness":ready,
            "Exactness":r["Exactness"],
            "Primary_Source":r["Primary_Source"],
            "Cost":r["Cost"],
            "Update_Frequency":r["Update_Frequency"],
            "Data_Accuracy":r["Data_Accuracy"],
            "Credential_or_License":r["Credential_or_License"],
            "Caveat":r["Caveat"],
        })

    total=len(rows)
    live_count=sum(r["Current_Data_Status"]=="ACTUAL" for r in rows)
    strict_ready=sum(r["Source_Readiness"]=="LIVE_READY" for r in rows)
    definition_checks=sum("DEFINITION" in r["Source_Readiness"] for r in rows)
    license_checks=sum("LICENSE" in r["Source_Readiness"] or "PAID" in r["Source_Readiness"] for r in rows)
    connector_needed=sum(r["Source_Readiness"]=="CONNECTOR_REQUIRED" for r in rows)

    write(OUT,rows,["Indicator","Factor_Group","Current_Data_Status","Source_Readiness","Exactness",
                    "Primary_Source","Cost","Update_Frequency","Data_Accuracy",
                    "Credential_or_License","Caveat"])

    summary=[{
        "Total_Indicators":total,
        "Current_ACTUAL":live_count,
        "Current_Coverage_Pct":round(live_count/total*100,2) if total else 0,
        "Strict_Live_Ready":strict_ready,
        "Strict_Ready_Pct":round(strict_ready/total*100,2) if total else 0,
        "Definition_Checks":definition_checks,
        "License_or_Paid_Checks":license_checks,
        "Connector_Needed":connector_needed,
        "STEP12_READY":"YES" if strict_ready==total else "NO"
    }]
    write(SUMMARY,summary,list(summary[0].keys()))

    print("="*78)
    print("STEP 11.5 - FULL 27 INDICATOR COVERAGE AUDIT")
    print("="*78)
    print(f"Current ACTUAL       : {live_count}/{total}")
    print(f"Strict LIVE_READY    : {strict_ready}/{total}")
    print(f"Definition checks    : {definition_checks}")
    print(f"License/Paid checks  : {license_checks}")
    print(f"Connector needed     : {connector_needed}")
    print(f"STEP12 READY         : {'YES' if strict_ready==total else 'NO'}")
    print()
    print("중요: ACTUAL 숫자만으로 exact 27/27이라고 판단하지 않습니다.")
    print("      proxy, 라이선스, 정의 미확정 지표를 별도로 검사합니다.")
    print()
    print("Generated:")
    print(" - data/step11_5_coverage_report.csv")
    print(" - data/step11_5_coverage_summary.csv")

if __name__=="__main__":
    main()
