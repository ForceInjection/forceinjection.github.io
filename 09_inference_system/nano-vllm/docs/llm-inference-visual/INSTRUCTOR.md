# 讲师指南

本指南帮助讲师高效地使用 nano-vLLM 实战课程进行教学。每课按 90 分钟设计。

## 课程主线

8 节课沿推理链路从外到内展开，可以按"端到端主干 → 数据结构 → 调度 → 显存 → 张量构建 → 注意力 → 优化"的逻辑线串讲。坚持"一张图 → 一段代码 → 一个脚本"的讲法：每引入一个新概念，先放示意图建立直觉，再读代码对应实现，最后跑验证脚本确认理解。

## 各课要点与时间分配

### 第 1 课（90 min）：从 `LLM.generate` 走到 step 循环

**重点**：让学生理解"函数调用树"，不是记住每个函数的所有细节。

| 阶段     | 时长   | 要点                                                                                     |
| -------- | ------ | ---------------------------------------------------------------------------------------- |
| 原理铺垫 | 25 min | Transformer 三段式 (Embed → Block × N → LM Head)；Tokenizer 做什么；自回归为什么需要循环 |
| 代码走读 | 35 min | `LLM` = `LLMEngine`（别名）；`generate` 主循环 (add → step loop → decode)；`step` 三段式 |
| 动手练习 | 20 min | 运行 L01 脚本，观察 `{"text", "token_ids"}` 结构                                         |
| 答疑     | 10 min |                                                                                          |

**常见卡点**：

- 学生可能不理解 "token 不是字"——用 `tokenizer.encode("你好世界")` 展示输出
- 自回归的循环必要性：先让学生手算"如果一次生成整句话"的输入输出是什么，再说为什么做不到
- `LLM = LLMEngine`：强调这是一种 API 设计模式（Facade），不是语言特性

### 第 2 课（90 min）：Sequence 数据结构

**重点**：`block_table` 类比页表是关键桥梁，后面调度和 KV cache 都靠它。

| 阶段     | 时长   | 要点                                                 |
| -------- | ------ | ---------------------------------------------------- |
| 概念回顾 | 10 min | 回顾 L01 step 循环，引出"step 操作的对象是 Sequence" |
| 代码走读 | 40 min | 三类字段、计数器语义、block_table、pickle 协议       |
| 动手练习 | 25 min | L02 脚本前半（block 公式手算）                       |
| 答疑     | 15 min |                                                      |

**常见卡点**：

- `num_cached_tokens` vs `num_scheduled_tokens` vs `num_tokens`：建议板书三列对照表
- `block(i)` 的返回值是 list 切片——提醒学生这和 Python 的 `list[i:j]` 一样
- Pickle 协议为什么有两个分支：用 TP 场景（主进程 ↔ 子进程）解释

### 第 3 课（90 min）：Scheduler

**重点**：这是学生第一次看到"操作系统概念在 Python 代码里落地"，preempt 机制是高潮。

| 阶段     | 时长   | 要点                                                                  |
| -------- | ------ | --------------------------------------------------------------------- |
| 概念回顾 | 10 min | OS 调度器类比：waiting=ready queue, running=running, preempt=swap out |
| 代码走读 | 40 min | prefill 循环 + chunked prefill 限制；decode 循环 + preempt            |
| 动手练习 | 25 min | L03 脚本的模拟部分，观察 chunked prefill 限制                         |
| 答疑     | 15 min |                                                                       |

**常见卡点**：

- `remaining < num_tokens and scheduled_seqs` → break：这是最微妙的条件，建议用黑板画三条 seq、逐个 token 预算推进
- preempt 为什么不保存 KV cache？让学生对比 OS swap：page 可以写回磁盘，KV cache 不行（太大），只能重算
- 第 6 节（真实 Scheduler 对比）可作为"彩蛋"——跑完模拟再看真实输出完全一致

### 第 4 课（90 min）：BlockManager

**重点**：prefix cache 的链式哈希是最精巧的设计，ref_count 是 OS 引用计数的直接应用。

| 阶段     | 时长   | 要点                                                                     |
| -------- | ------ | ------------------------------------------------------------------------ |
| 概念回顾 | 10 min | "注意力需要所有历史 KV" → 显存压力 → 分页管理                            |
| 代码走读 | 40 min | Block 类、免费/已用池、compute_hash、can_allocate、allocate、hash_blocks |
| 动手练习 | 25 min | L04 脚本的哈希链和 prefix cache 手算                                     |
| 答疑     | 15 min |                                                                          |

**常见卡点**：

- 链式哈希为什么不是独立哈希？画一条链 (h0=H(b0) → h1=H(b1|h0) → h2=H(b2|h1))，说明独立哈希无法保证前缀一致性
- `hash_blocks` 只写回完整 block 的原因：未满 block 的 token 还没写完，后续可能改变
- `ref_count` 何时 >1：用"两个请求共享 system prompt"举例

### 第 5 课（90 min）：prefill 批构建

