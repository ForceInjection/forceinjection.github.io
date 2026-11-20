#!/usr/bin/env python3
"""P2 验收：四页 Playwright 控制台检查 + 三视角计数与 analysis/skill-tree*.md 核对。

用法：python3 scripts/verify_pages.py
需要 playwright（含 sync_api）可用；四页分别为
skill-map-{society,campus}.html / jobs-{society,campus}.html。

检查项：
1. 页面加载无 console error / pageerror；
2. 关键区块渲染（KPI、三视角、谱系树、热力、明细表行数）；
3. skill-map 三视角计数与对应渠道的 skill-tree md 完全一致；
4. 单文件检查：无 <script src>/<link rel=stylesheet> 外部引用。
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAGES = [
    ("skill-map-society.html", "skill-tree-society.md"),
    ("skill-map-campus.html", "skill-tree-campus.md"),
    ("jobs-society.html", None),
    ("jobs-campus.html", None),
]

def parse_skill_tree_md(path: Path):
    """从 skill-tree md 解析三视角期望计数：{topic: {name: count}, technique: {...}, work: {...}}"""
    text = path.read_text(encoding="utf-8")
    out = {"topic": {}, "technique": {}, "work": {}}
    # 行业默认词（base）
    m = re.search(r"行业默认词：\*\*(.+?)\*\*\((\d+)", text)
    base = {}
    if m:
        base[m.group(1)] = int(m.group(2))
    # 主题覆盖率表
    sec = re.search(r"## 主题覆盖率（提及率）\n(.*?)\n## ", text, re.S)
    if sec:
        for name, n in re.findall(r"^\| ([^|]+?) \| (\d+) \| \d+% \|$", sec.group(1), re.M):
            out["topic"][name.strip()] = int(n)
    out["topic"].update(base)
    # 技术栈：### type 组 → **scope**：**name**(n)、…
    sec = re.search(r"## 技术栈（technique）\n(.*?)\n## ", text, re.S)
    if sec:
        for block in re.findall(r"### (.+?)\n(.*?)(?=\n### |\n$)", sec.group(1), re.S):
            for line in re.findall(r"^\*\*(?:AI Infra|Agent Infra|通用底座)\*\*：(.+)$", block[1], re.M):
                for name, n in re.findall(r"\*\*(.+?)\*\*\((\d+)\)", line):
                    out["technique"][name] = int(n)
    # 工作内容：### 组 → **name**(n)、…（整块直接抓全部加粗计数，无 scope 前缀行）
    sec = re.search(r"## 工作内容分布（work）\n(.*?)(?=\n## |\Z)", text, re.S)
    if sec:
        for name, n in re.findall(r"\*\*(.+?)\*\*\((\d+)\)", sec.group(1)):
            out["work"][name] = int(n)
    return out


def kv_from_html(html: str) -> dict:
    m = re.search(r"^const KV = (\{.*\});$", html, re.M)
    if not m:
        raise SystemExit("HTML 中未找到 const KV 数据行")
    return json.loads(m.group(1))


def kv_to_flat(kv: dict) -> dict:
    """KV JSON → {topic/technique/work: {name: count}}（topic 含 base）"""
    flat = {"topic": {}, "technique": {}, "work": {}}
    for x in kv["topic"].get("base", []) + kv["topic"].get("items", []):
        flat["topic"][x["name"]] = x["count"]
    for g in kv["technique"]:
        for sb in g["scope_blocks"]:
            for it in sb["items"]:
                flat["technique"][it["name"]] = it["count"]
    for g in kv["work"]:
        for it in g["items"]:
            flat["work"][it["name"]] = it["count"]
    return flat


def main():
    # ── 静态检查 ──
    for page, _ in PAGES:
        html = (BASE / page).read_text(encoding="utf-8")
        for pat, why in [(r"<script\s+src=", "外部 script"), (r'<link[^>]+stylesheet', "外部 CSS"),
                         (r"https?://cdn", "CDN 引用")]:
            if re.search(pat, html):
                print(f"[FAIL] {page}: 含{why}")
                sys.exit(1)
    print("[OK] 四页均为单文件（无外部 script/CSS/CDN 引用）")

    # ── 计数核对（skill-map 页 KV vs skill-tree md）──
    for page, md_name in PAGES:
        if not md_name:
            continue
        kv = kv_to_flat(kv_from_html((BASE / page).read_text(encoding="utf-8")))
        expect = parse_skill_tree_md(BASE / "analysis" / md_name)
        for kind in ("topic", "technique", "work"):
            got, want = kv[kind], expect[kind]
            if got != want:
                only_page = {k: v for k, v in got.items() if want.get(k) != v}
                only_md = {k: v for k, v in want.items() if got.get(k) != v}
                print(f"[FAIL] {page} {kind} 视角不一致：页面多出/不符 {only_page}；md 多出/不符 {only_md}")
                sys.exit(1)
        print(f"[OK] {page} 三视角计数与 analysis/{md_name} 完全一致"
              f"（topic {len(kv['topic'])} / technique {len(kv['technique'])} / work {len(kv['work'])} 词）")

    # ── Playwright 动态检查（缺依赖时跳过，不视为失败）──
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("[SKIP] 未安装 playwright，跳过动态验收（单文件检查与三视角计数核对已通过）")
        print("       安装后重跑可补动态验收：pip install playwright && playwright install chromium")
        return
    errors = []
    with sync_playwright() as p:
        # 自带 chromium 二进制缺失时回退到本机 Chrome（channel="chrome"）
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="chrome")
        pg = browser.new_page()
        pg.on("console", lambda m: errors.append((pg.url, "console", m.text)) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append((pg.url, "pageerror", str(e))))
        for page, _ in PAGES:
            url = (BASE / page).as_uri()
            pg.goto(url, wait_until="networkidle")
            # 关键区块渲染
            if page.startswith("skill-map"):
                total = pg.locator("#k-total").inner_text()
                n_tab = pg.locator(".kv-tab").count()
                n_rows = pg.locator("#tree .skill-row").count()
                n_heat = pg.locator("#skill-heat .s-cell").count()
                print(f"[OK] {page}：total={total} 三视角tab={n_tab} 树叶={n_rows} 热力格={n_heat}")
                assert n_tab == 3 and n_rows > 100 and n_heat > 100, f"{page} 区块渲染不全"
                # 过滤条存在且点击「技术栈」不报错、叶被隐藏一部分
                pg.locator(".tf-btn", has_text="技术栈").first.click()
                hidden = pg.locator("#tree .skill-row.hidden").count()
                print(f"     过滤[技术栈]：隐藏 {hidden} 叶；再点应用域[AI Infra]")
                pg.locator(".tf-sub .tf-btn", has_text="AI Infra").first.click()
                hidden2 = pg.locator("#tree .skill-row.hidden").count()
                assert hidden2 >= hidden, "scope 过滤后可见叶反而变多"
                pg.locator(".tf-btn", has_text="全部").first.click()
            else:
                total = pg.locator("#k-total").inner_text()
                n_rows = pg.locator("#jd-table tbody tr").count()
                n_city = pg.locator("#heatmap .h-row").count()
                dots = pg.locator("#jd-table .sk-dot").count()
                opts_kind = pg.locator("#f-kind option").count()
                print(f"[OK] {page}：total={total} 明细行={n_rows} 城市行={n_city} 色点={dots} 性质选项={opts_kind}")
                assert n_rows > 500 and dots > 0 and opts_kind == 4, f"{page} 明细表渲染不全"
                # 性质=技术栈筛选 → 行数变少且 scope 下拉启用
                pg.select_option("#f-kind", "technique")
                filtered = int(re.search(r"\d+", pg.locator("#jd-count").inner_text()).group())
                pg.select_option("#f-kind", "")
                pg.select_option("#f-kind", "topic")
                disabled = pg.locator("#f-scope").is_disabled()
                pg.click("#f-reset")
                print(f"     筛选[技术栈]→{filtered} 条；[主题]时应用域禁用={disabled}")
                assert filtered < n_rows and disabled, f"{page} 性质筛选逻辑异常"
        browser.close()
    if errors:
        print(f"[FAIL] 控制台/页面错误 {len(errors)} 条：")
        for u, t, m in errors[:10]:
            print(f"  {t}: {m}  ({u})")
        sys.exit(1)
    print("[OK] 四页 Playwright 加载无 console error / pageerror")


if __name__ == "__main__":
    main()
