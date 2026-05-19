# nano-vllm 与真实 vLLM 的差距

nano-vllm 约为 1,400 行 Python，真实 vLLM 约为 200,000+ 行。本文标注二者的关键差异，区分"教学简化"和"真正未实现的功能"，帮助读者建立从 nano 到 real 的升级路径。

---

## 1. 教学简化（概念保留，实现精简）

这些功能真实 vLLM 有，nano-vllm 也实现了核心逻辑，但实现方式更直白。

| 功能            | nano-vLLM 做法                             | vLLM 做法                                                                     | nano 里看什么           |
| --------------- | ------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------- |
| PagedAttention  | 固定 block_size=256, 手动管理 free/used 池 | 多 block_size (16/32/64/…), NuBlock 抽象, 支持 prefix caching + copy-on-write | L04 BlockManager        |
| 调度器          | 单一 `Scheduler` 类, FIFO + preempt        | `Scheduler` + `Policy` 解耦, 支持 FCFS/Priority/ChunkedPrefill 策略           | L03 schedule()          |
| Prefix Caching  | xxhash 链式哈希, hash_to_block_id 全局字典 | 相同方案, 外加完整 LRU block eviction + hash 清理                            | L04 hash_blocks()       |
| CUDA Graph      | 预 capture 几个固定 batch_size             | 动态 streaming capture, padding alignment, piecewise CUDAGraph                | L08 capture_cudagraph() |
| Tensor Parallel | spawn + SharedMemory 广播方法调用          | Ray actor 管理 + NCCL group, 支持 pipeline parallel + data parallel           | L08 TP 流程             |
| 采样            | Gumbel-Max + torch.compile                 | 插件式 sampler (top-k/top-p/min-p/beam search/penalties)                      | L08 Sampler.forward     |

---

## 2. 真正缺失的能力

这些功能 nano-vLLM 没有实现，但真实 vLLM 在生产环境中依赖它们。

### 2.1 Prefill / Decode 分离调度

真实 vLLM 将 prefill 和 decode 请求放入两个独立的调度队列，允许在 prefill batch 中插入 decode 请求（chunked prefill 的更一般形式）。

- nano 里：`Scheduler.schedule()` 先 prefill 后 decode，两者互斥
- vLLM 里：prefill 和 decode 在同一 batch 中混合调度，最大化 GPU 利用率
- 影响：长 prompt 请求会阻塞所有 decode 请求

### 2.2 连续批处理 (Continuous Batching)

真实 vLLM 的 decode 请求可以在每个 step 动态加入/离开 batch，不需要等待整个 batch 都完成。nano-vLLM 在 decode 中一旦 seq 加入 batch，就一直停留到 EOS/max_tokens。

- nano 里：decode batch 中的 seq 全部跑完才能释放资源
- vLLM 里：每步重新拼 batch，已完成的 seq 立即释放 slot

### 2.3 KV Cache Offloading

当 GPU 显存不够时，真实 vLLM 可以将不常用的 KV cache block 交换到 CPU 内存或 NVMe 磁盘。

- nano 里：block 不足时只能 preempt（丢弃 KV cache，下一轮 prefill 重算）
- vLLM 里：swap out → swap in，避免重算开销

### 2.4 Speculative Decoding

用草稿模型（draft model）先快速生成几个候选 token，再由主模型验证，一次 decode step 生成多个 token 以提高吞吐。

- 完全不涉及

### 2.5 多模态支持

vLLM 支持图像、视频等多模态输入，nano-vLLM 仅支持文本。

### 2.6 量化

vLLM 支持 AWQ、GPTQ、FP8、INT8 等多种量化方案，减少模型显存占用。nano-vLLM 只使用原始 FP16/BF16 权重。

### 2.7 异步调度与 Streaming

vLLM 的 `LLM.generate` 支持 `async` 模式和 token-level streaming。nano-vLLM 是同步生成。

---

## 3. 架构层面的差异

| 维度       | nano-vLLM        | vLLM                                   |
| ---------- | ---------------- | -------------------------------------- |
| 代码量     | ~1,400 行        | ~200,000+ 行                           |
| 模型支持   | 仅 Qwen3-0.6B    | 所有主流架构 (LLaMA/Qwen/Mistral/…)    |
| 进程管理   | 手动 spawn + shm | Ray / multiprocessing 抽象层           |
| 前后端分离 | 无               | API Server (FastAPI) + Engine 分离     |
| 日志/监控  | 仅 tqdm 进度条   | Prometheus metrics, structured logging |
| 配置系统   | dataclass Config | EngineArgs + 多层配置继承              |
| 测试覆盖   | 无自动化测试     | ~10,000+ 测试用例                      |

---

## 4. 阅读路线建议

学完 nano-vLLM 后，如果希望深入了解真实 vLLM，推荐按以下路线阅读 vLLM 源码：

1. **入口**：`vllm/entrypoints/llm.py` — 对应 nano 的 `nanovllm/llm.py`
2. **引擎**：`vllm/engine/llm_engine.py` — 对应 nano 的 `nanovllm/engine/llm_engine.py`
3. **调度器**：`vllm/core/scheduler.py` — 对应 nano 的 `nanovllm/engine/scheduler.py`（这里差异最大，可重点看）
4. **块管理器**：`vllm/core/block/` — 对应 nano 的 `nanovllm/engine/block_manager.py`
5. **模型执行**：`vllm/worker/model_runner.py` — 对应 nano 的 `nanovllm/engine/model_runner.py`
6. **注意力后端**：`vllm/attention/` — 对应 nano 的 `nanovllm/layers/attention.py`

每个模块 nano 都提供了清晰的起点，vLLM 版本则在其上叠加了生产级特性。带着 nano 的理解去看 vLLM，可以更快穿透抽象层。
