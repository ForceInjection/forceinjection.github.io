#!/usr/bin/env python3
"""转换 ~/Downloads/AI_Companies_JD/all_companies_ai_jobs.json → data/jd_2026-11-19.jsonl

来源文件是合并好的全量数据（meta/stats/jobs 顶层键，jobs 5447 条、每条带 company），
字段与项目 16 字段 schema 不同，按以下映射转换：

- company/title/url → 同名直取
- category/sub_category：data/skill_catalog.json 的 sub_category.rules 按 title 关键词
  派生（按序首个命中生效；无命中落 sub_category.fallback），category 取 items[sub].categories[0]
- 入库范围过滤（数据范围策略，非分类定义）：仅对 title 明写「算法」且分类落算法类的
  岗位做相关性判定（catalog.admission 规则）——title 含模型词保留；title 含应用信号
  直接剔除（不看正文）；两类信号皆无时看正文是否有训练/推理证据。非算法类岗位
  （如「测试开发工程师-算法评测」）不受此闸门影响
- location：cities（字符串化 list）解析后 `/` 连接
- employment_type：直接取源文件 employment_type 字段（已归一为全职/实习两值）
- responsibilities：description 全文按编号条目拆分为数组；requirements 留空
  （来源无独立的 requirement 字段，职责与要求合并在 description）
- skills：description+title 匹配技能词表（方法唯一实现在 scripts/extract_skills.py，
  词表与语境规则来自 catalog；全部命中保留、不设上限）
- level/salary：来源无可靠字段，留空
- source_platform：官网（12 家均为官网/官方 ATS 渠道）
- captured_at：2026-11-19
- completeness：full

幂等：纯转换，重复运行输出一致。
分类定义唯一来源：data/skill_catalog.json（本脚本不定义任何分类常量）。
"""
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = Path.home() / "Downloads" / "AI_Companies_JD" / "all_companies_ai_jobs.json"
OUT = BASE / "data" / "jd_2026-11-19.jsonl"

CAPTURED = "2026-11-19"

# ── 人工剔除清单：与 AI Infra 无关的岗位（逐条审定的 source_url 级排除，可审计）──
_EXCLUDE_FILE = BASE / "data" / "manual_exclusions.json"
_EXCLUDED_URLS = ({x["source_url"] for x in json.loads(_EXCLUDE_FILE.read_text(encoding="utf-8"))}
                  if _EXCLUDE_FILE.exists() else set())

# ── 分类与词表定义：唯一来源是 data/skill_catalog.json ──
_CATALOG = json.loads((BASE / "data" / "skill_catalog.json").read_text(encoding="utf-8"))
_SUB_ITEMS = _CATALOG["sub_category"]["items"]
_SUB_FALLBACK = _CATALOG["sub_category"]["fallback"]
_SUB_RULES = [(re.compile(r["pattern"], re.I), r["sub"])
              for r in _CATALOG["sub_category"]["rules"]]


def classify(title: str) -> tuple:
    """(sub_category, category)：catalog 规则按序首个命中；无命中落 fallback。"""
    for pat, sub in _SUB_RULES:
        if pat.search(title):
            return sub, _SUB_ITEMS[sub]["categories"][0]
    return _SUB_FALLBACK, _SUB_ITEMS[_SUB_FALLBACK]["categories"][0]


# ── 入库范围过滤：模式与触发条件全部来自 catalog.admission（非分类定义）──
_ADM = _CATALOG["admission"]
ALGO_MODEL_RE = re.compile(_ADM["model_pattern"], re.I)
ALGO_APPLY_RE = re.compile(_ADM["apply_pattern"], re.I)
ALGO_TRAIN_RE = re.compile(_ADM["train_pattern"], re.I)


def admitted(title: str, desc: str = "") -> bool:
    """算法岗相关性判定：title 含模型词保留、纯应用信号直接剔除（不看正文）、
    两类信号皆无看正文训练/推理证据。仅 title 明写「算法」且分类落算法类的岗位进入。"""
    if ALGO_MODEL_RE.search(title):
        return True
    if ALGO_APPLY_RE.search(title):
        return False
    return bool(ALGO_TRAIN_RE.search(f"{title} {desc or ''}"))


# ── 技能提取：唯一实现是 extract_skills.py（词表与语境规则读 catalog）──
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_skills import SkillExtractor  # noqa: E402

_EXTRACTOR = SkillExtractor()


