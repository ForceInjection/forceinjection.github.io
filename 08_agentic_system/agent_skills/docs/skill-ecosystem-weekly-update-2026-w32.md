# AI 原力注入 Skill 项目一周更新综述（2026 年第 33 周）

---

## 一、相关项目简介

本博主维护的 ForceInjection 组织下，与 Agent Skill 相关的仓库共有四个，定位互补，共同构成一个从"通用认知技能"到"领域方法论"再到"工程实践"的完整技能生态。

### 1.1 [awesome-skills](https://github.com/ForceInjection/awesome-skills)：通用认知技能库

技能生态的核心资产，收录 **17 个独立 Agent Skill**，覆盖四大场景：

- **代码阅读与架构分析**：`code-reader`（三重智能体协作 + 闭卷考试式验证循环的深度代码阅读）、`project-analyzer`（第三方仓库逆向工程与静态分析，产出 7 章节标准报告）
- **文档处理与评审**：`doc-reviewer`（多维度文档评审）、`pptx-reader`（PPT 解析）等
- **内容创作与设计**：`editorial-card-designer`（公众号排版设计）等
- **规范驱动开发**：与 OpenSpec 等规范协作的技能

仓库同时沉淀了技能开发的方法论资产：核心设计理念、最佳实践、深度解析案例（google skill pattern、gstack、superpowers 等）以及技能单元测试框架。

### 1.2 [domain-driven-design-skills](https://github.com/ForceInjection/domain-driven-design-skills)：领域建模技能链

以自研 `ddd-*` Skill 为核心，提供面向 AI Agent 的**领域建模主干链路**：发现 → 战略 → 战术 → 验证 → 规范衔接五个阶段。仓库配套了**验证案例集**（validation-cases）——用货运、保险等真实业务案例逐条验证流水线各阶段的触发逻辑，构成技能的回归测试体系。外部生态的 DDD Skill 以调研记录形式收录，仅作对比参考，不承担主流程职责。

### 1.3 [OpenSpec-practise](https://github.com/ForceInjection/OpenSpec-practise)：规范驱动开发实践

OpenSpec 是 Spec-Driven Development（SDD）的开放工具标准——以可审查的规范文件（spec）驱动 AI 编程全流程：`explore` → `propose` → `apply` → `sync` → `archive`。本项目通过完整实战案例演示 OpenSpec 在 AI 辅助编程中的应用，提供系统的文档分析、使用手册与多语言示例，并维护一套 Claude Code 斜杠命令（`/opsx:*`）作为工作流入口。

### 1.4 [ai-native-devops](https://github.com/ForceInjection/ai-native-devops)：AI 原生工程范式

从三个层次递进阐述人机协同的工程变革：**Vibe Coding**（个人开发模式）→ **AI Native DevOps**（团队研发流程）→ **AI Native Architecture**（应用架构）。核心立场：最终决策、风险承担、上线责任仍由人工 Owner 承担。仓库包含理论文档与真实案例工作区（如 CloudPilot）。

---

## 二、上周更新总览

四个仓库本周同时更新，围绕技能生态的可持续性展开：质量验证、跨语言复用、随上游规范演进。更新内容逐项解读如下。

---

## 三、awesome-skills：国际化与质量治理

本周最大的结构性变更发生在技能库基础设施层面。

**中英双语化。** 为核心技能补充英文版本（`SKILL-en.md`），覆盖 `dir-organizer`、`doc-reviewer`（含全部评审规则参考文件）、`editorial-card-designer` 等，共 24 个文件；配套新增英文 README、`AGENTS-en.md`、深度解析文档的英文翻译与独立英文技能评估指南。`SKILL.md` 与 `SKILL-en.md` 并存，按使用者语言环境选择，技能库由此覆盖英文使用者。

**质量治理流程化。** `CLAUDE.md` 新增两项流程规范：**new-skill checklist**（新增技能的准入检查）与 **eval framework**（技能质量评估框架）；README 重构为表格化总览。技能库的管理由此从个人维护转向流程化治理——新技能有准入检查，存量技能有评估机制。

**技能本体更新。** `editorial-card-designer` 合并上游 content-fit 方法论，排版技能从骨架模板升级为内容适配方法；`pptx-reader` 同步上游 soffice 与缩略图修复；推荐资源新增 `ai-delivery-spec`。

> 更新重心从"扩充技能数量"转向"完善技能基础设施"——双语、评估、准入检查、表格化导航。技能生态的瓶颈已从内容供给转向可信任性、可发现性与可用性。

---

## 四、domain-driven-design-skills：验证覆盖补全

DDD 技能库本周未新增功能，重点在于将分析流水线的验证覆盖补全：

