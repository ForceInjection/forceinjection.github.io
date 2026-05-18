# 原力注入 Agent Skill 合集

本项目收录了由“原力注入博主”使用和维护的优秀认知技能。这些技能旨在通过自动化的工作流和多智能体协作机制，帮助开发者深入理解代码库结构、提取核心业务逻辑并生成结构化的技术文档。

## 目录

- [原力注入 Agent Skill 合集](#原力注入-agent-skill-合集)
  - [目录](#目录)
  - [1. 核心技能介绍](#1-核心技能介绍)
    - [1.1 深度代码阅读](#11-深度代码阅读)
    - [1.2 深度项目架构分析](#12-深度项目架构分析)
    - [1.3 目录整理](#13-目录整理)
    - [1.4 文档评审](#14-文档评审)
    - [1.5 Markdown 总结器](#15-markdown-总结器)
    - [1.6 代码提交助手](#16-代码提交助手)
    - [1.7 `Agent Skill` 审查器](#17-agent-skill-审查器)
    - [1.8 `OpenSpec` 规范驱动开发辅助](#18-openspec-规范驱动开发辅助)
    - [1.9 网页内容下载器](#19-网页内容下载器)
    - [1.10 Markdown 翻译器](#110-markdown-翻译器)
    - [1.11 参考文献整理助手](#111-参考文献整理助手)
    - [1.12 Markdown 链接检查器](#112-markdown-链接检查器)
    - [1.13 Draw.io 架构图设计器](#113-drawio-架构图设计器)
    - [1.14 PPTX 读取器](#114-pptx-读取器)
    - [1.15 知识图谱本体管理](#115-知识图谱本体管理)
    - [1.16 杂志编辑式信息卡设计器](#116-杂志编辑式信息卡设计器)
    - [1.17 技术文章大纲规划器](#117-技术文章大纲规划器)
  - [2. 核心设计理念](#2-核心设计理念)
    - [2.1 语言规范：受众隔离](#21-语言规范受众隔离)
    - [2.2 产物定位：为什么是生成 SKILL 而非 Agent？](#22-产物定位为什么是生成-skill-而非-agent)
  - [3. `Agent Skill` 最佳实践](#3-agent-skill-最佳实践)
    - [3.1 生产级目录结构](#31-生产级目录结构)
    - [3.2 精准的触发描述](#32-精准的触发描述)
    - [3.3 渐进式知识披露](#33-渐进式知识披露)
    - [3.4 状态管理与流程编排](#34-状态管理与流程编排)
    - [3.5 技能测试金字塔](#35-技能测试金字塔)
    - [3.6 技能命名规范](#36-技能命名规范)
  - [4. 深度解析案例](#4-深度解析案例)
    - [4.1 gstack 项目深度解析](#41-gstack-项目深度解析)
    - [4.2 五种智能体技能设计模式](#42-五种智能体技能设计模式)
    - [4.3 superpowers 深度解析](#43-superpowers-深度解析)
  - [5. 推荐参考资源](#5-推荐参考资源)
    - [5.1 MiniMax-AI 官方技能库](#51-minimax-ai-官方技能库)
    - [5.2 CUDA Code Skill 文档与技能](#52-cuda-code-skill-文档与技能)
    - [5.3 vLLM 官方 Agent 技能库](#53-vllm-官方-agent-技能库)
    - [5.4 领域驱动设计 (DDD) 技能库](#54-领域驱动设计-ddd-技能库)
  - [6. `Skill` 单元测试](#6-skill-单元测试)

---

## 1. 核心技能介绍

针对复杂代码阅读、项目逆向工程、规范驱动开发等工程挑战，本项目封装了 17 个独立智能体技能，旨在通过多角色协同解决实际开发瓶颈。

### 1.1 深度代码阅读

[`code-reader`](./skills/code-reader) 技能旨在系统性地阅读和理解陌生的代码库，并通过严格的验证机制生成可复用的认知技能文件。

该技能引入了类似软件工程团队的三重智能体协作模式（技术作者、测试工程师和初级开发者）。通过 `QA` 工程师生成测试题并由初级开发者仅根据文档进行解答的“闭卷考试”式验证循环，有效避免了浅尝辄止的代码总结，确保所提取的模块能力、设计逻辑、数据结构和状态流等信息具有极高的准确性和深度。

使用示例如下：

```bash
# 触发深度代码阅读工作流
# 参数 source: 本地路径或 GitHub 仓库地址
# 参数 output-dir: 技能文件的输出根目录
# 注意：该工作流会在 output-dir 下为每个识别出的模块生成一个独立目录（如 {project-name}-fj-{module-name}），并包含对应的 SKILL.md 等技能文件。
/code-reader <source> <output-dir>
```

### 1.2 深度项目架构分析

[`project-analyzer`](./skills/project-analyzer) 技能在 `code-reader` 的基础上进行了扩展，用于对第三方代码仓库进行全面的**逆向工程与静态分析**，并生成客观、硬核的《项目架构深度分析报告》。

该技能协同了模块专家、运维工程师和首席架构师（作为第三方代码库分析师）三个角色的多智能体协作模式。它不仅关注代码级别的逻辑，还深入解析构建、测试和部署等工程实践。通过首席架构师汇总代码逻辑和基础设施配置，确保最终输出的架构图和文档在逻辑上保持一致且专业严谨。最终生成的文档中，系统架构、核心模块代码深度解析与执行流程分析约占 70% 的篇幅，其余 30% 涵盖项目全局摘要、质量与性能评估（包括测试覆盖）以及二次开发指南。

使用示例如下：

```bash
# 触发深度项目架构分析工作流
# 参数 source: 本地路径或 GitHub 仓库地址
# 参数 output-dir: 深度分析报告及中间分析文件的输出目录
# 注意：该工作流会在 output-dir 下生成以下内容：
# 1. 最终输出文件：<actual-project-name>-deep-dive.md（包含 7 个标准章节的综合性深度分析报告）
# 2. 中间分析文件（基础设施）：由 DevOps 工程师提取生成的构建、测试和部署策略报告
# 3. 中间分析文件（代码模块）：底层调用的 code-reader 生成的各个模块独立目录（如 {project-name}-fj-{module-name}）及包含的 SKILL.md
/project-analyzer <source> <output-dir>
```

### 1.3 目录整理

[`dir-organizer`](./skills/dir-organizer) 技能旨在帮助用户规范化和优化项目目录结构，从而提升工程的可维护性。

该技能支持对目录和文件进行基础及高级操作，如创建、重命名和移动文件。在执行时，它遵循严格的状态收集与方案审核流程，必须先在回复中完整打印出重构计划，并经用户同意后方可执行。此外，整理完成后该技能还会自动扫描并更新内部引用链接，确保文件间关联的准确性。

使用示例如下：

```bash
# 触发目录整理技能
# 参数 target-dir: 需要整理的目标目录路径（如果不提供，通常默认处理当前工作目录或通过对话指定）
/dir-organizer <target-dir>
```

### 1.4 文档评审

[`doc-reviewer`](./skills/doc-reviewer) 技能用于审查技术文档的准确性、一致性、结构规范和专业性，以确保项目文档的高质量。

该技能通过标准的评审闭环流程，逐项检查目标文档的排版结构（如中英文空格、章节编号）与内容质量（如术语统一、脱敏处理）。在明确指出具体问题和修改建议后，它还支持在用户授权下自动应用修复，极大提升了文档维护的效率。

使用示例如下：

```bash
# 触发文档评审技能
# 参数 target-file: 需要被审查的 Markdown 技术文档路径
/doc-reviewer <target-file>
```

### 1.5 Markdown 总结器

[`md-summarizer`](./skills/md-summarizer) 技能用于分析和总结本地的 Markdown 文件，并输出结构化、专业深度的中文分析报告。

该技能能对单个本地 Markdown 文件进行“核心概要”、“深度解析”和“关键要点”的提取，还支持对多个文件进行综合对比分析，提炼出共同主题与核心冲突。

使用示例如下：

```bash
# 触发 Markdown 总结器技能
# 提供一个或多个本地 Markdown 文件路径
/md-summarizer ./article1.md ./article2.md
```

### 1.6 代码提交助手

[`update-submitter`](./skills/update-submitter) 技能旨在自动分析本地代码仓库的变更，将相关联的文件修改进行逻辑分组，并生成符合 Conventional Commits 规范的提交信息。

该技能通过分析 `git status` 与 `git diff` 的输出，智能识别不同类型的变更（如功能开发、问题修复、文档更新等）。在为每个逻辑分组生成标准化的提交信息后，它会先向用户展示完整的提议计划，并在获取明确授权后自动执行提交操作。这有效保持了 Git 历史的整洁与规范。

使用示例如下：

```bash
# 触发代码提交工作流
# 参数 target-dir: 可选，目标项目目录路径（如果不提供，默认为当前工作目录）
/update-submitter <target-dir>
```

### 1.7 `Agent Skill` 审查器

[`agent-skill-reviewer`](./skills/agent-skill-reviewer) 技能旨在自动审查和验证用户编写的 `Agent Skill` 目录结构与 `SKILL.md` 文件，确保其符合最佳实践与核心规范。

该技能通过分析目标技能的目录命名、文件结构（如是否按关注点分离）、YAML Frontmatter（如描述是否遵循“功能 + 触发场景 + 关键词”公式）以及核心指令的清晰度。审查完成后，会输出一份包含目录结构、元数据、指令逻辑与改进建议的结构化审查报告，帮助开发者规范技能的编写。

使用示例如下：

```bash
# 触发 Agent Skill 审查工作流
# 参数 target-dir: 需要被审查的 Agent Skill 目录路径
/agent-skill-reviewer <target-dir>
```

### 1.8 `OpenSpec` 规范驱动开发辅助

[`openspec-assistant`](./skills/openspec-assistant) 技能旨在帮助用户使用 `OpenSpec` 框架进行敏捷且高确定性的规范驱动开发 (`SDD`) 。

该技能涵盖了意图对齐、规范生成、代码实现与自动化验证的完整生命周期。它支持架构师（撰写 Spec / 评审代码）、开发工程师（编写业务代码）和 QA 测试工程师（编写测试用例）三种角色的无缝协同。通过内置的 `/opsx` 指令体系，它严格约束 AI 生成代码的边界，确保实现逻辑与业务规范完全一致。

使用示例如下：

```bash
# 触发 OpenSpec 协作技能
# 附带你需要执行的具体意图或需求描述
/openspec-assistant [执行意图/变更描述]
```

### 1.9 网页内容下载器

[`web-content-downloader`](./skills/web-content-downloader) 技能用于下载指定的网页内容，剥离无关的 HTML 标签并转换为标准的 Markdown 格式，同时保留网页原始语言（不进行翻译）。

该技能特别强化了对多媒体与排版的支持：不仅能利用 Jina Reader 自动获取排版良好的正文内容，还能智能提取文章中的核心配图，将其批量下载到本地的 `img` 目录中，并根据上下文进行重命名和 Markdown 链接替换。此外，它还能将网页中的 HTML 表格精准转换为 Markdown 表格，极大地提高了网页内容的本地化存档效率。

使用示例如下：

```bash
# 触发网页内容下载与图片提取技能
# 参数 URL: 目标网页地址
/web-content-downloader <URL>
```

### 1.10 Markdown 翻译器

[`md-translator`](./skills/md-translator) 技能用于将指定的本地 Markdown 文件翻译成目标语言（默认中文），并在生成的新文件中添加语言标识后缀。

该技能在翻译过程中会严格保留原有的 Markdown 格式（包括标题、列表、代码块、加粗、链接、图片引用等）。同时内置了对文档排版规范的检查，例如确保中英文之间留有空格、代码块有注释说明，以及将 HTML 表格格式化为标准的 Markdown 表格。

使用示例如下：

```bash
# 触发本地 Markdown 文件翻译技能
# 参数 target-file: 本地 Markdown 文件路径
/md-translator <target-file>
```

### 1.11 参考文献整理助手

[`reference-organizer`](./skills/reference-organizer) 技能用于自动获取外部链接（如博客、技术白皮书、学术论文等）的元数据，并根据用户要求的级别和场景，将其格式化为标准的参考文献条目。

该技能内置了强大的跨平台信息抓取能力：对于 arXiv 预印本论文，使用定制的 Python 脚本通过 API 解析；对于 IEEE、ACM 等正式学术期刊和会议论文，调用 Crossref API 提取带 DOI 的结构化元数据（突破反爬虫拦截）；对于普通网页和技术白皮书，则使用无头浏览器抓取正文。最终输出完全符合 GB/T 7714-2015、APA 或 IEEE 权威标准的引文格式，可直接供 `doc-reviewer` 等其他技能协同调用。

使用示例如下：

```bash
# 触发参考文献整理技能
# 附带你需要格式化的一个或多个参考链接（URL / DOI / arXiv ID）
/reference-organizer [URL/DOI/ID]
```

### 1.12 Markdown 链接检查器

[`md-link-checker`](./skills/md-link-checker) 技能用于自动化验证 Markdown 文件中的本地和外部链接有效性，确保项目文档内链与外链的连通性。

该技能底层依赖多线程并发扫描架构并内置了 LRU 缓存机制，极大提升了对海量外部网络 URL 的排查速度与稳定性，同时兼容了标准 Markdown 语法及 HTML 图片标签的解析。通过灵活的参数配置，该技能可无缝适应单文件诊断、目录扫描及全项目的链接健康度审查。

使用示例如下：

```bash
# 触发 Markdown 链接检查技能
# 提供目标文件/目录路径，或不带参数以扫描全项目
/md-link-checker <target-file|target-dir>
```

### 1.13 Draw.io 架构图设计器

[`drawio-designer`](./skills/drawio-designer) 技能用于创建、编辑和管理 draw.io XML 架构图，支持自动化导出为透明背景的高分辨率 PNG 图片，并内置标准化的 AWS 官方图标与连线排版规范。

该技能通过直接操作底层的 `.drawio` XML 结构，能够精准控制架构图的排版布局、连线路由以及图元样式。它特别强化了 AWS 架构图的绘制标准，自动映射官方配色与资源图标，并内建防重叠的连线规则，确保在 Headless CLI 导出时各类图标和标签均能完美呈现。

使用示例如下：

```bash
# 触发 draw.io 架构图设计技能
# 可要求生成、修改架构图或将其转换为 PNG
/drawio-designer <diagram-file>
```

### 1.14 PPTX 读取器

[`pptx-reader`](./skills/pptx-reader) 技能用于理解、读取和分析 `.pptx` 幻灯片文件内容，支持纯文本提取、XML 解包以及将幻灯片无损渲染为高分辨率图像。

该技能通过集成 `markitdown` CLI 工具实现高效的纯文本摄取，同时利用 LibreOffice 和 Poppler 工具链将演示文稿无损转换为 PDF 并逐页切分为高分辨率 JPEG 图像。这为大语言模型的多模态视觉分析和排版审查提供了高质量的基础语料，同时支持在独立的 Python 虚拟环境中执行以隔离系统级依赖。

使用示例如下：

```bash
# 触发 PPTX 读取器技能
# 参数 target-file: 需要被处理的 .pptx 演示文稿文件路径
/pptx-reader <target-file>
```

### 1.15 知识图谱本体管理

> 原始出处：[openclaw/skills · oswalpalash/ontology](https://github.com/openclaw/skills/tree/main/skills/oswalpalash/ontology)
>
> 本仓库改动：导入 `SKILL.md`、`scripts/ontology.py` 及 `references/` 下的 `schema.md`、`queries.md`，删除上游仅用于市场分发的 `_meta.json`；并在本 README 的 §1.15 增补中文讲解（四个使用场景 + 端到端示例），同时将本 README 中实体/关系计数修正为与实际 schema 对齐的数值（16 种实体、15 种关系）。

[`ontology`](./skills/ontology) 技能为智能体提供了一套类型化的知识图谱系统，用于结构化的记忆存储与跨技能状态共享。

该技能基于实体-关系模型（Entity-Relation）构建可验证的知识图谱，内置了 16 种核心实体类型（如 Person、Project、Task、Event、Document 等）和 15 种关系类型（如 `has_owner`、`blocks`、`depends_on` 等），覆盖了人员、工作、时间地点、信息、资源与元数据等典型领域。在约束层面，它支持属性约束（必填字段、枚举值、禁止字段）、关系基数校验以及基于深度优先搜索（DFS）的环路检测。其中属性约束在实体 `create` 时即时校验，而关系类型、基数与环路等全局约束则通过 `validate` 命令进行批量复核。在存储层面，数据以追加式 JSONL 事件日志落盘，天然具备完整审计轨迹和冲突避免能力；同时该技能还定义了“技能契约”模式，允许其他技能声明对本体的读写依赖，实现可组合的多技能协作架构。

与其他单一职责的工具型技能不同，`ontology` 扮演的是**智能体记忆层与协作基座**的角色，其典型使用场景包括：

- **跨会话持久化记忆**：当用户希望智能体“记住”某些事实（如“Alice 是网站重构项目的负责人”、“任务 A 依赖任务 B”）时，将其落地为可查询、可验证的结构化图谱，避免上下文窗口丢失导致的信息遗忘。
- **多技能状态共享**：当多个技能需要在同一份“世界状态”上协同时（例如邮件技能产生 `Commitment`，任务技能消费后生成 `Task`），通过本体提供的统一读写契约消除各技能之间的数据格式割裂。
- **计划即图变换**：当智能体需要规划多步任务时，将整个计划建模为一系列带约束校验的图操作序列（即 Planning as Graph Transformation 模式），任一步违反约束即可回滚，显著提升长流程任务的可靠性。
- **依赖与影响分析**：针对项目管理场景（任务阻塞、人员分配、事件关联等）进行图遍历查询，例如“X 任务的上游阻塞有哪些”、“proj_001 下所有未完成任务的负责人是谁”。

**端到端示例**：以“为‘网站重构’项目建立知识图谱，并追踪任务依赖”为例，完整工作流如下：

```bash
# 步骤 1：初始化本体存储
mkdir -p memory/ontology && touch memory/ontology/graph.jsonl

# 步骤 2：声明 schema 约束（定义 Task 的必填字段与状态枚举）
python3 scripts/ontology.py schema-append --data '{
  "types": {
    "Person":  {"required": ["name"]},
    "Project": {"required": ["name", "status"]},
    "Task":    {"required": ["title", "status"], "status_enum": ["open", "in_progress", "done"]}
  },
  "relations": {
    "has_owner": {"from_types": ["Project"], "to_types": ["Person"], "cardinality": "many_to_one"},
    "has_task":  {"from_types": ["Project"], "to_types": ["Task"]},
    "blocks":    {"from_types": ["Task"],    "to_types": ["Task"], "acyclic": true}
  }
}'

# 步骤 3：创建核心实体（负责人、项目、两个任务）
python3 scripts/ontology.py create --type Person  --id p_001     --props '{"name":"Alice","email":"alice@example.com"}'
python3 scripts/ontology.py create --type Project --id proj_001  --props '{"name":"Website Redesign","status":"active"}'
python3 scripts/ontology.py create --type Task    --id task_001  --props '{"title":"Draft wireframes","status":"open"}'
python3 scripts/ontology.py create --type Task    --id task_002  --props '{"title":"Implement homepage","status":"open"}'

# 步骤 4：建立关系（项目负责人、项目-任务归属、任务间阻塞依赖）
python3 scripts/ontology.py relate --from proj_001 --rel has_owner --to p_001
python3 scripts/ontology.py relate --from proj_001 --rel has_task  --to task_001
python3 scripts/ontology.py relate --from proj_001 --rel has_task  --to task_002
python3 scripts/ontology.py relate --from task_001 --rel blocks    --to task_002

# 步骤 5：查询——列出项目下所有任务、所有开放状态任务，以及 task_002 的上游阻塞者
python3 scripts/ontology.py related --id proj_001 --rel has_task
python3 scripts/ontology.py query   --type Task   --where '{"status":"open"}'
python3 scripts/ontology.py related --id task_002 --rel blocks --dir incoming

# 步骤 6：全量校验（检查关系类型/基数、环路以及全量属性约束）
#   —— 对应“计划即图变换”场景：在外层工作流中将 validate 作为提交前的守门步骤，
#      一旦发现约束违反则由调用方执行整体回滚（ontology.py 本身只负责报告错误）
python3 scripts/ontology.py validate
```

执行完毕后，`memory/ontology/graph.jsonl` 中会沉淀一份完整的、可审计的事件日志；后续任何技能（如代码提交助手、OpenSpec 开发辅助）均可基于同一份图谱读取项目上下文或追加新的实体与关系，实现真正的**跨技能协同记忆**——这正是上文“多技能状态共享”场景在工程落地时的标准形态。

### 1.16 杂志编辑式信息卡设计器

> 原始技能来自：[shaom/infocard-skills](https://github.com/shaom/infocard-skills)
>
> 本仓库改动：将技能目录从上游的 `editorial-card-screenshot` 更名为语义更清晰的 [`editorial-card-designer`](./skills/editorial-card-designer)（突出“设计 + 截图”双阶段产出）；在 `SKILL.md` 的 `metadata.clawdbot.requires` 中补齐 Chrome / Chromium 二进制依赖以及 `trim_card_bottom.sh` 所需的 Python + Pillow 可选依赖；加固 [`scripts/capture_card.sh`](./skills/editorial-card-designer/scripts/capture_card.sh) 的跨平台 Chrome 可执行文件解析顺序，并将两个 shell 脚本改用 `#!/usr/bin/env bash` 以便在最小化 Linux 镜像中开箱即用；此外对面向 Agent 的英文 `SKILL.md` 与面向中文场景的 [`references/editorial-card-prompt.md`](./skills/editorial-card-designer/references/editorial-card-prompt.md) 做了受众隔离。

[`editorial-card-designer`](./skills/editorial-card-designer) 技能用于把一段文字或核心信息转化为一张**现代杂志编辑设计（Editorial Design）+ 瑞士国际主义平面设计风格（Swiss / International Typographic Style）**的高密度 HTML 信息卡，并直接渲染成与目标比例严格对齐的 PNG 截图，典型用途涵盖公众号封面、社交平台卡片、技术文档配图与演示开场图。

该技能内置 8 种固定比例预设——`3:4`（竖版信息卡）、`4:3`（横版信息卡）、`1:1`（方形贴文）、`16:9`（标准宽屏封面）、`9:16`（故事 / Reel 竖封）、`2.35:1`（电影级宽条）、`3:1`（个人主页横幅）、`5:2`（超宽条带）——并为每种比例在 [`references/recommended-skeletons.md`](./skills/editorial-card-designer/references/recommended-skeletons.md) 中提供了可复用的版式骨架（Hero + Stats + 主次模块 + 页脚条带等），避免简单地把同一套布局强行缩放到不同比例。在渲染层面，[`scripts/capture_card.sh`](./skills/editorial-card-designer/scripts/capture_card.sh) 以 headless Chrome 按预设像素（如 `16:9 → 1920×1080`）截图，强制 `--force-device-scale-factor=1` 保证像素对齐，同时内部预留 120px 高度缓冲以应对无头浏览器与常规浏览器的字体渲染差异，确保页脚完整捕获；后处理脚本 [`scripts/trim_card_bottom.sh`](./skills/editorial-card-designer/scripts/trim_card_bottom.sh)（依赖 Python + Pillow）再按固定像素 `--bottom 120` 精确裁回目标尺寸。在字体层面，默认引入 `Noto Serif SC` / `Noto Sans SC` / `Oswald` / `Inter` 的 Google Fonts 组合，并要求同时声明本地回退字体栈，避免远程字体加载失败导致版式漂移。

使用示例如下：

```bash
# 步骤 1：根据 SKILL.md 指示生成一份与目标比例严格匹配的 HTML（例如 1920×1080 用于 16:9）
#        可从 assets/card-template.html 的最小骨架开始，填入标题、摘要、模块与页脚条带

# 步骤 2：用 headless Chrome 截图（脚本内部已预留 120px 高度缓冲）
./skills/editorial-card-designer/scripts/capture_card.sh \
    path/to/your-card.html path/to/your-card.png 16:9

# 步骤 3（推荐）：按固定像素裁掉 120px 底部缓冲，恢复精确目标尺寸
#        —— 若跳过此步，成品高度将为目标值 +120px（例如 1920×1200）。
./skills/editorial-card-designer/scripts/trim_card_bottom.sh \
    path/to/your-card.png path/to/your-card.trimmed.png --bottom 120
```

**配套示例目录 `examples/editorial-card-designer/`**：为了让新用户直观理解该技能的产出形态，本仓库在 [`examples/editorial-card-designer/`](./examples/editorial-card-designer) 下沉淀了端到端的真实示例。当前收录了一份基于本技能 [`editorial-card-designer-intro.md`](./examples/editorial-card-designer/editorial-card-designer-intro.md) 生成的 16:9 信息卡：[`editorial-card-designer-intro.html`](./examples/editorial-card-designer/editorial-card-designer-intro.html) 为完整的源 HTML（可直接在浏览器打开或二次编辑样式），[`editorial-card-designer-intro.png`](./examples/editorial-card-designer/editorial-card-designer-intro.png) 为先经 `capture_card.sh` 截图、再经 `trim_card_bottom.sh --bottom 120` 裁剪得到的 1920×1080 PNG 成品。后续本仓库新增的信息卡示例会统一沉淀到该目录，形成可检索的**版式 + 比例 + 内容密度**三维度参考样例集，方便开发者在调用技能前对照挑选最贴近自己内容的骨架。

### 1.17 技术文章大纲规划器

[`tech-outline-planner`](./skills/tech-outline-planner) 技能用于为高质量的技术文章（特别是系统、AI 或底层架构类）设计“架构评审级”的大纲结构。

该技能采用**组合叙事结构**：外层使用 Context-first 风格（背景-问题-方案-权衡）确保宏观逻辑的严密性；内层使用 Process narrative 程序化描述确保技术细节的自然衔接。在编写过程中，它严格遵循“给定信息优先于新信息” (Given before new) 的认知原则，帮助作者构建具备深度且易于理解的技术叙事。

使用示例如下：

```bash
# 触发技术文章大纲规划技能
# 附带你需要规划的主题或核心意图
/tech-outline-planner [技术主题/核心痛点/方案草案]
```

---

## 2. 核心设计理念

为最大化大模型推理效能并保障开发者阅读体验，本项目的技能架构在受众隔离（中英文双语分层）与解耦轻量化上建立了严格的标准。

### 2.1 语言规范：受众隔离

为了在保证 AI 推理性能的同时提供良好的用户阅读体验，本项目中的技能严格遵循以下受众隔离的语言规范：

- **Agent/LLM 面向文件（全英文）**：所有作为外挂知识库供 Agent 读取的 `SKILL.md` 文件，以及控制工作流的 `*-prompt.md` 模板文件，均保持纯英文。这能最大化大模型的指令遵循能力和理解准确度。
- **人类面向文件（全中文）**：最终交付给开发者阅读的产物（如通过 `project-analyzer` 生成的《项目架构深度分析报告》），被严格限制为使用纯中文输出，并要求符合专业的技术文档排版规范。

**特例说明 (中文技能文档)**：

尽管底层提示词通常建议使用英文，但如 `dir-organizer` 和 `doc-reviewer` 等技能的 `SKILL.md` 采用了全中文编写。这是因为这些技能的核心目标是直接指导开发者制定重构计划或审查中文技术文档规范。采用中文编写能有效降低开发者的理解门槛，同时更精确地传达针对中文语境的排版与组织规则。

### 2.2 产物定位：为什么是生成 SKILL 而非 Agent？

`code-reader` 的核心输出是针对每个模块的 `SKILL.md`，而不是创建专门负责该模块的 `Agent`。这一设计的巧思在于：

- **解耦与轻量化**：如果为每个模块生成一个 Agent，会导致角色泛滥且业务逻辑被硬编码在提示词中。生成 `SKILL.md` 则相当于提取了“技能书”。
- **按需挂载**：开发者只需要让任何一个通用的 Agent（如默认的编程助手）在需要时加载对应模块的 `SKILL.md`，该 Agent 就能瞬间“学会”该模块的底层逻辑和修改规范。

---

## 3. `Agent Skill` 最佳实践

从生产级目录组织到渐进式上下文加载，一套标准化的工程规范是确保智能体技能稳定运行的基石。以下实践均参考自 [给 Claude 写本“标准操作手册”：Agent Skills 实战与深度解析](https://github.com/ForceInjection/AI-fundamentals/blob/main/08_agentic_system/agent_skills/docs/claude_skills_guide.md) 文档。

### 3.1 生产级目录结构

合理的目录结构能够有效解耦指令与实现，提升技能的可维护性。

建议将核心指令、执行脚本与参考资料进行分离，标准结构如下：

- **`SKILL.md`**：核心标准操作手册，文件名必须大写。
- **`scripts/`**：存放具体执行原子操作的可执行脚本。
- **`references/`**：存放按需加载的补充参考文档。
- **`assets/`**：存放各类静态资源。

### 3.2 精准的触发描述

准确的技能描述是大模型进行逻辑推理和决策触发的关键依据。

`SKILL.md` 头部 Frontmatter 中的 `description` 字段是系统判断是否加载该技能的唯一标准。编写时应遵循以下黄金公式：

> **[功能描述] + [触发场景] + [关键词]**

确保描述具体且场景明确，避免使用过于宽泛或模糊的表述。

### 3.3 渐进式知识披露

渐进式加载机制能够有效避免多个技能同时注册导致的上下文窗口溢出。

系统通常采用三层渐进式的知识加载策略：

1. **元数据层（常驻加载）**：仅加载所有技能的名称与描述，用于大模型建立可用能力的索引。
2. **核心指令层（按需加载）**：当技能被触发时，才将 `SKILL.md` 的正文指令注入当前上下文。
3. **详细文档层（引用加载）**：执行过程中遇到特定需求时，再读取 `references/` 目录下的外部文档。

### 3.4 状态管理与流程编排

理解技能的状态属性有助于避免多任务执行时的上下文冲突。

- **非并发安全**：与无状态的函数调用不同，Agent Skills 本质上是动态修改当前的对话上下文。因此它是有状态的，在一段对话线程中建议一次只激活一个技能。
- **复杂工作流**：技能非常适合作为“指挥官”来编排复杂工作流，例如多工具（MCP）协同、自我迭代纠错以及基于上下文的条件判断。

### 3.5 技能测试金字塔

系统化的测试是确保技能从可用走向稳定可靠的重要保障。

为了验证技能的健壮性，应建立多维度的评估体系：

- **触发测试**：包含正向测试（确保目标场景下能被触发）和负向测试（确保无关对话中不被误触发）。
- **功能测试**：验证技能调用的底层脚本或 API 能否正确返回预期结果。
- **性能评估**：对比引入技能前后的大模型 Token 消耗情况与交互轮数。

### 3.6 技能命名规范

规范的命名有助于开发者和系统快速理解技能的用途与角色定位。

推荐使用 **名词/执行者（Doer）** 形式，而非动词（Action）形式。例如，应使用 `agent-skill-reviewer` 而不是 `agent-skill-review`，使用 `pdf-translator` 而不是 `translate-pdf`。多个单词之间应使用 kebab-case（短横线）连接。这种命名方式与技能作为“拟人化”智能体角色的定位高度一致。

---

## 4. 深度解析案例

本项目不仅收录了实用的 Agent Skills，还包含对业界顶尖 AI 工程实践的深度解析，以帮助开发者更好地理解和构建虚拟工程团队。

### 4.1 gstack 项目深度解析

我们对 Y Combinator CEO Garry Tan 开源的 `gstack` 项目进行了详尽的逆向工程与架构分析，提炼出了其核心设计哲学：**将结构化的软件工程角色封装为特定的 AI 技能**。

该深度解析报告详细拆解了：

- **无头浏览器守护进程**：如何解决 AI 代理操作浏览器时的冷启动与状态丢失问题。
- **21 个核心技能全景**：覆盖产品规划、质量保障、发布运营等完整生命周期。
- **Prompt 工程最佳实践**：如防御性设计、跨阶段上下文继承以及注入专家级思维模式。

详细内容请阅读：[gstack 项目深度解析报告](./docs/gstack-deep-dive.md)

### 4.2 五种智能体技能设计模式

我们翻译并整理了来自 Google Cloud Tech 的关于 Agent Skill 设计模式的深度文章，帮助开发者跳出格式的局限，专注于技能内部逻辑的结构化设计。

该报告详细拆解了五种核心设计模式：

- **工具包装器 (Tool Wrapper)**：让 Agent 按需获取特定库或框架的上下文。
- **生成器 (Generator)**：通过编排模板与样式指南强制执行一致的文档输出。
- **审查器 (Reviewer)**：分离评分标准与检查流程，实现多领域的系统化审查。
- **反转模式 (Inversion)**：让 Agent 扮演面试官，在收集完整上下文前阻止执行。
- **管道模式 (Pipeline)**：通过硬检查点强制执行严格的多步骤工作流。

详细内容请阅读：[每位 ADK 开发者都应掌握的五种智能体技能设计模式](./docs/google-skill-patern.md)

### 4.3 superpowers 深度解析

该文档对 superpowers 插件与技能体系进行系统化的工程解析与实战指南，涵盖架构分层、核心模块、TDD/SDD 工作流、子智能体协作与钩子注入机制等内容，帮助读者快速掌握如何基于 superpowers 构建高确定性的 AI 工程能力。全文见：[superpowers 深度解析](./docs/superpowers-deep-dive.md)。

---

## 5. 推荐参考资源

除了本项目内置的工具流，诸如 MiniMax 与 vLLM 等官方维护的技能合集同样展示了在前端开发、多媒体生成与底层推理部署场景下的绝佳实践。

### 5.1 MiniMax-AI 官方技能库

[MiniMax-AI/skills](https://github.com/MiniMax-AI/skills) 是由 MiniMax 官方维护的优秀技能合集。该项目涵盖了从前端开发到复杂办公文档生成的广泛场景，为开发者提供了丰富的实战参考。

其核心技能模块包括：

- **全栈与客户端开发**：涵盖前端 (`frontend-dev`)、全栈 (`fullstack-dev`)、Android (`android-native-dev`) 以及 iOS (`ios-application-dev`) 的系统性开发指南与规范。
- **多媒体与创意生成**：提供着色器开发 (`shader-dev`) 与 GIF 动图生成 (`gif-sticker-maker`) 技能，结合 MiniMax 的图像和视频生成 API，实现高级视觉效果。
- **专业文档处理**：包含针对 PDF (`minimax-pdf`)、PPTX (`pptx-generator`)、Excel (`minimax-xlsx`) 和 DOCX (`minimax-docx`) 的深度处理技能，支持从零生成、模板填充与格式重构。

### 5.2 CUDA Code Skill 文档与技能

[ForceInjection/cuda-code-skill](https://github.com/ForceInjection/cuda-code-skill) 是由原力注入博主维护的 CUDA 开发者专属文档与 AI 技能库。该项目将 NVIDIA 的官方文档（包括 PTX ISA 9.1、CUDA Runtime API 13.1、CUDA Driver API 13.1、CUDA Math API 13.x、cuBLAS 13.2 和 NCCL 等）转换为结构化且易于检索的 Markdown 格式，并内置了支持 Claude Code、Trae 等工具的 GPU 开发与 LLM 推理优化专属技能。

其核心内容包括：

- **可检索的官方文档**：覆盖 PTX 指令集、CUDA 运行时与驱动 API、CUDA Math、cuBLAS 以及 NCCL 等核心库，彻底解决原版 HTML 文档跨页面检索困难的问题。
- **AI IDE 专属开发技能**：内置的技能库支持快速查询 PTX 指令、CUDA Math 内联函数、混合精度 GEMM 签名以及多 GPU 通信（NCCL）等底层开发细节，显著提升 AI（如 Claude Code, Trae 等）辅助 GPU 开发与 LLM 推理优化的准确率。

### 5.3 vLLM 官方 Agent 技能库

[vllm-project/vllm-skills](https://github.com/vllm-project/vllm-skills/tree/main) 是由 vLLM 官方项目维护的专属智能体技能集合。该项目遵循 Anthropics 的技能模板规范，提供了一系列模块化、可复用的自动化技能，专门用于 vLLM 模型的部署、调用与性能基准测试。

其核心技能模块包括：

- **容器化部署**：提供 `vllm-deploy-docker` 技能，支持通过预构建镜像或源码编译的方式，快速部署支持 NVIDIA GPU 加速的 vLLM 容器，并启动兼容 OpenAI API 的服务。
- **轻量级本地服务**：包含 `vllm-deploy-simple` 技能，能够自动检测硬件环境并安装 vLLM，在本地快速启动模型推理服务并提供测试与管理工具。
- **性能基准测试**：提供 `vllm-prefix-cache-bench` 技能，支持使用固定提示词、真实数据集或合成模式，全面评估 vLLM 自动前缀缓存（Prefix Caching）机制的运行效率。

### 5.4 领域驱动设计 (DDD) 技能库

[ForceInjection/domain-driven-design-skills](https://github.com/ForceInjection/domain-driven-design-skills) 是由原力注入博主维护的领域驱动设计专属技能库。该项目将 DDD 的核心概念、战术设计模式和最佳实践封装为可复用的 Agent Skills，帮助开发者和 AI 编程助手在复杂业务系统中正确应用领域驱动设计方法论。

其核心技能模块包括：

- **战略设计**：涵盖限界上下文（Bounded Context）识别、上下文映射（Context Mapping）和子域划分等核心技能，支持复杂业务架构的系统性分析。
- **战术设计**：提供实体（Entity）、值对象（Value Object）、聚合根（Aggregate Root）、领域服务（Domain Service）等 DDD 构建块的设计规范与实现指南。
- **事件驱动架构**：包含领域事件（Domain Event）建模、事件溯源（Event Sourcing）和 CQRS 模式的实战技能，支持响应式系统的设计与实现。

---

## 6. `Skill` 单元测试

为防止迭代过程中的能力退化，本项目在 `unit-test` 目录下构建了基于自动执行脚本和测试断言的技能评估体系，确保智能体任务的可靠性。

该测试框架包含以下核心组件与文档：

- **测试执行脚本**：`opencode-skill-eval.sh` 提供了自动化的测试执行能力。
- **测试指南**：[`skill-eval-minimal-guide.md`](./unit-test/skill-eval-minimal-guide.md) 详细说明了如何编写和运行技能的评估测试。
- **测试用例与数据**：包含 `evals`（评估逻辑）、`fixtures`（测试数据，如供 `doc-reviewer` 和 `md-translator` 使用的示例文档）、`skills`（被测技能配置）以及 `tests`（具体的测试断言脚本）。

通过系统化的单元测试，我们能够持续验证技能触发的精准度以及任务执行的可靠性。
