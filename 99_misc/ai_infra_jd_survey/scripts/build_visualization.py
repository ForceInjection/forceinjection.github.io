#!/usr/bin/env python3
"""生成 JD 数据集可视化单文件 HTML（分类 + 技能树 + 共现矩阵）。

用法：python3 scripts/build_visualization.py [data/jd_2026-11-18.jsonl]
输出：visualization.html（零外部依赖，离线可打开；数据更新后重跑即刷新）
技能归一化复用 analyze.py 的映射表。
"""
import json, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import norm_skill, CAT_ORDER  # noqa: E402

BASE = Path(__file__).resolve().parent.parent

TOP_SKILL_BAR_MAX = 30      # 全局条形数量
SUB_SKILL_SHOW = 18         # 每方向展示技能叶数
COOC_TOP = 12               # 共现矩阵维度（保留在 md 报告中）
COMPANY_SHOW = 12           # 公司表行数

# 学习路线：顺序是编辑判断（依据 JD 频次与技能依赖关系），jd 计数渲染时从数据实时查询。
# lane.sub 指定计数来源方向树（默认查线级）。
# 技能家族（用于学习路线着色）：lang=语言 eng=引擎与框架 infra=平台与设施 ai=AI 专项；未列出的为实践方法（墨色）
SKILL_FAMILY = {
    "lang": {"Python", "C++", "Go", "Java", "TypeScript", "Rust", "Shell", "CUDA"},
    "eng": {"vLLM", "SGLang", "Triton", "TensorRT", "TensorRT-LLM", "PyTorch", "Megatron", "DeepSpeed",
            "LangChain", "LangGraph", "TensorFlow"},
    "infra": {"Kubernetes", "Docker", "Ray", "Prometheus", "Grafana", "NCCL", "RDMA", "分布式存储",
              "GPU运维", "SLA/SLO"},
    "ai": {"大模型/LLM", "Agent框架", "RAG", "MCP", "Prompt工程", "Evals", "Function Calling",
           "模型量化", "KV Cache"},
}
ROADMAPS = {
    "研发": {
        "base": ["Python", "Linux", "Docker"],
        "lanes": [
            {"name": "推理引擎", "sub": "推理引擎",
             "skills": ["C++", "CUDA", "vLLM", "SGLang", "模型量化", "KV Cache", "Triton"]},
            {"name": "Agent 平台", "sub": "Agent平台",
             "skills": ["TypeScript", "LangChain", "LangGraph", "RAG", "MCP", "Evals"]},
            {"name": "训练框架", "sub": "训练框架",
             "skills": ["PyTorch", "Megatron", "DeepSpeed", "NCCL", "分布式训练"]},
            {"name": "ML 平台 / 调度", "sub": "ML平台",
             "skills": ["Go", "Java", "Kubernetes", "Ray"]},
        ],
    },
    "测试": {
        "base": ["Python", "Java", "Linux"],
        "lanes": [
            {"name": "AI 测试 / 评测", "sub": None,
             "skills": ["运维自动化", "CI/CD", "大模型/LLM", "Agent框架", "RAG", "Prompt工程", "性能优化"]},
        ],
    },
    "SRE": {
        "base": ["Linux", "Shell", "Python"],
        "lanes": [
            {"name": "平台稳定性", "sub": "稳定性",
             "skills": ["Kubernetes", "监控告警", "可观测性", "SLA/SLO", "故障排查", "分布式存储"]},
            {"name": "AI 基础设施专项", "sub": None,
             "skills": ["GPU运维", "NCCL", "vLLM", "SGLang", "KV Cache"]},
        ],
    },
    "运维": {
        "base": ["Linux", "Python"],
        "lanes": [
            {"name": "GPU 与智算中心", "sub": "GPU运维",
             "skills": ["GPU运维", "CUDA", "故障排查", "监控告警", "RDMA", "Grafana", "Prometheus"]},
            {"name": "推理服务运维", "sub": "推理服务运维",
             "skills": ["vLLM", "SGLang", "大模型/LLM", "Kubernetes"]},
        ],
    },
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
    }


