STEP12 STEP8 / STEP9 FINAL FIX

수정 1 - STEP8
기존 문제:
- 포트폴리오 실제 상태는 6개 자산(Bond, Domestic, Foreign, Cash, Other, Gold)
- STEP8 result/display는 투자대상 4개만 만들고 있어
  TOTAL 및 시나리오 분모에서 Cash/Other가 빠졌음.

수정:
- INVESTABLE_ASSETS = Domestic_Equity, Foreign_Equity, Bond, Gold
- PORTFOLIO_ASSETS = 위 4개 + Cash + Other
- 신규자금은 기존처럼 투자대상 4개에만 배분
- 현재 총원금, 현재 비중, 시나리오 총원금, 시나리오 비중은 6개 전체 자산 기준
- Cash/Other는 Allocation_Eligible=NO, Allocation_KRW=0으로 유지

따라서:
현재총원금 = Bond + Domestic + Foreign + Cash + Other + Gold
시나리오총원금 = 현재총원금 + scenario_amount

수정 2 - STEP9
기존 문제:
- legacy portfolio_summary.csv에서 Gold 비중을 읽어 6.42%가 남아 있었음.

수정:
- 1순위: outputs/portfolio/portfolio_invested_summary.csv
- 2순위: portfolio_summary.csv (fallback only)
- 정상 실행 시 로그:
  Gold 비중 기준 : INVESTED_PRINCIPAL

추가 검증:
engines/step12_step8_step9_consistency_check.py
- STEP8 6개 자산 모두 존재 확인
- STEP8 현재총원금 == portfolio_invested_summary 총원금
- STEP8 시나리오총원금 == 현재총원금 + 실제 scenario allocation 합계
- STEP9 Gold 비중 == portfolio_invested_summary Gold 비중
- STEP9 source == INVESTED_PRINCIPAL
하나라도 다르면 FAIL.

업로드/교체:
1. engines/step08_monthly_allocation_engine.py
2. engines/step09_rebalancing_engine.py
3. engines/step12_pipeline_runner.py
4. engines/step12_step8_step9_consistency_check.py (새로 추가)

그 외 파일은 기존 정상본 유지.

테스트:
Actions -> Portfolio Monthly Decision
scenario_amount = 원하는 테스트값
last_review_date = 기준일

정상 기대:
STEP08 현재 TOTAL = 20,951,735원 (실제 반영 전 현재 상태 기준)
Cash/Other도 현재/시나리오 목록에 표시
STEP09 Gold 비중 = 6.93% (현재 초기 상태라면)
Gold 비중 기준 = INVESTED_PRINCIPAL
STEP8/STEP9 Consistency Check = PASS
