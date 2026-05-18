# Agent Skills (AI 技能)

**Agent Skill**（智能体技能）是指封装了特定领域知识、最佳实践、自动化工作流及多角色协同机制的可复用认知模块。在现代 AI 辅助开发中，单靠基础的 Prompt 往往难以应对复杂的工程挑战（如架构逆向工程、深度代码理解、规范驱动开发等）。通过将这些复杂任务拆解并固化为一个个独立的 Agent Skill，大模型可以像调用 API 一样加载这些技能，从而极大地提升分析深度、准确性与工作效率。

本模块汇总了我们在实际工程中沉淀和验证过的核心技能集合，包含通用工程提效（Awesome Skills）、领域驱动设计（DDD）以及 CUDA 编程辅助三大方向。这些资源能够帮助开发者更好地利用大模型构建复杂的应用与智能系统。

---

## 核心技能库概览

### 1. Awesome Skills

由原力注入博主精心整理的通用 AI Agent 技能集合，涵盖日常研发流程中的高频痛点，当前包含 **17 个独立智能体技能**，覆盖代码理解、架构分析、文档治理、内容生产到知识图谱等完整工程闭环。

**链接**：[本地文档](./awesome-skills/README.html)，[GitHub 仓库](https://github.com/ForceInjection/awesome-skills)

**技能列表**：

| 技能名称                                           | 核心用途                        | 工作流与特点                                                                       |
| -------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| **深度代码阅读** (`code-reader`)                   | 系统性阅读与理解陌生代码库      | 引入技术作者 / QA / 初级开发三重协作，以"闭卷考试"机制深入解析模块，避免浅尝辄止。 |
| **项目架构分析** (`project-analyzer`)              | 第三方代码库静态分析与逆向工程  | 协同模块专家、运维工程师与首席架构师，输出含 7 章节的客观深度分析报告。            |
| **目录结构整理** (`dir-organizer`)                 | 规范化项目目录与文件重构        | 严格状态收集 + 计划确认，自动更新移动文件后的内部引用链接。                        |
| **文档自动化审查** (`doc-reviewer`)                | 审查技术文档准确性与专业性      | 含大纲、内容、资产、格式四种独立评审类型，并支持自动应用修复建议。                 |
| **Markdown 总结器** (`md-summarizer`)              | 本地文档分析与结构化提取        | 单文件核心概要 / 深度解析 / 关键要点提取，支持多文件对比与主题提炼。               |
| **智能代码提交助手** (`update-submitter`)          | 生成 Conventional Commits       | 分析 `git diff` 自动逻辑分组变更，授权后执行标准化的 Git 提交。                    |
| **Agent Skill 审查器** (`agent-skill-reviewer`)    | 规范化 Agent Skill 的编写与结构 | 自动审查目录命名、文件结构、Frontmatter 与指令清晰度，输出结构化改进报告。         |
| **OpenSpec 规范开发辅助** (`openspec-assistant`)   | 规范驱动的架构设计与验证        | 支持架构师 / 开发 / QA 多角色协同，覆盖意图对齐、代码实现与自动化验证全生命周期。  |
| **网页内容下载器** (`web-content-downloader`)      | 将网页转存为离线 Markdown       | 借助 Jina Reader 保留原文排版，自动提取图片至本地 `img` 目录并改写引用。           |
| **Markdown 翻译器** (`md-translator`)              | 技术文档的专业翻译              | 严格保留 Markdown 格式，自动处理中英文空格与语言标识后缀。                         |
| **参考文献整理助手** (`reference-organizer`)       | 生成标准化参考文献列表          | 兼容 arXiv / Crossref / 普通网页，输出 GB/T 7714、APA、IEEE 等权威引文格式。       |
| **Markdown 链接检查器** (`md-link-checker`)        | 文档链接的健康度检测            | 多线程并发 + LRU 缓存，批量校验本地与外部链接的可访问性。                          |
| **Draw.io 架构图设计** (`drawio-designer`)         | 自动化系统架构图与流程图绘制    | 内置 AWS / K8s 标准图标与防重叠连线规则，支持 Headless CLI 导出 PNG。              |
| **PPTX 读取器** (`pptx-reader`)                    | 演示文稿内容分析                | 集成 markitdown / LibreOffice / Poppler，支持纯文本提取与逐页高分辨率渲染。        |
| **知识图谱本体管理** (`ontology`)                  | 维护基于本体的图谱记忆结构      | 16 种实体 + 15 种关系，JSONL 事件日志，支持跨技能"计划即图变换"协作。              |
| **杂志编辑信息卡设计** (`editorial-card-designer`) | 响应式高密度数据卡片渲染        | 8 种固定比例预设，Headless Chrome 截图 + Pillow 裁剪输出像素精准的 PNG。           |
| **技术文章大纲规划** (`tech-outline-planner`)      | 内容结构与行文逻辑规划          | 结合 Context-first 与 Process narrative 组合叙事，输出"架构评审级"大纲。           |

### 2. Domain-Driven Design (DDD) Skills

> ⚠️ **WIP**：DDD 主干体系正在持续迭代中，部分结构与规范可能调整。

聚焦领域驱动设计落地的专属技能组，以自研 `ddd-*` Skill 构建覆盖 **5 阶段 / 9 Skills** 的完整建模主干链路（发现 → 战略 → 战术 → 验证 → 规范衔接），并以 Git Submodule 形式收录主流外部 DDD Skill 作为生态参考。

**链接**：[本地文档](./domain-driven-design-skills/README.html)，[GitHub 仓库](https://github.com/ForceInjection/domain-driven-design-skills)

**自研主干 Skill（5 阶段 / 9 Skills）**：

| 阶段     | Skill                     | 核心产出                                                        |
| :------- | :------------------------ | :-------------------------------------------------------------- |
| I 发现   | `ddd-scope`               | 范围收敛：问题陈述、目标 / 非目标、约束、术语种子、风险清单     |
| I 发现   | `ddd-discover`            | 协作式领域发现：事件流、命令 / 事件候选、热点与歧义清单         |
| II 战略  | `ddd-subdomains`          | 子域分类：Core / Supporting / Generic + 核心域声明与所有权建议  |
| II 战略  | `ddd-contexts`            | 限界上下文设计：职责、通用语言词汇表、边界 ADR、所有权          |
| II 战略  | `ddd-context-map`         | 上下文映射：集成模式（ACL / OHS / PL 等）、契约所有权、失败模式 |
| III 战术 | `ddd-aggregates`          | 聚合设计：不变量、实体 / 值对象、事务边界与跨聚合一致性策略     |
| III 战术 | `ddd-domain-interactions` | 领域交互：领域事件目录、领域服务、仓库接口、工厂                |
| IV 验证  | `ddd-model-review`        | 模型质量评估：一致性评分、完整性检查、耦合分析与回溯触发        |
| V 规范   | `ddd-openspec-bridge`     | 规范衔接：将 DDD 战术工件映射为 OpenSpec 结构化规范             |

**核心特色**：

- **非线性闭环**：阶段间支持双向反馈，验证阶段可触发回溯（如不变量表达率 < 60% 回到 `ddd-aggregates`），形成可观测的反馈环。
- **统一接口契约**：每个 SKILL.md 严格规范使用时机、输入、流程、输出、校验清单、回溯触发，确保阶段间工件可衔接。
- **质量可量化**：基于 Eric Evans + Citerus 的 Cargo Shipping DDD Sample 进行端到端盲跑验证，当前加权得分 **85.8%**（B+），回溯触发器测试 **3/3 全通过**。
- **生态参考**：以 Submodule 形式收录 `domain-driven-design`、`clean-ddd-hexagonal`、`ddd-strategic-design`、`arch-ddd`、`cleanddd-skills` 等 11 个外部代表性 DDD Skill，便于横向对比与按需组合。

### 3. CUDA Code Skill

针对 GPU 硬件编程、性能优化和 CUDA 算子开发的垂直领域技能库，以离线知识库 + Agent 技能深度结合的方式，缓解大模型在底层 GPU 编程中的幻觉问题。

**链接**：[本地文档](./cuda-code-skill/README.html)，[GitHub 仓库](https://github.com/ForceInjection/cuda-code-skill)

**技能矩阵**：

| 技能名称                | 角色     | 核心价值                                                                                                        |
| ----------------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| **cuda-knowledge**      | 知识基座 | 本地可搜索的 NVIDIA 官方文档库，覆盖 PTX、cuBLAS、Runtime / Driver、Math API、NCCL 等核心参考资料。             |
| **cuda-samples**        | 范例索引 | 精选 50+ NVIDIA 官方 CUDA Samples，按规约 / 扫描 / GEMM / CUDA Graph 等模式编排，附 GitHub 永久链接与关键片段。 |
| **cuda-optimizer**      | 任务编排 | 主导性能分析与优化循环，协调并调度其他专项技能共同完成复杂优化任务。                                            |
| **cuda-code-generator** | 代码生成 | 生成与修改 `.cu` 代码，内置 RAG 指令强制查阅 `cuda-knowledge` 与 `cuda-samples`，确保 API 与代码模式准确。      |
| **ncu-rep-analyzer**    | 性能分析 | 解析 Nsight Compute 报告，结合 `performance-traps.md` 进行访存合并、Warp 占用等瓶颈深度诊断。                   |
| **kernel-benchmarker**  | 基准测试 | 负责内核编译、正确性验证与基准测试，遇到错误时利用 `debugging-tools.md` 自动修复。                              |

**核心特色**：

- **基于知识增强的代码生成（RAG）**：操作技能被强制要求检索本地知识库与范例索引，避免对复杂 API（cuBLASLt、Tensor Cores、PTX 等）的幻觉调用。
- **文档抓取流水线**：内置 `scrape_cuda_docs.py` 单文件脚本（基于 `uv` + PEP 723 内联依赖），可一键同步 PTX、Runtime、Driver、cuBLAS、Math、NCCL 等最新官方文档。
- **AI IDE 即插即用**：兼容 Claude Code、Trae、Qoder 等主流 AI IDE，可直接将 `skills/` 目录加载为工作上下文。

---

> **提示**：以上各个技能库不仅是代码生成的利器，更是一套被验证过的工程方法论。请点击上方链接深入了解每个技能的具体指令与使用范例。
