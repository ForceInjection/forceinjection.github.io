#!/usr/bin/env python3
"""从 data/jd_*.jsonl 重算 skill_catalog.json 的全部派生统计。

catalog 中的定义字段（rules/aliases/admission/家族成员/路线）不由本脚本改动；
只刷新统计字段，保证「定义在 catalog、统计可复算」：

- skill.items[*].count          技能 JD 提及条数
- skill_family.items[*].jd_count      提及任一该家族技能的 JD 条数
- skill_family.items[*].mention_count 家族技能提及次数合计
- matrix.data                   岗位细分 × 家族提及率矩阵（逐技能占比求和）
- sub_category.items[*].count / top_skills / categories
- category.counts
- $source 条数

用法：python3 scripts/refresh_catalog_stats.py（先跑 import_ai_companies.py）
幂等：重复运行输出一致。
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE / "data" / "skill_catalog.json"

cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

rows = []
for p in sorted((BASE / "data").glob("jd_*.jsonl")):
    rows.extend(json.loads(l) for l in p.open(encoding="utf-8") if l.strip())
total = len(rows)

# ── 技能频次 ──
sk_n = Counter()
for r in rows:
    sk_n.update(r.get("skills") or [])
for name, item in cat["skill"]["items"].items():
    item["count"] = sk_n.get(name, 0)

# ── 家族两口径计数 ──
fam_of = {s: v.get("family") for s, v in cat["skill"]["items"].items()}
fam_jd = Counter()
fam_mention = Counter()
for r in rows:
    ss = set(r.get("skills") or [])
    fams = {fam_of[s] for s in ss if fam_of.get(s)}
    for f in fams:
        fam_jd[f] += 1
    for s in ss:
        f = fam_of.get(s)
        if f:
            fam_mention[f] += 1
for f, fv in cat["skill_family"]["items"].items():
    fv["jd_count"] = fam_jd.get(f, 0)
    fv["mention_count"] = fam_mention.get(f, 0)
uncl = [s for s, f in fam_of.items() if not f]
cat["skill_family"]["unclassified"]["skills"] = sorted(uncl)
cat["skill_family"]["unclassified"]["count"] = len(uncl)

# ── matrix：逐技能占比求和 ──
cols = cat["matrix"]["columns"]
sub_n = Counter(r["sub_category"] for r in rows)
sub_skjd = defaultdict(Counter)
for r in rows:
    for s in set(r.get("skills") or []):
        sub_skjd[r["sub_category"]][s] += 1
matrix = {}
for sub, n in sub_n.items():
    matrix[sub] = {
        f: round(sum(sub_skjd[sub].get(s, 0) for s, v in cat["skill"]["items"].items()
                     if v.get("family") == f) / n * 100, 1)
        for f in cols
    }
cat["matrix"]["data"] = matrix

# ── 方向计数 / top_skills / categories ──
sub_rows = defaultdict(list)
for r in rows:
    sub_rows[r["sub_category"]].append(r)
for sub, item in cat["sub_category"]["items"].items():
    subset = sub_rows.get(sub, [])
    item["count"] = len(subset)
    item["categories"] = sorted({r["category"] for r in subset}) or item["categories"]
    sk = Counter()
    for r in subset:
        sk.update(set(r.get("skills") or []))
    ranked = sorted(sk.items(), key=lambda kv: (-kv[1], kv[0]))
    item["top_skills"] = [s for s, _ in ranked[:10]]

# ── 类别计数 ──
cat["category"]["counts"] = dict(Counter(r["category"] for r in rows))

# ── 版本与来源 ──
cat["$source"] = f"data/jd_2026-11-19.jsonl（{total} 条）"

out = json.dumps(cat, ensure_ascii=False, indent=2) + "\n"
CATALOG_PATH.write_text(out, encoding="utf-8")
print(f"catalog 统计刷新完成：{total} 条 | 技能 {len(cat['skill']['items'])} | "
      f"方向 {len(matrix)} | 未归属 {len(uncl)}")
