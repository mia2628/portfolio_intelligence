STEP12 CONSISTENCY v2

수정사항
1. portfolio.csv Gold Target_Weight: 10 -> 20
2. STEP5: VIX 설명 방향을 Adjusted Risk Score와 일치하도록 canonical risk_details에 보정
3. STEP6: HARD_RANGE 정책점수 사용
   below lower: 50 + 50*(lower-current)/lower
   in [lower,upper]: 50
   above upper: 50 - 50*(current-upper)/(100-upper)
   Gold current 6.42%, lower18%이면 약 82.17
   Opportunity = .30 Target + .25 Macro + .20 RiskAdj + .15 History + .10 Drawdown
4. STEP7 Policy Health
   in range=100
   below lower=100*current/lower
   above upper=100*(100-current)/(100-upper)
   Gold 6.42%이면 약35.67
5. STEP7 Health에서 FX Exposure는 REPORT_ONLY이므로 effective weight=0
   Health=(.25 Concentration+.20 Volatility+.20 MaxDD+.15 Correlation+.10 TargetPolicy)/.90
   /0.90은 나머지 scored weights를 100%로 재정규화하는 것.

설치
- portfolio.csv -> 저장소 루트 기존 파일 교체
- config/step12_policy_consistency.csv 추가
- config/step12_math_policy.csv 추가
- engines/step12_consistency_patch.py 추가
- engines/step12_pipeline_runner.py 교체
- .github/workflows/portfolio_full_auto_update.yml 교체
- .github/workflows/portfolio_monthly_decision.yml 교체

기존 step05/06/07 엔진은 유지.
각 엔진 직후 consistency patch가 canonical output CSV를 수정하므로 STEP8~10은 보정된 결과를 읽는다.

실행
Actions -> Portfolio Full Auto Update -> Run workflow

마지막에 기대:
PASS: STEP5 narrative direction / STEP6 policy / STEP7 policy+FX semantics aligned

주의
patch가 STEP6/STEP7 CSV schema를 인식하지 못하면 FAIL로 멈추도록 설계.
조용히 잘못된 값을 통과시키지 않는다.
