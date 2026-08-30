from pathlib import Path
import py_compile, json
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")
macro_wf=(BASE/".github/workflows/step13_macro_market_update.yml").read_text(encoding="utf-8")

assert html.find("거시 리스크 복합 차트") < html.find("TODAY'S ACTION")
assert html.rfind("점수 흐름") > html.find("계산 구조")
for t in ["macroChart","macroScore","macroUs10y","macroVix","macroHy","macroFx"]:
    assert t in html
for t in ["renderMacro","macro_risk.json","MACRO TENSION" if False else "macro_tension"]:
    assert t in js
assert "portfolio-intelligence-v10" in sw
assert "macro_risk.json" in sw
assert '30 23 * * *' in macro_wf and '30 9 * * *' in macro_wf
py_compile.compile(str(BASE/"engines/step13_macro_risk_engine.py"),doraise=True)
print("PASS: STEP13 v10 macro composite + bottom trend + scheduled refresh validated.")
