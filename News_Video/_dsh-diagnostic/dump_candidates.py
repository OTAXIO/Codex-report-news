"""只读：候选数据字段 + 已用日志格式。"""
import json
from pathlib import Path

ROOT = Path(r"D:\Basement\Codex_Video\Codex-report-news\News_Video")
WANT = {"5e6464a0738108787727", "e374846629760dd1076c", "47d9a942c43faca94405", "7b09b93dae7452b9c122"}

cands = json.loads((ROOT / "data" / "candidates.json").read_text(encoding="utf-8"))
print("candidates.json type:", type(cands).__name__)
if isinstance(cands, dict):
    print("top keys:", list(cands.keys())[:10])
    items = cands.get("items") or cands.get("candidates") or []
else:
    items = cands
print("items count:", len(items))
if items:
    print("item[0] keys:", sorted(items[0].keys()))
    for it in items:
        if str(it.get("id")) in WANT:
            print("#" * 60)
            for k, v in it.items():
                if isinstance(v, str) and len(v) > 250:
                    print(" ", k, "=", v[:250] + "...")
                elif isinstance(v, (list, dict)):
                    print(" ", k, "=", json.dumps(v, ensure_ascii=False)[:400])
                else:
                    print(" ", k, "=", v)

print("#" * 70)
for g in [ROOT / "logs", ROOT / "data"]:
    for f in sorted(g.glob("**/*.jsonl"))[:8]:
        print("jsonl:", f.relative_to(ROOT))
        lines = f.read_text(encoding="utf-8").splitlines()
        if lines:
            try:
                d = json.loads(lines[-1])
                print("   last line keys:", sorted(d.keys()))
                print("   sample:", json.dumps(d, ensure_ascii=False)[:300])
            except Exception as e:
                print("   parse err:", e)