- **回溯分支全覆盖**：补齐此前未测试的 backtrack 触发逻辑（F4/F5），5 条路径全部通过——该分支处理流水线在计划外分岔时的回退行为，此前处于验证盲区
- **无参照物场景**：新增保险验证的 no-reference 案例——当代码库中不存在可参照实现时，验证流水线的自证逻辑
- **阶段覆盖收尾**：通过保险案例 09 覆盖 Stage V（规范衔接阶段），关闭验证 backlog——至此流水线各阶段均有真实案例验证

**依赖策略收敛。** 移除外部 relative-skills 子模块（约 300 个文件清理），外部生态引用改为纯文本保留。该变更明确了依赖定位：**技能仓库的依赖是"可读的引用"而非"可挂载的子模块"**——技能消费的是内容而非二进制产物，文本引用即可满足，子模块的拉取、更新、冲突管理成本可以省略。

> 验证案例集本质上是技能的回归测试套件。DDD 仓库的选择是优先完备验证覆盖，而非同步推进新功能。

---

## 五、OpenSpec-practise：随上游规范演进

OpenSpec 为快速演进的开放标准，实践仓库需持续跟随上游。本周核心变更：

**升级至 OpenSpec v1.7.0。** 涉及 `.claude/commands/opsx/` 下整套斜杠命令（`apply`、`archive`、`explore`、`propose`、`sync`、`update`，共 26 个文件）。升级的意义在于命令行为与最新 OpenSpec CLI 对齐，避免实践文档与工具实际行为因版本漂移而不一致。

**配套实践文档。** 新增 v1.7.0 工作流实践文档，README 升级为双语学习路径。文档在此承担双重角色：对使用者是操作手册，对维护者是回归测试——批量命令变更后，文档描述的流程必须依然成立，这本身就是一次验证。

> 以"版本锁定 + 实践文档"保障规范升级的收益落地、风险可控。

---

## 六、ai-native-devops：范式综合与案例沉淀

ai-native-devops 本周由课程仓库扩展为"范式 + 案例"结构：

- **SDD 范式综合文章**：将 Spec-Driven Development 从工具层面提升至范式层面——规范先行作为 AI 编程时代的协作方式，开发者意图如何通过规范文件转化为 AI 的可执行约束
- **CloudPilot openspec workspace 案例**：以真实项目展示 OpenSpec 工作区的落地形态——规范目录组织、命令流程串联、产出沉淀方式

两项更新与 OpenSpec-practise 的 v1.7.0 升级形成闭环：规范升级 → 范式总结 → 真实案例。技能生态从"工具"走向"方法论 + 证据"。

---

## 七、三个值得注意的取舍

**双语维护成本 vs 受众扩大。** 每个技能的每个参考文件均需维护中英两个版本，内容变更时需双写，这是最重的长期成本；收益是技能库覆盖英文使用者，可被国际社区检索、使用与反馈。

**验证完备性 vs 交付节奏。** DDD 技能本周将维护预算全部投入验证而非新功能。验证案例是技能质量的回归保障，但每补一条路径都消耗维护时间。选择"先完备后新功能"，反映技能质量的信任度优先于数量增长。

**子模块 vs 文本引用。** 移除子模块是一次依赖收束：子模块是版本管理层的耦合（拉取、更新、冲突），文本引用是内容层的耦合（读取、引用）。对技能仓库而言，后者是正确的耦合强度——将依赖从"必须同步的代码"调整为"可按需引用的知识"。

---

## 八、总结与观察点

四个仓库的更新共同指向一个判断：**技能生态的成熟标志不是技能数量的增长，而是围绕技能的工程基础设施成型**——验证案例集（DDD）、评估框架与准入检查（awesome-skills）、版本锁定与双语维护（OpenSpec）、范式总结与案例沉淀（ai-native-devops）。当技能可被验证、评估、国际化、版本化时，它才成为可交付的软件资产。

**下一周的观察点**：awesome-skills 的 eval framework 是否会产出实际技能评估报告；DDD 技能移除子模块后是否演化出独立技能仓库；OpenSpec v1.7.0 的实践文档是否会反向贡献给上游社区。

---

## 参考

- [awesome-skills](https://github.com/ForceInjection/awesome-skills) — Agent Skill 合集
- [domain-driven-design-skills](https://github.com/ForceInjection/domain-driven-design-skills) — DDD 领域建模技能链
- [OpenSpec-practise](https://github.com/ForceInjection/OpenSpec-practise) — OpenSpec 规范驱动开发实践
- [ai-native-devops](https://github.com/ForceInjection/ai-native-devops) — AI 原生 DevOps 范式
