from pathlib import Path
import py_compile
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
bridge=(BASE/".github/workflows/portfolio_mobile_command_bridge.yml").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")

assert "dataStateBanner" in html
assert "app.js?v=82" in html
assert "style.css?v=82" in html
assert "markDataState" in js
assert "STEP13 데이터가 아직 생성되지 않았습니다" in js
assert "dashboard_integrity_check.py" in bridge
assert "portfolio-intelligence-v8-2" in sw
py_compile.compile(str(BASE/"engines/step13_dashboard_export.py"),doraise=True)
py_compile.compile(str(BASE/"engines/step13_dashboard_integrity_check.py"),doraise=True)
print("PASS: v8.2 live dashboard recovery / fallback / integrity validation.")