def normalize_city(p: str) -> list:
    """单个城市片段归一：去市后缀、拆「上海市 北京市」空格连写。返回城市列表。"""
    p = re.sub(r"\s+", "", p)
    if not p:
        return []
    # 空格/连写拆分（如「上海市 北京市」去空格后为「上海市北京市」）
    if re.match(r"^([一-鿿]{2,4}?市)+$", p):
        return [c[:-1] for c in re.findall(r"[一-鿿]{2,4}?市", p)]
    if re.match(r"^[一-鿿]{2,7}市$", p):
        p = p[:-1]
    # 「总部」后缀（如「深圳总部」→「深圳」）
    if p.endswith("总部") and len(p) > 2:
        p = p[:-2]
    if p == "新加坡共和国":
        p = "新加坡"
    return [p]


def normalize_location(loc: str) -> str:
    # 分隔符不含空白：城市名内部的字间空格（如「北 京」）由 normalize_city 去除后合并，
    # 「上海市 北京市」去空格后走连写拆分分支
    parts = re.split(r"[/,，、;；]+", loc or "")
    out = []
    for p in parts:
        out.extend(normalize_city(p))
    seen = set()
    return "/".join(x for x in out if not (x in seen or seen.add(x)))


def parse_list_field(v) -> list:
    """cities/ai_tags 等是字符串化的 list： ast 解析；已是 list 则直用；失败返回 []。"""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.startswith("["):
        try:
            return [str(x).strip() for x in ast.literal_eval(v) if str(x).strip()]
        except (ValueError, SyntaxError):
            return []
    if isinstance(v, str) and v.strip() and v != "None":
        return [v.strip()]
    return []


def split_numbered(text: str) -> list:
    """按「1. 2. …」/「1、」编号把职责正文拆成数组；无编号则整段一条。"""
    if not text:
        return []
    parts = re.split(r"\n?\s*\d+[\.、）)]\s*", "\n" + text)
    items = [p.strip(" \r\n；;-—") for p in parts if p.strip(" \r\n；;-—")]
    items = [re.sub(r"\r\n?", " ", p) for p in items]
    return items if len(items) >= 2 else [re.sub(r"\r\n?", " ", text).strip()]


def main():
    src = json.load(SRC.open(encoding="utf-8"))
    jobs = src["jobs"]
    out, seen = [], set()
    stats = Counter()
    for j in jobs:
        if j.get("status") not in (None, "open", "OPEN", "Open"):
            stats["跳过(status 非 open)"] += 1
            continue
        company = (j.get("company") or "").strip()
        title = (j.get("title") or "").strip()
        url = (j.get("url") or "").strip()
        key = (company, title, url)
        if key in seen:
            stats["去重"] += 1
            continue
        seen.add(key)
        if url in _EXCLUDED_URLS:
            stats["人工剔除（见 manual_exclusions.json）"] += 1
            continue
        desc = j.get("description") or ""
        sub_category, category = classify(title)
        if "算法" in title and category == "算法" and not admitted(title, desc):
            stats["剔除·应用算法（非训练/推理）"] += 1
            continue
        cities = normalize_location("/".join(parse_list_field(j.get("cities"))) or "/".join(parse_list_field(j.get("location_text"))))
        site = (j.get("site") or "").strip()
        # employment_type：直接信任源文件标注（全职/实习；来源分 explicit / inferred_title /
        # inferred_default 三档，2026-11-19 用户处理后的口径）
        emp = (j.get("employment_type") or "").strip()
        if emp not in ("全职", "实习"):
            emp = ""
        rec = {
            "company": company,
            "title": title,
            "category": category,
            "sub_category": sub_category,
            "location": cities,  # normalize_location 已返回去重保序的城市串
            "employment_type": emp,
            "recruit_channel": (j.get("recruit_channel") or "").strip(),
            "level": "",
            "salary": "",
            "responsibilities": split_numbered(desc),
            "requirements": [],
            "skills": _EXTRACTOR.extract_jd(title, desc),
            "source_url": url,
            "source_platform": "官网",
            "captured_at": CAPTURED,
            "completeness": "full" if desc else "partial",
        }
        out.append(rec)
        stats[f"公司·{company or '（空）'}"] += 1

    assert all(len(r) == 16 for r in out), "字段数校验失败"
    urls = [r["source_url"] for r in out]
    assert len(urls) == len(set(urls)), "source_url 存在重复"
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print(f"转换 {len(out)} 条 → {OUT}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    cat = Counter(r["category"] for r in out)
    sub = Counter(r["sub_category"] for r in out)
    print("category:", dict(cat.most_common()))
    print("sub Top15:", dict(sub.most_common(15)))


if __name__ == "__main__":
    sys.exit(main())