def build_html(d: dict, recs: list) -> str:
    data_json = json.dumps(d, ensure_ascii=False)
    roadmaps_json = json.dumps(ROADMAPS, ensure_ascii=False)
    family_json = json.dumps({k: sorted(v) for k, v in SKILL_FAMILY.items()}, ensure_ascii=False)
    # 页脚口径动态生成，数据更新不脱节
    full = sum(1 for r in recs if r.get("completeness") == "full")
    partial = len(recs) - full
    plat = Counter(r.get("source_platform", "") for r in recs)
    plat_names = {"官网": "国内官网招聘接口", "HN": "HN「Who is hiring」", "猎聘快照": "猎聘快照",
                  "BOSS快照": "BOSS快照", "脉脉快照": "脉脉快照", "文章": "公开文章"}
    src_line = "、".join(f"{plat_names.get(k, k)} {v} 条" for k, v in plat.most_common() if k)
    html = (HTML_TEMPLATE
            .replace("__ROADMAPS__", roadmaps_json)
            .replace("__FAMILIES__", family_json)
            .replace("__DATA__", data_json)
            .replace("__FULL__", str(full))
            .replace("__PARTIAL__", str(partial))
            .replace("__SRCLINE__", src_line))
    return html


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Infra 岗位技能版图</title>
<style>
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

/* ── 头部 ── */
header{padding:56px 0 40px}
.brand{margin-bottom:26px}
.brand img{height:46px;display:block}
.brand a{display:inline-block}
.brand a:focus-visible{outline:2px solid var(--blue);outline-offset:4px}
h1{font-family:var(--kai);font-weight:700;font-size:clamp(38px,6vw,58px);letter-spacing:.04em;line-height:1.22}
.sub{margin-top:14px;color:var(--ink-soft);font-size:15px}
.rule{border:none;border-top:3px solid var(--ink);margin:34px 0 0}

