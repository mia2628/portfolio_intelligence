STEP13 v7 - TODAY'S ACTION 정리 + 모바일 INPUT 준비

변경 1
- '지금 무엇을 할까?' 문구 삭제.
- TODAY'S ACTION만 유지.
- TODAY'S ACTION 글자 크기를 한 단계 더 축소.

변경 2
- 모바일 입력 준비 화면 추가.
- 가상 시나리오 신규자금 입력칸.
- 실제 투자금 반영 예정액 입력칸.
- '입력값 저장' / '초기화' 버튼.
- 입력값은 localStorage에 저장되며 해당 휴대폰에서만 유지됨.

중요
- 이번 v7에서는 입력값을 저장만 함.
- STEP8~10 분석은 실행하지 않음.
- 실제 portfolio_invested_state.csv도 변경하지 않음.
- GitHub Actions 자동실행과 연결하는 것은 다음 단계임.

교체 파일
1. docs/index.html
2. docs/assets/style.css
3. docs/assets/app.js
4. docs/sw.js
5. engines/step13_validate.py

해야 할 일
1. 위 파일들을 동일 경로에 교체하고 Commit.
2. Actions -> STEP13 Mobile Dashboard -> Run workflow.
3. GitHub Pages 새로고침.
4. PWA 사용 중이면 완전 종료 후 다시 실행.
5. 확인:
   - '지금 무엇을 할까?' 없음.
   - TODAY'S ACTION만 작게 표시.
   - 가상 시나리오 신규자금 입력칸 표시.
   - 실제 투자금 반영 예정액 입력칸 표시.
   - 숫자 입력 후 저장 버튼을 누르고 앱을 다시 열어도 값이 유지됨.
   - 이 값이 아직 실제 분석/포트폴리오에는 반영되지 않는 상태가 맞음.

다음 단계
- 저장된 scenario_amount를 Portfolio Monthly Decision workflow 입력으로 전달.
- 저장된 actual_amount를 Portfolio Actual Contribution Update workflow 입력으로 전달.
- 인증정보를 GitHub Pages 코드에 노출하지 않는 방식으로 연결해야 함.
