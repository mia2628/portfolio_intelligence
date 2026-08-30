STEP13 v4 - MOBILE OPERATIONS

변경
1) 메인 문구
   포트폴리오 의사결정 자동화
   → 포트폴리오 정책 자동화

2) 정책 경보 카드
   STEP13 Alert Engine 결과를 docs/data/alerts.json에도 게시.
   모바일에서 현재 활성 경보를 바로 확인.
   MEDIUM/HIGH severity를 구분해 표시.

3) 모델 실행 카드
   미래 투자 시나리오
   → Portfolio Monthly Decision GitHub Actions 화면으로 이동

   실제 투자금 반영
   → Portfolio Actual Contribution Update GitHub Actions 화면으로 이동

4) 기존 원칙 유지
   - 미래 시나리오는 실제 자산 변경 없음
   - 실제 투자금 반영 workflow에서만 원금 상태 변경
   - 투자원금 기준
   - 금액 비공개 기본값 유지
   - Risk/Health/Opportunity 30일 트렌드 유지

5) PWA cache version v4
   새 UI/alert JSON이 모바일 홈화면 앱에서도 최신 반영되도록 캐시 버전 갱신.

업로드/교체 파일
- engines/step13_alert_engine.py
- engines/step13_validate.py
- docs/index.html
- docs/assets/style.css
- docs/assets/app.js
- docs/sw.js
- docs/data/alerts.json
- .github/workflows/step13_mobile_dashboard.yml

기존 trend 파일/engine은 그대로 유지.

해야 할 일
1. 위 파일 동일 경로에 업로드/교체 후 Commit
2. Actions → STEP13 Mobile Dashboard → Run workflow
3. 로그에서 dashboard export / trend snapshot / alert engine 모두 PASS 확인
4. GitHub Pages 모바일 화면 새로고침
5. 홈 화면 앱을 사용 중이면 완전히 종료 후 재실행
6. 화면에서:
   - 제목 = 포트폴리오 정책 자동화
   - 정책 경보 = 현재 Gold 정책 이탈 1건
   - 모델 실행 = 미래 투자 시나리오 / 실제 투자금 반영
   가 보이는지 확인

참고
모델 실행 버튼은 GitHub Actions 실행 페이지로 이동시키는 링크입니다.
정적 GitHub Pages에서 인증 없이 workflow를 직접 실행시키지는 않습니다.
