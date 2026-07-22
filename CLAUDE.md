# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

AI Fundamentals is a Chinese-language knowledge repository covering the full AI infrastructure stack: GPU architecture, CUDA programming, LLM theory, inference systems, cloud-native AI platforms, agentic systems, RAG, and more. All content is authored in Markdown.

- **License**: Apache 2.0
- **Content** is organized in semantically numbered top-level directories (`01_hardware_architecture/` through `99_misc/`, plus `20_agent_skills/` and `21_openspec_practise/`). Each directory corresponds to a major topic area with its own `README.md` portal.
- **`02_dpu_programming/`、`02_gpu_programming/` 和 `02_npu_programming/`** share the `02_` prefix — all three are sub-modules under "底层计算与异构编程."
- **`AGENTS.md`** exists alongside this file and covers module-level architecture details and content index for GitHub Copilot. This file focuses on project-level conventions that apply to all work in the repo.

## Jekyll / GitHub Pages dev environment

This site is a GitHub Pages site built with Jekyll and the `minima` theme. The `index.html` homepage provides a custom hero + card-grid entry point; all other pages receive Jekyll layouts automatically via `optional_front_matter` in `_config.yml`.

### Ruby version

- **Ruby 3.2.7** (managed via `rbenv`), pinned in `.ruby-version`. Never use the macOS system Ruby (2.6) — it will fail with Bundler version mismatches.
- All Jekyll commands must run through `rbenv exec` to pick up the correct Ruby/Gem context.

### Local server

```bash
rbenv exec bundle exec jekyll serve --port 4000
```

### Common errors

| Error | Cause | Fix |
|---|---|---|
| `Could not find 'bundler' (2.4.19)` | macOS system Ruby 2.6 | Use `rbenv exec bundle exec jekyll serve` |
| `You must use Bundler 4 or greater` | Homebrew's built-in Jekyll (Ruby 4) | Use `rbenv exec bundle exec jekyll serve` |
| `bundler: command not found: jekyll` | Not running inside the bundle context | `rbenv exec bundle install` first, then `rbenv exec bundle exec jekyll serve` |

After editing `_config.yml`, restart the Jekyll server for changes to take effect.

### Site search

The nav bar includes a client-side search box powered by `search.json`. This index is **manually built** (not auto-generated during `jekyll serve`):

```bash
python scripts/build_search_index.py
```

- `search.json` is tracked in git. **After adding or renaming articles, rebuild it before committing.**
- The script scans all `.md` and `.html` files (excluding `_site/`, `.git/`, etc.), extracts titles from front matter or the first `#` heading, and maps them to URLs.
- The search UI is implemented as inline JS in `_includes/header.html`.

## SCSS architecture

All content-page styling lives in `_sass/custom.scss`. The SCSS entry point is `assets/main.scss`, which imports `minima` (the Jekyll theme) then `custom`.

`custom.scss` is organized in sections:
1. **Color tokens** — Dell-inspired navy/blue palette (`$dell-navy`, `$dell-blue`, `$dell-light`, etc.)
2. **Font stacks** — `$font-body` (system font stack) and `$font-code` (JetBrains Mono)
3. **`.site-nav`** — sticky nav bar with dropdown module menu, hamburger toggle, and search box
4. **Body & page chrome** — global `body`, `a`, `.site-footer`
5. **`.post-content` / `.page-content`** — the main Markdown rendering area: headings, code, blockquotes, tables, lists, images, syntax highlighting (Rouge dark theme)
6. **`.post-header`** — article title & meta
7. **`.quote-footer`** — site-wide bottom quote strip

### Font strategy

The body font uses a system font stack rather than loading a web font:

```
'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
```

- **macOS/iOS**: PingFang SC — Latin + CJK glyphs designed as one family
- **Windows**: Microsoft YaHei
- **Linux/Android**: Noto Sans SC

This was chosen because these fonts have professionally-harmonized Latin and Chinese glyphs (unlike pairing a Latin-only font like Inter with an unrelated Chinese fallback). It also avoids downloading large CJK web fonts (~5 MB). Only `JetBrains Mono` is loaded from Google Fonts (for code).

## Liquid rendering and file exclusions

- **`render_with_liquid: false`** is the default for all `.md` files (set via `_config.yml` defaults). This prevents Liquid from parsing content, which would otherwise crash on Python f-strings (`{x}`) and similar syntax in code blocks.
- `index.html` overrides this with `render_with_liquid: true` in its own front matter because it uses Liquid for the homepage layout.
- **`liquid.error_mode: lax`** suppresses errors from stray Liquid syntax in content files.
- Some `.md` files contain syntax that still breaks even with lax mode. These are explicitly excluded in `_config.yml` → `exclude` and won't appear on the published site. When adding a new article that uses Python f-strings (`f"..."`), template variables (`{{ ... }}`), or `{% ... %}` in code blocks, test it with `jekyll serve` first. If Jekyll fails, add the file to the `exclude` list in `_config.yml`.
- `optional_front_matter.enabled: true` allows `.md` files without front matter to still receive a layout and CSS. This means you can write plain `.md` files without YAML front matter blocks.

## Commit conventions

This repo uses **Conventional Commits** with Chinese descriptions:

```
docs(scope): description
chore(scope): description
refactor(scope): description
feat(scope): description
```

Scopes are derived from directory/topic areas. Common scopes seen in the history: `readme`, `dpu`, `gpu`, `npu`, `training`, `llm-theory`, `rag`, `graph_rag`, `agentic`, `agent_infra`, `inference`, `kv_cache`, `vllm`, `reference_design`, `storage`, `gpu_manager`, `k8s`, `course`, `trae`, `multi_agent`, `ai-native`, `smart_customer_service`, `kvbm`, `submodule`. Look at `git log --oneline` for recent examples before committing.

