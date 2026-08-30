STEP12 ACTUAL PORTFOLIO STATE FINAL

핵심 원칙
A. Portfolio Monthly Decision
- scenario_amount는 사용자가 매번 직접 입력하는 미래 시나리오용 금액.
- STEP8은 배분안과 예상 비중을 계산하지만 실제 portfolio_invested_state.csv를 수정하지 않음.

B. Portfolio Actual Contribution Update
- 실제 매수/투자가 끝난 뒤 actual_amount를 입력.
- 가장 최근 STEP8 배분비율을 실제 금액에 적용.
- 이때만 data/portfolio_invested_state.csv를 영구 갱신.
- 이후 STEP6/7을 다시 계산해 새 실제 포트폴리오 비중을 반영.

현재 초기화된 투자원금 기준
- ISA 투자원금: 19,500,104원
- Gold 투자원금: 1,451,631원
- 전체 투자원금: 20,951,735원

ISA 자산별 투자원금은 자산별 실제 매입원금이 별도로 제공되지 않았으므로,
사용자가 제공한 최신 ISA 구성비(52.27/27.02/18.68/1.90/0.14)를 100%로 정규화한 뒤
ISA 투자원금 19,500,104원을 배분하여 초기화함:
- Bond: 10,191,685원
- Domestic_Equity: 5,268,401원
- Foreign_Equity: 3,642,255원
- Cash: 370,465원
- Other: 27,298원
- Gold: 1,451,631원

평가금액 처리
- data/portfolio_account_snapshot.csv에 수동 스냅샷으로 저장.
- 실제 신규 투자 반영 시 Invested_Amount_KRW만 증가.
- Evaluation_Amount_KRW는 자동 갱신하지 않음.
- 따라서 매일 시세가 반영되지 않아도 모델의 포트폴리오 비중은 투자원금 기준으로 일관됨.

새 파일
- data/portfolio_invested_state.csv
- data/portfolio_account_snapshot.csv
- engines/step12_portfolio_state_engine.py
- .github/workflows/portfolio_actual_contribution_update.yml

교체 파일
- engines/step06_opportunity_engine.py
- engines/step07_portfolio_health_engine.py
- engines/step08_monthly_allocation_engine.py
- engines/step12_pipeline_runner.py
- .github/workflows/portfolio_monthly_decision.yml

사용 순서
1) Portfolio Monthly Decision 실행
   scenario_amount = 가정하고 싶은 금액을 직접 입력
   - 고정값/기본값 없음
   - 300,000원/1,500,000원/3,000,000원 등 원하는 금액을 매번 입력
      -> 현재 포트폴리오 + 미래 시나리오를 보여줌
   -> 실제 상태는 변경하지 않음

2) 실제 투자 실행

3) Portfolio Actual Contribution Update 실행
   actual_amount = 실제로 투자 완료한 금액
   예: 실제로 800000원을 투자했다면 800000
   -> 최근 STEP8 배분비율대로 실제 원금에 반영
   -> 투자원금 기준 비중 재계산
   -> STEP6/STEP7 재계산
   -> GitHub에 새 실제 상태 저장

주의
- 실제 매수 배분이 STEP8 추천비율과 다르면 Actual Contribution Update를 실행하면 안 됨.
  현재 버전은 '가장 최근 STEP8 배분비율대로 실제 투자했다'는 전제를 사용함.
- 추후 모바일 화면에서는 실제 포트폴리오 / 시나리오 / 실제 반영 후를 분리해 보여주는 것이 적절함.
