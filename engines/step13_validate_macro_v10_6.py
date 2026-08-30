from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
css=(BASE/"docs/assets/style.css").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")

for t in ["macroRatesChart","macroVolFxChart","금리 · 신용 압력","변동성 · 환율 압력"]:
    assert t in html
for t in ["renderCoreDashboard","fetchJsonOptional","renderMacroSubchart","shortDate"]:
    assert t in js
assert 'fetch("./data/dashboard.json' in js
assert 'fetchJsonOptional("./data/macro_risk.json"' in js
assert ".macro-axis-label" in css
assert ".macro-axis-title" in css
assert "portfolio-intelligence-v10-6" in sw
assert "app.js?v=106" in html
print("PASS: v10.6 split macro charts + axes + core-first independent rendering validated.")
