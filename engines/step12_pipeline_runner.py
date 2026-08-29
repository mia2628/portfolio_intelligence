from pathlib import Path
import argparse, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
ENG=BASE/"engines"

def run(cmd,label,input_text=None):
    print("="*86);print(label);print("="*86)
    r=subprocess.run([str(x) for x in cmd],cwd=BASE,input=input_text,text=True)
    if r.returncode!=0:raise SystemExit(r.returncode)
    print(f"[PASS] {label}")

def req(p):
    if not p.exists():raise SystemExit(f"[STOP] missing: {p}")

def core():
    sequence=[
        ("STEP05 Risk",ENG/"step05_risk_engine.py","post5"),
        ("STEP06 Opportunity",ENG/"step06_opportunity_engine.py","post6"),
        ("STEP07 Portfolio Health",ENG/"step07_portfolio_health_engine.py","post7"),
    ]
    patch=ENG/"step12_consistency_patch.py";req(patch)
    for label,p,stage in sequence:
        req(p);run([sys.executable,p],label)
        run([sys.executable,patch,"--stage",stage],label+" Consistency Patch")
    run([sys.executable,patch,"--stage","check"],"STEP12 Math/Policy Check")

def decision(amount,last_review):
    for p in [ENG/"step08_monthly_allocation_engine.py",ENG/"step09_rebalancing_engine.py",ENG/"step10_recommendation_engine.py"]:
        req(p)
    if amount<=0:raise SystemExit("[STOP] amount must be >0")
    today=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    run([sys.executable,ENG/"step08_monthly_allocation_engine.py","--amount",str(int(amount))],"STEP08")
    run([sys.executable,ENG/"step09_rebalancing_engine.py"],"STEP09",f"{today}\n{last_review}\n")
    run([sys.executable,ENG/"step10_recommendation_engine.py"],"STEP10")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--mode",choices=["core","decision","full"],required=True)
    a.add_argument("--amount",type=float);a.add_argument("--last-review")
    x=a.parse_args()
    if x.mode in ("core","full"):core()
    if x.mode in ("decision","full"):
        if x.amount is None or not x.last_review:raise SystemExit("--amount and --last-review required")
        decision(x.amount,x.last_review)
if __name__=="__main__":main()
