#!/usr/bin/env python3
"""生成 JD 数据集四份独立可视化页面（社招/校招 × 技能地图/岗位版图）。

用法：python3 scripts/build_visualization.py
输出：skill-map-{society|campus}.html —— 技能地图（〇 三视角总览 / 一 技能谱系树 / 二 学习路线 / 三 技术栈×岗位类别热力）
      jobs-{society|campus}.html      —— 岗位版图（一 岗位堆叠条+公司表 / 二 城市×类别热力矩阵 / 三 JD 明细表）
四份为零外部 JS/CSS 依赖的单文件 HTML（页首 logo 引用同仓库 img/ 图片），按渠道各自独立成页；
数据更新后重跑即刷新。
技能归一化复用 analyze.py 的映射表；技能的 kind/type/scope/work_type 归属读 catalog 的
skill.taxonomy（唯一定义源），build 内不硬编码。
"""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import norm_skill, norm_sub  # noqa: E402

BASE = Path(__file__).resolve().parent.parent

SUB_SKILL_SHOW = 18         # 每方向展示技能叶数
COMPANY_SHOW = 12           # 公司表行数
HEAT_TOP = 25               # 热力矩阵行数（仅 technique 词）

CATALOG = json.loads((BASE / "data" / "skill_catalog.json").read_text(encoding="utf-8"))
CAT_ORDER = CATALOG["category"]["order"]
FAMILY_DEF = CATALOG["skill_family"]["items"]
ROADMAPS = CATALOG["roadmaps"]


def build_tax() -> dict:
    """catalog taxonomy → 页面用精简映射表（kind 归属的唯一定义源，build 内不硬编码）。"""
    tax = {}
    for x in CATALOG.get("skill", {}).get("taxonomy", []):
        d = {"kind": x["kind"]}
        if x.get("type"):
            d["type"] = x["type"]
        if x.get("scope"):
            d["scope"] = x["scope"]
        if x.get("scope_facets"):
            d["sf"] = x["scope_facets"]
        if x.get("work_type"):
            d["wt"] = x["work_type"]
        if x.get("base"):
            d["base"] = True
        tax[x["name"]] = d
    return tax


