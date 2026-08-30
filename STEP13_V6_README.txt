STEP13 v6 - TITLE CACHE FIX + LOCAL AMOUNT PRIVACY TOGGLE

핵심 수정 1: 메인 제목이 계속 '오늘의 투자 브리핑'으로 보이는 문제
- index.html 문구를 '포트폴리오 정책 자동화'로 강제 통일.
- 브라우저 탭 title도 동일하게 변경.
- app.js 실행 시 제목을 다시 강제 동기화.
- Service Worker cache를 v6로 변경.
- 기존 캐시를 activate 단계에서 전부 삭제.
- HTML 및 dashboard/trend/alerts JSON은 network-first + no-store.
- CSS/JS URL에 ?v=6 캐시버스터 추가.

즉 기존 PWA 캐시에 남아 있던 예전 index.html 때문에 제목이 안 바뀌는 문제까지 대응함.

핵심 수정 2: 모바일 금액 공개/비공개 토글
- 우측 상단에 '금액 공개 / 금액 비공개' 토글 추가.
- 기본값 = 비공개.
- 해당 휴대폰 브라우저의 localStorage에 상태 저장.
- 비공개일 때 실제 금액은 '••••••'로 마스킹.
- 공개로 켜면 실제 투자원금과 자산별 금액 표시.
- 페이지를 다시 열어도 해당 휴대폰의 선택을 기억함.

중요한 보안 의미
- 이 토글은 '화면 표시 보호' 기능임.
- config의 expose_amounts=true이므로 Public GitHub Pages의 dashboard.json 원본에는 금액이 존재함.
- 따라서 인터넷 전체에 대한 비밀보호 기능은 아님.
- GitHub 정책 위반은 아니지만 Public 저장소라면 누구나 원본 JSON을 열어볼 수 있음.
- 계좌번호, 비밀번호, 인증키, 주민번호 등은 절대 저장하지 말 것.

교체 파일
1. docs/index.html
2. docs/assets/app.js
3. docs/assets/style.css
4. docs/sw.js
5. config/step13_dashboard_config.json
6. engines/step13_validate.py

해야 할 일
1. 위 파일들을 GitHub 동일 경로에 교체.
2. Commit.
3. Actions -> STEP13 Mobile Dashboard -> Run workflow.
4. 로그에서:
   Amounts : VISIBLE
   확인.
5. GitHub Pages URL을 일반 Safari/Chrome 탭에서 먼저 열고 새로고침.
6. 홈 화면 PWA를 완전히 종료 후 다시 실행.
7. 그래도 이전 제목이면:
   - 홈 화면의 기존 앱 아이콘 삭제
   - Safari/Chrome에서 GitHub Pages URL 재접속
   - '포트폴리오 정책 자동화' 확인
   - 다시 홈 화면에 추가
8. 우측 상단 금액 토글 확인:
   기본 비공개 -> 금액 마스킹
   공개 -> 실제 금액 표시

아직 미완성인 기능
- 모바일 INPUT으로 미래 가상 시나리오 직접 실행
- 모바일 INPUT으로 실제 투자금액 최신화
이번 v6에서는 이 두 기능을 구현하지 않았으며 준비 중 상태 유지.
