from pathlib import Path
import csv
import argparse

BASE=Path(__file__).resolve().parents[1]
STEP06=BASE/"outputs"/"step06"
STEP07=BASE/"outputs"/"step07"
STEP08=BASE/"outputs"/"step08"
STEP08.mkdir(parents=True,exist_ok=True)

PORTFOLIO_SUMMARY=BASE/"portfolio_summary.csv"
OPPORTUNITY=STEP06/"opportunity_scores.csv"
TARGET_POLICY=STEP07/"target_policy_status.csv"

ASSETS=["Domestic_Equity","Foreign_Equity","Bond","Gold"]

def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def num(v,d=None):
    try:
        if v is None or v=="": return d
        return float(v)
    except:
        return d

def pick(row,names):
    for n in names:
        if n in row:
            v=num(row.get(n))
            if v is not None: return v
    return None

def load_portfolio():
    rows=read_csv(PORTFOLIO_SUMMARY)
    vals={}; wts={}; total=None
    for r in rows:
        a=r.get("Asset")
        if a not in ASSETS and a not in ["Cash","Other"]: continue
        v=pick(r,["Current_Value_KRW","Asset_Current_Value","Current_Value","Value_KRW"])
        w=pick(r,["Portfolio_Weight_Pct","Portfolio_Weight","Current_Portfolio_Weight","Current_Weight","Weight_Pct","Weight"])
        if v is not None: vals[a]=v
        if w is not None: wts[a]=w
        if total is None:
            total=pick(r,["Total_Current_Value","Portfolio_Total_Current_Value","Total_Portfolio_Value"])
    if total is None and vals: total=sum(vals.values())
    if total is None:
        raise ValueError("portfolio_summary.csv에서 전체 현재가치를 읽지 못했습니다.")
    for a,w in wts.items():
        if a not in vals: vals[a]=total*w/100
    return total,vals,wts

def load_opportunity():
    d={}
    for r in read_csv(OPPORTUNITY):
        a=r.get("Asset")
        if a in ASSETS:
            d[a]=num(r.get("Opportunity_Score"),50.0)
    miss=[a for a in ASSETS if a not in d]
    if miss:
        raise ValueError("STEP6 Opportunity 누락: "+", ".join(miss))
    return d

def load_gold_policy():
    for r in read_csv(TARGET_POLICY):
        if r.get("Asset")=="Gold":
            return {
                "Current":num(r.get("Current_Weight")),
                "Target":num(r.get("Target_Pct"),20.0),
                "Lower":num(r.get("Lower_Bound_Pct"),18.0),
                "Upper":num(r.get("Upper_Bound_Pct"),22.0),
                "Status":r.get("Status","")
            }
    raise ValueError("Gold 정책을 찾지 못했습니다.")

def attractiveness(score,strength):
    return max(0.2,1.0+strength*((score-50)/25))

def gold_needed(total,gold,contribution,target_pct):
    return max(0.0,target_pct/100*(total+contribution)-gold)

def normalize(d):
    s=sum(d.values())
    return {k:v/s for k,v in d.items()} if s>0 else d