def compute_kind_views(rows: list) -> dict:
    """从 JD 记录 + catalog taxonomy 聚合三视角总览数据（topic / technique / work）。

    计数前先过 norm_skill 归一化（与 analyze.py / 页面树同口径），否则别名
    计数会散落在 taxonomy 之外、三视角合计对不上 skill-tree*.md。
    """
    sk_n = Counter()
    for r in rows:
        sk_n.update({norm_skill(s) for s in (r.get("skills") or [])})
    total = len(rows)

    kind_of, ttype_of, scope_of, wt_of = {}, {}, {}, {}
    base_of = {}
    for x in CATALOG.get("skill", {}).get("taxonomy", []):
        name = x["name"]
        kind_of[name] = x["kind"]
        base_of[name] = bool(x.get("base"))
        if x["kind"] == "technique":
            ttype_of[name] = x.get("type", "")
            scope_of[name] = x.get("scope", "")
        if x["kind"] == "work":
            wt_of[name] = x.get("work_type", "")

    TYPE_LABEL = {
        "language": "编程/建模语言", "framework": "开发框架与库",
        "platform-tool": "工具、平台与协议", "hardware-interface": "物理硬件与互联接口",
        "data-system": "数据存储与处理系统", "method": "具名方法与范式",
    }
    SCOPE_LABEL = {"ai-infra": "AI Infra", "agent-infra": "Agent Infra", "general": "通用底座"}
    WORK_LABEL = {"action": "岗位动作", "role": "角色", "metric": "指标", "capability": "能力保障"}

    # topic：base 行业默认词置顶单独返回，其余按提及率降序（两段不合并排名）
    all_topic = sorted(
        [{"name": s, "count": sk_n[s], "pct": round(sk_n[s] / total * 100, 1)}
         for s in kind_of if kind_of[s] == "topic" and sk_n.get(s, 0) > 0],
        key=lambda x: -x["count"])
    topic = {
        "base": [x for x in all_topic if base_of.get(x["name"])],
        "items": [x for x in all_topic if not base_of.get(x["name"])],
    }

    # technique：按 type 分组 → scope 分块 → 词列表
    # （Python 3.15 起 defaultdict 不再继承 list，两层聚合须逐层下标取 list）
    tech_by_type = defaultdict(lambda: defaultdict(list))
    for s in kind_of:
        if kind_of[s] == "technique" and sk_n.get(s, 0) > 0:
            tech_by_type[ttype_of.get(s, "?")][scope_of.get(s, "")].append(
                {"name": s, "count": sk_n[s], "scope": scope_of.get(s, "")})
    technique = []
    for tp in ["language", "framework", "platform-tool", "hardware-interface", "data-system", "method"]:
        group = tech_by_type.get(tp)
        if not group:
            continue
        scope_blocks = []
        for sc in ["ai-infra", "agent-infra", "general"]:
            items = sorted(group.get(sc) or [], key=lambda x: -x["count"])
            if items:
                scope_blocks.append({"scope": sc, "label": SCOPE_LABEL.get(sc, sc), "items": items})
        if scope_blocks:
            technique.append({"type": tp, "label": TYPE_LABEL.get(tp, tp), "scope_blocks": scope_blocks})

    # work：按 work_type 分组
    work_groups = []
    for wt, label in [("action", "岗位动作"), ("role", "角色"), ("metric", "指标"), ("capability", "能力保障")]:
        members = sorted(
            [{"name": s, "count": sk_n[s]} for s in kind_of
             if kind_of[s] == "work" and wt_of.get(s) == wt and sk_n.get(s, 0) > 0],
            key=lambda x: -x["count"])
        if members:
            work_groups.append({"work_type": wt, "label": label, "items": members})

    return {
        "total": total,
        "topic": topic,
        "technique": technique,
        "work": work_groups,
    }


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

    # 城市 × 类别矩阵：国内中文 location 按提及计（一条 JD 涉多城分别计入）；
    # 海外城市不进矩阵（在明细表中按原文检索）。
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

    # 明细表精简记录（逐条浏览与联动过滤用；技能全量保留，kind 由页面查 TAX）
    records = [{
        "co": r.get("company") or "—",
        "t": r["title"],
        "c": r["category"],
        "s": norm_sub(r.get("sub_category")),
        "loc": r.get("location") or "",
        "ty": r.get("employment_type") or "",
        "sa": r.get("salary") or "",
        "sk": [norm_skill(x) for x in (r.get("skills") or [])],
        "u": r.get("source_url") or "",
        "p": r.get("source_platform") or "",
    } for r in recs]

    return {
        "total": total, "n_firms": n_firms, "n_skills": n_skills,
        "cat_n": dict(cat_n), "companies": dict(companies.most_common(COMPANY_SHOW)),
        "cat_company": {c: dict(m) for c, m in cat_company.items()},
        "tree": {c: {s: dict(v.most_common(SUB_SKILL_SHOW)) for s, v in subs.items()}
                 for c, subs in tree.items()},
        "sub_jd": {c: dict(subs.most_common()) for c, subs in sub_jd.items()},
        "cat_skills": {c: dict(m.most_common()) for c, m in cat_skills.items()},
        "city_cat": {c: dict(city_cat[c]) for c in cities_sorted},
        "records": records,
    }


# ── 数据键裁剪：两类页面各自只内嵌所需字段（records 是体积大头，skill-map 不带；
#    tree/roadmaps 是技能页专属，jobs 不带）。技能共现只在 md 报告（skill-tree*.md）。──
SKILL_MAP_KEYS = ("total", "n_skills", "cat_n", "tree", "sub_jd", "cat_skills")
JOBS_KEYS = ("total", "n_firms", "cat_n", "companies", "cat_company", "city_cat", "records")


