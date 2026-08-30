from pathlib import Path
import argparse, csv, json
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/"data"
OUT=BASE/"outputs"/"portfolio"
STEP08=BASE/"outputs"/"step08"
STATE=DATA/"portfolio_invested_state.csv"
ACCOUNT=DATA/"portfolio_account_snapshot.csv"
ALLOC=STEP08/"monthly_allocation.csv"
SUMMARY=OUT/"portfolio_invested_summary.csv"
HISTORY=OUT/"portfolio_contribution_history.csv"

ASSET_ORDER=["Bond","Domestic_Equity","Foreign_Equity","Cash","Other","Gold"]
KR={
    "Bond":"채권형","Domestic_Equity":"국내주식","Foreign_Equity":"해외주식",
    "Cash":"유동성","Other":"기타","Gold":"금"
}

def read(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def num(v,d=0.0):
    try:return float(str(v).replace(",","").strip())
    except:return d

def load_state():
    if not STATE.exists(): raise SystemExit(f"[STOP] state missing: {STATE}")
    rows=read(STATE)
    d={}
    for r in rows:
        a=r["Asset"]
        d[a]={
            "Asset":a,
            "Asset_KR":r.get("Asset_KR") or KR.get(a,a),
            "Account":r.get("Account",""),
            "Invested_Amount_KRW":round(num(r.get("Invested_Amount_KRW"))),
            "Source":r.get("Source","")
        }
    for a in ASSET_ORDER:
        if a not in d:
            d[a]={"Asset":a,"Asset_KR":KR[a],"Account":"GOLD" if a=="Gold" else "ISA",
                  "Invested_Amount_KRW":0,"Source":"AUTO_CREATED"}
    return d

def summary_rows(state):
    total=sum(v["Invested_Amount_KRW"] for v in state.values())
    rows=[]
    for a in ASSET_ORDER:
        v=state[a]["Invested_Amount_KRW"]
        rows.append({
            "Asset":a,"Asset_KR":state[a]["Asset_KR"],"Account":state[a]["Account"],
            "Invested_Amount_KRW":round(v),
            "Portfolio_Weight_Pct":round(100*v/total,4) if total>0 else 0,
            "Total_Invested_Amount_KRW":round(total),
            "Basis":"INVESTED_PRINCIPAL"
        })
    return rows

def save_summary(state):
    rows=summary_rows(state)
    write(SUMMARY,rows,list(rows[0].keys()))
    return rows

def print_state(state,title="현재 포트폴리오"):
    rows=summary_rows(state)
    total=rows[0]["Total_Invested_Amount_KRW"] if rows else 0
    isa=sum(r["Invested_Amount_KRW"] for r in rows if r["Account"]=="ISA")
    gold=sum(r["Invested_Amount_KRW"] for r in rows if r["Account"]=="GOLD")
    print()
    print("="*82)
    print(title)
    print("="*82)
    print(f"전체 투자원금 : {total:,.0f}원")
    print(f"ISA 투자원금  : {isa:,.0f}원")
    print(f"금 투자원금   : {gold:,.0f}원")
    print("-"*82)
    for r in rows:
        print(f"{r['Asset_KR']:<8} {r['Invested_Amount_KRW']:>14,.0f}원  {r['Portfolio_Weight_Pct']:>7.2f}%")
    print("-"*82)
    print("※ 비중은 평가금액이 아니라 투자원금 기준입니다.")
    return rows

def load_last_allocation():
    if not ALLOC.exists():
        raise SystemExit("[STOP] STEP8 monthly_allocation.csv가 없습니다. 먼저 Portfolio Monthly Decision을 실행하세요.")
    rows=read(ALLOC)
    d={}
    for r in rows:
        a=r.get("Asset")
        if not a: continue
        share=num(r.get("Allocation_Share_Pct"),0)/100
        d[a]=share
    s=sum(d.values())
    if s<=0: raise SystemExit("[STOP] STEP8 배분비율 합계가 0입니다.")
    return {a:v/s for a,v in d.items() if v>0}

def allocate_integer(total,shares):
    raw={a:total*w for a,w in shares.items()}
    ints={a:int(v) for a,v in raw.items()}
    rem=int(round(total))-sum(ints.values())
    if rem>0:
        order=sorted(shares,key=lambda a:(raw[a]-ints[a]),reverse=True)
        for a in order[:rem]:
            ints[a]+=1
    return ints

def preview(amount):
    amount=round(float(amount))
    if amount<=0: raise SystemExit("[STOP] amount must be >0")
    state=load_state()
    shares=load_last_allocation()
    add=allocate_integer(amount,shares)
    projected={a:dict(v) for a,v in state.items()}
    for a,x in add.items():
        if a not in projected:
            projected[a]={"Asset":a,"Asset_KR":KR.get(a,a),"Account":"GOLD" if a=="Gold" else "ISA",
                          "Invested_Amount_KRW":0,"Source":"AUTO_CREATED"}
        projected[a]["Invested_Amount_KRW"]+=x
    print_state(state,"[현재 포트폴리오 - 실제 원금 기준]")
    print()
    print(f"시나리오 신규자금 : {amount:,.0f}원")
    print("STEP8 배분비율을 적용한 미래 시나리오이며 실제 상태는 변경하지 않습니다.")
    print_state(projected,"[시나리오 적용 후 예상 포트폴리오]")
    return projected

def update_account_snapshot(add):
    if not ACCOUNT.exists(): return
    rows=read(ACCOUNT)
    inc={"ISA":0,"GOLD":0}
    for a,x in add.items():
        inc["GOLD" if a=="Gold" else "ISA"]+=x
    for r in rows:
        acct=r.get("Account")
        if acct in inc:
            r["Invested_Amount_KRW"]=str(round(num(r.get("Invested_Amount_KRW"))+inc[acct]))
            # Evaluation amount/return intentionally unchanged.
            r["Update_Mode"]="INVESTED_PRINCIPAL_UPDATED_EVALUATION_UNCHANGED"
    write(ACCOUNT,rows,list(rows[0].keys()))

def append_history(amount,add,before_total,after_total):
    fields=["Applied_At_KST","Actual_Contribution_KRW","Allocation_JSON",
            "Before_Total_Invested_KRW","After_Total_Invested_KRW","Basis"]
    old=read(HISTORY) if HISTORY.exists() else []
    old.append({
        "Applied_At_KST":datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "Actual_Contribution_KRW":round(amount),
        "Allocation_JSON":json.dumps(add,ensure_ascii=False,sort_keys=True),
        "Before_Total_Invested_KRW":round(before_total),
        "After_Total_Invested_KRW":round(after_total),
        "Basis":"LAST_STEP8_ALLOCATION"
    })
    write(HISTORY,old,fields)

def apply(amount):
    amount=round(float(amount))
    if amount<=0: raise SystemExit("[STOP] amount must be >0")
    state=load_state()
    shares=load_last_allocation()
    add=allocate_integer(amount,shares)
    before=sum(v["Invested_Amount_KRW"] for v in state.values())
    before_rows=print_state(state,"[실제 반영 전 포트폴리오]")
    print()
    print(f"실제 신규 투자금 : {amount:,.0f}원")
    print("실제 반영 배분:")
    for a,x in sorted(add.items(),key=lambda kv:kv[1],reverse=True):
        print(f"  {KR.get(a,a):<8} {x:>14,.0f}원")

    for a,x in add.items():
        state[a]["Invested_Amount_KRW"]+=x
        state[a]["Source"]="ACTUAL_CONTRIBUTION_APPLIED"

    rows=[]
    for a in ASSET_ORDER:
        rows.append(state[a])
    write(STATE,rows,["Asset","Asset_KR","Account","Invested_Amount_KRW","Source"])
    update_account_snapshot(add)
    save_summary(state)
    after=sum(v["Invested_Amount_KRW"] for v in state.values())
    append_history(amount,add,before,after)

    print_state(state,"[실제 반영 후 포트폴리오]")
    print(f"[APPLIED] 실제 투자원금 +{amount:,.0f}원 영구 반영 완료")
    print("※ 평가금액은 자동 변경하지 않았습니다.")
    return state

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["show","preview","apply"],required=True)
    ap.add_argument("--amount",type=float)
    a=ap.parse_args()
    state=load_state()
    save_summary(state)
    if a.mode=="show":
        print_state(state,"[현재 포트폴리오 - 실제 투자원금 기준]")
    elif a.mode=="preview":
        if a.amount is None: raise SystemExit("--amount required")
        preview(a.amount)
    else:
        if a.amount is None: raise SystemExit("--amount required")
        apply(a.amount)

if __name__=="__main__":
    main()
