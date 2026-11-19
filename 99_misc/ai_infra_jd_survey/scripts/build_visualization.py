#!/usr/bin/env python3
"""生成 JD 数据集两份独立可视化页面（技能地图 + 岗位版图）。

用法：python3 scripts/build_visualization.py
输出：skill-map.html —— 技能地图（一 技能谱系树 / 二 学习路线 / 三 大类→细分→技能 Sankey / 四 UpSet）
      jobs.html      —— 岗位版图（一 岗位堆叠条+公司表 / 二 城市×类别热力矩阵 / 三 JD 明细表）
两份均零外部依赖、离线可打开，各自独立成页；数据更新后重跑即刷新。
技能归一化复用 analyze.py 的映射表。
"""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import norm_skill, norm_sub  # noqa: E402

BASE = Path(__file__).resolve().parent.parent

TOP_SKILL_BAR_MAX = 30      # 全局条形数量
SUB_SKILL_SHOW = 18         # 每方向展示技能叶数
COOC_TOP = 12               # 共现矩阵维度（保留在 md 报告中）
COMPANY_SHOW = 12           # 公司表行数

CATALOG = json.loads((BASE / "data" / "skill_catalog.json").read_text(encoding="utf-8"))
CAT_ORDER = CATALOG["category"]["order"]
FAMILY_DEF = CATALOG["skill_family"]["items"]
ROADMAPS = CATALOG["roadmaps"]


