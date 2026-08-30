STEP12 FINAL INTEGRATED

무엇이 바뀌었나
1) STEP5
- VIX 설명문을 Adjusted Risk Score 방향과 직접 연결.
- 계산식은 변경하지 않음.

2) STEP6
- 패치 제거.
- config/portfolio_target_policy.csv를 본체가 직접 읽음.
- Gold HARD_RANGE = target 20 / lower 18 / upper 22.
- Target Opportunity:
  below lower: 50 + 50*(lower-current)/lower
  in range: 50
  above upper: 50 - 50*(current-upper)/(100-upper)
- 최종 Opportunity:
  0.30 Target + 0.25 Macro + 0.20 RiskAdj + 0.15 History + 0.10 Drawdown.
- downstream authoritative output = outputs/step06/opportunity_scores.csv.

3) STEP7
- 패치 제거.
- HARD_RANGE policy health:
  in range=100
  below lower=100*current/lower
  above upper=100*(100-current)/(100-upper)
- FX가 REPORT_ONLY면 Effective Weight=0.
- 나머지 scored component weights를 다시 합계 1로 정규화.
- 금 설명도 config 값을 직접 사용.

4) STEP8/9/10 검증
STEP8 reads:
- outputs/step06/opportunity_scores.csv
- outputs/step07/target_policy_status.csv

STEP9 reads:
- outputs/step07/portfolio_health_summary.csv
- outputs/step07/portfolio_health_components.csv
- outputs/step07/target_policy_status.csv

STEP10 reads:
- outputs/step06/opportunity_scores.csv
- outputs/step07/portfolio_health_summary.csv
- STEP8/STEP9 outputs

따라서 STEP8/9/10의 데이터 연결은 현재 통합본과 일치하며 로직 수정은 필요 없음.

5) Cron
- 변경: 30 22 * * 0-4
- 의미: 한국시간 월~금 오전 07:30.
- UTC 기준 전날 일~목 22:30.

업로드/교체
ROOT:
- portfolio.csv 교체 (Gold Target_Weight 20)

config:
- portfolio_target_policy.csv 교체

engines:
- step05_risk_engine.py 교체
- step06_opportunity_engine.py 교체
- step07_portfolio_health_engine.py 교체
- step12_pipeline_runner.py 교체
- step12_final_integrated_check.py 추가

선택:
- step08_monthly_allocation_engine.py
- step09_rebalancing_engine.py
- step10_recommendation_engine.py
  => 본 ZIP에도 검증한 동일본을 넣었지만 기존 정상본이면 교체하지 않아도 됨.

workflows:
- portfolio_full_auto_update.yml 교체
- portfolio_monthly_decision.yml 교체

삭제
- engines/step12_consistency_patch.py 삭제
이제 STEP5/6/7 본체에 직접 통합되어 필요 없음.

첫 검증
Actions -> Portfolio Full Auto Update -> Run workflow

정상이라면:
STEP 06 - OPPORTUNITY ENGINE v5 POLICY INTEGRATED
STEP 07 - PORTFOLIO HEALTH ENGINE v2 POLICY INTEGRATED
STEP12 FINAL INTEGRATED VALIDATION
PASS: STEP5/6/7 integrated; policy math aligned; downstream dependencies verified.

그 다음
Portfolio Monthly Decision을 테스트하면 STEP8->9->10 실제 연결까지 최종 확인 가능.
