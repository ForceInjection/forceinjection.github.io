#!/usr/bin/env python3
"""
Build latest-updates list for the Jekyll site.
Run locally after sync (sync.sh calls this automatically):
    python3 scripts/build_latest_updates.py
Scans the Pages repo's git log for content files touched within the last
N days, extracts title + URL (reusing build_search_index helpers), and
writes latest.json for the homepage section and /updates/ page.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from build_search_index import ROOT, EXCLUDE_DIRS, extract_title, url_for

OUT = ROOT / "latest.json"
DAYS = 30
MAX_ITEMS = 300

# Files git touches but readers shouldn't see in an update list
# (portals, infra pages, generated data)
SKIP_FILES = {
    "README.md", "AGENTS.md", "index.html", "mermaid_editor.html",
    "search.json", "latest.json", "updates/index.html",
}

# Top-level directory → short Chinese label for display
MODULE_LABELS = {
    "01_hardware_architecture": "硬件架构",
    "02_dpu_programming": "DPU 编程",
    "02_gpu_programming": "GPU 编程",
    "02_npu_programming": "NPU 编程",
    "03_ai_cluster_ops": "集群运维",
    "04_cloud_native_ai_platform": "云原生 AI",
    "05_model_training_and_fine_tuning": "训练与微调",
    "06_llm_theory_and_fundamentals": "LLM 理论",
    "07_rag_and_tools": "RAG 与工具",
    "08_agentic_system": "智能体",
    "09_inference_system": "推理系统",
    "10_ai_related_course": "课程",
    "11_ai_native_everything": "AI Native",
    "20_agent_skills": "Agent Skills",
    "21_openspec_practise": "OpenSpec",
    "98_llm_programming": "LLM 编程",
    "99_misc": "杂项",
}


def is_content_file(rel: Path) -> bool:
    """Keep article pages only: md/html outside infra dirs and skip-list."""
    if rel.suffix not in (".md", ".html"):
        return False
    if any(part.startswith(".") or part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if rel.name in SKIP_FILES or "/".join(rel.parts[-2:]) in SKIP_FILES:
        return False
    return True


def collect_git_changes(days: int) -> dict[str, dict]:
    """Walk git log once; return {path: {last_ts, added_in_window}}."""
    since_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    out = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--name-status",
         "--format=%ct", f"--since={days} days ago"],
        capture_output=True, text=True, check=True,
    ).stdout

    entries: dict[str, dict] = {}
    ts = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            ts = int(line)
            continue
        if ts is None or ts < since_ts:
            continue
        parts = line.split("\t")
        status, paths = parts[0], parts[1:]
        if status[0] in ("R", "C"):
            paths = paths[1:]  # keep the new path only
        for path in paths:
            entry = entries.setdefault(path, {"last_ts": 0, "added_in_window": False})
            entry["last_ts"] = max(entry["last_ts"], ts)
            if status == "A":
                entry["added_in_window"] = True
    return entries


def build_latest():
    raw = collect_git_changes(DAYS)

    items = []
    seen_urls = set()
    for path_str, info in sorted(raw.items(), key=lambda kv: -kv[1]["last_ts"]):
        rel = Path(path_str)
        if not is_content_file(rel):
            continue
        abs_path = ROOT / rel
        if not abs_path.exists():
            continue  # deleted since it was touched
        url = url_for(abs_path)
        if not url or url in seen_urls:
            continue
        title = extract_title(abs_path)
        if not title:
            continue
        seen_urls.add(url)

        module_raw = rel.parts[0] if len(rel.parts) > 1 else ""
        items.append({
            "title": title,
            "url": url,
            "date": datetime.fromtimestamp(info["last_ts"], timezone.utc).strftime("%Y-%m-%d"),
            "status": "new" if info["added_in_window"] else "updated",
            "module": MODULE_LABELS.get(module_raw, module_raw),
        })
        if len(items) >= MAX_ITEMS:
            break

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": DAYS,
        "count": len(items),
        "items": items,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    added = sum(1 for it in items if it["status"] == "new")
    print(f"[latest-updates] Wrote {len(items)} entries "
          f"({added} new, {len(items) - added} updated) to {OUT}")


if __name__ == "__main__":
    sys.exit(build_latest())
