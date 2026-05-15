# Domain-Driven Design (DDD) Skill Panorama

> 🌐 中文版本: [Chinese](README.md)

---

> :warning: **Work In Progress (WIP)**: This repository and its in-house backbone are under active construction and continuous iteration. Some structures, documentation, and specifications may change at any time.

This repository centers on self-developed `ddd-*` Skills, providing a domain modeling backbone pipeline for AI Agents (Discovery / Strategic / Tactical / Validation / Specification Bridging). It also incorporates mainstream DDD-related AI Skills from the ecosystem via Git Submodules as reference for comparison and on-demand use.

```bash
# Quick clone (with all submodules)
git clone --recurse-submodules https://github.com/<your-org>/domain-driven-design-skills.git
```

---

## In-House DDD Skills (`ddd-*` Skills)

The core deliverable of this repository is the set of **self-developed `ddd-*` Skills** under the `skills/` directory, forming a domain modeling backbone pipeline for AI Agents. The external submodules under `relative-skills/` serve only as **ecosystem references** for comparison and on-demand use — they do not carry mainline responsibilities.

### Design Motivation & Boundaries

**Problems to solve**:

- Most DDD Skills in the open-source ecosystem are **single-point capabilities** (e.g., only doing event storming, only doing aggregate code generation), lacking a **complete, loopable pipeline** from problem space discovery -> strategic decomposition -> tactical modeling -> model validation.
- Input/output formats across different Skills are not unified, making it difficult for AI Agents to **chain them** into deliverable modeling artifacts.
- The modeling process is inherently **non-linear**, but most Skills don't provide explicit backtrack trigger conditions, making it impossible to locate the upstream stage that needs correction when issues are found later.

**Goals**:

- Provide standardized Skills covering 5 stages (Discovery / Strategic / Tactical / Validation / Specification Bridging), with each Skill producing **structured artifacts** in a single conversation turn.
- Unify the SKILL.md interface contract (When to Use, Input, Process, Output, Validation Checklist, Backtrack Triggers) to ensure cross-stage artifact compatibility.
- Explicitly define **backtrack trigger conditions** (e.g., invariant expression rate < 60% -> return to `ddd-aggregates`) to support bidirectional closed-loop feedback.
- Support **non-sequential entry**: new projects, existing systems, partial deepening, quality audits, and specification generation can all find an appropriate entry Skill.

**Non-goals**:

- **No direct business code generation** — this repository focuses on domain modeling and engineering specification bridging (OpenSpec); concrete code implementation is left to developers or downstream AI tools.
- **No specific tech stack prescribed** (for Java / Kotlin / Python / .NET implementations, use external ecosystem Skills).

### Skill List (5 Stages / 9 Skills)

| Stage           | Skill                     | Summary                                                                                                               | Optional Enhancement (External)               |
| :-------------- | :------------------------ | :-------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------- |
| I Discovery     | `ddd-scope`               | Scope convergence: problem statement, goals/non-goals, constraints, terminology seeds, risk inventory                 | `ddd-strategic-design`, `ddd-planning`        |
| I Discovery     | `ddd-discover`            | Collaborative domain discovery: event flows, command/event candidates, hotspots, ambiguity list                       |                                               |
| II Strategic    | `ddd-subdomains`          | Subdomain classification: Core/Supporting/Generic + core domain declaration & ownership recommendations               | `ddd-context-mapping`, `domain-driven-design` |
| II Strategic    | `ddd-contexts`            | Bounded Context design: responsibilities, Ubiquitous Language glossary, boundary ADRs, ownership                      |                                               |
| II Strategic    | `ddd-context-map`         | Context mapping: integration patterns (ACL/OHS/PL etc.), contract ownership, failure modes                            |                                               |
| III Tactical    | `ddd-aggregates`          | Aggregate design: invariants, entities/value objects, transaction boundaries & cross-aggregate consistency strategies | `domain-driven-design`, `clean-ddd-hexagonal` |
| III Tactical    | `ddd-domain-interactions` | Domain interactions: domain event directory, domain services, repository interfaces, factories                        |                                               |
| IV Validation   | `ddd-model-review`        | Model quality assessment: consistency scoring, completeness checks, coupling analysis & backtrack triggers            | `clean-architecture`                          |
| V Specification | `ddd-openspec-bridge`     | Specification bridging: map DDD tactical artifacts to OpenSpec structured specifications                              | `openspec-assistant`                          |

> **Non-linear process**: Bidirectional feedback is supported between stages. Model validation (Stage IV) can trigger backtracking to earlier stages for correction, ultimately exporting through Stage V to engineering specifications. See Appendix B in [ddd-skill-system-design.en.md](docs/ddd-skill-system-design.en.md) for the detailed dependency graph and backtrack trigger matrix.

![DDD Modeling Workflow Overview](assets/ddd_process_en.png)

