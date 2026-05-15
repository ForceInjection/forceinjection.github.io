# CUDA 代码技能库

本项目是一个面向 AI IDE（如 Claude Code、Trae、Qoder 等）的 CUDA 内核开发辅助项目，通过结合抓取自 NVIDIA 官方文档的**深度本地知识库**与**基于 Agent 的代码生成技能**，为底层 GPU 开发者提供准确、高效的自动化代码编写与查阅辅助。

---

## 1. 核心特性

针对大模型在底层 GPU 编程中易产生幻觉的问题，本项目通过离线知识库与 Agent 技能的深度结合，提供了以下三大技术优势：

- **基于知识增强的代码生成 (RAG)**：操作技能被专门指导去搜索本地的 `cuda-knowledge` 技能，以确保对复杂 API（如 cuBLASLt、Tensor Cores、PTX 等）的准确使用，从而避免 AI 产生幻觉。
- **全面的离线文档**：包含大量从 NVIDIA HTML 文档转换而来的、支持本地搜索的 Markdown 文件，涵盖了底层开发中最常用的官方参考资料。
- **文档抓取流水线**：内置了一套完善的文档抓取工具，能够随时同步和更新最新的官方文档内容。

---

## 2. 技能概览和使用

本项目采用多技能单体仓库（Monorepo）的结构进行组织，`skills/` 目录下的各个 Agent 技能不仅可以独立运作，还能相互配合形成一套自动化的性能分析与优化工作流。下面将详细介绍这些技能的作用以及如何在 AI IDE 中进行集成调用。

### 2.1 技能概览

当前已就绪的各项核心技能涵盖了从知识检索、代码生成到性能分析的完整闭环，具体分工如下：

| 技能名称                | 角色     | 描述                                                                                                                     |
| ----------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| **cuda-knowledge**      | 知识基座 | 提供支持搜索的本地文档库（包含来自 NVIDIA 官方文档的 PTX、cuBLAS、Runtime / Driver、Math API、NCCL 等参考资料）。        |
| **cuda-optimizer**      | 任务编排 | 负责主导核心性能分析与优化循环，负责协调并调度其他专项技能共同完成复杂的优化任务。                                       |
| **cuda-code-generator** | 代码生成 | 用于生成和修改 `.cu` 代码文件，内置指令要求其在执行时必须查阅 `cuda-knowledge` 以保证 API 的准确性。                     |
| **ncu-rep-analyzer**    | 性能分析 | 负责解析 NCU（Nsight Compute）性能分析报告，并结合内置的性能陷阱指南（如 `performance-traps.md` ）进行深度的瓶颈诊断。   |
| **kernel-benchmarker**  | 基准测试 | 负责内核代码的编译、正确性验证与基准测试，当遇到编译或运行错误时会利用调试指南（如 `debugging-tools.md` ）进行自动修复。 |

### 2.2 快速开始

无论是在 Claude Code 还是 Trae 中，本项目提供的技能都可以通过简单的目录加载方式快速接入到日常开发工作流中。

大多数 AI IDE 都支持从目录加载技能。我们可以一次性加载整个目录，或者只选择特定的技能。

**对于 Qoder / Trae / Claude Code：**
直接将 `skills/` 目录加载为你的工作上下文，或者通过 IDE 提供的技能管理界面安装它们。

加载完成后，你可以直接在对话中通过自然语言提示词要求 Agent 使用对应的技能，例如：

```text
# 调用代码生成技能并结合本地知识库
"使用 cuda-code-generator，帮我写一个矩阵转置的 CUDA kernel，并在实现前查阅 cuda-knowledge 中的相关文档。"
```

---

## 3. 文档抓取工具

[scrape_cuda_docs.py](nvidia_doc_sync/scrape_cuda_docs.py) 是一个采用了统一的单文件设计的脚本，并且针对不同 API 文档支持灵活的抓取与清理策略。

> [!NOTE]
> 位于 `cuda-knowledge` 中的原始文档是通过自定义的抓取工具生成的。

### 3.1 安装与运行

`scrape_cuda_docs.py` 依赖于 [`uv`](https://docs.astral.sh/uv/) 运行，它是一个包含内联依赖声明（PEP 723）的单文件脚本，无需繁琐的虚拟环境配置。关于如何添加新 API 支持，详细可参阅 [nvidia_doc_sync/README.md](nvidia_doc_sync/README.md) 文件。

```bash
# 如果尚未安装 uv 工具，请先执行安装
curl -LsSf https://astral.sh/uv/install.sh | sh

# 抓取各类 CUDA 官方文档
uv run nvidia_doc_sync/scrape_cuda_docs.py ptx
uv run nvidia_doc_sync/scrape_cuda_docs.py runtime
uv run nvidia_doc_sync/scrape_cuda_docs.py driver
uv run nvidia_doc_sync/scrape_cuda_docs.py cublas
uv run nvidia_doc_sync/scrape_cuda_docs.py math
uv run nvidia_doc_sync/scrape_cuda_docs.py nccl

# 跳过网络下载，仅对缓存的原始文件重新运行清理流程
uv run nvidia_doc_sync/scrape_cuda_docs.py driver --skip-download
```
