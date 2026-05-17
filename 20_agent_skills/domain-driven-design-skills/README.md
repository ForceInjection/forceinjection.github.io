# 领域驱动设计 (DDD) Skill 全景图

> 🌐 English version: [English](README.en.md)

---

> ⚠️ **Work In Progress (WIP)**：本仓库及其自研体系主干正处于积极建设与持续迭代中，部分结构、文档与规范可能随时调整。

本仓库以自研的 `ddd-*` Skill 为核心，提供一套面向 AI Agent 的领域建模主干链路（发现 / 战略 / 战术 / 验证 / 规范衔接）；同时以 Git Submodule 形式收录主流 DDD 相关 AI Skill，作为生态参考便于对比与按需引用。

```bash
# 快速克隆（含所有子模块）
git clone --recurse-submodules https://github.com/<your-org>/domain-driven-design-skills.git
```

---

## 本仓库 DDD Skills（`ddd-*` Skill）

本仓库的核心交付物是 `skills/` 目录下的一组 **自研 `ddd-*` Skill**，它们构成一套面向 AI Agent 的领域建模主干链路。`relative-skills/` 下的外部子模块仅作为**生态参考**，用于对比与按需引用，不承担主流程职责。

### 设计动机与边界

**要解决的问题**：

- 开源生态中的 DDD Skill 大多是**单点能力**（如只做事件风暴、只做聚合代码生成），缺乏从问题空间发现 → 战略分解 → 战术建模 → 模型验证的**完整、可回环链路**。
- 不同 Skill 的输入/输出格式不统一，AI Agent 难以把它们**串联**成可交付的建模工件。
- 建模过程本质是**非线性**的，但多数 Skill 不提供明确的回溯触发条件，后期发现问题时无法定位到该修正的上游环节。

**目标**：

- 提供覆盖 5 阶段（发现 / 战略 / 战术 / 验证 / 规范衔接）的标准化 Skill，每个 Skill 在一次对话轮次内产出**结构化工件**。
- 统一 SKILL.md 接口契约（使用时机、输入、流程、输出、校验清单、回溯触发），保证阶段间工件可衔接。
- 显式定义**触发回溯条件**（如不变量表达率 < 60% 回到 `ddd-aggregates`），支持双向闭环反馈。
- 支持**非顺序入口**：全新项目、已有系统、局部深化、质量审查、规范生成都能找到合适的切入 Skill。

**非目标**：

- **不直接生成业务代码**，本仓库聚焦于领域建模与工程规范的衔接（OpenSpec），具体代码实现由开发者或下游 AI 工具完成。
- **不规定特定技术栈**（Java / Kotlin / Python / .NET 相关实现请使用外部生态 Skill）。

### Skill 清单（5 阶段 / 9 Skills）

| 阶段     | Skill                     | 简介                                                        | 可选增强（外部）                              |
| :------- | :------------------------ | :---------------------------------------------------------- | :-------------------------------------------- |
| I 发现   | `ddd-scope`               | 范围收敛：问题陈述、目标/非目标、约束、术语种子、风险清单   | `ddd-strategic-design`, `ddd-planning`        |
| I 发现   | `ddd-discover`            | 协作式领域发现：事件流、命令/事件候选、热点与歧义清单       |                                               |
| II 战略  | `ddd-subdomains`          | 子域分类：Core/Supporting/Generic + 核心域声明与所有权建议  | `ddd-context-mapping`, `domain-driven-design` |
| II 战略  | `ddd-contexts`            | 限界上下文设计：职责、通用语言词汇表、边界 ADR、所有权      |                                               |
| II 战略  | `ddd-context-map`         | 上下文映射：集成模式（ACL/OHS/PL 等）、契约所有权、失败模式 |                                               |
| III 战术 | `ddd-aggregates`          | 聚合设计：不变量、实体/值对象、事务边界与跨聚合一致性策略   | `domain-driven-design`, `clean-ddd-hexagonal` |
| III 战术 | `ddd-domain-interactions` | 领域交互：领域事件目录、领域服务、仓库接口、工厂            |                                               |
| IV 验证  | `ddd-model-review`        | 模型质量评估：一致性评分、完整性检查、耦合分析与回溯触发    | `clean-architecture`                          |
| V 规范   | `ddd-openspec-bridge`     | 规范衔接：将 DDD 战术工件映射为 OpenSpec 结构化规范         | `openspec-assistant`                          |

> **非线性流程**：阶段之间支持双向反馈，模型验证（阶段 IV）可触发回溯至前置阶段进行修正，最终通过阶段 V 导出为工程规范。详细的依赖图与触发回溯矩阵见 [ddd-skill-system-design.md](docs/ddd-skill-system-design.md) 附录 B。

![DDD 建模流程全景图](assets/ddd_process.png)

### 入口选择与调用方式

**按场景选择入口**：

