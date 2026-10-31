"""只读：打印上一期 X 场景完整字段 + config story_order / allowed_producers。"""
import json
from pathlib import Path

ROOT = Path(r"D:\Basement\Codex_Video\Codex-report-news\News_Video")

prev = json.loads((ROOT / "data" / "night-20261030" / "editorial.json").read_text(encoding="utf-8"))
for i, s in enumerate(prev["scenes"]):
    if s.get("source_type") == "official_x":
        print("=== scene[%d] official_x full ===" % i)
        print(json.dumps(s, ensure_ascii=False, indent=1)[:2500])
        break

cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
print("=== config story_order ===")
print(json.dumps(cfg.get("production", {}).get("story_order", {}), ensure_ascii=False))
print("allowed_producers:", cfg.get("production", {}).get("allowed_producers"))
print("scheduling:", json.dumps(cfg.get("production", {}).get("scheduling", {}), ensure_ascii=False)[:400])
