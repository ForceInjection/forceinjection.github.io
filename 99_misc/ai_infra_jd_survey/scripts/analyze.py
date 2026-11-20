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


# 技能树三视角的固定序列与标签（定义取自 docs/技能分类体系设计.md，与 catalog taxonomy 对应）
TYPE_ORDER = ["language", "framework", "platform-tool", "hardware-interface", "data-system", "method"]
TYPE_LABEL = {
    "language": "编程/建模语言", "framework": "开发框架与库", "platform-tool": "工具、平台与协议",
    "hardware-interface": "物理硬件与互联接口", "data-system": "数据存储与处理系统", "method": "具名方法与范式",
}
SCOPE_ORDER = ["ai-infra", "agent-infra", "general"]
SCOPE_LABEL = {"ai-infra": "AI Infra", "agent-infra": "Agent Infra", "general": "通用底座"}
WORK_LABEL = {"action": "岗位动作", "role": "角色", "metric": "指标", "capability": "能力保障"}


def build_skill_tree(recs: list, total: int, caliber: str) -> list:
    """生成技能树 markdown 行（三视角：主题覆盖率 / 技术栈 / 工作内容）。

    caliber 为口径说明（如「全库」「社招」「校招」），写入文件头。
    """
    kind_of, ttype_of, wtype_of = {}, {}, {}
    scope_of = {}
    for x in CATALOG["skill"].get("taxonomy", []):
        name = x["name"]
        kind_of[name] = x["kind"]
        if x["kind"] == "technique":
            ttype_of[name] = x["type"]
            scope_of[name] = x.get("scope")
        if x["kind"] == "work":
            wtype_of[name] = x.get("work_type")
    topic_skills = {s for s, k in kind_of.items() if k == "topic"}

    # category → sub → skill，同时记录各方向 JD 记录数
    tree = defaultdict(lambda: defaultdict(Counter))
    sub_jd_count = defaultdict(Counter)
    cat_skills = defaultdict(Counter)
    by_cat = Counter()
    for r in recs:
        c = r["category"]
        by_cat[c] += 1
        sub = norm_sub(r.get("sub_category"))
        sub_jd_count[c][sub] += 1
        skills = {norm_skill(s) for s in (r.get("skills") or [])}
        for s in skills:
            tree[c][sub][s] += 1
            cat_skills[c][s] += 1
    global_skills = Counter()
    for c in cat_skills:
        global_skills.update(cat_skills[c])

    t = [f"# AI Infra / Agent 岗位技能树（{caliber}）", "",
         f"> 口径：{caliber}，共 {total} 条 JD（skills 标签聚合，括号内为要求该技能的 JD 条数）。",
         "> 生成：`scripts/analyze.py`；用途：技能学习材料的组织索引与可视化页面计数基准。",
         "> 技能分三视角：主题覆盖率（市场在谈什么）、技术栈（要学什么）、工作内容（岗位在干什么），三榜不互相比较。", ""]

    # 视角 1：主题覆盖率（base 行业默认词置顶单独说明，不进下表）
    base_topic = {s for s in topic_skills if CATALOG["skill"]["items"][s].get("base")}
    base_line = "、".join(f"**{s}**({global_skills[s]}，{pct(global_skills[s], total)})" for s in sorted(base_topic, key=lambda x: -global_skills[x]))
    t += ["## 主题覆盖率（提及率）", "",
          f"行业默认词：{base_line}——绝大多数 JD 默认提及，只说明「这是 AI 行业」。", "",
          "| 主题 | 提及 JD 数 | 覆盖率 |", "| --- | --- | --- |"]
    for s in sorted(topic_skills - base_topic, key=lambda x: -global_skills[x]):
        t.append(f"| {s} | {global_skills[s]} | {pct(global_skills[s], total)} |")

    # 视角 2：技术栈（technique 按 type 分组、组内按 scope 分块，块内按提及数排名）
    t += ["", "## 技术栈（technique）", "",
          "按学习单元类型分组，组内按应用域（scope）分块，块内按提及 JD 数排名，组间不比较。", ""]
    for tp in TYPE_ORDER:
        members = sorted(((s, n) for s, n in global_skills.most_common() if ttype_of.get(s) == tp and n > 0), key=lambda x: (-x[1], x[0]))
        if not members:
            continue
        t.append(f"### {TYPE_LABEL[tp]}")
        by_scope = defaultdict(list)
        for s, n in members:
            by_scope[scope_of.get(s)].append((s, n))
        for sc in SCOPE_ORDER:
            part = by_scope.get(sc)
            if part:
                t.append(f"**{SCOPE_LABEL[sc]}**：" + "、".join(f"**{s2}**({n2})" for s2, n2 in part))
        t.append("")

    # 视角 3：工作内容分布（work 按 work_type 分组）
    t += ["## 工作内容分布（work）", "", "按岗位动作 / 角色 / 指标 / 能力分组。", ""]
    for wt in ("action", "role", "metric", "capability"):
        members = sorted(((s, n) for s, n in global_skills.most_common() if wtype_of.get(s) == wt and n > 0), key=lambda x: (-x[1], x[0]))
        if not members:
            continue
        t.append(f"### {WORK_LABEL[wt]}")
        t.append("、".join(f"**{s}**({n})" for s, n in members))
        t.append("")

    # 各线高频与方向级子树（子树保留全部词，作索引，不参与三榜排名）
    for c in CAT_ORDER:
        if c not in tree:
            continue
        t += ["", f"## {c}线（{by_cat[c]} 条 JD）", ""]
        top_t = [(s, n) for s, n in cat_skills[c].most_common(15) if kind_of.get(s) == "technique"][:10]
        top_w = [(s, n) for s, n in cat_skills[c].most_common(15) if kind_of.get(s) == "work"][:6]
        t.append("技术栈高频：" + "、".join(f"**{s}**({n})" for s, n in top_t))
        t.append("")
        t.append("工作内容高频：" + "、".join(f"**{s}**({n})" for s, n in top_w))
        t.append("")
        for sub, skills in sorted(tree[c].items(), key=lambda kv: -sub_jd_count[c][kv[0]]):
            n_sub = sub_jd_count[c][sub]
            if n_sub < 2:
                continue
            t.append(f"### {sub}（{n_sub} 条 JD）")
            t.append("├─ " + " ｜ ".join(f"{s}({n})" for s, n in skills.most_common()[:18]))
            t.append("")

    # 共现：研发 + 算法线 technique 词的两两共现
    t += ["## 研发 + 算法线技能共现（Top 12 技能）", "",
          "同一条 JD 同时要求两个技能的次数，反映技能绑定量。统计范围为研发 + 算法两类岗位；"
          "仅统计 technique 词，Top 12 取两线合并后提及数最高的 12 个 technique 词。", "",
          "| 技能对 | 共现 JD 数 |", "| --- | --- |"]
    dev_recs = [r for r in recs if r["category"] in ("研发", "算法")]
    dev_sk = Counter()
    dev_sets = []
    for r in dev_recs:
        ss = {norm_skill(s) for s in (r.get("skills") or []) if kind_of.get(norm_skill(s)) == "technique"}
        dev_sets.append(ss)
        dev_sk.update(ss)
    top12 = {s for s, _ in dev_sk.most_common(12)}
    pairs = Counter()
    for ss in dev_sets:
        hit = sorted(s for s in ss if s in top12)
        for i in range(len(hit)):
            for j in range(i + 1, len(hit)):
                pairs[(hit[i], hit[j])] += 1
    for (a, b), n in pairs.most_common(15):
        t.append(f"| {a} + {b} | {n} |")
    return t


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
        # 城市：按提及计，一条 JD 涉多城市分别计入（与文章城市口径一致）
        loc = (r.get("location") or "").strip()
        if not loc:
            by_loc["未标注"] += 1
        else:
            for city in re.split(r"[/、]", loc):
                city = city.strip()
                if city:
                    by_loc[city] += 1
        by_type[r.get("employment_type") or "未标注"] += 1

    # ── 输出 1：分类报告 ──
    lines = ["# JD 分类报告", "",
             f"> 数据：`data/` 全部批次（jd_*.jsonl），{total} 条。分析脚本：`scripts/analyze.py`（可重跑刷新）", ""]
    lines += ["## 一、按岗位类别", "", "| 类别 | 条数 | 占比 |", "| --- | --- | --- |"]
    for c in CAT_ORDER:
        if by_cat.get(c):
            lines.append(f"| {c} | {by_cat[c]} | {pct(by_cat[c], total)} |")
    lines += ["", "## 二、按公司（全部 12 家）", "", "| 公司 | 条数 | 类别构成 |", "| --- | --- | --- |"]
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
              "口径：按城市提及计，一条 JD 涉多城市分别计入；location 为空的记录计「未标注」。", "",
              "| 城市 | 条数 |", "| --- | --- |"]
    for loc, n in by_loc.most_common(12):
        lines.append(f"| {loc} | {n} |")
    lines += ["", f"未标注 {sum(1 for r in recs if not (r.get('location') or '').strip())} 条。",
              "", "招聘类型：" + "、".join(f"{t} {n}" for t, n in by_type.most_common())]
    (OUT / "classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 输出 2：技能树三份（全库 / 社招 / 校招），页面与文章按对应口径引用 ──
    society = [r for r in recs if r.get("recruit_channel") == "社招"]
    campus = [r for r in recs if r.get("recruit_channel") == "校招"]
    (OUT / "skill-tree.md").write_text(
        "\n".join(build_skill_tree(recs, total, "全库")) + "\n", encoding="utf-8")
    (OUT / "skill-tree-society.md").write_text(
        "\n".join(build_skill_tree(society, len(society), "社招")) + "\n", encoding="utf-8")
    (OUT / "skill-tree-campus.md").write_text(
        "\n".join(build_skill_tree(campus, len(campus), "校招")) + "\n", encoding="utf-8")

    print(f"分析完成：{total} 条 JD（社招 {len(society)} / 校招 {len(campus)}）")
    print(f"  {OUT/'classification.md'}")
    print(f"  {OUT/'skill-tree.md'}  +  skill-tree-society.md / skill-tree-campus.md")


if __name__ == "__main__":
    main()
