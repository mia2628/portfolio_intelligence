from pathlib import Path
import csv, sys

BASE=Path(__file__).resolve().parents[1]

checks=[
("STEP3",BASE/"data/step03_results.csv"),
("STEP5 Risk",BASE/"outputs/step05/risk_scores.csv"),
("STEP6 Opportunity",BASE/"outputs/step06/opportunity_scores.csv"),
("STEP7 Health",BASE/"outputs/step07/portfolio_health_summary.csv"),
]

# tolerate known alternative summary filenames while still being explicit
alternates={
"STEP6 Opportunity":[BASE/"outputs/step06/opportunity_scores.csv",BASE/"outputs/step06/opportunity_results.csv"],
"STEP7 Health":[BASE/"outputs/step07/portfolio_health_summary.csv",BASE/"outputs/step07/portfolio_health.csv"],
}

print("="*86)
print("STEP12 AUTOMATION STATUS CHECK")
print("="*86)

failed=[]
for name,path in checks:
    candidates=alternates.get(name,[path])
    found=next((x for x in candidates if x.exists()),None)
    if found:
        print(f"PASS {name:<20} {found.relative_to(BASE)}")
    else:
        print(f"FAIL {name:<20} expected one of: {', '.join(str(x.relative_to(BASE)) for x in candidates)}")
        failed.append(name)

if failed:
    print()
    print("[WARN] 출력 파일명이 현재 엔진과 다를 수 있습니다.")
    print("엔진 실행 자체가 성공했다면 해당 Generated 로그를 확인하세요.")
    raise SystemExit(2)

print()
print("PASS: STEP12 automatic core pipeline outputs detected.")
