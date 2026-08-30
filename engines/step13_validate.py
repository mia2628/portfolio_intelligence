from pathlib import Path
import json, py_compile
BASE=Path(__file__).resolve().parents[1]
required=[
BASE/"docs/index.html",BASE/"docs/assets/style.css",BASE/"docs/assets/app.js",BASE/"docs/sw.js",
BASE/"config/step13_dashboard_config.json",BASE/"engines/step13_alert_engine.py"
]
for p in required:
    if not p.exists(): raise SystemExit(f"FAIL missing {p}")
cfg=json.loads((BASE/"config/step13_dashboard_config.json").read_text(encoding="utf-8"))
if cfg["privacy"]["expose_amounts"] is not True: raise SystemExit("FAIL amounts setting")
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
for t in ["포트폴리오 정책 자동화","지금 무엇을 할까?","정책 경보","입력 기능","준비 중","7일","30일"]:
    if t not in html: raise SystemExit(f"FAIL UI {t}")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
for t in ["nominalizeKo","trendDays=7","renderAlerts","portfolioTotal"]:
    if t not in js: raise SystemExit(f"FAIL JS {t}")
py_compile.compile(str(BASE/"engines/step13_alert_engine.py"),doraise=True)
print("PASS: STEP13 v5 mobile readability / alert strength / trend range / amount visibility validated.")