def pick(d: dict, keys) -> dict:
    return {k: d[k] for k in keys if k in d}


# 页脚来源行按数据实时生成，数据更新不脱节
PLAT_NAMES = {"官网": "公司官网/官方 ATS", "HN": "HN「Who is hiring」",
              "猎聘快照": "猎聘快照", "BOSS快照": "BOSS快照", "脉脉快照": "脉脉快照",
              "文章": "公开文章",
              "Ashby": "海外 Ashby（OpenAI 等 7 家）", "Greenhouse": "海外 Greenhouse（Anthropic 等 3 家）"}


def _src_line(recs: list) -> str:
    plat = Counter(r.get("source_platform", "") for r in recs)
    # 公司数按当前子集实算（社招 12 家、校招 11 家，各自如实）
    n_firms = len({(r.get("company") or "").strip() for r in recs} - {""})
    names = dict(PLAT_NAMES)
    names["官网"] = f"{n_firms} 家公司官网/官方 ATS（华为、百度无公开数据）"
    return "、".join(f"{names.get(k, k)} {v} 条" for k, v in plat.most_common() if k)

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
.heatmap .s-row .row-tag{font-weight:400;color:var(--ink-soft);font-size:11px;margin-left:5px;white-space:nowrap}
.heat-legend{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:12.5px;color:var(--ink-soft)}
.heat-legend .sw{width:22px;height:14px;border:1px solid var(--line)}

/* ── kind 徽标（主题黄 / 技术蓝 / 工作红，谱系树与三视角共用色系）── */
.kd{display:inline-block;font-size:10.5px;line-height:1;padding:2px 5px;border-radius:2px;
  vertical-align:1.5px;margin-right:5px;font-weight:600;letter-spacing:.05em}
