from pathlib import Path
import json, py_compile, sys

BASE=Path(__file__).resolve().parents[1]
required=[
    BASE/"docs"/"index.html",
    BASE/"docs"/"assets"/"style.css",
    BASE/"docs"/"assets"/"app.js",
    BASE/"docs"/"manifest.webmanifest",
    BASE/"docs"/"sw.js",
    BASE/"engines"/"step13_dashboard_export.py",
    BASE/"engines"/"step13_alert_engine.py",
    BASE/".github"/"workflows"/"step13_mobile_dashboard.yml",
    BASE/"config"/"step13_dashboard_config.json",
]
for p in required:
    if not p.exists(): raise SystemExit(f"FAIL missing {p}")

cfg=json.loads((BASE/"config"/"step13_dashboard_config.json").read_text(encoding="utf-8"))
if cfg.get("privacy",{}).get("expose_amounts") is not False:
    raise SystemExit("FAIL privacy default must be false")

for p in [BASE/"engines"/"step13_dashboard_export.py",BASE/"engines"/"step13_alert_engine.py"]:
    py_compile.compile(str(p),doraise=True)

html=(BASE/"docs"/"index.html").read_text(encoding="utf-8")
for text in ["오늘의 포트폴리오","지금 무엇을 할까","내 포트폴리오","왜 이런 결과인가","계산 구조"]:
    if text not in html: raise SystemExit(f"FAIL dashboard section {text}")

wf=(BASE/".github"/"workflows"/"step13_mobile_dashboard.yml").read_text(encoding="utf-8")
for text in ["Portfolio Monthly Decision","Portfolio Actual Contribution Update","issues: write"]:
    if text not in wf: raise SystemExit(f"FAIL workflow {text}")

print("PASS: STEP13 files / privacy / dashboard sections / alert workflow validated.")
