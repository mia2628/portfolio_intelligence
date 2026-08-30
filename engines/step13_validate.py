from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
css=(BASE/"docs/assets/style.css").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")

assert "지금 무엇을 할까?" not in html
assert "TODAY'S ACTION" in html
assert "today-action-only" in html
assert "scenarioAmountInput" in html
assert "actualAmountInput" in html
assert "입력값 저장" in html
assert "INPUT_DRAFT_KEY" in js
assert "localStorage" in js
assert "portfolio-intelligence-v7" in sw
assert "style.css?v=7" in html
assert "app.js?v=7" in html
print("PASS: STEP13 v7 TODAY'S ACTION + local input preparation validated.")
