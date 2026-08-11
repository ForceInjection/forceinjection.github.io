# 原力注入 Agent Skill 合集

[English](README-en.md) | **中文**

本项目收录了由“原力注入博主”使用和维护的优秀认知技能。这些技能通过自动化的工作流与多智能体协作机制，覆盖代码阅读与架构分析、文档处理与评审、内容创作与设计、规范驱动开发等工程场景，帮助开发者显著提升 AI 辅助编程与自动化运维的效能。

## 目录

- [1. 核心技能介绍](#1-核心技能介绍)
- [2. 核心设计理念](#2-核心设计理念)
- [3. `Agent Skill` 最佳实践](#3-agent-skill-最佳实践)
- [4. 深度解析案例](#4-深度解析案例)
- [5. 推荐参考资源](#5-推荐参考资源)
- [6. `Skill` 单元测试](#6-skill-单元测试)

---

## 1. 核心技能介绍

针对复杂代码阅读、项目逆向工程、规范驱动开发等工程挑战，本项目封装了 17 个独立智能体技能，旨在通过多角色协同解决实际开发瓶颈。

| 技能                                                          | 功能                                                                                                                                                      | 触发命令                                  |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| [`code-reader`](./skills/code-reader)                         | 深度代码阅读：三重智能体协作（技术作者 / QA / 初级开发者）+ 闭卷考试式验证循环，系统化阅读陌生代码库并生成可复用的认知技能                                | `/code-reader <source> <output-dir>`      |
| [`project-analyzer`](./skills/project-analyzer)               | 深度项目架构分析：在 `code-reader` 基础上对第三方仓库逆向工程与静态分析，产出含 7 个标准章节的《项目架构深度分析报告》（代码解析与执行流程约占 70% 篇幅） | `/project-analyzer <source> <output-dir>` |
| [`dir-organizer`](./skills/dir-organizer)                     | 目录整理：规范化重构项目目录结构，先完整打印重构计划并经用户同意后执行，完成后自动更新内部引用链接                                                        | `/dir-organizer <target-dir>`             |
| [`doc-reviewer`](./skills/doc-reviewer)                       | 文档评审：四种独立评审类型（大纲 / 内容 / 资产链接 / 格式），规则按需加载，支持用户授权下自动应用修复                                                     | `/doc-reviewer <target-file>`             |
| [`md-summarizer`](./skills/md-summarizer)                     | Markdown 总结器：提取核心概要、深度解析与关键要点，支持多文件综合对比分析，输出结构化中文报告                                                             | `/md-summarizer <file...>`                |
| [`update-submitter`](./skills/update-submitter)               | 代码提交助手：分析 `git status`/`git diff`，将相关变更逻辑分组并生成符合 Conventional Commits 规范的提交信息，授权后执行提交                              | `/update-submitter <target-dir>`          |
| [`agent-skill-reviewer`](./skills/agent-skill-reviewer)       | Agent Skill 审查器：审查技能目录结构、YAML Frontmatter（描述公式）与指令清晰度，输出结构化审查报告                                                        | `/agent-skill-reviewer <target-dir>`      |
| [`openspec-assistant`](./skills/openspec-assistant)           | OpenSpec 规范驱动开发：架构师 / 开发 / QA 三角色协同，覆盖意图对齐、规范生成、代码实现与自动化验证，内置 `/opsx` 指令体系                                 | `/openspec-assistant [执行意图]`          |
| [`web-content-downloader`](./skills/web-content-downloader)   | 网页内容下载器：Jina Reader 正文提取 + 核心配图智能下载重命名 + HTML 表格转 Markdown，保留网页原始语言                                                    | `/web-content-downloader <URL>`           |
| [`md-translator`](./skills/md-translator)                     | Markdown 翻译器：翻译为指定语言（默认中文），严格保留 Markdown 格式，内置中英空格等排版规范检查                                                           | `/md-translator <target-file>`            |
| [`reference-organizer`](./skills/reference-organizer)         | 参考文献整理：arXiv API / Crossref DOI / 无头浏览器三种抓取通道，输出符合 GB/T 7714 / APA / IEEE 标准的引文                                               | `/reference-organizer [URL/DOI/ID]`       |
| [`md-link-checker`](./skills/md-link-checker)                 | Markdown 链接检查器：多线程并发 + LRU 缓存，校验本地与外部链接连通性，兼容 HTML 图片标签                                                                  | `/md-link-checker <target-file\|dir>`     |
| [`drawio-designer`](./skills/drawio-designer)                 | Draw.io 架构图设计器：直接操作 `.drawio` XML，内置 AWS 官方图标映射与防重叠连线规则，headless 导出透明背景高分辨率 PNG                                    | `/drawio-designer <diagram-file>`         |
| [`pptx-reader`](./skills/pptx-reader)                         | PPTX 读取器：markitdown 文本提取 + XML 解包 + LibreOffice/Poppler 无损渲染为高分辨率图像，独立 venv 隔离系统依赖                                          | `/pptx-reader <target-file>`              |
| [`ontology`](./skills/ontology)                               | 知识图谱本体管理：16 种实体 / 15 种关系的类型化知识图谱，属性 / 基数 / 环路约束校验，JSONL 事件日志落盘审计，作为跨技能状态共享的记忆基座                 | `python3 scripts/ontology.py <cmd>`       |
| [`editorial-card-designer`](./skills/editorial-card-designer) | 杂志编辑式信息卡：现代杂志 + 瑞士国际主义风格的高密度 HTML 信息卡，8 种固定比例预设，headless Chrome 渲染为精确对齐的 PNG                                 | 对话式工作流                              |
| [`tech-outline-planner`](./skills/tech-outline-planner)       | 技术文章大纲规划：Context-first + Process narrative 组合叙事结构，遵循 Given-before-new 认知原则，产出"架构评审级"大纲                                    | `/tech-outline-planner [主题/痛点/方案]`  |

> 来源说明：`ontology` 导入自 [hanzoskill/ontology](https://github.com/hanzoskill/ontology)（本地增强为超集），`editorial-card-designer` 导入自 [shaom/infocard-skills](https://github.com/shaom/infocard-skills)（本地更名 + 加固），`pptx-reader` 参考自 [anthropics/skills](https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md)。各技能的详细使用示例与端到端演示见各自 `SKILL.md` 及 `examples/` 目录。

---

## 2. 核心设计理念

为最大化大模型推理效能并保障开发者阅读体验，本项目的技能架构在受众隔离（中英文双语分层）与解耦轻量化上建立了严格的标准。

### 2.1 语言规范：受众隔离

为了在保证 AI 推理性能的同时提供良好的用户阅读体验，本项目中的技能严格遵循以下受众隔离的语言规范：

- **Agent/LLM 面向文件（全英文）**：所有作为外挂知识库供 Agent 读取的 `SKILL.md` 文件，以及控制工作流的 `*-prompt.md` 模板文件，均保持纯英文。这能最大化大模型的指令遵循能力和理解准确度。
- **人类面向文件（全中文）**：最终交付给开发者阅读的产物（如通过 `project-analyzer` 生成的《项目架构深度分析报告》），被严格限制为使用纯中文输出，并要求符合专业的技术文档排版规范。

**特例说明（中文技能文档）**：

尽管底层提示词通常建议使用英文，但如 `dir-organizer` 和 `doc-reviewer` 等技能的 `SKILL.md` 采用了全中文编写。这是因为这些技能的核心目标是直接指导开发者制定重构计划或审查中文技术文档规范。采用中文编写能有效降低开发者的理解门槛，同时更精确地传达针对中文语境的排版与组织规则。

### 2.2 产物定位：为什么是生成 SKILL 而非 Agent？

`code-reader` 的核心输出是针对每个模块的 `SKILL.md`，而不是创建专门负责该模块的 `Agent`。这一设计的巧思在于：

- **解耦与轻量化**：如果为每个模块生成一个 Agent，会导致角色泛滥且业务逻辑被硬编码在提示词中。生成 `SKILL.md` 则相当于提取了"技能书"。
- **按需挂载**：开发者只需要让任何一个通用的 Agent（如默认的编程助手）在需要时加载对应模块的 `SKILL.md`，该 Agent 就能瞬间"学会"该模块的底层逻辑和修改规范。

---

## 3. `Agent Skill` 最佳实践

从生产级目录组织到渐进式上下文加载，一套标准化的工程规范是确保智能体技能稳定运行的基石。以下实践均参考自 [给 Claude 写本"标准操作手册"：Agent Skills 实战与深度解析](https://github.com/ForceInjection/AI-fundamentals/blob/main/08_agentic_system/agent_skills/docs/claude_skills_guide.md) 文档。

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
- **复杂工作流**：技能非常适合作为"指挥官"来编排复杂工作流，例如多工具（MCP）协同、自我迭代纠错以及基于上下文的条件判断。

### 3.5 技能测试金字塔

系统化的测试是确保技能从可用走向稳定可靠的重要保障。

为了验证技能的健壮性，应建立多维度的评估体系：

- **触发测试**：包含正向测试（确保目标场景下能被触发）和负向测试（确保无关对话中不被误触发）。
- **功能测试**：验证技能调用的底层脚本或 API 能否正确返回预期结果。
- **性能评估**：对比引入技能前后的大模型 Token 消耗情况与交互轮数。

### 3.6 技能命名规范

规范的命名有助于开发者和系统快速理解技能的用途与角色定位。

推荐使用 **名词/执行者（Doer）** 形式，而非动词（Action）形式。例如，应使用 `agent-skill-reviewer` 而不是 `agent-skill-review`，使用 `pdf-translator` 而不是 `translate-pdf`。多个单词之间应使用 kebab-case（短横线）连接。这种命名方式与技能作为"拟人化"智能体角色的定位高度一致。

---

## 4. 深度解析案例

本项目不仅收录了实用的 Agent Skills，还包含对业界顶尖 AI 工程实践的深度解析，以帮助开发者更好地理解和构建虚拟工程团队。

### 4.1 gstack 项目深度解析

我们对 Y Combinator CEO Garry Tan 开源的 `gstack` 项目进行了详尽的逆向工程与架构分析，提炼出了其核心设计哲学：**将结构化的软件工程角色封装为特定的 AI 技能**。

该深度解析报告详细拆解了：

- **无头浏览器守护进程**：如何解决 AI 代理操作浏览器时的冷启动与状态丢失问题。
- **23 个核心技能全景**：覆盖产品规划、质量保障、发布运营等完整生命周期。
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

除了本项目内置的工具流，以下由官方或原力注入博主维护的技能合集同样展示了在各自领域的绝佳实践。

| 仓库                                                                                                        | 领域               | 说明                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| [MiniMax-AI/skills](https://github.com/MiniMax-AI/skills)                                                   | 全栈开发与办公文档 | 官方技能合集：前端 / 全栈 / Android / iOS 开发，着色器与 GIF 生成，PDF / PPTX / Excel / DOCX 文档处理                        |
| [ForceInjection/cuda-code-skill](https://github.com/ForceInjection/cuda-code-skill)                         | CUDA 开发          | 将 PTX ISA、CUDA Runtime/Driver API、CUDA Math、cuBLAS、NCCL 官方文档转换为可检索 Markdown，内置 GPU 开发专属技能            |
| [vllm-project/vllm-skills](https://github.com/vllm-project/vllm-skills/tree/main)                           | vLLM 部署与基准    | Claude Code 插件形式分发，6 个技能：部署（docker / k8s / simple）+ 性能基准（serve / random-synthetic / prefix-cache-bench） |
| [ForceInjection/domain-driven-design-skills](https://github.com/ForceInjection/domain-driven-design-skills) | 领域驱动设计       | DDD 战略设计、战术设计与事件驱动架构（CQRS/Event Sourcing）技能封装                                                          |
| [franklinxkk/ai-delivery-spec](https://github.com/franklinxkk/ai-delivery-spec)                             | 需求管理 / SDD     | 面向产品经理的需求管理 Kernel：intake→澄清→PRD/契约→评审→基线→变更/验收证据，自带 CLI、领域包与结构门禁                      |
| [ForceInjection/cufile-skill](https://github.com/ForceInjection/cufile-skill)                               | GPUDirect Storage  | cuFile API 生命周期、同步/异步/批量 I/O、性能调优、`cufile.json` 配置与 GDS 兼容性检测（含 `check_gds.sh`）                  |
| [ForceInjection/elf-skill](https://github.com/ForceInjection/elf-skill)                                     | 二进制安全         | elf-analyzer / binary-reverse / linux-pwn 三技能套件，内置 `allowed-tools` + `trust-level` 安全设计                          |
| [ForceInjection/nvme-programming-skill](https://github.com/ForceInjection/nvme-programming-skill)           | NVMe 编程          | 队列模型与命令构造、多队列调优，NVMe 2.3 规范章节提取为可 grep 文本，4 个可编译 C 示例                                       |

---

## 6. `Skill` 单元测试

为防止迭代过程中的能力退化，本项目在 `unit-test` 目录下构建了基于自动执行脚本和测试断言的技能评估体系，确保智能体任务的可靠性。

该测试框架包含以下核心组件与文档：

- **测试执行脚本**：`opencode-skill-eval.sh` 提供了自动化的测试执行能力。
- **测试指南**：[`skill-eval-minimal-guide.md`](./unit-test/skill-eval-minimal-guide.md) 详细说明了如何编写和运行技能的评估测试。
- **测试用例与数据**：包含 `evals`（评估逻辑）、`fixtures`（测试数据，如供 `doc-reviewer` 和 `md-translator` 使用的示例文档）、`skills`（被测技能配置）以及 `tests`（具体的测试断言脚本）。

通过系统化的单元测试，我们能够持续验证技能触发的精准度以及任务执行的可靠性。
