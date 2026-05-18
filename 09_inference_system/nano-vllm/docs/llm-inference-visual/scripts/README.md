# 课内练习脚本

---

## 模型路径

所有需要模型的脚本支持两种方式（优先级从高到低）：

```bash
# 方式 1：命令行参数
python L01_end_to_end.py /path/to/Qwen3-0.6B/

# 方式 2：环境变量
export NANOVLLM_MODEL_PATH=/path/to/Qwen3-0.6B/
python L01_end_to_end.py
```

---

## 环境搭建

[`setup_remote.sh`](./setup_remote.sh) 用于在远端服务器上搭建 nano-vllm 运行环境：安装依赖、下载 Qwen3-0.6B 模型。

## 功能验证

[`verify_nanovllm.py`](./verify_nanovllm.py) 覆盖 nano-vllm 的典型用法，6 个用例：Quick Start、多请求并发、token_ids 输入、SamplingParams 参数、Chat Template、吞吐统计。

```bash
python verify_nanovllm.py /path/to/model
```

全部通过即表示 nano-vllm 在 GPU 环境正常工作。

---

## 性能测试

[`benchmark.py`](./benchmark.py) 独立性能基准测试，对齐 `bench.py`，支持参数化配置。

```bash
python benchmark.py /path/to/model --num-seqs 64 --max-input 512 --max-output 256
```

---

## 课内练习（L01—L08）

每课一个独立验证脚本，配合 [课程文档](../) 使用。每个脚本的结构：**真实源码片段 → 模拟/真实执行 → 断言验证**。

| 脚本                                                 | 对应课次 | 依赖             | 说明                                                                     |
| ---------------------------------------------------- | -------- | ---------------- | ------------------------------------------------------------------------ |
| [L01_end_to_end.py](./L01_end_to_end.py)             | 第 1 课  | GPU + 模型       | 端到端推理链路：`LLM.generate` → `step` 三段式 → 返回结构                |
| [L02_sequence.py](./L02_sequence.py)                 | 第 2 课  | nano-vllm (CPU)  | Sequence 字段、block 切分公式、pickle 协议                               |
| [L03_scheduler.py](./L03_scheduler.py)               | 第 3 课  | nano-vllm (CPU)  | prefill 批拼接、chunked prefill、decode + preempt，含真实 Scheduler 对比 |
| [L04_block_manager.py](./L04_block_manager.py)       | 第 4 课  | nano-vllm (CPU)  | 链式哈希、prefix cache 命中、ref_count 引用计数                          |
| [L05_prefill_batching.py](./L05_prefill_batching.py) | 第 5 课  | torch + 模型路径 | cu_seqlens 展平拼接、slot_mapping 构造、Context 注入                     |
| [L06_decode.py](./L06_decode.py)                     | 第 6 课  | torch + 模型路径 | decode slot 公式、may_append 触发条件、prefill/decode 张量对比           |
| [L07_attention.py](./L07_attention.py)               | 第 7 课  | torch + 模型路径 | -1 哨兵、算子分支决策树、prefix cache 触发、KV cache 张量写入            |
| [L08_optimizations.py](./L08_optimizations.py)       | 第 8 课  | 纯 Python        | CUDA Graph replay 条件、TP 广播流程、torch.compile 位置                  |

```bash
# 全部（需要 GPU）
bash run_all.sh --all

# 仅 CPU（L02-L08）
bash run_all.sh

# 单课
python L03_scheduler.py /path/to/model
```