### Entry Selection & Invocation

**Choose entry by scenario**:

| Scenario                               | Recommended Entry                    | Description                                                                        |
| :------------------------------------- | :----------------------------------- | :--------------------------------------------------------------------------------- |
| New project, vague requirements        | `ddd-scope` -> `ddd-discover` -> ... | Start from scope convergence, complete all 5 stages                                |
| Requirements clear, direct exploration | `ddd-discover`                       | Scope context already available, skip scope convergence                            |
| Subdomains known, refine boundaries    | `ddd-contexts`                       | Design contexts and Ubiquitous Language based on existing subdomain classification |
| Deep tactical work on single context   | `ddd-aggregates`                     | Context definitions available, focus on aggregates and domain interactions         |
| Existing model needs health check      | `ddd-model-review`                   | Assess consistency, completeness, and coupling of existing modeling artifacts      |
| Ready for development, generate specs  | `ddd-openspec-bridge`                | Convert tactical models to OpenSpec changesets                                     |

**Invocation**: Use `@skill-name` syntax in AI Agent conversations. Artifacts can be directly passed as input to the next stage's Skill:

```text
@ddd-scope        <business problem description>
@ddd-discover     <scope artifacts>
@ddd-subdomains   <discover artifacts>
...
@ddd-model-review <existing modeling artifacts>
```

---

## External Ecosystem Reference

The table below summarizes representative DDD-related Skills from the open-source community, frozen via Git Submodules for **understanding the landscape, comparing differences, and composing on-demand**. They are **not part of this repository's backbone** and are provided for reference.