| 场景                 | 推荐入口                         | 说明                                     |
| :------------------- | :------------------------------- | :--------------------------------------- |
| 全新项目、需求模糊   | `ddd-scope` → `ddd-discover` → … | 从范围收敛开始，完整走完 5 阶段          |
| 已明确需求，直接探索 | `ddd-discover`                   | 已有 scope 上下文，跳过范围收敛          |
| 子域已知，需细化边界 | `ddd-contexts`                   | 基于既有子域分类设计上下文与通用语言     |
| 单个上下文深化战术   | `ddd-aggregates`                 | 已有上下文定义，聚焦聚合与领域交互       |
| 已有模型需要体检     | `ddd-model-review`               | 对现有建模工件做一致性、完整性与耦合评估 |
| 准备开发，生成规范   | `ddd-openspec-bridge`            | 将战术模型转化为 OpenSpec 变更集         |

**调用方式**：在 AI Agent 对话中使用 `@skill-name` 语法，工件可作为下一阶段 Skill 的输入直接传递：

```text
@ddd-scope        <业务问题描述>
@ddd-discover     <scope 工件>
@ddd-subdomains   <discover 工件>
...
@ddd-model-review <已有建模工件>
```

---

## 外部生态参考

下表汇总了开源社区中具有代表性的 DDD 相关 Skill，以 Git Submodule 形式冻结引用，便于**了解现状、对比差异、按需组合**。它们**不是本仓库主干的一部分**，供参考使用。

