#!/usr/bin/env python3
"""从 data/jd_*.jsonl 重算 skill_catalog.json 的全部派生统计。

catalog 中的定义字段（rules/aliases/admission/家族成员/路线）不由本脚本改动；
只刷新统计字段，保证「定义在 catalog、统计可复算」：

- skill.items[*].count          技能 JD 提及条数
- skill_family.items[*].jd_count      提及任一该家族技能的 JD 条数
- skill_family.items[*].mention_count 家族技能提及次数合计
- matrix_content                 岗位细分 × 家族 内容提及率矩阵（逐技能占比求和，混合 kind 口径）
- matrix_technique               岗位细分 × technique_type JD覆盖率矩阵（技能结论专用）
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

# ── taxonomy 校验与回写（kind/type/facets/base 唯一来源是 skill.taxonomy）──
tax = cat["skill"].get("taxonomy") or []
names = [x["name"] for x in tax]
assert len(names) == 109 == len(set(names)), f"taxonomy 应为 109 行唯一词表，实际 {len(names)}"
assert set(names) == set(cat["skill"]["items"].keys()), "taxonomy 与 skill.items 键集不一致"
WORK_TYPES = {"action", "role", "metric", "capability"}
KINDS = {"topic", "work", "technique"}
TECH_TYPES = {"language", "framework", "platform-tool", "hardware-interface", "data-system", "method"}
SCOPES = {"general", "ai-infra", "agent-infra"}
for x in tax:
    assert x["kind"] in KINDS, f"{x['name']}: 非法 kind {x['kind']}"
    if x["kind"] == "technique":
        assert x.get("type") in TECH_TYPES, f"{x['name']}: 非法/缺 type {x.get('type')}"
        assert x.get("scope") in SCOPES, f"{x['name']}: technique 缺合法 scope"
        for sf in x.get("scope_facets", []):
            assert sf in SCOPES and sf != x["scope"], f"{x['name']}: 非法 scope_facets {sf}"
    else:
        assert not x.get("type"), f"{x['name']}: 非 technique 行不应有 type"
        assert not x.get("scope"), f"{x['name']}: 仅 technique 行可有 scope"
    if x["kind"] == "work":
        assert x.get("work_type") in WORK_TYPES, f"{x['name']}: work 行缺合法 work_type"
    else:
        assert not x.get("work_type"), f"{x['name']}: 仅 work 行可有 work_type"
    if x.get("base"):
        assert x["kind"] == "topic", f"{x['name']}: base 仅允许 topic 行"
    for f in x.get("facets", []):
        assert f in ("topic", "work", "technique") and f != x["kind"], f"{x['name']}: facets 非法 {f}"
tax_by_name = {x["name"]: x for x in tax}

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
    # ── taxonomy 回写（kind/type/facets/base 单一来源在 skill.taxonomy）──
    x = tax_by_name[name]
    item["kind"] = x["kind"]
    if x["kind"] == "technique":
        item["type"] = x["type"]
        item["scope"] = x["scope"]
        if x.get("scope_facets"):
            item["scope_facets"] = x["scope_facets"]
        else:
            item.pop("scope_facets", None)
    else:
        item.pop("type", None)
        item.pop("scope", None)
        item.pop("scope_facets", None)
    if x["kind"] == "work":
        item["work_type"] = x["work_type"]
    else:
        item.pop("work_type", None)
    if x.get("facets"):
        item["facets"] = x["facets"]
    else:
        item.pop("facets", None)
    if x.get("base"):
        item["base"] = True
    else:
        item.pop("base", None)

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

# ── 双 matrix：内容提及口径（family × sub）+ 技能结论口径（technique_type × sub）──
cols = cat["matrix_content"]["columns"]
tcols = cat["matrix_technique"]["columns"]
sub_n = Counter(r["sub_category"] for r in rows)
sub_skjd = defaultdict(Counter)
for r in rows:
    for s in set(r.get("skills") or []):
        sub_skjd[r["sub_category"]][s] += 1

matrix_content = {}
matrix_technique = {}
for sub, n in sub_n.items():
    matrix_content[sub] = {
        f: round(sum(sub_skjd[sub].get(s, 0) for s, v in cat["skill"]["items"].items()
                     if v.get("family") == f) / n * 100, 1)
        for f in cols
    }
    cov = {}
    for t in tcols:
        hit = sum(1 for r in rows if r["sub_category"] == sub
                  and any(cat["skill"]["items"][s].get("type") == t for s in set(r.get("skills") or [])))
        cov[t] = round(hit / n * 100, 1)
    matrix_technique[sub] = cov

cat["matrix_content"]["data"] = matrix_content
cat["matrix_technique"]["data"] = matrix_technique

# ── 方向计数 / top_skills（categories 是定义字段，由 catalog 维护，此处不改写）──
sub_rows = defaultdict(list)
for r in rows:
    sub_rows[r["sub_category"]].append(r)
for sub, item in cat["sub_category"]["items"].items():
    subset = sub_rows.get(sub, [])
    item["count"] = len(subset)
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
      f"方向 {len(matrix_content)} | 未归属 {len(uncl)}")