def load(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def aggregate(recs):
    total = len(recs)
    cat_n = Counter(r["category"] for r in recs)
    cat_company = defaultdict(Counter)
    sub_jd = defaultdict(Counter)
    tree = defaultdict(lambda: defaultdict(Counter))
    cat_skills = defaultdict(Counter)
    for r in recs:
        c = r["category"]
        comp = r.get("company") or "（未显示）"
        cat_company[c][comp] += 1
        sub = r.get("sub_category") or "未标注"
        sub_jd[c][sub] += 1
        skills = {norm_skill(s) for s in (r.get("skills") or [])}
        for s in skills:
            tree[c][sub][s] += 1
            cat_skills[c][s] += 1

    companies = Counter()
    for c in cat_company:
        companies.update(cat_company[c])
    n_firms = len([k for k in companies if k != "（未显示）"])
    n_skills = len({norm_skill(s) for r in recs for s in (r.get("skills") or [])})

    # 共现矩阵（取研发+算法合线的 Top 技能，与 analyze 口径一致）
    dev = [r for r in recs if r["category"] in ("研发", "算法")]
    dev_skills = Counter()
    dev_sets = []
    for r in dev:
        ss = {norm_skill(s) for s in (r.get("skills") or [])}
        dev_sets.append(ss)
        dev_skills.update(ss)
    top = [s for s, _ in dev_skills.most_common(COOC_TOP)]
    idx = {s: i for i, s in enumerate(top)}
    mat = [[0] * len(top) for _ in top]
    for ss in dev_sets:
        hit = sorted(idx[s] for s in ss if s in idx)
        for a in range(len(hit)):
            mat[hit[a]][hit[a]] += 1
            for b in range(a + 1, len(hit)):
                mat[hit[a]][hit[b]] += 1
                mat[hit[b]][hit[a]] += 1

    # 城市 × 类别矩阵：国内中文 location 按提及计（一条 JD 涉多城分别计入）；
    # HN 英文原文不进矩阵（在明细表中按原文检索）。
    cn_re = re.compile(r"[一-鿿]")
    city_cat = defaultdict(Counter)
    city_total = Counter()
    for r in recs:
        loc = (r.get("location") or "").strip()
        if not cn_re.search(loc):
            continue
        for city in re.split(r"[/,，、]", loc.replace(" ", "")):
            city = city.strip()
            if city:
                city_cat[city][r["category"]] += 1
                city_total[city] += 1
    cities_sorted = [c for c, _ in city_total.most_common()]

    # Sankey：大类 → 归并细分 → 全局 Top15 技能。cat→sub 按 JD 条数；sub→skill 按技能展开
    sankey_link = Counter()
    sankey_subskill = defaultdict(Counter)
    glob_skill = Counter()
    for r in recs:
        c = r["category"]
        s = norm_sub(r.get("sub_category"))
        sankey_link[(c, s)] += 1
        for sk in {norm_skill(x) for x in (r.get("skills") or [])}:
            sankey_subskill[s][sk] += 1
            glob_skill[sk] += 1
    top15 = [s for s, _ in glob_skill.most_common(15)]
    # sub 层「其他」与 cat 层「其他」撞名（同名节点会被归进同一层），改名区分
    links = [{"source": c, "target": ("其他（细分）" if s == "其他" else s), "value": n}
             for (c, s), n in sankey_link.items()]
    for s, cnt in sankey_subskill.items():
        for sk in top15:
            if cnt.get(sk):
                links.append({"source": s, "target": sk, "value": cnt[sk]})

    # UpSet：研发+算法线 Top12 技能的精确组合交集（≥2 技能的 JD 按其观测组合计数）
    exact = Counter()
    for ss in dev_sets:
        hit = frozenset(x for x in top if x in ss)
        if len(hit) >= 2:
            exact[hit] += 1
    combos = [{"set": sorted(k), "n": v} for k, v in exact.most_common(12)]

    # 明细表精简记录（逐条浏览与联动过滤用）
    records = [{
        "co": r.get("company") or "—",
        "t": r["title"],
        "c": r["category"],
        "s": norm_sub(r.get("sub_category")),
        "loc": r.get("location") or "",
        "ty": r.get("employment_type") or "",
        "sa": r.get("salary") or "",
        "sk": [norm_skill(x) for x in (r.get("skills") or [])][:10],
        "u": r.get("source_url") or "",
        "p": r.get("source_platform") or "",
    } for r in recs]

    return {
        "total": total, "n_firms": n_firms, "n_skills": n_skills,
        "cat_n": dict(cat_n), "companies": dict(companies.most_common(COMPANY_SHOW)),
        "cat_company": {c: dict(m.most_common(6)) for c, m in cat_company.items()},
        "tree": {c: {s: dict(v.most_common(SUB_SKILL_SHOW)) for s, v in subs.items()}
                 for c, subs in tree.items()},
        "sub_jd": {c: dict(subs.most_common()) for c, subs in sub_jd.items()},
        "cat_skills": {c: dict(m.most_common()) for c, m in cat_skills.items()},
        "cooc": {"skills": top, "matrix": mat,
                 "n_dev": len(dev)},
        "city_cat": {c: dict(city_cat[c]) for c in cities_sorted},
        "sankey": {"links": links, "skills": top15},
        "upset": {"skills": top, "combos": combos},
        "records": records,
    }


# ── 数据键裁剪：两份页面各自只内嵌所需字段（records 是体积大头，skill-map 不带；
#    tree/roadmaps 是技能页专属，jobs 不带）。cooc 只进 md 报告，两份页面都不带。──
SKILL_MAP_KEYS = ("total", "n_skills", "cat_n", "tree", "sub_jd", "cat_skills", "sankey", "upset")
JOBS_KEYS = ("total", "n_firms", "cat_n", "companies", "cat_company", "city_cat", "records")


def pick(d: dict, keys) -> dict:
    return {k: d[k] for k in keys if k in d}


# 页脚来源行按数据实时生成，数据更新不脱节
PLAT_NAMES = {"官网": "12 家公司官网/官方 ATS（华为、百度无公开数据）", "HN": "HN「Who is hiring」",
              "猎聘快照": "猎聘快照", "BOSS快照": "BOSS快照", "脉脉快照": "脉脉快照",
              "文章": "公开文章",
              "Ashby": "海外 Ashby（OpenAI 等 7 家）", "Greenhouse": "海外 Greenhouse（Anthropic 等 3 家）"}


def _src_line(recs: list) -> str:
    plat = Counter(r.get("source_platform", "") for r in recs)
    return "、".join(f"{PLAT_NAMES.get(k, k)} {v} 条" for k, v in plat.most_common() if k)

def _page_head(title: str) -> str:
    return ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title>\n<style>\n')

# ── 共用基础样式（两页共用）──
_CSS_BASE = r"""
:root{
  --paper:#FBF8F1; --ink:#2b2b2b; --blue:#3D6DB5; --yellow:#F7D154; --red:#D9483B;
  --ink-soft:rgba(43,43,43,.62); --bar:rgba(43,43,43,.13); --line:rgba(43,43,43,.18);
  --kai:"LXGW WenKai","LXGW WenKai GB","Kaiti SC",STKaiti,KaiTi,serif;
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI","Microsoft YaHei",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important;animation:none!important}}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.75}
.wrap{max-width:1080px;margin:0 auto;padding:0 28px 96px}
a{color:var(--blue)}
.num{font-variant-numeric:tabular-nums}

/* ── 头部 / 幕结构 / 页脚（两页共用）── */
header{padding:56px 0 40px}
.brand{margin-bottom:26px}
.brand img{height:46px;display:block}
.brand a{display:inline-block}
.brand a:focus-visible{outline:2px solid var(--blue);outline-offset:4px}
h1{font-family:var(--kai);font-weight:700;font-size:clamp(38px,6vw,58px);letter-spacing:.04em;line-height:1.22}
.sub{margin-top:14px;color:var(--ink-soft);font-size:15px}
.rule{border:none;border-top:3px solid var(--ink);margin:34px 0 0}
.sec{margin-top:72px}
.sec-head{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
.sec-title{font-family:var(--kai);font-size:30px;font-weight:700;letter-spacing:.03em}
.sec-note{color:var(--ink-soft);font-size:13.5px}
.hint{margin-top:14px;font-size:13px;color:var(--ink-soft)}
footer{margin-top:88px;border-top:3px solid var(--ink);padding-top:22px;font-size:13px;color:var(--ink-soft)}
footer .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:34px}
footer p{margin:0}
.copyright{margin-top:20px !important;font-size:12.5px}
footer a{color:var(--blue)}
@media (max-width:860px){footer .cols{grid-template-columns:1fr;gap:14px} header{padding-top:56px}}
"""


# ── 技能地图页样式 ──
_CSS_SKILL_MAP = r"""


/* ── 一、技能谱系树 ── */
.tree{margin-top:34px;border-top:3px solid var(--ink)}
.line-h{cursor:pointer;user-select:none;padding:20px 4px;border-bottom:1px solid var(--line);
  display:flex;align-items:baseline;flex-wrap:wrap;gap:8px 18px}
.line-h:hover{background:rgba(61,109,181,.06)}
.line-h .caret{font-size:13px;color:var(--blue);width:1.2em;display:inline-block;transition:transform .25s ease}
.line-h.open .caret{transform:rotate(90deg)}
.line-h .name{font-family:var(--kai);font-size:24px;font-weight:700;letter-spacing:.02em}
.line-h .cnt{color:var(--ink-soft);font-size:13.5px}
.line-h .tops{margin-left:auto;font-size:13px;color:var(--ink-soft);max-width:56%;}
.line-h .tops b{color:var(--ink);font-weight:600}
.line-body{max-height:0;overflow:hidden;transition:max-height .5s ease}
.line-body.open{max-height:3600px}
.dir{border-bottom:1px solid var(--line);padding:14px 4px 14px 34px}
.dir-h{cursor:pointer;user-select:none;display:flex;align-items:baseline;gap:12px}
.dir-h:hover .dir-name{color:var(--blue)}
.dir-h .caret{font-size:12px;color:var(--blue);width:1em;display:inline-block;transition:transform .25s ease}
.dir.open > .dir-h .caret{transform:rotate(90deg)}
.dir-name{font-weight:600;font-size:15.5px}
.dir-h .cnt{color:var(--ink-soft);font-size:12.5px}
.skills{max-height:0;overflow:hidden;transition:max-height .4s ease}
.dir.open > .skills{max-height:700px}
.skill-row{display:grid;grid-template-columns:200px 1fr 44px;gap:14px;align-items:center;
  padding:5px 0 5px 26px;font-size:13.5px}
.skill-row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.skill-row .track{height:13px;background:var(--bar);position:relative}
.skill-row .fill{position:absolute;inset:0 auto 0 0;background:var(--ink);transition:width .5s cubic-bezier(.6,0,.2,1),background .2s}
.skill-row:hover .fill{background:var(--blue)}
.skill-row .v{text-align:right;color:var(--blue);font-variant-numeric:tabular-nums}

/* ── 二、按岗位的学习路线 ── */
.path-tabs{display:flex;gap:8px;margin-top:28px;flex-wrap:wrap}
.path-tab{font-family:var(--kai);font-size:17px;padding:7px 20px;border:2px solid var(--ink);
  background:transparent;cursor:pointer;color:var(--ink)}
.path-tab[aria-selected="true"]{background:var(--ink);color:var(--paper)}
.path-tab:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.stage{margin-top:30px}
.stage-label{font-size:13px;color:var(--ink-soft);margin-bottom:10px}
.stage-label b{color:var(--ink);font-weight:600}
.base-row{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.lanes{display:grid;gap:18px;margin-top:8px}
@media (min-width:900px){.lanes{grid-template-columns:1fr 1fr}}
.lane{border:1.5px solid var(--line);padding:16px 18px 14px;overflow-x:auto}
.lane-h{font-family:var(--kai);font-weight:700;font-size:17px;margin-bottom:4px}
.lane-sub{font-size:12px;color:var(--ink-soft);margin-bottom:12px}
.flow{display:flex;align-items:stretch;gap:0;flex-wrap:wrap;row-gap:10px}
.node{border:2px solid var(--ink);background:var(--bar);padding:7px 13px;font-size:13.5px;white-space:nowrap;
  display:inline-flex;align-items:baseline;gap:7px}
__FAM_CSS__
.node .n{color:var(--blue);font-size:12px;font-variant-numeric:tabular-nums}
.node:hover{outline:2px solid var(--blue);outline-offset:-1px}
.fam-legend{display:flex;flex-wrap:wrap;gap:8px 22px;margin:16px 0 4px;font-size:13px;color:var(--ink-soft)}
.fam-legend .sw{display:inline-block;width:13px;height:13px;border:1.5px solid var(--ink);vertical-align:-2px;margin-right:7px}
.joint{width:26px;flex:none;display:flex;align-items:center;justify-content:center;color:var(--ink-soft);
  font-size:14px}
.dir-minor{padding:10px 4px 10px 34px;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink-soft)}
.skill-heat{display:grid;gap:3px;font-size:13px;margin-top:8px}
.skill-heat .s-row{font-weight:600;text-align:right;padding:5px 10px 5px 0;white-space:nowrap}
.skill-heat .s-col{font-weight:600;text-align:center;padding:4px}
.skill-heat .s-cell{display:flex;align-items:center;justify-content:flex-end;padding:5px 8px;
  font-variant-numeric:tabular-nums;border-radius:2px;min-height:30px}
.skill-heat .s-cell:hover{outline:2px solid var(--blue);outline-offset:-1px}
.skill-heat .s-cell.z{background:rgba(43,43,43,.04)}
.heatmap{display:grid;gap:3px;font-size:13px;margin-top:8px}
.heatmap .s-row{font-weight:600;text-align:right;padding:5px 10px 5px 0;white-space:nowrap}
.heatmap .s-col{font-weight:600;text-align:center;padding:4px}
.heatmap .s-cell{display:flex;align-items:center;justify-content:flex-end;padding:5px 8px;
  font-variant-numeric:tabular-nums;border-radius:2px;min-height:30px}
.heatmap .s-cell:hover{outline:2px solid var(--blue);outline-offset:-1px}
.heatmap .s-cell.z{background:rgba(43,43,43,.04)}
.heatmap .h-col{font-weight:600;text-align:center;padding:4px}
.heatmap .h-sum{color:var(--ink-soft)}
.heat-legend{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:12.5px;color:var(--ink-soft)}
.heat-legend .sw{width:22px;height:14px;border:1px solid var(--line)}

"""


# ── 岗位版图页样式 ──
_CSS_JOBS = r"""




/* ── 一、岗位版图（堆叠条 + 公司表）── */
.stack{margin-top:30px}
.stack-bar{display:flex;height:64px;overflow:hidden;border:2px solid var(--ink)}
.seg{position:relative;cursor:default;transition:flex-grow .45s cubic-bezier(.6,0,.2,1);min-width:64px;overflow:hidden}
.seg + .seg{border-left:2px solid var(--ink)}
.seg .lab{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 12px;
  color:var(--ink);white-space:nowrap}
.seg .lab b{font-size:20px;line-height:1.3}
.seg .lab span{font-size:12.5px;color:var(--ink-soft)}
.seg.hot .lab b{color:var(--blue)}
.seg-detail{margin-top:0;max-height:0;overflow:hidden;transition:max-height .4s ease}
.seg-detail.open{max-height:220px}
.seg-detail .inner{border:2px solid var(--ink);border-top:none;padding:14px 18px;display:flex;flex-wrap:wrap;gap:8px 22px;font-size:13.5px}
.seg-detail .inner span{white-space:nowrap}
.seg-detail .inner b{color:var(--blue)}
.legend{display:flex;flex-wrap:wrap;gap:10px 26px;margin-top:16px;font-size:13px;color:var(--ink-soft)}
.asym{display:grid;grid-template-columns:220px 1fr;gap:40px;margin-top:44px;align-items:start}
.howto{font-size:13.5px;color:var(--ink-soft);position:sticky;top:24px}
.howto p{margin-bottom:10px}
.howto b{color:var(--ink)}
table.firms{width:100%;border-collapse:collapse;font-size:14px}
table.firms th{font-weight:600;text-align:left;border-bottom:2px solid var(--ink);padding:8px 10px 8px 0}
table.firms td{border-bottom:1px solid var(--line);padding:8px 10px 8px 0;vertical-align:baseline}
table.firms td.n{text-align:right;font-variant-numeric:tabular-nums}
table.firms .mini{color:var(--ink-soft);font-size:12.5px}

/* ── 二、城市 × 类别热力矩阵 ── */
.heatmap{display:grid;gap:3px;font-size:13.5px;margin-top:6px}
.heatmap .h-cell{display:flex;align-items:center;justify-content:flex-end;padding:6px 8px;
  font-variant-numeric:tabular-nums;border-radius:2px;cursor:pointer;min-height:34px}
.heatmap .h-cell:hover{outline:2px solid var(--blue);outline-offset:-1px}
.heatmap .h-row{font-weight:600;text-align:right;padding:6px 10px 6px 0;white-space:nowrap}
.heatmap .h-col{font-weight:600;text-align:center;padding:4px}
.heatmap .h-sum{color:var(--ink-soft);font-variant-numeric:tabular-nums;font-weight:400}
.heat-legend{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:12.5px;color:var(--ink-soft)}
.heat-legend .sw{width:22px;height:14px;border:1px solid var(--line)}

/* ── 三、JD 明细表 ── */
.jd-filters{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:end;margin:8px 0 14px;
  font-size:13.5px;color:var(--ink-soft)}
.jd-filters label{display:flex;flex-direction:column;gap:4px}
.jd-filters select,.jd-filters input{font:inherit;color:var(--ink);background:var(--paper);
  border:1px solid var(--line);padding:5px 8px;min-width:120px}
.jd-filters button{font:inherit;border:1px solid var(--ink);background:none;padding:6px 14px;
  cursor:pointer;align-self:end}
.jd-filters button:hover{background:var(--ink);color:var(--paper)}
table.jd-table{width:100%;border-collapse:collapse;font-size:13.5px}
table.jd-table th{font-weight:600;text-align:left;border-bottom:2px solid var(--ink);
  padding:8px 10px 8px 0;white-space:nowrap}
table.jd-table td{border-bottom:1px solid var(--line);padding:7px 10px 7px 0;vertical-align:top}
table.jd-table td.n{white-space:nowrap}
table.jd-table .t{font-weight:600}
table.jd-table a{color:var(--blue)}
table.jd-table .sk span{display:inline-block;border:1px solid var(--line);padding:1px 7px;
  margin:1px 4px 1px 0;font-size:12px;border-radius:9px;white-space:nowrap}
table.jd-table .sub{color:var(--ink-soft);font-size:12.5px}
table.jd-table tbody tr:hover{background:rgba(61,109,181,.06)}

@media (max-width:860px){
  .asym{grid-template-columns:1fr;gap:24px}
  .howto{position:static}
}
"""


_HEAD_CLOSE = "</style>\n</head>\n<body>\n"
_TAIL = "\n</body>\n</html>\n"


_SKILL_MAP_BODY = r"""<div class="wrap">
<header>
  <div class="brand"><a href="https://github.com/ForceInjection" title="ForceInjection on GitHub" target="_blank" rel="noopener"><img src="../../img/AI原力注入-logo.png" alt="AI 原力注入"></a></div>
  <h1>AI Infra 技能地图 · __CH_NAME__</h1>
  <p class="sub">从 <span class="num" id="k-total"></span> 条__CH_NAME__在招岗位说明（JD）中提炼的分类与技能谱系。数据全部来自公开发布的招聘页面，逐条留有出处，采集于 2026-11-19，数据来自国内 AI 公司官方招聘渠道。</p>
  <hr class="rule">
</header>

<section class="sec">
  <div class="sec-head"><span class="sec-title">一、技能谱系树</span>
    <span class="sec-note">点线名展开；叶长 = JD 条数</span></div>
  <div class="tree" id="tree"></div>
  <p class="hint">技能名做过归一化（Kubernetes/K8s 合并、LLM 与大模型合并等）；每方向展示前 18 个技能，完整清单见分析报告 skill-tree.md（本地 analysis/ 目录）。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">二、按岗位的学习路线</span>
    <span class="sec-note">块色 = 技能家族（见下方图例）；块上数字 = 要求该技能的 JD 条数</span></div>
  <div class="path-tabs" id="path-tabs"></div>
  <div id="path-view"></div>
  <p class="hint">路线的先后顺序是编辑判断：依据 JD 频次（数字大小）与技能间的依赖关系（底层语言先于框架，框架先于调优），JD 原文本身没有顺序。技能共现分析见本地分析报告 skill-tree.md（analysis/ 目录）。计数口径：方向 JD 提及的技能按方向计，其余按整条线计。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">三、技能 × 岗位类别</span>
    <span class="sec-note">格色深浅 = 要求该技能的 JD 条数</span></div>
  <div id="skill-heat"></div>
  <p class="hint">技能取本渠道要求频次 Top 25，横轴按类别展开（一条 JD 多技能分别计入）。同一技能在不同类别中的位次差异，就是岗位对它要求程度的直接对比。</p>
</section>

<footer><div class="cols">
  <p><b>口径。</b>全部记录为 JD 全文（full）。岗位职责逐条照抄原文拆分，未做概括。</p>
  <p><b>来源。</b>__SRCLINE__。每条记录的 source_url 可追溯到原页。完整方法见 <a href="README.md">README</a>。</p>
  <p><b>时效。</b>数字为采集日（2026-11-19）快照。学习路线的先后顺序是编辑判断，技能计数随数据更新。</p>
</div>
<p class="copyright">© 2026 公众号「AI 原力注入」 · 数据可视化基于 ai_infra_jd_survey 数据集生成 · 转载请保留出处与数据口径</p>
</footer>
</div>

<script>
const D = __DATA__;
const CAT_DISPLAY_ORDER = __CAT_ORDER__;
/* ── KPI ── */
document.getElementById('k-total').textContent = D.total;

/* ── 大类清单（技能树与路线计数共用）── */
const CATS = CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]);

/* ── 一、技能谱系树 ── */
const tree = document.getElementById('tree');
const LINES = CATS.filter(c => (D.sub_jd[c] && Object.keys(D.sub_jd[c]).length));
LINES.forEach((c, li) => {
  const line = document.createElement('div');
  const tops = Object.entries(D.cat_skills[c] || {}).slice(0, 6)
    .map(([s,n]) => `<b>${s}</b>(${n})`).join('、');
  line.innerHTML = `<div class="line-h" role="button" tabindex="0" aria-expanded="false">
      <span class="caret">▶</span><span class="name">${c}线</span>
      <span class="cnt num">${D.cat_n[c]} 条 JD</span>
      <span class="tops">${tops}</span></div>
    <div class="line-body"></div>`;
  const body = line.querySelector('.line-body');
  // 方向排序：JD 数降序；<3 条的方向合并成一行次要条目
  const subs = Object.entries(D.sub_jd[c]).sort((a,b) => b[1]-a[1]);
  const minor = [];
  subs.forEach(([sub, nSub]) => {
    if (nSub < 3) { minor.push(`${sub}(${nSub})`); return; }
    const skills = (D.tree[c] && D.tree[c][sub]) || {};
    const mx = Math.max(1, ...Object.values(skills));
    const dir = document.createElement('div');
    dir.className = 'dir';
    dir.innerHTML = `<div class="dir-h" role="button" tabindex="0" aria-expanded="false">
        <span class="caret">▶</span><span class="dir-name">${sub}</span>
        <span class="cnt num">${nSub} 条</span></div>
      <div class="skills">${Object.entries(skills).map(([s,n]) =>
        `<div class="skill-row"><span class="nm">${s}</span>
         <span class="track"><span class="fill" data-w="${(n/mx*100).toFixed(1)}" style="width:0"></span></span>
         <span class="v num">${n}</span></div>`).join('')}</div>`;
    const dh = dir.querySelector('.dir-h');
    const toggleDir = () => {
      const on = dir.classList.toggle('open');
      dh.setAttribute('aria-expanded', on);
      if (on) dir.querySelectorAll('.fill').forEach(f => f.style.width = f.dataset.w + '%');
    };
    dh.addEventListener('click', toggleDir);
    dh.addEventListener('keydown', e => { if (e.key==='Enter'||e.key===' ') { e.preventDefault(); toggleDir(); } });
    body.appendChild(dir);
  });
  if (minor.length) {
    const mrow = document.createElement('div');
    mrow.className = 'dir-minor';
    mrow.textContent = `其余方向：${minor.join('、')}`;
    body.appendChild(mrow);
  }
  const lh = line.querySelector('.line-h');
  const toggleLine = () => {
    const on = line.classList.toggle('open') !== undefined ? line.classList.contains('open') : false;
    lh.classList.toggle('open', on);
    lh.setAttribute('aria-expanded', on);
    body.classList.toggle('open', on);
  };
  lh.addEventListener('click', toggleLine);
  lh.addEventListener('keydown', e => { if (e.key==='Enter'||e.key===' ') { e.preventDefault(); toggleLine(); } });
  tree.appendChild(line);
  if (li === 0 || new URLSearchParams(location.search).get('expand') === 'all') {
    if (!line.classList.contains('open')) toggleLine();
  }
});
// ?expand=all 同时展开全部方向
if (new URLSearchParams(location.search).get('expand') === 'all') {
  document.querySelectorAll('.dir-h').forEach(dh => dh.click());
}

/* ── 二、按岗位的学习路线 ── */
const ROADMAPS = __ROADMAPS__;
const FAMILY_DEF = __FAMILIES__;
const FAMILIES = {};
const FAM_LABEL = {};
Object.entries(FAMILY_DEF).forEach(([f, v]) => { FAMILIES[f] = v.skills; FAM_LABEL[f] = v.label; });
const famOf = {};
Object.entries(FAMILIES).forEach(([f, names]) => names.forEach(n => famOf[n] = f));
const tabs = document.getElementById('path-tabs');
const view = document.getElementById('path-view');
const LINE_NAMES = Object.keys(ROADMAPS);
let curLine = null;

// 计数查找：方向树优先（该方向的 JD 数），方向内未提及则回退线级
function skillCount(line, sub, name) {
  if (sub && D.tree[line] && D.tree[line][sub] && D.tree[line][sub][name]) return D.tree[line][sub][name];
  return (D.cat_skills[line] || {})[name] || 0;
}
function nodeHTML(line, sub, name) {
  const n = skillCount(line, sub, name);
  const f = famOf[name];
  return `<span class="node${f ? ' f-' + f : ''}">${name}<span class="n num">${n}</span></span>`;
}

function renderPath(line) {
  curLine = line;
  view.innerHTML = '';
  const R = ROADMAPS[line];
  // 图例
  const legend = document.createElement('div');
  legend.className = 'fam-legend';
  legend.innerHTML = Object.entries(FAM_LABEL).map(([f, lab]) =>
    `<span><span class="sw ${f}"></span>${lab}</span>`).join('');
  view.appendChild(legend);
  // 底座层（非技术线 base 为空，整段不渲染）
  if (R.base && R.base.length) {
    const base = document.createElement('div');
    base.className = 'stage';
    base.innerHTML = `<div class="stage-label"><b>第 0 层 · 底座</b>——编辑推荐的公共底座（数字为 JD 显式提及条数；Linux / Python 属行业默认技能，多数 JD 不再显式写出，提及少不代表不需要）</div>
      <div class="base-row">${R.base.map(s => nodeHTML(line, null, s)).join('<span class="joint">+</span>')}</div>`;
    view.appendChild(base);
  }
  // 分支泳道
  const stage = document.createElement('div');
  stage.className = 'stage';
  stage.innerHTML = `<div class="stage-label"><b>分方向路线</b>——每个方向从左到右是建议的学习顺序</div>`;
  const lanes = document.createElement('div');
  lanes.className = 'lanes';
  R.lanes.forEach(L => {
    const nSub = (D.sub_jd[line] && D.sub_jd[line][L.sub]) || D.cat_n[line];
    const lane = document.createElement('div');
    lane.className = 'lane';
    lane.innerHTML = `<div class="lane-h">${L.name}</div>
      <div class="lane-sub num">${nSub} 条 JD</div>
      <div class="flow">${L.skills.map((s, i) =>
        (i ? '<span class="joint">→</span>' : '') + nodeHTML(line, L.sub, s)
      ).join('')}</div>`;
    lanes.appendChild(lane);
  });
  stage.appendChild(lanes);
  view.appendChild(stage);
}

LINE_NAMES.forEach(line => {
  const b = document.createElement('button');
  b.className = 'path-tab';
  b.textContent = line + '线';
  b.setAttribute('role', 'tab');
  b.addEventListener('click', () => {
    tabs.querySelectorAll('.path-tab').forEach(t => t.setAttribute('aria-selected', 'false'));
    b.setAttribute('aria-selected', 'true');
    renderPath(line);
  });
  tabs.appendChild(b);
});
if (LINE_NAMES.length) tabs.firstChild.click();
/* ── 三、技能 × 岗位类别热力矩阵 ── */
(function () {
  const box = document.getElementById('skill-heat');
  const cats = CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]);
  const skCats = D.cat_skills || {};
  const skills = Object.entries(Object.values(skCats).reduce((acc, m) => {
    Object.entries(m).forEach(([s, n]) => acc[s] = (acc[s] || 0) + n);
    return acc;
  }, {})).sort((a, b) => b[1] - a[1]).slice(0, 25).map(x => x[0]);
  if (!skills.length) { box.textContent = '（无数据）'; return; }
  const grid = document.createElement('div');
  grid.className = 'heatmap';
  grid.style.gridTemplateColumns = `170px repeat(${cats.length}, 1fr) 64px`;
  const mk = (cls, txt) => { const e = document.createElement('div'); e.className = cls; if (txt != null) e.textContent = txt; return e; };
  grid.appendChild(mk('h-col', ''));
  cats.forEach(c => grid.appendChild(mk('h-col', c)));
  grid.appendChild(mk('h-col h-sum', '合计'));
  let max = 1;
  const cellVal = (s, c) => ((skCats[c] || {})[s] || 0);
  skills.forEach(s => cats.forEach(c => { const v = cellVal(s, c); if (v > max) max = v; }));
  skills.forEach(s => {
    grid.appendChild(mk('s-row', s));
    let sum = 0;
    cats.forEach(c => {
      const v = cellVal(s, c);
      sum += v;
      const cell = mk('s-cell', v ? v : '');
      if (v) {
        cell.style.background = `rgba(61,109,181,${(0.08 + 0.52 * v / max).toFixed(3)})`;
        cell.title = `${s} × ${c}：${v} 条`;
      } else { cell.classList.add('z'); }
      grid.appendChild(cell);
    });
    const t = mk('s-cell h-sum', sum);
    t.style.fontWeight = '600';
    grid.appendChild(t);
  });
  box.appendChild(grid);
  const lg = document.createElement('div');
  lg.className = 'heat-legend';
  lg.appendChild(mk('span', '浅'));
  for (const a of [0.10, 0.28, 0.46, 0.60]) { const sw = mk('span', ''); sw.className = 'sw'; sw.style.background = `rgba(61,109,181,${a})`; lg.appendChild(sw); }
  lg.appendChild(mk('span', '深 = 条数多（每格最大值 ' + max + '）'));
  box.appendChild(lg);
})();

</script>"""


_JOBS_BODY = r"""<div class="wrap">
<header>
  <div class="brand"><a href="https://github.com/ForceInjection" title="ForceInjection on GitHub" target="_blank" rel="noopener"><img src="../../img/AI原力注入-logo.png" alt="AI 原力注入"></a></div>
  <h1>AI Infra 岗位版图 · __CH_NAME__</h1>
  <p class="sub">从 <span class="num" id="k-total"></span> 条__CH_NAME__在招岗位说明（JD）中提炼的分类与技能谱系。数据全部来自公开发布的招聘页面，逐条留有出处，采集于 2026-11-19，数据来自国内 AI 公司官方招聘渠道。</p>
  <hr class="rule">
</header>

<section class="sec">
  <div class="sec-head"><span class="sec-title">一、岗位从哪来</span>
    <span class="sec-note">宽度即条数，悬停查看公司构成</span></div>
  <div class="stack">
    <div class="stack-bar" id="stack"></div>
    <div id="seg-detail" class="seg-detail"><div class="inner" id="seg-inner"></div></div>
    <div class="legend" id="legend"></div>
  </div>

  <div class="asym">
    <div class="howto">
      <p><b>怎么读这张页。</b>条形与数字都是「要求该技能的 JD 条数」。</p>
      <p>计数单位是岗位，不是出现次数：一条 JD 写三遍 Python 也只算一次。</p>
      <p>每条线、每个方向都可以点开。样本少于 5 条的方向只做参考。</p>
    </div>
    <div>
      <table class="firms" id="firms">
        <thead><tr><th>公司</th><th style="text-align:right">JD 条数</th><th>类别构成</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">二、城市 × 岗位类别</span>
    <span class="sec-note">格色深浅 = JD 条数；点击格子跳到明细表</span></div>
  <div id="heatmap"></div>
  <p class="hint">按城市提及计数，一条 JD 涉多城市分别计入，列合计大于总条数；含少量海外城市（新加坡、伦敦等），海外岗位可在明细表检索。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">三、JD 明细</span>
    <span class="sec-note">全部记录逐条可查；从上面任意一幕点击元素会联动过滤到此表</span></div>
  <div class="jd-filters" id="jd-filters">
    <label>类别 <select id="f-cat"><option value="">全部</option></select></label>
    <label>城市 <select id="f-city"><option value="">全部</option></select></label>
    <label>类型 <select id="f-ty"><option value="">全部</option></select></label>
    <label>技能 <input id="f-skill" type="search" placeholder="如 CUDA / vLLM"></label>
    <label>公司 <input id="f-co" type="search" placeholder="如 字节 / DeepSeek"></label>
    <button id="f-reset" type="button">重置</button>
  </div>
  <table class="jd-table" id="jd-table">
    <thead><tr><th>公司</th><th>职位</th><th>类别 / 细分</th><th>城市</th><th>类型</th><th>技能</th></tr></thead>
    <tbody></tbody>
  </table>
  <p class="hint" id="jd-count"></p>
</section>

<footer><div class="cols">
  <p><b>口径。</b>全部记录为 JD 全文（full）。岗位职责逐条照抄原文拆分，未做概括。</p>
  <p><b>来源。</b>__SRCLINE__。每条记录的 source_url 可追溯到原页。完整方法见 <a href="README.md">README</a>。</p>
  <p><b>时效。</b>数字为采集日（2026-11-19）快照，技能计数随数据更新。</p>
</div>
<p class="copyright">© 2026 公众号「AI 原力注入」 · 数据可视化基于 ai_infra_jd_survey 数据集生成 · 转载请保留出处与数据口径</p>
</footer>
</div>

<script>
const D = __DATA__;
const CAT_DISPLAY_ORDER = __CAT_ORDER__;

/* ── KPI ── */
document.getElementById('k-total').textContent = D.total;

/* ── 一、岗位版图（堆叠条）── */
const CATS = CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]);
const stack = document.getElementById('stack');
const detail = document.getElementById('seg-detail');
const segInner = document.getElementById('seg-inner');
let opened = null;
CATS.forEach((c, i) => {
  const seg = document.createElement('div');
  seg.className = 'seg';
  seg.style.flexGrow = D.cat_n[c];
  seg.style.background = i % 2 ? 'rgba(43,43,43,.16)' : 'rgba(43,43,43,.07)';
  seg.innerHTML = `<div class="lab"><b class="num">${D.cat_n[c]}</b><span>${c} ${Math.round(D.cat_n[c]/D.total*100)}%</span></div>`;
  seg.addEventListener('mouseenter', () => { seg.classList.add('hot'); openDetail(c); });
  seg.addEventListener('mouseleave', () => seg.classList.remove('hot'));
  seg.addEventListener('click', () => openDetail(c));
  stack.appendChild(seg);
  const lg = document.createElement('span');
  lg.textContent = `${c} ${D.cat_n[c]}`;
  document.getElementById('legend').appendChild(lg);
});
function openDetail(c){
  if (opened === c) return; opened = c;
  const items = D.cat_company[c] || {};
  segInner.innerHTML = `<b>${c}线 · 公司构成</b>` +
    Object.entries(items).map(([k,v]) => `<span>${k} <b class="num">${v}</b></span>`).join('');
  detail.classList.add('open');
}

/* ── 公司表 ── */
const tbody = document.querySelector('#firms tbody');
Object.entries(D.companies).forEach(([k,v]) => {
  const parts = CATS.map(c => (D.cat_company[c]||{})[k] ? `${c}${D.cat_company[c][k]}` : null).filter(Boolean).join('/');
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${k}</td><td class="n num">${v}</td><td class="mini">${parts}</td>`;
  tbody.appendChild(tr);
});

/* ── 二、城市 × 类别热力矩阵 ── */
(function () {
  const wrap = document.getElementById('heatmap');
  const cities = Object.keys(D.city_cat || {});
  if (!cities.length) { wrap.textContent = '（无国内城市数据）'; return; }
  const cats = CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]);
  const grid = document.createElement('div');
  grid.className = 'heatmap';
  grid.style.gridTemplateColumns = `110px repeat(${cats.length}, 1fr) 52px`;
  const mk = (tag, cls, txt) => { const e = document.createElement(tag); e.className = cls; e.textContent = txt; return e; };
  // 列头
  grid.appendChild(mk('div', 'h-col', ''));
  cats.forEach(c => grid.appendChild(mk('div', 'h-col', c)));
  grid.appendChild(mk('div', 'h-col h-sum', '合计'));
  // 数据行
  let max = 1;
  cities.forEach(c => Object.values(D.city_cat[c]).forEach(v => { if (v > max) max = v; }));
  cities.forEach(city => {
    grid.appendChild(mk('div', 'h-row', city));
    let sum = 0;
    cats.forEach(cat => {
      const v = (D.city_cat[city][cat] || 0);
      sum += v;
      const cell = mk('div', 'h-cell', v ? v : '');
      if (v) {
        cell.style.background = `rgba(61,109,181,${(0.08 + 0.52 * v / max).toFixed(3)})`;
        cell.title = `${city} × ${cat}：${v} 条（点击查看明细）`;
        cell.addEventListener('click', () => window.jdFilter({ cat, city, plat: '', skill: '', co: '' }));
      } else { cell.style.background = 'rgba(61,109,181,.04)'; }
      grid.appendChild(cell);
    });
    const t = mk('div', 'h-cell h-sum', sum);
    t.style.fontWeight = '600';
    grid.appendChild(t);
  });
  wrap.appendChild(grid);
  const lg = document.createElement('div');
  lg.className = 'heat-legend';
  lg.appendChild(mk('span', '', '浅'));
  for (let a of [0.10, 0.28, 0.46, 0.60]) { const s = mk('span', 'sw'); s.style.background = `rgba(61,109,181,${a})`; lg.appendChild(s); }
  lg.appendChild(mk('span', '', '深 = 条数多（每格最大值 ' + max + '）'));
  wrap.appendChild(lg);
})();

/* ── 三、JD 明细表 ── */
(function () {
  const REC = D.records || [];
  const $ = id => document.getElementById(id);
  const fCat = $('f-cat'), fCity = $('f-city'), fTy = $('f-ty'),
        fSkill = $('f-skill'), fCo = $('f-co'), fReset = $('f-reset');
  const state = { cat: '', city: '', ty: '', skill: '', co: '' };

  // 下拉选项
  CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]).forEach(c => fCat.appendChild(new Option(c, c)));
  const cnRe = /[一-鿿]/;
  const citySet = new Set();
  REC.forEach(r => (r.loc || '').replace(/ /g, '').split(/[/,，、]/).forEach(x => { if (x && cnRe.test(x)) citySet.add(x); }));
  [...citySet].sort().forEach(c => fCity.appendChild(new Option(c, c)));
  [...new Set(REC.map(r => r.ty).filter(Boolean))].sort().forEach(t => fTy.appendChild(new Option(t, t)));

  function syncControls() {
    fCat.value = state.cat; fCity.value = state.city; fTy.value = state.ty;
    fSkill.value = state.skill; fCo.value = state.co;
  }
  function apply() {
    const q = { skill: state.skill.trim().toLowerCase(), co: state.co.trim().toLowerCase() };
    const rows = REC.filter(r =>
      (!state.cat || r.c === state.cat) &&
      (!state.city || (r.loc || '').replace(/ /g, '').split(/[/,，、]/).includes(state.city)) &&
      (!state.ty || r.ty === state.ty) &&
      (!q.skill || r.sk.some(s => s.toLowerCase().includes(q.skill))) &&
      (!q.co || (r.co + ' ' + r.t).toLowerCase().includes(q.co)));
    const tb = $('jd-table').querySelector('tbody');
    tb.innerHTML = '';
    const frag = document.createDocumentFragment();
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="n">${r.co}</td>` +
        `<td class="t">${r.u ? `<a href="${r.u}" target="_blank" rel="noopener">${r.t}</a>` : r.t}</td>` +
        `<td>${r.c}<span class="sub">${r.s ? ' · ' + r.s : ''}</span></td>` +
        `<td class="n">${r.loc || '—'}</td>` +
        `<td class="n">${r.ty || '—'}</td>` +
        `<td class="sk">${(r.sk || []).map(s => `<span>${s}</span>`).join('')}</td>`;
      frag.appendChild(tr);
    });
    tb.appendChild(frag);
    $('jd-count').textContent = `筛选后 ${rows.length} 条 / 全部 ${REC.length} 条`;
  }
  [fCat, fCity, fTy].forEach(s => s.addEventListener('change', () => { state[s.id.slice(2).toLowerCase()] = s.value; apply(); }));
  fSkill.addEventListener('input', () => { state.skill = fSkill.value; apply(); });
  fCo.addEventListener('input', () => { state.co = fCo.value; apply(); });
  fReset.addEventListener('click', () => { Object.assign(state, { cat: '', city: '', ty: '', skill: '', co: '' }); syncControls(); apply(); });
  // 联动入口：其他幕的点击 → jdFilter({cat, city, ...})，滚动到明细
  window.jdFilter = function (patch) {
    Object.assign(state, patch);
    syncControls(); apply();
    document.getElementById('jd-table').scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  apply();
})();
</script>"""


SKILL_MAP_TEMPLATE = (_page_head("AI Infra 技能地图") + _CSS_BASE + _CSS_SKILL_MAP
                      + _HEAD_CLOSE + _SKILL_MAP_BODY + _TAIL)
JOBS_TEMPLATE = (_page_head("AI Infra 岗位版图") + _CSS_BASE + _CSS_JOBS
                 + _HEAD_CLOSE + _JOBS_BODY + _TAIL)


def build_skill_map(d: dict, recs: list, ch_name: str) -> str:
    data_json = json.dumps(pick(d, SKILL_MAP_KEYS), ensure_ascii=False)
    roadmaps_json = json.dumps(ROADMAPS, ensure_ascii=False)
    family_json = json.dumps(
        {k: {"label": v.get("label", k), "skills": sorted(v["skills"])} for k, v in FAMILY_DEF.items()},
        ensure_ascii=False)
    order_json = json.dumps(CAT_ORDER, ensure_ascii=False)
    # 家族色板：由 catalog 的 skill_family.items[*].color 生成（节点块与图例色样共用一条规则）
    fam_css = "\n".join(
        f".node.f-{k},.fam-legend .sw.{k}{{background:{v['color']}}}"
        for k, v in FAMILY_DEF.items())
    return (SKILL_MAP_TEMPLATE
            .replace("__FAM_CSS__", fam_css)
            .replace("__ROADMAPS__", roadmaps_json)
            .replace("__FAMILIES__", family_json)
            .replace("__CAT_ORDER__", order_json)
            .replace("__DATA__", data_json)
            .replace("__SRCLINE__", _src_line(recs))
            .replace("__CH_NAME__", ch_name))


def build_jobs(d: dict, recs: list, ch_name: str) -> str:
    data_json = json.dumps(pick(d, JOBS_KEYS), ensure_ascii=False)
    order_json = json.dumps(CAT_ORDER, ensure_ascii=False)
    return (JOBS_TEMPLATE
            .replace("__CAT_ORDER__", order_json)
            .replace("__DATA__", data_json)
            .replace("__SRCLINE__", _src_line(recs))
            .replace("__CH_NAME__", ch_name))


CHANNELS = (("社招", "society"), ("校招", "campus"))


def main():
    paths = sorted((BASE / "data").glob("jd_*.jsonl"))
    recs = []
    for p in paths:
        recs.extend(load(p))
    made = []
    for ch_name, ch_slug in CHANNELS:
        subset = [r for r in recs if r.get("recruit_channel") == ch_name]
        d = aggregate(subset)
        for template_name, out_name, build in (
                ("技能地图", f"skill-map-{ch_slug}.html", build_skill_map),
                ("岗位版图", f"jobs-{ch_slug}.html", build_jobs)):
            html = build(d, subset, ch_name)
            out = BASE / out_name
            out.write_text(html, encoding="utf-8")
            made.append(f"{out_name}（{template_name}·{ch_name} {len(subset)} 条，{len(html) // 1024} KB）")
    print("生成：" + "；".join(made))


if __name__ == "__main__":
    main()
