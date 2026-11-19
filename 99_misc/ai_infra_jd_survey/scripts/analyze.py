#!/usr/bin/env python3
"""JD 数据集分析：分类统计 + 岗位技能树生成。

用法：python3 scripts/analyze.py [可选：指定单个 jsonl；默认合并 data/ 全部批次]
输出：analysis/classification.md（分类报告）+ analysis/skill-tree.md（技能树）
可重复运行，数据集更新后重跑即刷新。
"""
import json, sys, re
from pathlib import Path
from collections import Counter, defaultdict

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"  # 默认合并目录下全部 jd_*.jsonl 批次；显式传单文件路径则只用该文件
OUT = BASE / "analysis"
CATALOG = json.loads((BASE / "data" / "skill_catalog.json").read_text(encoding="utf-8"))
CAT_ORDER = CATALOG["category"]["order"]

# 技能归一化：变体 → 规范名（唯一定义源是 data/skill_catalog.json 的 skill.aliases）
SKILL_NORMALIZE = CATALOG["skill"]["aliases"]

# sub_category 口径：入库时已按 data/skill_catalog.json 的 sub_category.rules
# 写入标准方向名（行业通用岗位名），分析端不再做任何改名，只兜空值。


def norm_sub(s):
    """sub_category 只兜空值；标准名以 catalog 为唯一口径。"""
    s = (s or "").strip()
    return s if s else "未标注"


def norm_skill(s: str) -> str:
    key = s.strip().lower()
    if key in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[key]
    return s.strip()


