STEP9 NameError 수정본

원인
- load_gold_weight()가 (gold_weight, gold_weight_source)를 반환하도록 변경됨.
- main()에서는 두 값을 정상 수신했지만 evaluate()에는 gold_weight만 전달됨.
- evaluate() 반환 딕셔너리에서 gold_weight_source를 참조하여 NameError 발생.

수정
1. evaluate() 인자에 gold_weight_source 추가.
2. main() -> evaluate() 호출 시 gold_weight_source 전달.
3. STEP9 필수 현재상태 입력을 portfolio_invested_summary.csv로 명확화.
4. 회귀검사 step12_step9_regression_check.py 추가.
5. STEP8 신규자금 배분 출력에서는 Cash/Other를 표시하지 않음.
   (Cash/Other는 전체 원금/시나리오 분모에는 계속 포함됨.)

교체/추가
- engines/step09_rebalancing_engine.py 교체
- engines/step08_monthly_allocation_engine.py 교체
- engines/step12_pipeline_runner.py 교체
- engines/step12_step9_regression_check.py 추가

테스트
Actions -> Portfolio Monthly Decision -> Run workflow

정상 기대
Gold 비중         : 6.93%
Gold 비중 기준    : INVESTED_PRINCIPAL
STEP9 Regression Check : PASS
STEP8/STEP9 Consistency Check : PASS
STEP10 : PASS
