from pathlib import Path
import argparse, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
ENG=BASE/"engines"

def run(cmd,label,input_text=None):
    print("="*88);print(label);print("="*88)
    r=subprocess.run([str(x) for x in cmd],cwd=BASE,input=input_text,text=True)
    if r.returncode!=0: raise SystemExit(r.returncode)
    print(f"[PASS] {label}")

def req(p):
    if not p.exists():raise SystemExit(f"[STOP] missing: {p}")

def core():
    state=ENG/"step12_portfolio_state_engine.py"; req(state)
    run([sys.executable,state,"--mode","show"],"Portfolio Invested State")
    for label,name in [
        ("STEP05 Risk","step05_risk_engine.py"),
        ("STEP06 Opportunity","step06_opportunity_engine.py"),
        ("STEP07 Portfolio Health","step07_portfolio_health_engine.py"),
    ]:
        p=ENG/name;req(p);run([sys.executable,p],label)
    chk=ENG/"step12_final_integrated_check.py";req(chk)
    run([sys.executable,chk],"STEP12 Final Integrated Check")

def decision(amount,last_review):
    if amount<=0:raise SystemExit("[STOP] amount must be >0")
    today=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    for name in ["step08_monthly_allocation_engine.py","step09_rebalancing_engine.py","step10_recommendation_engine.py"]:
        req(ENG/name)
    run([sys.executable,ENG/"step08_monthly_allocation_engine.py","--amount",str(int(amount))],"STEP08")
    # Preview only: no mutation of actual invested state.
    run([sys.executable,ENG/"step12_portfolio_state_engine.py","--mode","preview","--amount",str(int(amount))],"Portfolio Scenario Preview")
    run([sys.executable,ENG/"step09_rebalancing_engine.py"],"STEP09",f"{today}\n{last_review}\n")
    run([sys.executable,ENG/"step10_recommendation_engine.py"],"STEP10")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["core","decision","full"],required=True)
    ap.add_argument("--amount",type=float)
    ap.add_argument("--last-review")
    a=ap.parse_args()
    if a.mode in ("core","full"):core()
    if a.mode in ("decision","full"):
        if a.amount is None or not a.last_review:raise SystemExit("--amount and --last-review required")
        decision(a.amount,a.last_review)
if __name__=="__main__":main()
