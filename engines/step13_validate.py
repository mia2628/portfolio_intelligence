from pathlib import Path
import json
BASE=Path(__file__).resolve().parents[1]

html=(BASE/"docs/index.html").read_text(encoding="utf-8")
js=(BASE/"docs/assets/app.js").read_text(encoding="utf-8")
sw=(BASE/"docs/sw.js").read_text(encoding="utf-8")
cfg=json.loads((BASE/"config/step13_dashboard_config.json").read_text(encoding="utf-8"))

assert "오늘의 투자 브리핑" not in html
assert "포트폴리오 의사결정 자동화" not in html
assert "포트폴리오 정책 자동화" in html
assert "<title>포트폴리오 정책 자동화</title>" in html
assert "amountVisibilityToggle" in html
assert "APP_TITLE" in js and "포트폴리오 정책 자동화" in js
assert "localStorage" in js
assert 'portfolio-intelligence-v6' in sw
assert 'caches.delete' in sw
assert 'cache:"no-store"' in sw
assert cfg["privacy"]["expose_amounts"] is True
print("PASS: v6 title cache reset + local amount visibility toggle validated.")