/* ── 第一幕：岗位版图（堆叠条）── */
.sec{margin-top:72px}
.sec-head{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
.sec-title{font-family:var(--kai);font-size:30px;font-weight:700;letter-spacing:.03em}
.sec-note{color:var(--ink-soft);font-size:13.5px}
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

/* ── 第二幕头部之间的非对称两栏 ── */
.asym{display:grid;grid-template-columns:220px 1fr;gap:40px;margin-top:44px;align-items:start}
.howto{font-size:13.5px;color:var(--ink-soft);position:sticky;top:24px}
.howto p{margin-bottom:10px}
.howto b{color:var(--ink)}
table.firms{width:100%;border-collapse:collapse;font-size:14px}
table.firms th{font-weight:600;text-align:left;border-bottom:2px solid var(--ink);padding:8px 10px 8px 0}
table.firms td{border-bottom:1px solid var(--line);padding:8px 10px 8px 0;vertical-align:baseline}
table.firms td.n{text-align:right;font-variant-numeric:tabular-nums}
table.firms .mini{color:var(--ink-soft);font-size:12.5px}

/* ── 第三幕：技能树 ── */
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
.hint{margin-top:14px;font-size:13px;color:var(--ink-soft)}

/* ── 学习路线 ── */
.path-tabs{display:flex;gap:8px;margin-top:28px;flex-wrap:wrap}
.path-tab{font-family:var(--kai);font-size:17px;padding:7px 20px;border:2px solid var(--ink);
  background:transparent;cursor:pointer;color:var(--ink)}
.path-tab[aria-selected="true"]{background:var(--ink);color:var(--paper)}
.path-tab:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.stage{margin-top:30px}
.stage-label{font-size:13px;color:var(--ink-soft);margin-bottom:10px}
.stage-label b{color:var(--ink);font-weight:600}
.base-row{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:baseline;gap:8px;border:2px solid var(--ink);background:var(--paper);
  padding:8px 16px;font-size:15px}
.chip .n{color:var(--blue);font-size:13px;font-variant-numeric:tabular-nums}
.lanes{display:grid;gap:18px;margin-top:8px}
@media (min-width:900px){.lanes{grid-template-columns:1fr 1fr}}
.lane{border:1.5px solid var(--line);padding:16px 18px 14px;overflow-x:auto}
.lane-h{font-family:var(--kai);font-weight:700;font-size:17px;margin-bottom:4px}
.lane-sub{font-size:12px;color:var(--ink-soft);margin-bottom:12px}
.flow{display:flex;align-items:stretch;gap:0;flex-wrap:wrap;row-gap:10px}
.step{display:flex;align-items:center}
.node{border:2px solid var(--ink);background:var(--bar);padding:7px 13px;font-size:13.5px;white-space:nowrap;
  display:inline-flex;align-items:baseline;gap:7px}
.node.f-lang{background:#EAF0FA}
.node.f-eng{background:#F9E9A0}
.node.f-infra{background:#F6DEDB}
.node.f-ai{background:#E3EFE3}
.node .n{color:var(--blue);font-size:12px;font-variant-numeric:tabular-nums}
.node:hover{outline:2px solid var(--blue);outline-offset:-1px}
.fam-legend{display:flex;flex-wrap:wrap;gap:8px 22px;margin:16px 0 4px;font-size:13px;color:var(--ink-soft)}
.fam-legend .sw{display:inline-block;width:13px;height:13px;border:1.5px solid var(--ink);vertical-align:-2px;margin-right:7px}
.fam-legend .sw.lang{background:#EAF0FA}
.fam-legend .sw.eng{background:#F9E9A0}
.fam-legend .sw.infra{background:#F6DEDB}
.fam-legend .sw.ai{background:#E3EFE3}
.fam-legend .sw.meth{background:var(--bar)}
.joint{width:26px;flex:none;display:flex;align-items:center;justify-content:center;color:var(--ink-soft);
  font-size:14px}
.dir-minor{padding:10px 4px 10px 34px;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink-soft)}
.mx-corner{background:var(--paper)}
.mx-cell:hover{outline:2px solid var(--blue);outline-offset:-1px}
#tip{position:fixed;z-index:9;background:var(--ink);color:var(--paper);padding:6px 10px;font-size:12.5px;
  pointer-events:none;opacity:0;transition:opacity .15s;max-width:280px}
.cooc-read{font-size:14px}
.cooc-read h3{font-family:var(--kai);font-size:19px;margin-bottom:12px;letter-spacing:.02em}
.cooc-read p{margin-bottom:12px;color:var(--ink-soft)}
.cooc-read p b{color:var(--ink)}
.warn{margin-top:18px;padding:10px 14px;border-left:3px solid var(--red);font-size:13px;color:var(--ink-soft)}
.warn b{color:var(--red);font-weight:600}

/* ── 页脚 ── */
footer{margin-top:88px;border-top:3px solid var(--ink);padding-top:22px;font-size:13px;color:var(--ink-soft)}
footer .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:34px}
footer p{margin:0}
.copyright{margin-top:20px !important;font-size:12.5px}
footer a{color:var(--blue)}
@media (max-width:860px){footer .cols{grid-template-columns:1fr;gap:14px}}

@media (max-width:860px){
  .asym{grid-template-columns:1fr;gap:24px}
  .howto{position:static}
  .cooc-wrap{grid-template-columns:1fr}
  .skill-row{grid-template-columns:130px 1fr 36px}
  .line-h .tops{max-width:100%;margin-left:0;flex-basis:100%}
  header{padding-top:56px}
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="brand"><a href="https://github.com/ForceInjection" title="ForceInjection on GitHub" target="_blank" rel="noopener"><img src="../../img/AI原力注入-logo.png" alt="AI 原力注入"></a></div>
  <h1>AI Infra 岗位技能版图</h1>
  <p class="sub">从 <span class="num" id="k-total"></span> 条在招岗位说明（JD）中提炼的分类与技能谱系。数据全部来自公开发布的招聘页面，逐条留有出处，数字以采集日（2026-11-18）为准。</p>
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
  <div class="sec-head"><span class="sec-title">二、技能谱系树</span>
    <span class="sec-note">点线名展开；叶长 = JD 条数</span></div>
  <div class="tree" id="tree"></div>
  <p class="hint">技能名做过归一化（Kubernetes/K8s 合并、LLM 与大模型合并等）；每方向展示前 18 个技能，完整清单见 <a href="analysis/skill-tree.md">skill-tree.md</a>。</p>
</section>

<section class="sec">
  <div class="sec-head"><span class="sec-title">三、按岗位的学习路线</span>
    <span class="sec-note">块色 = 技能家族（见下方图例）；块上数字 = 要求该技能的 JD 条数</span></div>
  <div class="path-tabs" id="path-tabs"></div>
  <div id="path-view"></div>
  <p class="hint">路线的先后顺序是编辑判断：依据 JD 频次（数字大小）与技能间的依赖关系（底层语言先于框架，框架先于调优），JD 原文本身没有顺序。技能共现分析见 <a href="analysis/skill-tree.md">skill-tree.md</a>。计数口径：方向 JD 提及的技能按方向计，其余按整条线计。</p>
</section>

<footer><div class="cols">
  <p><b>口径。</b>full <span class="num">__FULL__</span> 条（JD 全文）参与技能计数；partial <span class="num">__PARTIAL__</span> 条（聚合平台搜索快照）只填了快照可见字段，未参与词频统计。职责与要求逐条照抄原文，未做概括。</p>
  <p><b>来源。</b>__SRCLINE__。每条记录的 source_url 可追溯到原页。完整方法见 <a href="README.md">README</a>。</p>
  <p><b>时效。</b>数字为采集日（2026-11-18）快照。学习路线的先后顺序是编辑判断，技能计数随数据更新。</p>
</div>
<p class="copyright">© 2026 公众号「AI 原力注入」 · 数据可视化基于 ai_infra_jd_survey 数据集生成 · 转载请保留出处与数据口径</p>
</footer>
</div>

<script>
const D = __DATA__;

/* ── KPI ── */
document.getElementById('k-total').textContent = D.total;

/* ── 堆叠条 ── */
const CATS = ["研发","测试","SRE","运维","算法","其他"].filter(c => D.cat_n[c]);
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

/* ── 技能树 ── */
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

/* ── 学习路线 ── */
const ROADMAPS = __ROADMAPS__;
const FAMILIES = __FAMILIES__;
const famOf = {};
Object.entries(FAMILIES).forEach(([f, names]) => names.forEach(n => famOf[n] = f));
const FAM_LABEL = {lang: '语言', eng: '引擎与框架', infra: '平台与设施', ai: 'AI 专项', meth: '实践方法'};
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
  // 底座层
  const base = document.createElement('div');
  base.className = 'stage';
  base.innerHTML = `<div class="stage-label"><b>第 0 层 · 底座</b>—— ${line}线几乎所有 JD 都要求</div>
    <div class="base-row">${R.base.map(s => nodeHTML(line, null, s)).join('<span class="joint">+</span>')}</div>`;
  view.appendChild(base);
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
</script>
</body>
</html>
"""


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "data" / "jd_2026-11-18.jsonl"
    recs = load(data_path)
    d = aggregate(recs)
    html = build_html(d, recs)
    out = BASE / "visualization.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}（{len(recs)} 条 JD，{len(html)//1024} KB）")


if __name__ == "__main__":
    main()