| 设计层级      | Skill 名称                | 子模块路径                                   | 源仓库                                                                                      | 适用场景                                                       |
| :------------ | :------------------------ | :------------------------------------------- | :------------------------------------------------------------------------------------------ | :------------------------------------------------------------- |
| 通用战术建模  | `domain-driven-design`    | `relative-skills/wondelai-skills`            | [wondelai/skills](https://github.com/wondelai/skills)                                       | 通用战术建模工具，聚焦实体、值对象、聚合、领域服务、仓库等模式 |
| 架构风格融合  | `clean-ddd-hexagonal`     | `relative-skills/robust-skills`              | [ccheney/robust-skills](https://github.com/ccheney/robust-skills)                           | DDD + 整洁架构 + 六边形架构融合，提供依赖规则决策树            |
| 战略规划设计  | `ddd-strategic-design`    | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | 限界上下文、子域、通用语言、上下文映射等战略设计               |
| 战略规划设计  | `ddd-context-mapping`     | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | 限界上下文之间的集成，防腐层、开放主机服务等模式               |
| 战略规划设计  | `architecture-patterns`   | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | 涵盖整洁架构、六边形架构和 DDD 的综合架构模式集                |
| 技术栈专精    | `arch-ddd`                | `relative-skills/aiee-team`                  | [ai-enhanced-engineer/aiee-team](https://github.com/ai-enhanced-engineer/aiee-team)         | Python DDD 架构师，指导领域模型、仓库模式、工作单元等          |
| 技术栈专精    | `ddd-planning`            | `relative-skills/claude-skill-registry`      | [majiayu000/claude-skill-registry](https://github.com/majiayu000/claude-skill-registry)     | Kotlin DDD 规划器，支持 Event Storming 与 Kotlin 代码生成      |
| 特定框架/平台 | `cleanddd-skills`         | `relative-skills/cleanddd-skills`            | [netcorepal/cleanddd-skills](https://github.com/netcorepal/cleanddd-skills)                 | Clean DDD 四阶段套件：需求分析 → 建模 → 项目初始化 → 代码实现  |
| 特定框架/平台 | `claude-flow`             | `relative-skills/agentic-flow`               | [ruvnet/agentic-flow](https://github.com/ruvnet/agentic-flow)                               | Claude Flow 内核，利用 DDD 构建模块化 AI 代理系统              |
| 特定框架/平台 | `Solon AI Skills`         | `relative-skills/solon-ai`                   | [opensolon/solon-ai](https://github.com/opensolon/solon-ai)                                 | Solon AI 框架，将 Skill 视为自治语义上下文，借鉴 DDD 思想      |
| 重点场景/应用 | `microservices-architect` | `relative-skills/jeffallan-claude-skills`    | [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills)                       | 微服务架构师，运用 DDD 限界上下文指导服务拆分                  |

> 使用方式：通过 Git Submodule 拉取到本地后，可在各自仓库中按其原生约定调用（通常为 `@skill-name`）。

**选型建议**：

| 如果你需要……                            | 推荐 Skill                                                     |
| :-------------------------------------- | :------------------------------------------------------------- |
| 辅助编写符合 DDD 风格的代码             | **通用战术建模类** (`domain-driven-design`)                    |
| 评估或重构现有代码的 DDD 合规性         | **通用战术建模类** (`domain-driven-design`)                    |
| 设计一个新的、架构清晰的系统            | **架构风格融合类** (`clean-ddd-hexagonal`)                     |
| 规划或梳理复杂业务的模块与微服务边界    | **战略规划类** (`ddd-strategic-design`, `ddd-context-mapping`) |
| 项目有明确的技术栈偏好                  | **技术栈专精类** (`arch-ddd`, `ddd-planning`)                  |
| 为团队寻找规范化、结构化的 DDD 实施流程 | **特定框架/平台类** (`cleanddd-skills`)                        |
| 构建复杂的 AI 代理系统                  | **特定框架/平台类** (`claude-flow`, `Solon AI Skills`)         |

---

## 质量验证

为了对自研 `ddd-*` Skill 主干做 **客观、可重复的质量评估**，仓库维护一个独立的 `validation-cases/` 目录，收录端到端的盲跑验证案例与通用验证方法。

- [validation-cases/README.md](validation-cases/README.md) —— **验证方法总纲**：6 步流程（模糊输入 → 盲跑 8 Skill → 真值抽取 → 对标评分 → 回溯注入测试 → 汇总报告）、盲跑约束、注入矩阵、可复用步骤与已知局限。
- [validation-cases/cargo-validation/](validation-cases/cargo-validation/) —— **Cargo 验证案例**：以 Eric Evans + Citerus 的 Cargo Shipping DDD Sample（子模块 `validation-cases/cargo-shipping`）为真值参照，完整运行 8 Skill 流水线。当前加权得分 **85.8 %**（B+ 良好），回溯触发器测试 **3/3 全通过**；完整结论见 [REPORT.md](validation-cases/cargo-validation/REPORT.md)。

验证结果已反哺到主干 SKILL 的迭代（例如 `ddd-aggregates` 的"外部引用再审视 + Specification 模式"、`ddd-model-review` 的"行业对标维度"、`ddd-contexts` 的"中间概念 ADR"），形成可观测的反馈闭环。

---

## 目录结构

```text
skills/
├── ddd-scope/                  # 阶段 I：范围收敛
├── ddd-discover/               # 阶段 I：领域发现
├── ddd-subdomains/             # 阶段 II：子域分类
├── ddd-contexts/               # 阶段 II：限界上下文 + 通用语言
├── ddd-context-map/            # 阶段 II：上下文映射
├── ddd-aggregates/             # 阶段 III：聚合设计
├── ddd-domain-interactions/    # 阶段 III：领域交互
├── ddd-model-review/           # 阶段 IV：模型验证
└── ddd-openspec-bridge/        # 阶段 V：规范衔接（OpenSpec）

validation-cases/
├── README.md                   # 验证方法总纲（6 步流程）
├── cargo-shipping/             # Cargo Shipping DDD Sample（子模块，真值来源）
└── cargo-validation/           # Cargo 验证案例（盲产出 + 真值 + 评分 + 回溯注入 + REPORT）

relative-skills/
├── wondelai-skills/            # domain-driven-design
├── robust-skills/              # clean-ddd-hexagonal
├── antigravity-awesome-skills/ # ddd-strategic-design, ddd-context-mapping, architecture-patterns
├── aiee-team/                  # arch-ddd
├── claude-skill-registry/      # ddd-planning（通用 DDD Skill 注册表，本表仅收录 ddd-planning）
├── cleanddd-skills/            # cleanddd-skills
├── agentic-flow/               # claude-flow
├── solon-ai/                   # Solon AI Skills
└── jeffallan-claude-skills/    # microservices-architect
```

---

## 相关文档

- [ddd-skill-system-design.md](docs/ddd-skill-system-design.md) — 领域驱动设计自研体系主干设计文档（5 阶段模型、依赖图、反馈环矩阵）
- [ddd-pipeline-article.md](docs/ddd-pipeline-article.md) — 技能流水线叙述性介绍（4 阶段 / 8 Skill 首版设计 + Cargo 验证关键结论）
- [ddd-openspec-mapping.md](docs/ddd-openspec-mapping.md) — 映射指南：DDD 战术工件向 OpenSpec 规格转化的标准定义
- [ddd-skills-report.md](docs/ddd-skills-report.md) — 领域驱动设计技能调研报告（含引用与改进 Backlog）
- [validation-cases/README.md](validation-cases/README.md) — 验证方法总纲（6 步盲跑流程、注入矩阵、复用指南）
- [validation-cases/cargo-validation/REPORT.md](validation-cases/cargo-validation/REPORT.md) — Cargo Shipping 验证报告（当前得分 85.8 %）

---

## 子模块管理

如果已克隆但未拉取子模块：

```bash
git submodule update --init --recursive
```

更新所有子模块到最新版本：

```bash
git submodule update --remote
```

更新指定子模块：

```bash
cd relative-skills/<submodule-name>
git pull origin main
cd ../..
git add relative-skills/<submodule-name>
git commit -m "update: bump <submodule-name> to latest"
```
