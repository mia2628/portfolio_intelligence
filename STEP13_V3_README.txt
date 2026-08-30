STEP13 v3
- 메인 제목: 포트폴리오 의사결정 자동화
- 보조문구: 데이터 기반 투자 판단 · 신규자금 배분 · 리스크 관리
- 최근 30일 Risk / Health / Opportunity 트렌드 추가
- 하루 여러 번 실행해도 같은 날짜는 최신값 1개로 유지
- 최대 365일 기록, 모바일은 최근 30일 표시
- 기존 STEP1~12 계산엔진 변경 없음
- 금액 비공개 기본값 유지

업로드/교체:
engines/step13_trend_snapshot.py
engines/step13_validate.py
data/dashboard_history.csv
docs/index.html
docs/assets/style.css
docs/assets/app.js
docs/data/trend.json
.github/workflows/step13_mobile_dashboard.yml

실행:
Actions -> STEP13 Mobile Dashboard -> Run workflow

첫날은 트렌드 점 1개만 있으므로 안내문이 보임.
다음 날짜부터 선그래프가 형성됨.