**重点**：展示"数据从 Sequence 列表变成张量"的全过程，`slot_mapping` 是打通逻辑 KV 和物理 KV 的关键。

| 阶段     | 时长   | 要点                                             |
| -------- | ------ | ------------------------------------------------ |
| 原理铺垫 | 20 min | Self-Attention 直觉: Q/K/V, 变长边界问题         |
| 代码走读 | 35 min | cu_seqlens 构造、slot_mapping 构造、context 注入 |
| 动手练习 | 25 min | L05 脚本的 cu_seqlens 手算 + torch 张量展示      |
| 答疑     | 10 min |                                                  |

**常见卡点**：

- `cu_seqlens` 是前缀和：建议用 `cumsum` 这个词，学生会更快联想到算法课内容
- `slot_mapping` 的块内偏移计算：用 block_size=4 的小例子手推一遍
- Context 的 `set_context` / `get_context` 是模块级全局变量：学生可能质疑这种做法——承认这确实是"为了方便而牺牲纯粹性"

### 第 6 课（90 min）：decode 张量

**重点**：decode 的 input 比 prefill 简单得多，但 block_tables 的 padding 是细节。

| 阶段     | 时长   | 要点                                                      |
| -------- | ------ | --------------------------------------------------------- |
| 概念回顾 | 10 min | "decode 每步 1 token" + KV cache 已存历史                 |
| 代码走读 | 40 min | slot 公式、context_lens、block_tables padding、may_append |
| 动手练习 | 25 min | L06 脚本的 slot/may_append 手算 + torch 张量              |
| 答疑     | 15 min |                                                           |

**常见卡点**：

- 为什么 decode 需要 `block_tables` 但不需要 `cu_seqlens`：因为每个 seq 只有一个 token，注意力算子通过 block_table 找到该 seq 的所有历史 K/V
- `may_append` 公式的推导：从 `num_blocks` 公式倒推"什么条件下 num_blocks 会 +1"
- prefill/decode 对比表（L06 脚本第 5 节）可以直接板书

### 第 7 课（90 min）：Attention

**重点**：这是前面 5-6 课上下文的"消费方"——所有那些字段最终在这里被使用。

| 阶段     | 时长   | 要点                                                             |
| -------- | ------ | ---------------------------------------------------------------- |
| 原理铺垫 | 15 min | KV Cache 数学动机：为什么可以只算新 token 的 Q                   |
| 代码走读 | 40 min | store_kvcache kernel、三个注意力分支、prefix cache 下的 K/V 替换 |
| 动手练习 | 20 min | L07 脚本的 -1 哨兵 + Context 生命周期                            |
| 答疑     | 15 min |                                                                  |

**常见卡点**：

- KV Cache 的数学原理：不必推导，用"历史 K/V 不因新 token 加入而改变"这一句话建立直觉即可
- `flash_attn_varlen_func` vs `flash_attn_with_kvcache`：不要进入 FlashAttention 内部实现，只要对比参数签名
- Triton kernel：只展示"slot == -1 时跳过"的逻辑，不用解释 `tl.arange` 等 Triton 语法

### 第 8 课（90 min）：优化地图

**重点**：这是综合讨论课，比前面 7 课更偏"俯瞰"而非"细读"。

| 阶段     | 时长   | 要点                                                            |
| -------- | ------ | --------------------------------------------------------------- |
| 概念回顾 | 10 min | 回顾推理主链路，标注"优化可以作用的位置"                        |
| 代码走读 | 35 min | TP 进程模型、CUDA Graph capture/replay 条件、torch.compile 位置 |
| 动手练习 | 20 min | L08 脚本的 replay 判定函数                                      |
| 答疑     | 25 min | 开放讨论                                                        |

**常见卡点**：

- TP 的共享内存广播：学生可能没见过 `SharedMemory`——解释这和 `multiprocessing.Queue` 的区别（前者零拷贝）
- CUDA Graph 为什么 limit 在 512：不做深入，只说"过大的 graph 占用显存且 capture 时间长"
- 三种优化的协同：板书一张"优化→瓶颈→位置"对应表（L08 脚本第四节已有）

## 教学建议

- 配套示意图：L01/L02/L03/L07 使用 Mermaid 内嵌于 markdown；L04/L05/L06/L08 使用 draw.io（`diagrams/` 下有 `.drawio` 源文件和 `.png` 导出图）
- 建议每位学生提前搭建好环境，或者在机房统一提供 GPU 服务器
- `scripts/run_all.sh` 可以作为每课结束后的"验证信号"——跑通了就表示理解了

## 拓展阅读

- [nano-vllm vs vLLM 对比](vs-vllm.md)：学完 8 课后推荐阅读
- [AI Fundamentals](https://github.com/ForceInjection/AI-fundamentals)：Transformer/Attention 原理的补充材料
- vLLM 源码入口：`vllm/entrypoints/llm.py` → `vllm/engine/llm_engine.py` → `vllm/core/scheduler.py`
