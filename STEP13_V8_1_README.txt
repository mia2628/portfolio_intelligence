STEP13 v8.1 - MOBILE COMMAND Invalid TYPE FIX

원인
v8 app.js에서 GitHub Issue 본문을 만들 때:
  .join("\\n")
을 사용해 실제 줄바꿈이 아니라 문자 '\n'이 들어감.

그 결과 Issue body가 사실상 한 줄이 되어 workflow parser가
TYPE=SCENARIO를 독립 필드로 읽지 못했고:
  Invalid TYPE
오류가 발생함.

수정
1. docs/assets/app.js
   .join("\n")으로 변경
   -> 실제 줄바꿈으로 Issue body 생성.

2. portfolio_mobile_command_bridge.yml
   과거 v8에서 만들어진 literal '\n' 명령도 자동 정규화.
   -> 새 UI뿐 아니라 legacy issue body도 parser가 복구 가능.

3. Parse 로그 보강
   Parsed fields
   Parsed TYPE
   를 출력하여 같은 오류가 생길 경우 즉시 원인 확인 가능.

4. PWA cache
   portfolio-intelligence-v8-1로 갱신.
   app.js?v=81 캐시버스터 적용.

교체 파일
- docs/assets/app.js
- docs/index.html
- docs/sw.js
- .github/workflows/portfolio_mobile_command_bridge.yml
- engines/step13_validate.py

해야 할 일
1. 위 파일을 동일 경로에 교체하고 Commit.
2. 홈 화면 PWA를 완전히 종료.
3. 일반 Safari/Chrome에서 GitHub Pages를 한 번 새로고침.
4. PWA 다시 실행.
5. 가상 시나리오 금액 예: 1000000 입력.
6. '가상 시나리오 실행' 클릭.
7. 열리는 Issue 본문이 아래처럼 줄마다 분리되어 있는지 확인:

PORTFOLIO_COMMAND_V1
TYPE=SCENARIO
AMOUNT=1000000
LAST_REVIEW_DATE=YYYYMMDD
NONCE=...
CONFIRM=SCENARIO

8. Submit issue.
9. Actions -> Portfolio Mobile Command Bridge 확인.
10. 정상 기대:
    Parsed fields: ['AMOUNT','CONFIRM','LAST_REVIEW_DATE','NONCE','TYPE']
    Parsed TYPE: SCENARIO
    이후 STEP08/09/10 실행.

아직 ACTUAL 테스트는 하지 말고 SCENARIO가 끝까지 PASS한 뒤 진행할 것.
