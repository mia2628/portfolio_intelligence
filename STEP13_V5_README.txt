STEP13 v5 - MOBILE READABILITY REFINEMENT

핵심 변경
1. 메인 제목
   포트폴리오 정책 자동화

2. '지금 무엇을 할까?' 카드
   - 제목/본문 크기 축소
   - 모바일 첫 화면에서 정보밀도 개선
   - 동적 문구 종결을 가능한 범위에서 ~함/~임 체로 정리

3. 정책 경보
   - HIGH / MEDIUM / NORMAL 강도를 상단에 별도 표시
   - 경보 개수와 강도를 분리
   - 경보 메시지 크기 축소
   - 정책 경보가 화면을 과도하게 점유하지 않도록 압축

4. 트렌드
   - 기본 7일
   - 7일 / 30일 토글
   - 마지막 점 표시
   - 데이터 포인트 수와 변화폭을 짧게 요약
   - 데이터가 1개면 첫 기준점 안내만 표시

5. INPUT 기능 상태
   - 미래 투자 시나리오 / 실제 투자금 반영은 아직 완성 전이므로
     모바일 버튼을 비활성화하고 '준비 중' 표시
   - 현재 모바일은 조회 중심 UI로 유지

6. 실제 투자금액 표시
   config/step13_dashboard_config.json:
   expose_amounts = true
   show_invested_total = true

   GitHub 정책 위반은 아님.
   단, Public 저장소 + GitHub Pages라면 투자금액과 비중을 누구나 볼 수 있음.
   사용자가 공개에 동의하므로 표시 활성화함.
   계좌번호/주민번호/비밀번호/인증정보는 절대 저장하지 말 것.

교체 파일
- config/step13_dashboard_config.json
- docs/index.html
- docs/assets/style.css
- docs/assets/app.js
- docs/sw.js
- engines/step13_validate.py

기존 계산엔진 STEP1~12, trend engine, alert engine 로직은 변경하지 않음.

해야 할 일
1. 위 파일을 동일 경로에 교체하고 Commit.
2. Actions → STEP13 Mobile Dashboard → Run workflow.
3. dashboard export 로그에서 Amounts : VISIBLE 확인.
4. GitHub Pages 새로고침.
5. 홈 화면 PWA 사용 중이면 완전 종료 후 재실행.
6. 확인사항:
   - 제목: 포트폴리오 정책 자동화
   - '지금 무엇을 할까?' 카드 글자 크기 축소
   - 실제 투자금액과 총 투자원금 표시
   - 정책 경보 강도 MEDIUM 표시
   - 트렌드 7일/30일 버튼 표시
   - 미래 투자 시나리오/실제 투자금 반영은 '준비 중'

다음 단계
- 모바일에서 INPUT 값을 직접 받아 GitHub Actions를 실행하는 기능은 별도 단계로 구현 필요.
- 실제 원금 업데이트도 동일하게 인증/실행 흐름을 설계한 뒤 구현 필요.
