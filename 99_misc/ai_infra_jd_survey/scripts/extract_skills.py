#!/usr/bin/env python3
"""技能提取器：从 JD 文本提取技能标签的唯一方法实现（固定脚本，可独立评估）。

方法说明（词表与语境规则全部来自 data/skill_catalog.json，本脚本不含任何硬编码词表）：

1. 词表 = skill.aliases（别名 → 规范名）∪ skill.items（规范名自映射），共百余词；
2. 按词逐一生成匹配模式（见 _key_pattern）：
   - 有语境守卫的别名（skill.alias_context_guards）：加前后环视排除，
     如「量化」排除 轻量化/向量化/可量化（前置）与 量化策略/量化投资（后置）；
   - ASCII 词：非字母数字环视边界。不用 \\b——CJK 字符属 \\w，
     「使用Go」这类紧邻写法会漏；
   - CJK 串：按原文匹配（中文无词边界，不能加边界）；
3. 匹配范围 = 职位名 + 职责全文；re.I 大小写不敏感；模式按长度降序合成一个
   alternation（最长优先，保证「SGLang」不会被「Lang」截走）；
4. 命中去重（小写归一）后，按技能名长度降序排序（等长按名称序，保证幂等），
   全部保留、不设数量上限——每次命中都是文本里真实出现的技能，
   截断会系统性丢弃短名技能（Go/GPU/MoE 等在多技能 JD 里总排最后）。

用法：
  python3 scripts/extract_skills.py "职位名" "职责全文"   # 单条提取
  python3 scripts/extract_skills.py --demo               # 跑边界用例（评估匹配行为）
  python3 scripts/extract_skills.py --eval               # 对当前数据集重放，
                                                         # 与落盘 skills 对比（改 catalog 后
                                                         # 先看影响面，再决定是否重跑 import）

import_ai_companies.py 已调用本模块（技能提取唯一实现）。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE / "data" / "skill_catalog.json"


class SkillExtractor:
    """技能提取器：构建一次，反复使用。"""

    def __init__(self, catalog_path: Path = CATALOG_PATH):
        cat = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        self.guards = cat["skill"].get("alias_context_guards", {})
        # 词表：别名 → 规范名，规范名自映射兜底
        variants = {}
        for alt, std in cat["skill"]["aliases"].items():
            variants[alt.lower()] = std
            variants.setdefault(std.lower(), std)
        for name in cat["skill"]["items"]:
            variants.setdefault(name.lower(), name)
        self.variants = variants
        # 按「词本身长度」降序合成 alternation（最长优先）：
        # 若按 pattern 字符串长度排，带环视的短 ASCII 词（GPU）会排在混合词（GPU池化）之前，
        # 把「实现GPU池化」截成 GPU + 池化，混合词永远匹配不到。
        pairs = sorted(((k, self._key_pattern(k)) for k in variants),
                       key=lambda kv: len(kv[0]), reverse=True)
        self._re = re.compile("|".join(pat for _, pat in pairs), re.I)

    def _key_pattern(self, key: str) -> str:
        """单个词的匹配模式。"""
        guard = self.guards.get(key)
        if guard:
            pat = re.escape(key)
            if guard.get("excluded_words"):
                pat += "(?!" + "|".join(guard["excluded_words"]) + ")"
            if guard.get("preceded_chars"):
                pat = "(?<!" + "|".join(guard["preceded_chars"]) + ")" + pat
            return pat
        if all(ord(c) < 128 for c in key):
            return r"(?<![A-Za-z0-9])" + re.escape(key) + r"(?![A-Za-z0-9])"
        return re.escape(key)

    def extract(self, text: str) -> list:
        """从文本提取技能规范名列表（全部命中，长度降序）。"""
        hits = {self.variants[m.group(0).lower()] for m in self._re.finditer(text)}
        return sorted(hits, key=lambda s: (-len(s), s))

    def extract_jd(self, title: str, desc: str = "") -> list:
        """按 JD 口径提取：职位名 + 职责全文拼接后扫描。"""
        return self.extract(f"{title} {desc}")


# ── CLI ──

DEMO_CASES = [
    ("边界：CJK 紧邻英文", "使用Go与Python开发，熟悉golang优先"),
    ("边界：英文词内不误报", "对compatible和flexible的ib架构有理解，IBM背景优先"),
    ("量化：正常命中", "负责INT8量化和模型量化压缩"),
    ("量化：前置词排除", "做模型轻量化和效果可量化的评估体系"),
    ("量化：后置词排除", "搭建量化策略回测框架，负责量化投资研究"),
    ("量化：混合语境", "模型轻量化落地，含INT8量化部署"),
    ("大小写与别名", "熟悉vllm、SGLang，了解k8s和Langchain"),
]


def run_demo(ex: SkillExtractor) -> None:
    print("── 边界用例 ──")
    for name, text in DEMO_CASES:
        print(f"[{name}]")
        print(f"  文本: {text}")
        print(f"  提取: {ex.extract(text)}")
    print()


def run_eval(ex: SkillExtractor) -> None:
    """重放当前数据集，与落盘 skills 对比——评估改 catalog 后的影响面。"""
    rows = []
    data_dir = BASE / "data"
    for p in sorted(data_dir.glob("jd_*.jsonl")):
        rows.extend(json.loads(l) for l in p.open(encoding="utf-8") if l.strip())

    same = changed = empty_before = empty_after = n_gain = n_lost = 0
    gain_cnt, lost_cnt = Counter(), Counter()
    empty_fixed_samples, empty_new_samples = [], []
    for r in rows:
        old = set(r.get("skills") or [])
        new = set(ex.extract_jd(r["title"], " ".join(r.get("responsibilities") or [])))
        if not old:
            empty_before += 1
        if not new:
            empty_after += 1
        add, rem = new - old, old - new
        if add and not old and len(empty_fixed_samples) < 5:
            empty_fixed_samples.append((r["title"][:40], sorted(add)))
        if rem and not new and len(empty_new_samples) < 5:
            empty_new_samples.append((r["title"][:40], sorted(rem)))
        if add:
            gain_cnt.update(add)
            n_gain += 1
        if rem:
            lost_cnt.update(rem)
            n_lost += 1
        if add or rem:
            changed += 1
        else:
            same += 1

    total = len(rows)
    print(f"── 重放对比（{total} 条，catalog 词表 {len(ex.variants)} 键）──")
    print(f"不变 {same}（{same/total*100:.1f}%） | 有变化 {changed}（{changed/total*100:.1f}%）")
    print(f"空 skills：{empty_before} → {empty_after}")
    print(f"将新增标签的 JD：{n_gain} 条，新增标签计数 Top10：{gain_cnt.most_common(10)}")
    print(f"将丢失标签的 JD：{n_lost} 条，丢失标签计数 Top10：{lost_cnt.most_common(10)}")
    if empty_fixed_samples:
        print("由空转非空样例:")
        for t, add in empty_fixed_samples:
            print(f"   {t} → +{add}")
    if empty_new_samples:
        print("将转为空的样例（原标签全部被规则排除时才发生，应逐条确认）:")
        for t, rem in empty_new_samples:
            print(f"   {t} → -{rem}")


def main(argv: list) -> int:
    ex = SkillExtractor()
    if "--demo" in argv:
        run_demo(ex)
        return 0
    if "--eval" in argv:
        run_eval(ex)
        return 0
    if len(argv) >= 2:
        title, desc = argv[0], " ".join(argv[1:])
        print(ex.extract_jd(title, desc))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