Recent commits use `sync: update from AI-fundermentals` — this is the standard message when syncing content from the upstream source repo.

## File conventions

- All top-level topic directories use zero-padded numeric prefixes (e.g., `01_`, `02_`, `03_`) to maintain ordering.
- Within a topic directory, files may use numeric prefixes for ordering (e.g., `01_concepts.md`, `02_practice.md`).
- Translated content appends a language suffix to the filename (e.g., `file.zh-CN.md`).
- Image assets live in `img/` at the repo root, or alongside the files that reference them within topic subdirectories.
- Interactive HTML visualizations (e.g., inference pipeline demos) are placed alongside the markdown documents they complement, in the same topic subdirectory.
- `README.md` files at directory roots serve as navigation portals and contain link trees to content within that directory. **When adding a new article, you must update the corresponding directory's `README.md` portal** to include a link to the new file — this is the primary navigation mechanism for readers.
- The root `index.html` doesn't need updating for new articles unless you're adding a brand-new top-level module directory.
- `search.json` is a machine-generated search index (built by `scripts/build_search_index.py`). Rebuild it after adding or renaming articles.

## Content creation workflow

When creating a new technical article, follow this sequence:

1. **Plan** — use `tech-outline-planner` to design the article structure with the C-I-S-T (Context → Issue → Solution → Trade-off) framework.
2. **Write** — create the `.md` file in the appropriate topic directory with a numeric prefix and Chinese descriptive filename.
3. **Link** — add the new article to the parent directory's `README.md` link tree.
4. **Review** — use `doc-reviewer` (outline + content + format) to catch structural, accuracy, and formatting issues.
5. **Validate** — use `md-link-checker` to ensure all local and external links are accessible.
6. **Commit** — use `update-submitter` to generate a Conventional Commit message and submit.

## Python demos and notebooks

Some directories contain small Python projects and Jupyter notebooks for demonstration purposes. Each is self-contained and may include its own `.venv/` (gitignored). Notable locations:

- `04_cloud_native_ai_platform/gpu_manager/code/` — GPU scheduler and virtualization examples
- `07_rag_and_tools/synergized_llms_kgs/demo/` — Anti-fraud system demo (LLM + KG)
- `08_agentic_system/memory/langchain/code/` — LangChain memory demos
- `09_inference_system/memory_calc/` — Memory calculation scripts
- Scattered `*.ipynb` notebooks in `05_model_training_and_fine_tuning/`, `07_rag_and_tools/`, `98_llm_programming/`

These are primarily educational references, not a cohesive application. There is no top-level build system, linter, or test runner.

## Markdown links

- Local links between documents use **relative paths**.
- External links must remain accessible; validate with the `md-link-checker` Skill when modifying link-heavy files.
- When restructuring documents or moving files, update all cross-references.

## Writing conventions

- **All content is in Chinese** (Simplified). Code comments, commit descriptions, and directory README portals are also in Chinese.
- Major section headings in long-form articles often use **Chinese numerals** (一、二、三…) rather than Arabic numbers. Follow the existing heading style of the document you are editing.
- Article series that follow a numbered sequence (e.g., `09_inference_system/reference_design/`) use zero-padded numeric prefixes with Chinese descriptive filenames: `01-背景与目标.md`, `02-集群规模分类与特征分析.md`. Maintain this convention when adding new entries to an existing series.
- Interactive HTML visualizations (e.g., inference pipeline demos) placed alongside the markdown documents they complement should include a `.gif` preview in the same directory when possible.
- Math is authored with LaTeX via MathJax 3 (configured in `_config.yml` through kramdown's `math_engine: mathjax`). Use `$$` for block math and `$` for inline.

## Companion media files

Markdown documents are frequently accompanied by:

- **`.pptx` slide decks** — PowerPoint presentations that mirror or expand on the markdown content. Placed in the same directory as the `.md` file. When creating new technical deep-dives, consider whether a companion slide deck would be helpful.
- **`.pdf` references** — Reference papers, whitepapers, or exported slide decks, typically in a `references/` subdirectory.
- **`.gif` previews** — Animated previews of interactive HTML visualizations, placed alongside the `.html` file.
- **`.ipynb` notebooks** — Jupyter notebooks with executable code demonstrations.

## Project-specific skills

This repo has a rich set of Skills available for content authoring and review. Use them when the task matches:

| Skill | When to use |
|---|---|
| `doc-reviewer` | Review markdown docs — supports outline, content, asset, and format review types |
| `md-link-checker` | Validate local and external links in markdown files |
| `md-translator` | Translate markdown files to another language (adds language suffix to filename) |
| `md-summarizer` | Generate structured Chinese summaries of markdown documents |
| `tech-outline-planner` | Plan and structure new technical articles using context-first + process-narrative approach |
| `update-submitter` | Analyze git changes and generate Conventional Commit messages |
| `reference-organizer` | Format and organize reference links into structured citations |

## Multi-IDE support

The repo supports multiple AI-assisted IDEs beyond Claude Code:

- **`.trae/`** — Trae IDE configuration (gitignored, created per-user)
- **`.qoder/`** — Qoder IDE configuration with `agents/` and `skills/` subdirectories (gitignored, created per-user)
- **`.claude/`** — Claude Code settings (gitignored, `settings.local.json` contains per-user permissions)

These directories are all in `.gitignore` — they are local development environments, not repo content.

## CI/CD

This repo has **no GitHub Actions workflows or CI pipelines**. There is no build step, no linting, and no automated testing. Content quality is maintained through manual review (using the `doc-reviewer` skill).
