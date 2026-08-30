STEP13 MOBILE DASHBOARD + ALERT

목표
- 휴대폰을 켰을 때 가장 먼저:
  1) 현재 Risk
  2) 가장 높은 Opportunity
  3) Portfolio Health
  4) 지금 해야 할 행동
  5) 현재 자산구성
  6) 최근 What-if 시나리오
  를 한 화면에서 확인.

설명가능성
- "왜 이런 결과인가"를 누르면 Risk 주요 요인, Opportunity 5개 구성점수,
  Health 구성점수를 확인.
- 화면 아래에는 핵심 계산구조를 짧게 상시 표시.

파일
[추가]
config/step13_dashboard_config.json
engines/step13_dashboard_export.py
engines/step13_alert_engine.py
engines/step13_validate.py
.github/workflows/step13_mobile_dashboard.yml
docs/index.html
docs/assets/style.css
docs/assets/app.js
docs/data/dashboard.json
docs/manifest.webmanifest
docs/sw.js

기존 STEP1~12 파일은 수정하지 않음.

────────────────────────────────────────
1. GitHub 업로드
────────────────────────────────────────
위 STEP13 파일/폴더를 저장소의 동일 경로에 업로드하고 Commit.

────────────────────────────────────────
2. GitHub Pages 켜기
────────────────────────────────────────
GitHub 저장소:
Settings -> Pages

Build and deployment:
Source = Deploy from a branch
Branch = master 또는 main (현재 사용하는 기본 브랜치)
Folder = /docs
Save

잠시 뒤 Pages 주소가 생성됨.

※ 저장소가 Public이면 Pages 데이터도 공개될 수 있음.
기본 config는 expose_amounts=false라서 dashboard.json에 금액을 넣지 않음.
비중/점수 역시 공개가 부담되면 Public Pages를 사용하지 말고 저장소/호스팅 정책을 먼저 조정할 것.

────────────────────────────────────────
3. STEP13 최초 실행
────────────────────────────────────────
Actions -> STEP13 Mobile Dashboard -> Run workflow

정상 로그:
STEP13 DASHBOARD EXPORT
Saved : docs/data/dashboard.json

이후 STEP12의 아래 workflow가 성공하면 STEP13도 자동 실행:
- Portfolio Full Auto Update
- Portfolio Monthly Decision
- Portfolio Actual Contribution Update

────────────────────────────────────────
4. 핸드폰 홈 화면에 설치
────────────────────────────────────────
iPhone:
Safari로 GitHub Pages 주소 열기
-> 공유
-> 홈 화면에 추가

Android:
Chrome으로 주소 열기
-> 메뉴
-> 홈 화면에 추가 / 앱 설치

PWA 형태로 실행됨.

────────────────────────────────────────
5. GitHub Mobile 알림
────────────────────────────────────────
STEP13 Alert Engine은 다음을 감시:
- Risk >= 65
- Health < 50
- Data Confidence < 60
- Gold 18~22% 정책범위 이탈
- STEP9 Action Level HIGH

활성 경보가 생기면:
[Portfolio Alert] 현재 확인 필요
라는 GitHub Issue를 자동 생성/갱신.

경보가 모두 해소되면 해당 Issue를 자동 Close.

휴대폰 알림을 받으려면:
- GitHub Mobile 앱 설치/로그인
- 해당 저장소 Watch 설정에서 Issues 알림을 켜기
- 휴대폰 OS에서 GitHub 알림 허용

────────────────────────────────────────
6. 금액 표시를 원할 때
────────────────────────────────────────
config/step13_dashboard_config.json

"privacy": {
  "expose_amounts": false
}

기본 false.
true로 바꾸면 다음 STEP13 생성 때 금액이 dashboard.json에도 포함됨.
공개 저장소에서는 true 사용을 권장하지 않음.

────────────────────────────────────────
7. 화면 철학
────────────────────────────────────────
상단 3개:
Risk / Best Opportunity / Health

그 아래:
"지금 무엇을 할까"

그 다음:
현재 포트폴리오 도넛 + 비중

그 다음:
최근 What-if Scenario

그 다음:
왜? (Risk/Opportunity/Health 계산 근거)

즉 엔진의 계산값을 숨기는 Dashboard가 아니라,
결과와 이유를 동시에 볼 수 있는 Explainable Dashboard 구조.
