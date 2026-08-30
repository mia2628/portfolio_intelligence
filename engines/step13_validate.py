from pathlib import Path
import json,py_compile

BASE=Path(__file__).resolve().parents[1]
required=[
    BASE/"docs/index.html",
    BASE/"docs/assets/style.css",
    BASE/"docs/assets/app.js",
    BASE/"docs/sw.js",
    BASE/"docs/data/dashboard.json",
    BASE/"docs/data/trend.json",
    BASE/"docs/data/alerts.json",
    BASE/"engines/step13_dashboard_export.py",
    BASE/"engines/step13_alert_engine.py",
    BASE/"engines/step13_trend_snapshot.py",
    BASE/".github/workflows/step13_mobile_dashboard.yml",
    BASE/"config/step13_dashboard_config.json",
]
for p in required:
    if not p.exists(): raise SystemExit(f"FAIL missing: {p}")

for p in [
    BASE/"engines/step13_dashboard_export.py",
    BASE/"engines/step13_alert_engine.py",
    BASE/"engines/step13_trend_snapshot.py"
]:
    py_compile.compile(str(p),doraise=True)

cfg=json.loads((BASE/"config/step13_dashboard_config.json").read_text(encoding="utf-8"))
if cfg.get("privacy",{}).get("expose_amounts") is not False:
    raise SystemExit("FAIL privacy default")

html=(BASE/"docs/index.html").read_text(encoding="utf-8")
for t in [
    "포트폴리오 정책 자동화",
    "지금 무엇을 할까?",
    "정책 경보",
    "모델 실행",
    "미래 투자 시나리오",
    "실제 투자금 반영",
    "내 포트폴리오",
    "점수 흐름",
]:
    if t not in html: raise SystemExit(f"FAIL UI section: {t}")

js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
if "renderAlerts" not in js or 'alerts.json' not in js:
    raise SystemExit("FAIL alert UI binding")

wf=(BASE/".github/workflows/step13_mobile_dashboard.yml").read_text(encoding="utf-8")
if "docs/data/alerts.json" not in wf:
    raise SystemExit("FAIL alerts publish commit")

print("PASS: STEP13 v4 title / alert center / quick actions / trend / privacy validated.")