def load(path: Path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def pct(n: int, total: int) -> str:
    return f"{n/total*100:.0f}%"


def main():
    if len(sys.argv) > 1:
        recs = load(Path(sys.argv[1]))
    else:
        recs = []
        for p in sorted(DATA.glob("jd_*.jsonl")):
            recs.extend(load(p))
    total = len(recs)
    OUT.mkdir(exist_ok=True)

    # ── 分类统计 ──
    by_cat = Counter(r["category"] for r in recs)
    by_company = Counter(r.get("company") or "（未显示）" for r in recs)
    cat_company = defaultdict(Counter)
    by_sub = defaultdict(Counter)
    by_loc = Counter()
    by_type = Counter()
    for r in recs:
        c = r["category"]
        cat_company[c][r.get("company") or "（未显示）"] += 1
        sub = norm_sub(r.get("sub_category"))
        by_sub[c][sub] += 1
        loc = r.get("location") or "未标注"
        by_loc[loc.split("/")[0].split("、")[0].strip()] += 1
        by_type[r.get("employment_type") or "未标注"] += 1

    # ── 技能树：category → sub → skill（同时记录各方向的 JD 记录数）──
    tree = defaultdict(lambda: defaultdict(Counter))
    sub_jd_count = defaultdict(Counter)  # category → {sub: 该方向 JD 条数}
    cat_skills = defaultdict(Counter)
    for r in recs:
        c = r["category"]
        sub = norm_sub(r.get("sub_category"))
        sub_jd_count[c][sub] += 1
        skills = {norm_skill(s) for s in (r.get("skills") or [])}
        for s in skills:
            tree[c][sub][s] += 1
            cat_skills[c][s] += 1
    global_skills = Counter()
    for c in cat_skills:
        global_skills.update(cat_skills[c])

    # ── 输出 1：分类报告 ──
    lines = ["# JD 分类报告", "",
             f"> 数据：`data/` 全部批次（jd_*.jsonl），{total} 条。分析脚本：`scripts/analyze.py`（可重跑刷新）", ""]
    lines += ["## 一、按岗位类别", "", "| 类别 | 条数 | 占比 |", "| --- | --- | --- |"]
    for c in CAT_ORDER:
        if by_cat.get(c):
            lines.append(f"| {c} | {by_cat[c]} | {pct(by_cat[c], total)} |")
    lines += ["", "## 二、按公司（Top 25）", "", "| 公司 | 条数 | 类别构成 |", "| --- | --- | --- |"]
    for comp, n in by_company.most_common(25):
        parts_items = sorted(
            ((c, m.get(comp, 0)) for c, m in cat_company.items()),
            key=lambda x: -x[1])
        parts = " / ".join(f"{c}{m}" for c, m in parts_items if m > 0)
        lines.append(f"| {comp} | {n} | {parts} |")
    lines += ["", "## 三、按类别 × 公司", ""]
    for c in CAT_ORDER:
        if not by_cat.get(c):
            continue
        lines += [f"### {c}（{by_cat[c]} 条）", "", "| 公司 | 条数 |", "| --- | --- |"]
        for comp, n in cat_company[c].most_common():
            lines.append(f"| {comp} | {n} |")
        lines.append("")
    lines += ["## 四、细分方向", ""]
    for c in CAT_ORDER:
        if not by_cat.get(c):
            continue
        subs = "、".join(f"{s}({n})" for s, n in by_sub[c].most_common())
        lines.append(f"- **{c}**：{subs}")
    lines += ["", "## 五、地域与招聘类型", "",
              "| 城市 | 条数 |", "| --- | --- |"]
    for loc, n in by_loc.most_common(12):
        lines.append(f"| {loc} | {n} |")
    lines += ["", "招聘类型：" + "、".join(f"{t} {n}" for t, n in by_type.most_common())]
    (OUT / "classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 输出 2：技能树 ──
    t = ["# AI Infra / Agent 岗位技能树", "",
         f"> 从 {total} 条 JD 的 skills 标签聚合生成，括号内为要求该技能的 JD 条数。",
         "> 生成：`scripts/analyze.py`；用途：技能学习材料的组织索引。", ""]
    # 全局高频
    t += ["## 全局技能 Top 30", "", "| 排名 | 技能 | JD 数 | 占比 |", "| --- | --- | --- | --- |"]
    for i, (s, n) in enumerate(global_skills.most_common(30), 1):
        t.append(f"| {i} | {s} | {n} | {pct(n, total)} |")
    # 按类别
    for c in CAT_ORDER:
        if c not in tree:
            continue
        n_cat = by_cat[c]
        t += ["", f"## {c}线（{n_cat} 条 JD）", ""]
        # 类别内高频
        top = cat_skills[c].most_common(15)
        t.append("高频技能：" + "、".join(f"**{s}**({n})" for s, n in top))
        t.append("")
        # 方向级子树（标题用该方向的 JD 记录数，非技能标签数）
        for sub, skills in sorted(tree[c].items(), key=lambda kv: -sub_jd_count[c][kv[0]]):
            n_sub = sub_jd_count[c][sub]
            if n_sub < 2:
                continue
            t.append(f"### {sub}（{n_sub} 条 JD）")
            subs_sorted = skills.most_common()
            t.append("├─ " + " ｜ ".join(f"{s}({n})" for s, n in subs_sorted[:18]))
            t.append("")
    # 共现：研发线 Top10 技能的两两共现
    t += ["## 研发线技能共现（Top 12 技能）", "",
          "同一条 JD 同时要求两个技能的次数，反映技能绑定量。", "",
          "| 技能对 | 共现 JD 数 |", "| --- | --- |"]
    dev_recs = [r for r in recs if r["category"] in ("研发", "算法")]
    pairs = Counter()
    for r in dev_recs:
        ss = sorted({norm_skill(s) for s in (r.get("skills") or [])})
        top12 = {s for s, _ in cat_skills["研发"].most_common(12)}
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                if ss[i] in top12 and ss[j] in top12:
                    pairs[(ss[i], ss[j])] += 1
    for (a, b), n in pairs.most_common(15):
        t.append(f"| {a} + {b} | {n} |")
    (OUT / "skill-tree.md").write_text("\n".join(t) + "\n", encoding="utf-8")

    print(f"分析完成：{total} 条 JD")
    print(f"  {OUT/'classification.md'}")
    print(f"  {OUT/'skill-tree.md'}")


if __name__ == "__main__":
    main()
