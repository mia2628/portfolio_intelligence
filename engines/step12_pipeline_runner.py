from pathlib import Path
import argparse
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
ENG=BASE/"engines"

CORE_STEPS=[
    ("STEP05 Risk", ENG/"step05_risk_engine.py"),
    ("STEP06 Opportunity", ENG/"step06_opportunity_engine.py"),
    ("STEP07 Portfolio Health", ENG/"step07_portfolio_health_engine.py"),
]

DECISION_STEPS=[
    ("STEP08 Monthly Allocation", ENG/"step08_monthly_allocation_engine.py"),
    ("STEP09 Rebalancing", ENG/"step09_rebalancing_engine.py"),
    ("STEP10 Recommendation", ENG/"step10_recommendation_engine.py"),
]

def run(cmd,label,input_text=None):
    print("="*86)
    print(label)
    print("="*86)
    print("COMMAND:", " ".join(map(str,cmd)))
    result=subprocess.run(
        [str(x) for x in cmd],
        cwd=BASE,
        input=input_text,
        text=True,
        check=False,
    )
    if result.returncode!=0:
        print(f"[FAIL] {label} exit={result.returncode}")
        raise SystemExit(result.returncode)
    print(f"[PASS] {label}")

def require(path):
    if not path.exists():
        raise SystemExit(f"[STOP] 필수 엔진 없음: {path}")

def run_core():
    for label,p in CORE_STEPS:
        require(p)
        run([sys.executable,p],label)

def run_decision(amount,last_review):
    if amount<=0:
        raise SystemExit("[STOP] monthly amount must be > 0")

    today=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")

    p8=DECISION_STEPS[0][1]
    p9=DECISION_STEPS[1][1]
    p10=DECISION_STEPS[2][1]
    for _,p in DECISION_STEPS: require(p)

    # STEP8 confirmed CLI interface.
    run([sys.executable,p8,"--amount",str(int(amount))],"STEP08 Monthly Allocation")

    # STEP9 existing engine accepts date inputs interactively.
    # Supply check-date then last-review-date through stdin, preserving its internal logic.
    stdin=f"{today}\n{last_review}\n"
    run([sys.executable,p9],"STEP09 Rebalancing",input_text=stdin)

    run([sys.executable,p10],"STEP10 Recommendation")

    print()
    print("="*86)
    print("STEP12 DECISION PIPELINE COMPLETE")
    print("="*86)
    print(f"Today KST          : {today}")
    print(f"Monthly Amount KRW : {int(amount):,}")
    print(f"Last Review Date   : {last_review}")
    print("→ 실제 투자금은 사용자가 입력한 값만 사용했습니다.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["core","decision","full"],required=True)
    ap.add_argument("--amount",type=float)
    ap.add_argument("--last-review")
    args=ap.parse_args()

    if args.mode in ("core","full"):
        run_core()

    if args.mode in ("decision","full"):
        if args.amount is None or not args.last_review:
            raise SystemExit(
                "[STOP] decision/full mode requires --amount and --last-review YYYYMMDD"
            )
        run_decision(args.amount,args.last_review)

if __name__=="__main__":
    main()