def allocate_monthly(
    contribution_krw,
    opportunity_tilt_strength=0.40,
    flexible_asset_max_share=0.50,
    gold_opportunity_cap_pct=20.0,
    minimum_allocation_krw=10000
):
    if contribution_krw is None:
        raise ValueError("이번 달 투자금액을 입력해야 합니다.")
    contribution=float(contribution_krw)
    if contribution<=0:
        raise ValueError("투자금액은 0원보다 커야 합니다.")

    total,vals,wts=load_portfolio()
    opp=load_opportunity()
    gp=load_gold_policy()

    gold_val=vals.get("Gold")
    if gold_val is None:
        gw=wts.get("Gold")
        if gw is None: raise ValueError("Gold 현재가치/비중을 읽지 못했습니다.")
        gold_val=total*gw/100

    current_gold=100*gold_val/total
    alloc={a:0.0 for a in ASSETS}

    # 1) POLICY FIRST: Gold below 18% -> use new money to approach lower bound
    policy_gold=0.0
    if current_gold < gp["Lower"]:
        policy_gold=min(
            contribution,
            gold_needed(total,gold_val,contribution,gp["Lower"])
        )
        alloc["Gold"]+=policy_gold

    remain=max(0.0,contribution-policy_gold)

    # 2) Opportunity tilt on remaining money
    pool=["Domestic_Equity","Foreign_Equity","Bond"]

    post_gold=gold_val+policy_gold
    post_total=total+policy_gold
    post_w=100*post_gold/post_total if post_total>0 else current_gold

    # Gold may participate until center target 20%, but never above it via STEP8
    if remain>0 and post_w < gold_opportunity_cap_pct:
        pool.append("Gold")

    base={a:max(wts.get(a,1.0),0.01) for a in pool}
    base=normalize(base)

    tilted={
        a:base[a]*attractiveness(opp[a],opportunity_tilt_strength)
        for a in pool
    }
    tilted=normalize(tilted)

    # conservative cap
    for _ in range(10):
        over=[a for a,v in tilted.items() if v>flexible_asset_max_share]
        if not over: break
        excess=sum(tilted[a]-flexible_asset_max_share for a in over)
        for a in over:
            tilted[a]=flexible_asset_max_share
        free=[a for a in tilted if a not in over]
        if not free: break
        fs=sum(tilted[a] for a in free)
        for a in free:
            tilted[a]+=excess*((tilted[a]/fs) if fs>0 else 1/len(free))
    tilted=normalize(tilted)

    for a,w in tilted.items():
        alloc[a]+=remain*w

    # 3) Gold center target guardrail = 20%
    max_gold_total=gold_needed(
        total,gold_val,contribution,gold_opportunity_cap_pct
    )

    if alloc["Gold"]>max_gold_total:
        excess=alloc["Gold"]-max_gold_total
        alloc["Gold"]=max_gold_total
        non=["Domestic_Equity","Foreign_Equity","Bond"]
        den=sum(tilted.get(a,0) for a in non)
        for a in non:
            alloc[a]+=excess*((tilted.get(a,0)/den) if den>0 else 1/3)

    # 4) Minimum order
    tiny=[a for a,x in alloc.items() if 0<x<minimum_allocation_krw]
    reclaimed=sum(alloc[a] for a in tiny)
    for a in tiny: alloc[a]=0.0
    if reclaimed>0:
        eligible=[a for a,x in alloc.items() if x>=minimum_allocation_krw]
        if eligible:
            best=max(eligible,key=lambda a:opp[a])
            alloc[best]+=reclaimed

    shares={a:alloc[a]/contribution for a in ASSETS}

    result=[]
    for a in ASSETS:
        result.append({
            "Asset":a,
            "Opportunity_Score":round(opp[a],2),
            "Allocation_Share_Pct":round(shares[a]*100,2),
            "Allocation_KRW":round(alloc[a]),
            "Policy_First_Gold_KRW":round(policy_gold) if a=="Gold" else 0
        })

    return {
        "Monthly_Contribution_KRW":round(contribution),
        "Current_Gold_Weight_Pct":round(current_gold,2),
        "Gold_Lower_Bound_Pct":gp["Lower"],
        "Gold_Target_Pct":gp["Target"],
        "Gold_Upper_Bound_Pct":gp["Upper"],
        "Gold_Status":gp["Status"],
        "Policy_First_Gold_KRW":round(policy_gold),
        "Allocations":result
    }

def save_result(result):
    rows=result["Allocations"]
    with (STEP08/"monthly_allocation.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    summary=[{
        "Monthly_Contribution_KRW":result["Monthly_Contribution_KRW"],
        "Current_Gold_Weight_Pct":result["Current_Gold_Weight_Pct"],
        "Gold_Status":result["Gold_Status"],
        "Gold_Policy_First_KRW":result["Policy_First_Gold_KRW"],
        "Rule":"Policy-first -> Opportunity tilt -> No selling"
    }]
    with (STEP08/"monthly_allocation_summary.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--amount",type=float,help="이번 달 신규 투자금(KRW)")
    args=parser.parse_args()

    amount=args.amount
    if amount is None:
        text=input("이번 달 투자금액(KRW)을 입력하세요: ").replace(",","").strip()
        amount=float(text)

    result=allocate_monthly(amount)
    save_result(result)

    print("="*78)
    print("STEP 08 - MONTHLY ALLOCATION ENGINE v3 GOLD 20%")
    print("="*78)
    print(f"이번 달 투자금 : {result['Monthly_Contribution_KRW']:,.0f}원")
    print(f"현재 Gold     : {result['Current_Gold_Weight_Pct']:.2f}%")
    print(
        f"Gold 정책     : {result['Gold_Lower_Bound_Pct']:.0f}"
        f"~{result['Gold_Upper_Bound_Pct']:.0f}% "
        f"(중심 {result['Gold_Target_Pct']:.0f}%)"
    )
    print(f"Gold 우선배정 : {result['Policy_First_Gold_KRW']:,.0f}원")
    print()
    print("이번 달 신규자금 배분")
    for r in sorted(result["Allocations"],key=lambda x:x["Allocation_Share_Pct"],reverse=True):
        print(
            f"{r['Asset']:<18} {r['Allocation_Share_Pct']:>6.2f}%  "
            f"{r['Allocation_KRW']:>12,.0f}원  "
            f"(Opportunity {r['Opportunity_Score']:.2f})"
        )

if __name__=="__main__":
    main()