| Design Layer              | Skill Name                | Submodule Path                               | Source Repository                                                                           | Use Case                                                                                             |
| :------------------------ | :------------------------ | :------------------------------------------- | :------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------- |
| General Tactical Modeling | `domain-driven-design`    | `relative-skills/wondelai-skills`            | [wondelai/skills](https://github.com/wondelai/skills)                                       | General tactical modeling tool focusing on entities, VOs, aggregates, domain services, repositories  |
| Architecture Style Fusion | `clean-ddd-hexagonal`     | `relative-skills/robust-skills`              | [ccheney/robust-skills](https://github.com/ccheney/robust-skills)                           | DDD + Clean Architecture + Hexagonal Architecture fusion with dependency rule decision tree          |
| Strategic Planning        | `ddd-strategic-design`    | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Bounded Contexts, subdomains, Ubiquitous Language, context mapping for strategic design              |
| Strategic Planning        | `ddd-context-mapping`     | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Integration between Bounded Contexts: Anti-Corruption Layer, Open Host Service patterns              |
| Strategic Planning        | `architecture-patterns`   | `relative-skills/antigravity-awesome-skills` | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Comprehensive architecture pattern set covering Clean Architecture, Hexagonal, and DDD               |
| Tech Stack Specialization | `arch-ddd`                | `relative-skills/aiee-team`                  | [ai-enhanced-engineer/aiee-team](https://github.com/ai-enhanced-engineer/aiee-team)         | Python DDD architect guiding domain models, repository patterns, Unit of Work                        |
| Tech Stack Specialization | `ddd-planning`            | `relative-skills/claude-skill-registry`      | [majiayu000/claude-skill-registry](https://github.com/majiayu000/claude-skill-registry)     | Kotlin DDD planner supporting Event Storming and Kotlin code generation                              |
| Platform-Specific         | `cleanddd-skills`         | `relative-skills/cleanddd-skills`            | [netcorepal/cleanddd-skills](https://github.com/netcorepal/cleanddd-skills)                 | Clean DDD four-stage suite: requirements analysis -> modeling -> project init -> code implementation |
| Platform-Specific         | `claude-flow`             | `relative-skills/agentic-flow`               | [ruvnet/agentic-flow](https://github.com/ruvnet/agentic-flow)                               | Claude Flow kernel using DDD to build modular AI agent systems                                       |
| Platform-Specific         | `Solon AI Skills`         | `relative-skills/solon-ai`                   | [opensolon/solon-ai](https://github.com/opensolon/solon-ai)                                 | Solon AI framework treating Skills as autonomous semantic contexts, inspired by DDD                  |
| Domain-Specific           | `microservices-architect` | `relative-skills/jeffallan-claude-skills`    | [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills)                       | Microservices architect using DDD Bounded Contexts to guide service decomposition                    |

> Usage: After pulling via Git Submodules, invoke each repository's Skills according to their native conventions (typically `@skill-name`).

**Selection Guide**:

| If you need...                                                         | Recommended Skill                                                      |
| :--------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| Help writing DDD-style code                                            | **General Tactical Modeling** (`domain-driven-design`)                 |
| Assessing or refactoring existing code for DDD compliance              | **General Tactical Modeling** (`domain-driven-design`)                 |
| Designing a new, architecturally clean system                          | **Architecture Style Fusion** (`clean-ddd-hexagonal`)                  |
| Planning or organizing complex business module/microservice boundaries | **Strategic Planning** (`ddd-strategic-design`, `ddd-context-mapping`) |
| Project has a specific tech stack preference                           | **Tech Stack Specialization** (`arch-ddd`, `ddd-planning`)             |
| Finding a standardized, structured DDD process for the team            | **Platform-Specific** (`cleanddd-skills`)                              |
| Building complex AI agent systems                                      | **Platform-Specific** (`claude-flow`, `Solon AI Skills`)               |

---

## Quality Validation

To perform **objective, repeatable quality assessment** of the in-house `ddd-*` Skill backbone, the repository maintains an independent `validation-cases/` directory containing end-to-end blind-run validation cases and general validation methodology.

- [validation-cases/README.en.md](validation-cases/README.en.md) — **Validation Method Overview**: 6-step process (fuzzy input -> blind-run 8 Skills -> ground truth extraction -> benchmark scoring -> backtrack injection test -> summary report), blind-run constraints, injection matrix, reusable steps, and known limitations.
- [validation-cases/cargo-validation/](validation-cases/cargo-validation/) — **Cargo Validation Case**: Using Eric Evans + Citerus' Cargo Shipping DDD Sample (submodule `validation-cases/cargo-shipping`) as ground truth reference, running the full 8-Skill pipeline. Current weighted score **85.8%** (B+ Good), backtrack trigger tests **3/3 all passed**; see [REPORT.md](validation-cases/cargo-validation/REPORT.md) (in Chinese) for full conclusions.

Validation results have been fed back into backbone SKILL iterations (e.g., `ddd-aggregates`' "foreign reference re-examination + Specification pattern," `ddd-model-review`'s "industry benchmarking dimension," `ddd-contexts`' "intermediate concept ADR"), forming an observable feedback loop.

---

## Directory Structure

```text
skills/
├── ddd-scope/                  # Stage I: Scope Convergence
├── ddd-discover/               # Stage I: Domain Discovery
├── ddd-subdomains/             # Stage II: Subdomain Classification
├── ddd-contexts/               # Stage II: Bounded Contexts + Ubiquitous Language
├── ddd-context-map/            # Stage II: Context Mapping
├── ddd-aggregates/             # Stage III: Aggregate Design
├── ddd-domain-interactions/    # Stage III: Domain Interactions
├── ddd-model-review/           # Stage IV: Model Validation
└── ddd-openspec-bridge/        # Stage V: Specification Bridging (OpenSpec)

validation-cases/
├── README.md                   # Validation Method Overview (6-step process)
├── cargo-shipping/             # Cargo Shipping DDD Sample (submodule, ground truth source)
└── cargo-validation/           # Cargo Validation Case (blind outputs + ground truth + scoring + backtrack injection + REPORT)

relative-skills/
├── wondelai-skills/            # domain-driven-design
├── robust-skills/              # clean-ddd-hexagonal
├── antigravity-awesome-skills/ # ddd-strategic-design, ddd-context-mapping, architecture-patterns
├── aiee-team/                  # arch-ddd
├── claude-skill-registry/      # ddd-planning (general DDD skill registry; only ddd-planning is curated here)
├── cleanddd-skills/            # cleanddd-skills
├── agentic-flow/               # claude-flow
├── solon-ai/                   # Solon AI Skills
└── jeffallan-claude-skills/    # microservices-architect
```

---

## Related Documents

- [ddd-skill-system-design.en.md](docs/ddd-skill-system-design.en.md) — In-house backbone system design document (5-stage model, dependency graph, feedback loop matrix)
- [ddd-pipeline-article.en.md](docs/ddd-pipeline-article.en.md) — Narrative introduction to the skill pipeline (first-gen 4-stage / 8-Skill design + Cargo validation key findings)
- [ddd-openspec-mapping.en.md](docs/ddd-openspec-mapping.en.md) — Mapping Guide: Standard definitions for converting DDD tactical artifacts to OpenSpec specifications
- [ddd-skills-report.en.md](docs/ddd-skills-report.en.md) — DDD skills research report (with references and improvement backlog)
- [validation-cases/README.en.md](validation-cases/README.en.md) — Validation Method Overview (6-step blind-run process, injection matrix, reuse guide)
- [validation-cases/cargo-validation/REPORT.md](validation-cases/cargo-validation/REPORT.md) — Cargo Shipping validation report (current score 85.8%) (in Chinese)

---

## Submodule Management

If you've cloned but haven't pulled submodules:

```bash
git submodule update --init --recursive
```

Update all submodules to latest:

```bash
git submodule update --remote
```

Update a specific submodule:

```bash
cd relative-skills/<submodule-name>
git pull origin main
cd ../..
git add relative-skills/<submodule-name>
git commit -m "update: bump <submodule-name> to latest"
```
