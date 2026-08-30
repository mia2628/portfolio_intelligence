from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
wf=(BASE/".github/workflows/portfolio_mobile_command_bridge.yml").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")

for t in ["runScenarioBtn","runActualBtn","actualConfirmCheck"]:
    assert t in html
for t in ["buildIssueUrl","PORTFOLIO_COMMAND_V1","CONFIRM_ACTUAL","GITHUB_REPO"]:
    assert t in js
for t in [
    "github.actor == github.repository_owner",
    "TYPE",
    "CONFIRM_ACTUAL",
    "step12_pipeline_runner.py",
    "step12_portfolio_state_engine.py",
    "step13_dashboard_export.py"
]:
    assert t in wf
assert "portfolio-intelligence-v8" in sw
print("PASS: STEP13 v8 authenticated mobile command bridge validated.")
