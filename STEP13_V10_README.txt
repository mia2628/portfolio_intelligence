STEP13 v10 - MACRO MARKET COMPOSITE

UI 변경
- 기존 '30-DAY TREND / 점수 흐름' 카드를 메인 화면 가장 하단으로 이동.
- 기존 위치에는 '거시 리스크 복합 차트' 배치.

거시 차트 구성
1. 미국 10년물 국채금리: FRED DGS10
2. VIX: FRED VIXCLS
3. 미국 하이일드 OAS: FRED BAMLH0A0HYM2
4. USD/KRW: FRED DEXKOUS

정규화
- 각 지표의 최근 최대 252개 유효 관측치에서 percentile 0~100 계산.
- 0 = 최근 분포 하단
- 100 = 최근 분포 상단
- 네 지표 모두 높은 값일수록 금융시장 긴장/압력 방향으로 해석.
- Macro Tension = 사용 가능한 네 정규화 점수 평균.
- 최소 3개 지표가 있어야 composite 계산.
- 이 점수는 '위험확률'이 아니라 최근 분포 내 상대적 위치임.

차트
- 최근 최대 90개 일별 관측점.
- 미 10Y / VIX / HY / USDKRW 4개 정규화 선.
- Macro Tension composite를 굵은 선으로 겹쳐 표시.
- 하단에 원래 실제값 + 정규화 긴장점수 표시.

자동 갱신
새 workflow:
.github/workflows/step13_macro_market_update.yml

자동 실행:
- 매일 08:30 KST
- 매일 18:30 KST
- Actions에서 수동 Run workflow도 가능.

API Key
- 필요 없음.
- FRED fredgraph.csv 공개 endpoint 사용.

추가/교체 파일
- engines/step13_macro_risk_engine.py                신규
- engines/step13_validate.py
- docs/data/macro_risk.json                          신규 placeholder
- docs/index.html
- docs/assets/app.js
- docs/assets/style.css
- docs/sw.js
- .github/workflows/step13_macro_market_update.yml   신규
- .github/workflows/step13_mobile_dashboard.yml

해야 할 일
1. 위 파일들을 동일한 GitHub 경로에 업로드/교체하고 Commit.
2. Actions에서 'STEP13 Macro Market Update'가 생겼는지 확인.
3. 최초 1회:
   Actions -> STEP13 Macro Market Update -> Run workflow.
4. 로그에서 아래 확인:
   STEP13 MACRO RISK v10
   Source           : FRED
   Latest date      : 날짜
   Macro Tension    : 숫자 상태
   Display points   : 20 이상
   PASS: macro risk composite generated.
5. 'Validate macro JSON' PASS 확인.
6. Commit macro data가 성공하면 Pages build and deployment가 이어서 성공하는지 확인.
7. 모바일/PWA 새로고침.
8. 메인 상단 기존 점수흐름 자리에서:
   - 거시 리스크 복합 차트
   - Macro Tension
   - 미 10Y / VIX / HY / USDKRW 네 선
   - 실제 현재값 및 긴장 정규화값
   확인.
9. 페이지 맨 아래에서 기존 '점수 흐름' 카드가 유지되는지 확인.
10. 이후에는 수동 Action을 실행하지 않아도 하루 2회 macro data가 자동 갱신됨.

주의
- FRED의 각 지표 업데이트 시각/휴장일이 다르므로 같은 시각의 tick 데이터가 아님.
- 거시 판단용 준실시간 차트이며 초/분 단위 시장 가격 차트가 아님.