.kd-topic{background:var(--yellow);color:var(--ink)}
.kd-technique{background:var(--blue);color:#fff}
.kd-work{background:var(--red);color:#fff}

/* ── 谱系树 kind/scope 过滤条 ── */
.tree-filter{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:18px 0 4px;font-size:13px}
.tree-filter .tf-label{color:var(--ink-soft);margin-right:2px}
.tf-btn{padding:3px 12px;border:1.5px solid var(--ink);background:transparent;cursor:pointer;
  font-size:12.5px;color:var(--ink);font-family:inherit}
.tf-btn.on{background:var(--ink);color:var(--paper)}
.tf-btn:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.tf-sub{display:none;align-items:center;gap:6px}
.tf-sub.show{display:flex}
.skill-row.hidden{display:none}

/* ── 三视角总览 ── */
.kv-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.kv-tab{padding:5px 14px;border:1.5px solid var(--ink);cursor:pointer;font-size:13px;background:transparent;color:var(--ink);font-family:inherit}
.kv-tab.on{background:var(--ink);color:var(--paper)}
.kv-tab:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.kv-view{margin-top:12px}
.kv-h{font-size:14px;font-weight:700;margin-bottom:8px;color:var(--ink)}
.kv-base{border:1.5px solid var(--ink);background:rgba(247,209,84,.16);padding:10px 14px;
  margin-bottom:12px;font-size:13.5px}
.kv-base b{font-size:15px}
.kv-base .n{color:var(--blue);font-weight:600;font-variant-numeric:tabular-nums}
.kv-base .note{color:var(--ink-soft);font-size:12.5px;margin-left:8px}
.kv-row{display:grid;grid-template-columns:160px 1fr 64px;gap:8px;align-items:center;padding:3px 0}
.kv-name{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kv-bar{height:14px;background:var(--bar);position:relative}
.kv-bar .kv-fill{position:absolute;inset:0 auto 0 0;background:var(--blue);transition:width .5s cubic-bezier(.6,0,.2,1)}
.kv-num{text-align:right;color:var(--blue);font-variant-numeric:tabular-nums;font-weight:600}
.kv-block{margin-top:14px;padding:12px;border:1.5px solid var(--line);background:rgba(43,43,43,.02)}
.kv-block-h{font-size:13px;font-weight:700;margin-bottom:6px;color:var(--ink)}
.kv-scope-row{display:flex;gap:10px;align-items:baseline;margin:5px 0;flex-wrap:wrap}
.kv-scope-label{flex:none;width:78px;font-size:12px;color:var(--ink-soft);font-weight:600}
.kv-scope-row .kv-chips{flex:1;min-width:0}
.kv-chips{display:flex;flex-wrap:wrap;gap:4px}
.kv-chip{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border:1px solid var(--line);
  border-radius:3px;font-size:12.5px;background:var(--paper)}
.kv-chip b{font-weight:600;color:var(--ink)}
.kv-chip .kv-chip-n{color:var(--blue);font-variant-numeric:tabular-nums;font-size:11.5px}

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
/* 技能 chip 的 kind 色点（与技能地图徽标同色系） */
.sk-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:0}
.sk-dot.k-topic{background:#E7B93A}
.sk-dot.k-technique{background:var(--blue)}
.sk-dot.k-work{background:var(--red)}
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
  <div class="sec-head"><span class="sec-title">〇、三视角总览</span>
    <span class="sec-note">主题覆盖率 / 技术栈 / 工作内容分布——三视角各自成榜，不互相比较</span></div>
  <div id="kind-views"></div>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">一、技能谱系树</span>
    <span class="sec-note">点线名展开；叶长 = JD 条数；徽标 = 主题 / 技术 / 工作，支持按性质与应用域过滤</span></div>
  <div class="tree" id="tree"></div>
  <p class="hint">技能名做过归一化（Kubernetes/K8s 合并、LLM 与大模型合并等）；徽标标注技能性质：主题（黄）/ 技术（蓝）/ 工作（红）。每方向展示前 18 个技能，全量清单与计数基准见本地分析报告 skill-tree.md 及分渠道 skill-tree-society.md / skill-tree-campus.md（analysis/ 目录，本页计数为当前渠道口径）。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">二、按岗位的学习路线</span>
    <span class="sec-note">块色 = 技能家族（见下方图例）；块上数字 = 要求该技能的 JD 条数</span></div>
  <div class="path-tabs" id="path-tabs"></div>
  <div id="path-view"></div>
  <p class="hint">路线的先后顺序是编辑判断：以技能间的依赖关系为主（底层语言先于框架，框架先于调优）、JD 频次为参考，个别低频技能按岗位常识排序，JD 原文本身没有顺序。技能共现分析见本地分析报告 skill-tree.md（analysis/ 目录）。计数口径：方向 JD 提及的技能按方向计，其余按整条线计。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">三、技术栈 × 岗位类别</span>
    <span class="sec-note">格色深浅 = 要求该技术栈词的 JD 条数；仅统计 technique 词</span></div>
  <div id="skill-heat"></div>
  <p class="hint">技术栈词取本渠道要求频次 Top 25（主题词与工作内容词不进本表，见三视角总览），行名旁小字为学习单元类型与应用域，横轴按类别展开（一条 JD 多技能分别计入）。同一技术栈词在不同类别中的位次差异，就是岗位对它要求程度的直接对比。</p>
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

/* ── 〇、三视角总览（topic / technique / work 三榜不互相比较）── */
const KV = __KIND_VIEWS__;
const TAX = __TAX__;
const TYPE_CN = {language: '语言', framework: '框架', 'platform-tool': '工具', 'hardware-interface': '硬件', 'data-system': '数据', 'method': '方法'};
const SCOPE_CN = {'ai-infra': 'AI Infra', 'agent-infra': 'Agent Infra', 'general': '通用底座'};
const WORK_CN = {action: '岗位动作', role: '角色', metric: '指标', capability: '能力保障'};
(function renderKindViews() {
  const root = document.getElementById('kind-views');
  if (!root || !KV) return;
  const KIND_LABEL = {topic: '主题覆盖率', technique: '技术栈', work: '工作内容分布'};
  const KIND_DESC = {
    topic: 'JD 中提及该主题的占比（分母 = 全部 JD）。行业默认词置顶单列，不参与下方排名',
    technique: '按学习单元类型分组，组内按应用域分块，块内按提及 JD 数排名，组间不比较',
    work: '按岗位动作 / 角色 / 指标 / 能力保障分组，组内按提及 JD 数排名，组间不比较',
  };
  const tabs = ['topic', 'technique', 'work'];
  const bar = document.createElement('div'); bar.className = 'kv-tabs';
  const view = document.createElement('div'); view.className = 'kv-view';
  let active = 'topic';
  const btns = {};
  tabs.forEach(t => {
    const b = document.createElement('button');
    b.className = 'kv-tab'; b.textContent = KIND_LABEL[t];
    b.setAttribute('role', 'tab');
    b.onclick = () => {
      active = t;
      tabs.forEach(x => btns[x].classList.toggle('on', x === t));
      render();
    };
    btns[t] = b; bar.appendChild(b);
  });
  btns.topic.classList.add('on');
  root.appendChild(bar); root.appendChild(view);
  const maxOf = arr => Math.max(1, ...arr.map(x => x.count));
  const barRow = (x, mx) =>
    `<div class="kv-row"><span class="kv-name">${x.name}</span>` +
    `<span class="kv-bar"><span class="kv-fill" style="width:${(x.count / mx * 100).toFixed(1)}%"></span></span>` +
    `<span class="kv-num">${x.count}</span></div>`;
  function render() {
    view.innerHTML = '';
    const h = document.createElement('div'); h.className = 'kv-h';
    h.textContent = KIND_DESC[active] || '';
    view.appendChild(h);
    if (active === 'topic') {
      (KV.topic.base || []).forEach(x => {
        const card = document.createElement('div'); card.className = 'kv-base';
        card.innerHTML = `行业默认词：<b>${x.name}</b> <span class="n num">${x.count}</span>` +
          `<span class="note">覆盖率 ${x.pct}%——绝大多数 JD 默认提及，只说明「这是 AI 行业」，不参与下方排名</span>`;
        view.appendChild(card);
      });
      const mx = maxOf(KV.topic.items);
      KV.topic.items.forEach(x => { view.insertAdjacentHTML('beforeend', barRow(x, mx)); });
    } else if (active === 'technique') {
      KV.technique.forEach(g => {
        const blk = document.createElement('div'); blk.className = 'kv-block';
        blk.innerHTML = `<div class="kv-block-h">${g.label}</div>`;
        g.scope_blocks.forEach(sb => {
          const chips = sb.items.map(it =>
            `<span class="kv-chip"><b>${it.name}</b><span class="kv-chip-n">${it.count}</span></span>`).join('');
          blk.insertAdjacentHTML('beforeend',
            `<div class="kv-scope-row"><span class="kv-scope-label">${sb.label}</span><span class="kv-chips">${chips}</span></div>`);
        });
        view.appendChild(blk);
      });
    } else {
      KV.work.forEach(g => {
        const blk = document.createElement('div'); blk.className = 'kv-block';
        blk.innerHTML = `<div class="kv-block-h">${g.label}</div>`;
        const mx = maxOf(g.items);
        g.items.forEach(x => { blk.insertAdjacentHTML('beforeend', barRow(x, mx)); });
        view.appendChild(blk);
      });
    }
  }
  render();
})();

/* ── 一、技能谱系树（kind 徽标 + 性质/应用域过滤；子树保留全部词，作索引）── */
const tree = document.getElementById('tree');
const KIND_META = {
  topic:     {label: '主题', cls: 'kd-topic'},
  technique: {label: '技术', cls: 'kd-technique'},
  work:      {label: '工作', cls: 'kd-work'},
};
const kindOf = s => (TAX[s] || {}).kind || '';
const scopeOf = s => (TAX[s] || {}).scope || '';

// 过滤条：性质（kind）× 应用域（scope，仅在技术栈时生效）
let fKind = '', fScope = '';
const tfBar = document.createElement('div'); tfBar.className = 'tree-filter';
tfBar.innerHTML = '<span class="tf-label">按性质过滤：</span>';
[['', '全部'], ['topic', '主题'], ['technique', '技术栈'], ['work', '工作内容']].forEach(([k, label]) => {
  const b = document.createElement('button'); b.type = 'button';
  b.className = 'tf-btn' + (k === '' ? ' on' : ''); b.textContent = label;
  b.onclick = () => {
    fKind = k;
    if (fKind !== 'technique') fScope = '';
    tfBar.querySelectorAll(':scope > .tf-btn').forEach(x => x.classList.toggle('on', x.textContent === label));
    subBar.classList.toggle('show', fKind === 'technique');
    if (fKind !== 'technique') subBar.querySelectorAll('.tf-btn').forEach((x, i) => x.classList.toggle('on', i === 0));
    applyFilter();
  };
  tfBar.appendChild(b);
});
const subBar = document.createElement('div'); subBar.className = 'tf-sub';
subBar.innerHTML = '<span class="tf-label">应用域：</span>';
[['', '全部'], ['ai-infra', 'AI Infra'], ['agent-infra', 'Agent Infra'], ['general', '通用底座']].forEach(([k, label]) => {
  const b = document.createElement('button'); b.type = 'button';
  b.className = 'tf-btn' + (k === '' ? ' on' : ''); b.textContent = label;
  b.onclick = () => {
    fScope = k;
    subBar.querySelectorAll('.tf-btn').forEach(x => x.classList.toggle('on', x.textContent === label));
    applyFilter();
  };
  subBar.appendChild(b);
});
tfBar.appendChild(subBar);
tree.parentNode.insertBefore(tfBar, tree);

function applyFilter() {
  document.querySelectorAll('#tree .dir').forEach(dir => {
    let vis = 0, tot = 0;
    dir.querySelectorAll('.skill-row').forEach(row => {
      tot++;
      const ok = (!fKind || row.dataset.kind === fKind) &&
                 (!fScope || fKind !== 'technique' || row.dataset.scope === fScope);
      row.classList.toggle('hidden', !ok);
      if (ok) vis++;
    });
    const cnt = dir.querySelector('.dir-h .cnt');
    if (cnt && cnt.dataset.base) cnt.textContent = cnt.dataset.base + (vis < tot ? ` · 匹配 ${vis}/${tot}` : '');
  });
}

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
        <span class="cnt num" data-base="${nSub} 条">${nSub} 条</span></div>
      <div class="skills">${Object.entries(skills).map(([s,n]) => {
        const k = kindOf(s), km = KIND_META[k];
        const badge = km ? `<span class="kd ${km.cls}">${km.label}</span>` : '';
        return `<div class="skill-row" data-kind="${k}" data-scope="${scopeOf(s)}">
         <span class="nm">${badge}${s}</span>
         <span class="track"><span class="fill" data-w="${(n/mx*100).toFixed(1)}" style="width:0"></span></span>
         <span class="v num">${n}</span></div>`;
      }).join('')}</div>`;
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
/* ── 三、技术栈 × 岗位类别热力矩阵（仅 technique 词）── */
(function () {
  const box = document.getElementById('skill-heat');
  const cats = CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]);
  const skCats = D.cat_skills || {};
  // 只取 technique 词，按全类别合计提及数取 Top N（主题词与工作内容词不进本表）
  const merged = {};
  Object.values(skCats).forEach(m => Object.entries(m).forEach(([s, n]) => merged[s] = (merged[s] || 0) + n));
  const skills = Object.entries(merged)
    .filter(([s]) => kindOf(s) === 'technique')
    .sort((a, b) => b[1] - a[1]).slice(0, __HEAT_TOP__).map(x => x[0]);
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
    const tx = TAX[s] || {};
    const rowHead = mk('s-row', '');
    rowHead.innerHTML = `${s}<span class="row-tag">${TYPE_CN[tx.type] || ''} · ${SCOPE_CN[tx.scope] || ''}</span>`;
    grid.appendChild(rowHead);
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
    <span class="sec-note">全部记录逐条可查；技能色点 = 主题（黄）/ 技术（蓝）/ 工作（红），悬停看完整归属；从上面任意一幕点击元素会联动过滤到此表</span></div>
  <div class="jd-filters" id="jd-filters">
    <label>类别 <select id="f-cat"><option value="">全部</option></select></label>
    <label>城市 <select id="f-city"><option value="">全部</option></select></label>
    <label>类型 <select id="f-ty"><option value="">全部</option></select></label>
    <label>性质 <select id="f-kind"><option value="">全部</option><option value="topic">主题</option><option value="technique">技术栈</option><option value="work">工作内容</option></select></label>
    <label>应用域 <select id="f-scope" disabled><option value="">全部</option><option value="ai-infra">AI Infra</option><option value="agent-infra">Agent Infra</option><option value="general">通用底座</option></select></label>
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
const TAX = __TAX__;
const TYPE_CN = {language: '语言', framework: '框架', 'platform-tool': '工具', 'hardware-interface': '硬件', 'data-system': '数据', 'method': '方法'};
const SCOPE_CN = {'ai-infra': 'AI Infra', 'agent-infra': 'Agent Infra', 'general': '通用底座'};
const WORK_CN = {action: '岗位动作', role: '角色', metric: '指标', capability: '能力保障'};

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

/* ── 三、JD 明细表（性质 / 应用域筛选；技能检索仅作查询，不做跨 kind 排名）── */
(function () {
  const REC = D.records || [];
  const $ = id => document.getElementById(id);
  const fCat = $('f-cat'), fCity = $('f-city'), fTy = $('f-ty'),
        fKind = $('f-kind'), fScope = $('f-scope'),
        fSkill = $('f-skill'), fCo = $('f-co'), fReset = $('f-reset');
  const state = { cat: '', city: '', ty: '', kind: '', scope: '', skill: '', co: '' };

  // 技能 chip：色点标注性质 + tooltip 完整归属（kind/type/scope 或 work_type）
  function chipHTML(s) {
    const x = TAX[s] || {};
    const kc = x.kind === 'topic' ? 'k-topic' : x.kind === 'work' ? 'k-work' : 'k-technique';
    const tip = x.kind === 'technique'
      ? `技术栈 · ${TYPE_CN[x.type] || x.type || ''} · ${SCOPE_CN[x.scope] || x.scope || ''}`
      : x.kind === 'work' ? `工作内容 · ${WORK_CN[x.wt] || x.wt || ''}`
      : (x.base ? '主题 · 行业默认词' : '主题');
    return `<span title="${tip}"><span class="sk-dot ${kc}"></span>${s}</span>`;
  }

  // 下拉选项
  CAT_DISPLAY_ORDER.filter(c => D.cat_n[c]).forEach(c => fCat.appendChild(new Option(c, c)));
  const cnRe = /[一-鿿]/;
  const citySet = new Set();
  REC.forEach(r => (r.loc || '').replace(/ /g, '').split(/[/,，、]/).forEach(x => { if (x && cnRe.test(x)) citySet.add(x); }));
  [...citySet].sort().forEach(c => fCity.appendChild(new Option(c, c)));
  [...new Set(REC.map(r => r.ty).filter(Boolean))].sort().forEach(t => fTy.appendChild(new Option(t, t)));

  function syncControls() {
    fCat.value = state.cat; fCity.value = state.city; fTy.value = state.ty;
    fKind.value = state.kind; fScope.value = state.scope;
    fSkill.value = state.skill; fCo.value = state.co;
    // 应用域只对技术栈（technique）有意义：未选技术栈时禁用并清空
    const scopeOn = !state.kind || state.kind === 'technique';
    fScope.disabled = !scopeOn;
    if (!scopeOn && state.scope) { state.scope = ''; fScope.value = ''; }
  }
  function apply() {
    const q = { skill: state.skill.trim().toLowerCase(), co: state.co.trim().toLowerCase() };
    const rows = REC.filter(r =>
      (!state.cat || r.c === state.cat) &&
      (!state.city || (r.loc || '').replace(/ /g, '').split(/[/,，、]/).includes(state.city)) &&
      (!state.ty || r.ty === state.ty) &&
      (!state.kind || r.sk.some(s => (TAX[s] || {}).kind === state.kind)) &&
      (!state.scope || r.sk.some(s => (TAX[s] || {}).scope === state.scope)) &&
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
        `<td class="sk">${(r.sk || []).map(chipHTML).join('')}</td>`;
      frag.appendChild(tr);
    });
    tb.appendChild(frag);
    $('jd-count').textContent = `筛选后 ${rows.length} 条 / 全部 ${REC.length} 条（性质/应用域按「JD 技能集合中至少含一个匹配词」过滤）`;
  }
  [fCat, fCity, fTy, fKind, fScope].forEach(s => s.addEventListener('change', () => { state[s.id.slice(2).toLowerCase()] = s.value; syncControls(); apply(); }));
  fSkill.addEventListener('input', () => { state.skill = fSkill.value; apply(); });
  fCo.addEventListener('input', () => { state.co = fCo.value; apply(); });
  fReset.addEventListener('click', () => { Object.assign(state, { cat: '', city: '', ty: '', kind: '', scope: '', skill: '', co: '' }); syncControls(); apply(); });
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

TAX_JSON = json.dumps(build_tax(), ensure_ascii=False)


def build_skill_map(d: dict, recs: list, ch_name: str) -> str:
    data_json = json.dumps(pick(d, SKILL_MAP_KEYS), ensure_ascii=False)
    roadmaps_json = json.dumps(ROADMAPS, ensure_ascii=False)
    family_json = json.dumps(
        {k: {"label": v.get("label", k), "skills": sorted(v["skills"])} for k, v in FAMILY_DEF.items()},
        ensure_ascii=False)
    order_json = json.dumps(CAT_ORDER, ensure_ascii=False)
    kind_views_json = json.dumps(compute_kind_views(recs), ensure_ascii=False)
    # 家族色板：由 catalog 的 skill_family.items[*].color 生成（节点块与图例色样共用一条规则）
    fam_css = "\n".join(
        f".node.f-{k},.fam-legend .sw.{k}{{background:{v['color']}}}"
        for k, v in FAMILY_DEF.items())
    return (SKILL_MAP_TEMPLATE
            .replace("__FAM_CSS__", fam_css)
            .replace("__ROADMAPS__", roadmaps_json)
            .replace("__FAMILIES__", family_json)
            .replace("__CAT_ORDER__", order_json)
            .replace("__KIND_VIEWS__", kind_views_json)
            .replace("__HEAT_TOP__", str(HEAT_TOP))
            .replace("__TAX__", TAX_JSON)
            .replace("__DATA__", data_json)
            .replace("__SRCLINE__", _src_line(recs))
            .replace("__CH_NAME__", ch_name))


def build_jobs(d: dict, recs: list, ch_name: str) -> str:
    data_json = json.dumps(pick(d, JOBS_KEYS), ensure_ascii=False)
    order_json = json.dumps(CAT_ORDER, ensure_ascii=False)
    return (JOBS_TEMPLATE
            .replace("__CAT_ORDER__", order_json)
            .replace("__TAX__", TAX_JSON)
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
