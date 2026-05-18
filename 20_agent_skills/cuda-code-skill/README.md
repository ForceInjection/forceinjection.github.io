# CUDA 代码技能库

本项目是一个面向 AI IDE（如 Claude Code、Trae、Qoder 等）的 CUDA 内核开发辅助项目，通过结合抓取自 NVIDIA 官方文档的**深度本地知识库**、**官方代码范例索引**与**基于 Agent 的代码生成技能**，为底层 GPU 开发者提供准确、高效的自动化代码编写与查阅辅助。

---

## 1. 核心特性

针对大模型在底层 GPU 编程中易产生幻觉的问题，本项目通过离线知识库与 Agent 技能的深度结合，提供了以下三大技术优势：

- **基于知识增强的代码生成 (RAG)**：操作技能被专门指导去搜索本地的 `cuda-knowledge`（API 文档）和 `cuda-samples`（代码范例）技能，以确保对复杂 API（如 cuBLASLt、Tensor Cores、PTX 等）的准确使用和代码模式参考，从而避免 AI 产生幻觉。
- **全面的离线文档**：包含大量从 NVIDIA HTML 文档转换而来的、支持本地搜索的 Markdown 文件，涵盖了底层开发中最常用的官方参考资料。
- **文档抓取流水线**：内置了一套完善的文档抓取工具，能够随时同步和更新最新的官方文档内容。

---

## 2. 技能概览和使用

本项目采用多技能单体仓库（Monorepo）的结构进行组织，`skills/` 目录下的各个 Agent 技能不仅可以独立运作，还能相互配合形成一套自动化的性能分析与优化工作流。

### 2.1 技能概览

当前已就绪的各项核心技能涵盖了从知识检索、范例匹配、代码生成到性能分析的完整闭环，具体分工如下：

| 技能名称                | 角色     | 描述                                                                                                                             |
| ----------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **cuda-knowledge**      | 知识基座 | 提供支持搜索的本地文档库（包含来自 NVIDIA 官方文档的 PTX、cuBLAS、Runtime / Driver、Math API、NCCL 等参考资料）。                |
| **cuda-samples**        | 范例索引 | 精选 50+ NVIDIA 官方 CUDA Samples，按模式（规约/扫描/GEMM/CUDA Graph 等）编排，含 GitHub 永久链接和关键代码片段。                |
| **cuda-optimizer**      | 任务编排 | 负责主导核心性能分析与优化循环，负责协调并调度其他专项技能共同完成复杂的优化任务。                                               |
| **cuda-code-generator** | 代码生成 | 用于生成和修改 `.cu` 代码文件，内置指令要求其在执行时必须查阅 `cuda-knowledge` 和 `cuda-samples` 以保证 API 和代码模式的准确性。 |
| **ncu-rep-analyzer**    | 性能分析 | 负责解析 NCU（Nsight Compute）性能分析报告，并结合内置的性能陷阱指南（如 `performance-traps.md`）进行深度的瓶颈诊断。            |
| **kernel-benchmarker**  | 基准测试 | 负责内核代码的编译、正确性验证与基准测试，当遇到编译或运行错误时会利用调试指南（如 `debugging-tools.md`）进行自动修复。          |

### 2.2 快速开始

将 `skills/` 目录加载到支持的 AI IDE（Claude Code、Trae、Qoder 等）中即可启用所有技能。

加载完成后，在对话中通过自然语言即可调用对应技能，例如：

```text
# 查阅官方范例寻找代码模式
"使用 cuda-samples，帮我找一个 shared memory 矩阵转置的 CUDA 代码范例。"

# 调用代码生成技能并结合本地知识库与范例
"使用 cuda-code-generator，帮我写一个矩阵转置的 CUDA kernel，并在实现前查阅 cuda-knowledge 和 cuda-samples 中的相关文档与范例。"
```

也可以直接在命令行中检索和运行示例：

```bash
# 查看官方 vectorAdd 范例
cat cuda-samples/cpp/0_Introduction/vectorAdd/vectorAdd.cu

# 运行 benchmark 示例
python3 skills/kernel-benchmarker/scripts/benchmark.py examples/vectorAdd/solution.cu --N=1000000
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

---

## 4. 校验与测试

本项目内置了多层次的校验与测试工具。

### 4.1 静态校验

```bash
# 校验各技能间的接口一致性（子技能引用、瓶颈类型对齐、路径解析等）
python3 scripts/check_skills.py

# 校验文档中的文件数/大小与磁盘实际内容一致
python3 scripts/check_counts.py

# 校验 cuda-samples 参考文件中的路径在子模块中均存在
uv run scripts/check_links.py
```

> [!NOTE]
> `check_links.py` 依赖 `cuda-samples` 子模块。首次使用前需执行：
>
> ```bash
> git submodule update --init
> ```

### 4.2 Kernel 基准测试

对 CUDA kernel（`extern "C" __global__ void solve(...)`）进行编译、执行和性能测试，支持与 PyTorch 参考实现对比验证。示例文件在 `examples/vectorAdd/`：

```bash
# 仅基准测试（无参考对比）
python3 skills/kernel-benchmarker/scripts/benchmark.py examples/vectorAdd/solution.cu \
    --N=1000000 --repeat=20

# 编译 + 正确性验证 + 性能对比
python3 skills/kernel-benchmarker/scripts/benchmark.py examples/vectorAdd/solution.cu \
    --ref=examples/vectorAdd/ref.py --N=1000000 --repeat=20
```

kernel 通过 `nvcc -ptx` 编译为 PTX，经由 CUDA Driver API (`cuLaunchKernel`) 在同一进程中加载执行。PTX 文件自动缓存，首次后的运行跳过编译。

### 4.3 NCU Profiling

通过 `ncu_profile.py` 构建自包含 profiling 可执行文件（无子进程，NCU 不会断连）：

```bash
# 构建 profiling 专用可执行文件
python3 skills/kernel-benchmarker/scripts/ncu_profile.py examples/vectorAdd/solution.cu \
    --N=1000000 --build-only

# 默认模式（--set launch），所有环境可用（容器/云主机等无需 PMU 权限）
ncu --kernel-name solve --launch-skip 10 --launch-count 1 \
    --set launch -o report -f ./examples/vectorAdd/solution_bench --N=1000000

# 详细性能指标模式（需宿主机 PMU 权限: perf_event_paranoid=0）
# ncu --kernel-name solve ... --set full ...
```

> 样例报告见 [`examples/ncu-profile/`](examples/ncu-profile/)，含 `.ncu-rep` 二进制文件和文本导出。

### 4.4 查阅官方代码范例

通过 `cuda-samples` 技能索引查找 NVIDIA 官方 CUDA 代码范例：

```bash
# 按模式搜索
grep -r "reduction\|GEMM\|CUDA Graph" skills/cuda-samples/SKILL.md

# 查看完整源码（需先 git submodule update --init）
cat cuda-samples/cpp/0_Introduction/vectorAdd/vectorAdd.cu
```
