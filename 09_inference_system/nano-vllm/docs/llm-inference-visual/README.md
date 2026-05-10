# nano-vllm 实战课程

> 从源码走读 LLM 推理引擎：调度、KV cache、注意力、Tensor Parallel、CUDA Graph

## 1. 课程概述

本课程只需要具备 Python 编程基础。Transformer 与注意力机制等 LLM 原理知识将在课中逐步引入，无需提前掌握。

> 更多关于大模型相关内容请参考：[AI Fundermentals](https://github.com/ForceInjection/AI-fundermentals) | [GitHubPages](https://forceinjection.github.io/)。

本课程目标是基于 nano-vllm 的真实代码路径，建立对 LLM 推理引擎的整体认识：从 `LLM.generate` 的入口出发，理解调度（prefill/decode）、KV cache 的 block 管理、注意力算子分支、Tensor Parallel 与 CUDA Graph 等关键机制，并在关键细节用示意图将程序逻辑、数据结构和张量（多维数组）的形状呈现出来。

### 1.1 代码引用

本课程所有关键结论均以仓库代码为依据。为了兼顾阅读流畅度与可核验性，代码引用按三种形式分层呈现：

- **内联链接**：在行文首次提到某个符号时直接点击跳转，适合单一目标（例如推理主循环入口 [llm_engine.py:L49-L90](../../nanovllm/engine/llm_engine.py#L49-L90)）。
- **要点列表**：当一段逻辑涉及 ≥2 个代码位置（多文件、多行号段）时，用要点列表并列呈现。
- **嵌入片段**：对于控制流密集、一眼即懂胜过千字的小函数或关键分支，直接从源码逐字摘录一段（≤ ~17 行）嵌入正文，并以行内注释点明要观察的点。

具体使用规范与图资产组织见 [AGENTS.md](../../AGENTS.md) §4.4。

### 1.2 阅读前置

本课程对前置知识的要求很低，核心 LLM 原理会在对应课次中逐步引入：

- Python 基础：能读懂函数定义、列表操作、字典结构
- 基本数学：矩阵乘法的直觉（不需要手推公式）
- 好奇心：想知道 LLM 生成文字时底层到底发生了什么
- 不要求提前理解 FlashAttention/Triton 的实现细节（会在第 7 课以"接口与分支"为主解释）

### 1.3 原理知识分布

下表说明 LLM 原理知识在哪一课引入，帮助读者提前了解知识点的位置：

| 原理主题                        | 所在课次 | 关联的工程概念                        |
| ------------------------------- | -------- | ------------------------------------- |
| Transformer 整体架构            | 第 1 课  | 理解 `LLM` 对象是什么                 |
| Tokenizer：文本 → token_ids     | 第 1 课  | 理解 `add_request` 为什么先 tokenize  |
| 自回归生成：为什么逐 token 生成 | 第 1 课  | 理解 step 循环存在的原因              |
| Self-Attention 直觉             | 第 5 课  | 理解为什么 prefill 要做变长注意力     |
| KV Cache 的数学动机             | 第 7 课  | 理解为什么 decode 只需处理 1 个 token |

### 1.4 课时安排说明

每课设计为 **90 分钟**课堂使用，包含四个阶段：

1. **原理铺垫**（或概念回顾）：建立本课所需的 LLM 原理直觉或回顾前课要点
2. **代码走读**：沿真实代码路径，逐函数讲解控制流与数据结构，必要时在正文嵌入源码片段
3. **动手练习**：完成课内"最小练习"，用代码或手算验证理解
4. **答疑讨论**：开放提问与延伸讨论

具体时间分配见各课首部的"课时安排"表。第 1 课原理内容最重；第 2–7 课以代码走读为主；第 8 课偏讨论与综合。

---

## 2. 课程目录

课程按推理链路从外到内展开：先打通端到端主干，再逐层拆开数据结构、调度、显存、批构建、注意力，最后把常见优化叠回地图上。每课均包含：本课概述（含课时安排与学习目标）、原理铺垫（如适用）、关键代码锚点与嵌入片段、示意图（Mermaid / draw.io）、最小练习与验收要点。

### 第 1 课：从 `LLM.generate` 走到 step 循环

[01-llm-generate-and-step.md](./01-llm-generate-and-step.md)

**主题**：端到端主干——用户调 `generate` 之后，代码究竟按什么路径跑到"生成的回答"。

本课把 `LLM → LLMEngine → Scheduler → ModelRunner` 串成一条线：prompt 先被包成 `Sequence`，调度器在每个 step 里选择做 prefill（一次性吞下 prompt）还是 decode（逐 token 续写），模型执行端返回 token，调度器推进状态直到请求完成。读完后我们会得到一张端到端流程图，以及在代码里一键定位每个方框的锚点，也顺势补齐 Transformer、Tokenizer、自回归生成这三条基础直觉。

### 第 2 课：`Sequence` 数据结构与请求生命周期

[02-sequence-lifecycle.md](./02-sequence-lifecycle.md)

**主题**：把"一个推理请求"实体化——`Sequence` 是每个请求在引擎内部的"身份证"。

`Sequence` 同时承载三类信息：token 序列（prompt + 已生成 token）、调度计数器（`num_cached_tokens / num_scheduled_tokens / num_tokens`）、以及通往 KV cache 的 `block_table`。它的状态机在 WAITING / RUNNING / FINISHED 之间切换，恰好对应调度器里的行为分支。掌握这节课的字段语义后，后续调度与 KV cache 管理都有清晰的落点。

### 第 3 课：Scheduler 的队列、chunked prefill 与 preempt

[03-scheduler-queues-and-preempt.md](./03-scheduler-queues-and-preempt.md)

**主题**：调度器是怎么在"吞吐量优先"的约束下做批处理的，它的角色可以类比操作系统的进程调度器。

本课沿着 `schedule()` 的代码路径，把 waiting / running 两个队列的流转讲清楚：prefill 阶段怎么拼 batch、`max_num_seqs` 与 `max_num_batched_tokens` 如何卡住批大小、decode 阶段 KV cache block 不足时怎样执行 preempt（把某个请求临时退回 waiting 以腾出资源）。最终产出一张调度流程图，每个分支条件都能对应回代码位置。

### 第 4 课：BlockManager 与 prefix caching

[04-block-manager-and-prefix-cache.md](./04-block-manager-and-prefix-cache.md)

**主题**：KV cache 的显存管理——BlockManager 就是 LLM 推理里的"内存分页管理器"。

注意力需要访问所有历史 token 的 K/V，KV cache 因而占满显存，必须精细管理。nano-vllm 把显存切成固定大小的 block，用 `free_block_ids / used_block_ids / hash_to_block_id` 三件套支撑 `can_allocate / allocate / deallocate / hash_blocks`。Prefix caching 则可以类比操作系统的共享只读页：相同前缀的 block 被多个请求共同引用、不重复分配，也不重复计算。

### 第 5 课：prefill 批构建与 context 注入

[05-prefill-batching-and-context.md](./05-prefill-batching-and-context.md)

**主题**：prefill 阶段模型实际吃进去的张量长什么样——多个变长请求如何被展平拼接成一个大批次。

本课从 `ModelRunner.prepare_prefill` 出发，讲清为什么 `input_ids` 是 1D 展平张量而不是二维 padding 矩阵，`cu_seqlens_q / cu_seqlens_k / max_seqlen_q / max_seqlen_k` 分别在变长注意力里担任什么边界角色，以及 `slot_mapping` 和 `block_tables` 为什么要以 context 的形式注入到注意力层。Self-Attention 为什么需要看所有 token，也会在原理铺垫里补齐直觉。

### 第 6 课：decode 一步生成与 block_tables

[06-decode-and-block-tables.md](./06-decode-and-block-tables.md)

**主题**：decode 一步只生成 1 个新 token，它需要的张量最少、却最能看清 KV cache 的结构。

因为历史 token 的 K/V 已经缓存好，decode 阶段每个 seq 只需送 1 个 token。`prepare_decode` 为每个 seq 构造一套最小输入：`input_ids`（last_token）、`positions`（当前位置）、`context_lens`（cache 长度）、`slot_mapping`（本步写入位置）与 `block_tables`（每个 seq 的 block_table 被 padding 成矩阵）。这节课把"decode 比 prefill 简单"这句直觉具体化到每一个字段上。

### 第 7 课：Attention——KV 写入与算子分支

[07-attention-kv-cache-and-branches.md](./07-attention-kv-cache-and-branches.md)

**主题**：把前两课注入的上下文字段真正"落"到注意力计算函数里。

核心是两件事：一是 `slot_mapping` 如何驱动 Triton kernel 把 K/V 写入 KV cache；二是 prefill 与 decode 为什么调用不同的注意力 API——`flash_attn_varlen_func` 负责变长批注意力，`flash_attn_with_kvcache` 负责增量生成。Prefix cache 命中时，K/V 会直接改用 `k_cache / v_cache` 作为输入，相当于从"共享只读页"里读数据。读完本课，"上下文对象"和"注意力算子调用"就在脑中连成一条线。

### 第 8 课：常见优化的"位置感"（TP、CUDA Graph、torch.compile）

[08-where-optimizations-live.md](./08-where-optimizations-live.md)

**主题**：建立一张"优化地图"——告诉我们三种常见优化分别"住在"代码的哪里、触发条件是什么、各自解决什么瓶颈。

LLM 推理瓶颈可以粗分为计算瓶颈和内存瓶颈。本课定位三处开关：Tensor Parallel（多进程 + 共享内存广播方法调用，与 OS 的 spawn + 共享内存 IPC 同构）在哪里启动、如何广播；CUDA Graph 在什么条件下 capture / replay，为什么主要覆盖 decode；`torch.compile` 为什么只出现在采样模块。目标是让我们在未来做性能排查时，能快速定位入口与触发条件，并知道这些优化分别影响"吞吐、延迟、显存"中的哪些维度。

---

## 3. 运行与验证建议

以下是最小的本地运行建议，用于把"代码阅读"与"实际运行现象"对齐。nano-vllm 运行需要本地模型权重路径，仓库提供了示例用法。

```bash
# 运行说明：安装本仓库并执行示例脚本（需要本地模型权重）。
python -m pip install -e .
python example.py
```

- 示例用法来源：[README.md §Quick Start](../../README.md#L35-L46) 与 [example.py](../../example.py)
