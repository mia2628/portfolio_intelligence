from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
wf=(BASE/".github/workflows/portfolio_mobile_command_bridge.yml").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")
html=(BASE/"docs/index.html").read_text(encoding="utf-8")

# JS source must contain actual newline escape \n, not escaped literal \\n, in issue body join.
assert js.count('].join("\\n");') >= 2
assert '].join("\\\\n");' not in js

# Workflow must normalize legacy bodies too.
assert 'body=body.replace("\\\\r\\\\n","\\n").replace("\\\\n","\\n")' in wf
assert 'Parsed TYPE:' in wf
assert 'portfolio-intelligence-v8-1' in sw
assert 'app.js?v=81' in html
print("PASS: v8.1 command body newline + legacy parser compatibility validated.")
