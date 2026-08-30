STEP13 v8 - MOBILE INPUT -> GITHUB ACTIONS BRIDGE

목표
휴대폰에서 입력한 값을 실제 모델 실행과 연결함.
GitHub token/PAT를 Public Pages JavaScript에 넣지 않음.

구조
모바일 입력
 -> GitHub Issue 작성 화면
 -> 사용자가 GitHub에 로그인한 상태에서 Issue 제출
 -> Portfolio Mobile Command Bridge
 -> github.actor == github.repository_owner 검증
 -> SCENARIO 또는 ACTUAL 실행
 -> STEP13 데이터 재생성
 -> Issue에 완료 댓글 후 자동 Close

SCENARIO
- 모바일 '가상 시나리오 실행'
- 입력한 scenario_amount 사용
- STEP12 decision mode -> STEP8/9/10 실행
- 실제 portfolio_invested_state.csv 변경 없음

ACTUAL
- 모바일 '실제 투자금 반영'
- 체크박스 확인 필수
- GitHub 명령에도 CONFIRM_ACTUAL 포함
- 저장소 소유자 계정만 실행 가능
- step12_portfolio_state_engine.py --mode apply
- 이후 STEP6/7, STEP13 재계산
- 실제 투자원금 상태 변경됨

보안
- Public Pages에 GitHub API token 없음.
- Issue 명령은 누구나 보낼 수 있는 Public repo 환경일 수 있으나
  workflow가 github.actor == github.repository_owner인 경우에만 실행함.
- 타인이 명령 Issue를 생성하면 자동 거부/닫힘.
- 실제 반영은 UI 체크 + CONFIRM_ACTUAL + owner authorization 3단계.
- 계좌번호/비밀번호/인증정보를 Issue나 repo에 넣지 말 것.

주의
현재 ACTUAL 반영 엔진은 '가장 최근 STEP8 배분비율'에 따라 actual_amount를 배분하는 기존 STEP12 논리를 사용함.
따라서 실제 매수가 최근 STEP8 추천과 다르면 ACTUAL을 실행하면 안 됨.
실제 자산별 매수금액 직접입력 방식은 후속 단계에서 확장 가능함.

추가/교체 파일
1. docs/index.html
2. docs/assets/app.js
3. docs/assets/style.css
4. docs/sw.js
5. .github/workflows/portfolio_mobile_command_bridge.yml (새로 추가)
6. engines/step13_validate.py

해야 할 일
1. 파일들을 동일 경로에 업로드/교체 후 Commit.
2. GitHub Actions 탭에서 "Portfolio Mobile Command Bridge" workflow가 보이는지 확인.
3. 모바일 GitHub Pages/PWA 새로고침.
4. 먼저 SCENARIO만 시험:
   - 가상 시나리오 신규자금에 예: 1000000
   - '가상 시나리오 실행'
   - GitHub Issue 작성 화면이 열림
   - BODY의 TYPE=SCENARIO, AMOUNT=1000000 확인
   - Issue 제출
5. Actions -> Portfolio Mobile Command Bridge 실행 확인.
6. Issue에 '가상 시나리오 실행 완료함' 댓글 후 자동 Close 확인.
7. 모바일 Dashboard 새로고침 후 STEP8 시나리오 결과 변경 확인.
8. 이 검증이 끝나기 전에는 ACTUAL 버튼을 시험하지 말 것.
9. SCENARIO 검증 로그를 먼저 확인한 뒤 ACTUAL 테스트 진행 권장.
