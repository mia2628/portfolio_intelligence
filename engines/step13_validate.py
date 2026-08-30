from pathlib import Path
import json,py_compile
BASE=Path(__file__).resolve().parents[1]
required=[
BASE/"docs/index.html",BASE/"docs/assets/style.css",BASE/"docs/assets/app.js",
BASE/"docs/data/dashboard.json",BASE/"docs/data/trend.json",
BASE/"engines/step13_dashboard_export.py",BASE/"engines/step13_alert_engine.py",
BASE/"engines/step13_trend_snapshot.py",BASE/".github/workflows/step13_mobile_dashboard.yml",
BASE/"config/step13_dashboard_config.json"]
for p in required:
    if not p.exists():raise SystemExit(f"FAIL missing: {p}")
for p in [BASE/"engines/step13_dashboard_export.py",BASE/"engines/step13_alert_engine.py",BASE/"engines/step13_trend_snapshot.py"]:
    py_compile.compile(str(p),doraise=True)
cfg=json.loads((BASE/"config/step13_dashboard_config.json").read_text(encoding="utf-8"))
if cfg.get("privacy",{}).get("expose_amounts") is not False:raise SystemExit("FAIL privacy default")
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
for t in ["포트폴리오 의사결정 자동화","지금 무엇을 할까?","내 포트폴리오","이번 투자 시나리오","왜 이런 결과가 나왔을까?","점수 흐름"]:
    if t not in html:raise SystemExit(f"FAIL UI section: {t}")
wf=(BASE/".github/workflows/step13_mobile_dashboard.yml").read_text(encoding="utf-8")
for t in ["Portfolio Monthly Decision","Portfolio Actual Contribution Update","step13_trend_snapshot.py","issues: write"]:
    if t not in wf:raise SystemExit(f"FAIL workflow: {t}")
print("PASS: STEP13 v3 UI / trend / privacy / alert workflow validated.")
