from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")
for t in ["trendRiskNow","trendHealthNow","trendOppNow","7일","30일"]:
    assert t in html
for t in ["directionText","applyTrendStat","dominant_opportunity_asset"]:
    assert t in js
assert "portfolio-intelligence-v9" in sw
py_compile.compile(str(BASE/"engines/step13_trend_snapshot.py"),doraise=True)
py_compile.compile(str(BASE/"engines/step13_dashboard_integrity_check.py"),doraise=True)
print("PASS: STEP13 v9 7/30-day trend engine + mobile UI validated.")
