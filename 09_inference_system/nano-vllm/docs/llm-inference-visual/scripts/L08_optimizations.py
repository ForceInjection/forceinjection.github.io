#!/usr/bin/env python3
"""
L08 练习：常见优化的"位置感"（TP、CUDA Graph、torch.compile）

验证要点：
- CUDA Graph replay 条件：!is_prefill && !enforce_eager && batch_size <= 512
- TP 进程入口：LLMEngine.__init__ spawn 子进程，共享内存广播调用
- torch.compile 仅用于 Sampler.forward（Gumbel-Max 采样）

依赖：无（纯 Python 模拟）
用法：python L08_optimizations.py
"""

import os


def show_source(file_path, start, end):
    # scripts/ → llm-inference-visual/ → docs/ → repo_root
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    full = os.path.join(repo_root, file_path)
    if not os.path.exists(full):
        return []
    with open(full) as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[start - 1:end]]


def show_code_block(title, file_path, lines):
    print(f"  // {title}  ({file_path})")
    for l in lines:
        print(f"  {l}")
    print()


# ── CUDA Graph replay 判定（对齐 model_runner.py:L195-L203）────────────

def will_replay(is_prefill, enforce_eager, batch_size):
    if is_prefill:
        return False, "prefill 走 eager"
    if enforce_eager:
        return False, "enforce_eager=True"
    if batch_size > 512:
        return False, f"batch_size({batch_size}) > 512"
    return True, "decode + eager=False + bs≤512"


# ── TP 广播模拟 ──────────────────────────────────────────────────────

def simulate_tp_broadcast(method_name, world_size):
    """
    模拟 TP 的共享内存广播流程。
    对齐 model_runner.py:L61-L89。
    """
    log = []

    log.append(f"  [rank0] 调用 call('{method_name}')")
    log.append(f"  [rank0] pickle.dumps(['{method_name}', *args]) → 共享内存")
    log.append(f"  [rank0] 写长度 n={len(method_name)+20} 到 shm.buf[0:4]")
    log.append(f"  [rank0] 写数据到 shm.buf[4:n+4]")
    for i in range(1, world_size):
        log.append(f"  [rank0] event[{i-1}].set() ← 唤醒 rank{i}")
        log.append(f"  [rank{i}] event[{i-1}].wait() → 被唤醒")
        log.append(f"  [rank{i}] 读 shm.buf[0:4] → n")
        log.append(f"  [rank{i}] pickle.loads(shm.buf[4:n+4]) → '{method_name}'")
        log.append(f"  [rank{i}] 执行 self.{method_name}(*args)")

    # NCCL 同步
    for op in ["all_reduce", "gather"]:
        log.append(f"  NCCL {op}: 各 rank 的 GPU 结果同步")

    log.append(f"  [rank0] 返回 token_ids, rank>0 返回 None")
    return log


def find_graph_bucket(bs, graph_bs):
    """模拟 graph replay 的 bucket 选择: 取 ≥ bs 的最小值。"""
    for g in graph_bs:
        if g >= bs:
            return g
    return None


# ── 验证 1: CUDA Graph replay 条件 ───────────────────────────────────

def verify_cudagraph_conditions():
    print("=" * 64)
    print("L08 验证：优化地图 — CUDA Graph / TP / torch.compile")
    print("=" * 64)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. CUDA Graph replay 触发条件                               │")
    print("│     run_model (model_runner.py:L195-L212)                   │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("run_model replay 分支", "nanovllm/engine/model_runner.py",
                     show_source("nanovllm/engine/model_runner.py", 195, 213))

    test_cases = [
        (True,  False, 128),
        (False, True,  128),
        (False, False, 600),
        (False, False, 512),
        (False, False, 256),
        (False, False, 1),
    ]

    for is_prefill, eager, bs in test_cases:
        replay, reason = will_replay(is_prefill, eager, bs)
        marker = "▶ replay" if replay else "✗ eager"
        mode = "prefill" if is_prefill else "decode"
        e = "+eager" if eager else ""
        print(f"  [{marker}] {mode} {e} bs={bs:>3}  ← {reason}")
        assert replay == (not is_prefill and not eager and bs <= 512)

    # Graph bucket 选择
    graph_bs = [1, 2, 4, 8] + list(range(16, 256 + 1, 16))
    print(f"\n  graph_bs (已 capture 的 batch size):")
    print(f"    [1, 2, 4, 8, 16, 32, 48, ..., {graph_bs[-1]}]")
    for bs in [1, 3, 7, 9, 100, 255, 256]:
        bucket = find_graph_bucket(bs, graph_bs)
        print(f"    bs={bs:>3} → 选用 graph[{bucket}]  (取 ≥ {bs} 的最小值)")
    print("  [PASS]")


# ── 验证 2: TP 广播流程 ──────────────────────────────────────────────

def verify_tp_broadcast():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  2. Tensor Parallel: SharedMemory 广播调用                   │")
    print("│     对齐 model_runner.py:L61-L89, llm_engine.py:L22-L34     │")
    print("└─────────────────────────────────────────────────────────────┘")

    log = simulate_tp_broadcast("run", world_size=3)
    print(f"\n  以 call('run', seqs, is_prefill) 为例, world_size=3:")
    for line in log:
        print(f"    {line}")

    print(f"\n  进程拓扑:")
    print(f"    Rank 0: 主进程 (LLMEngine.__init__ 不 spawn)")
    print(f"    Rank 1: mp.Process(target=ModelRunner, args=(config, 1, event_0))")
    print(f"    Rank 2: mp.Process(target=ModelRunner, args=(config, 2, event_1))")
    print(f"  OS 类比: fork/spawn + 共享内存 IPC，与多进程编程模型同构")
    print("  [READ]")


# ── 验证 3: torch.compile 位置 ───────────────────────────────────────

def verify_torch_compile():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  3. torch.compile 唯一使用位置: Sampler.forward               │")
    print("│     对齐 sampler.py:L7                                       │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("Sampler.forward (with @torch.compile)", "nanovllm/layers/sampler.py",
                     show_source("nanovllm/layers/sampler.py", 1, 13))

    print("  为什么只在这里用 torch.compile?")
    print("    采样计算图稳定: temp_scale → softmax → gumbel_max → argmax")
    print("    无分支、无动态 shape → 编译一次，持续复用")
    print("    其余模块 (Transformer forward) 有太多 shape 变化，不适合")

    print("  Gumbel-Max 等价性:")
    print("    P(token_i) = exp(logit_i/T) / Σ exp(logit_j/T)")
    print("    Gumbel-Max: 对每个 logit 加 Gumbel 噪声后取 argmax")
    print("    → 结果等价于按 softmax 概率采样")
    print("    → 代码中 .exponential_(1) 生成的就是 Gumbel 噪声")
    print("  [READ]")


# ── 验证 4: 优化地图总结 ──────────────────────────────────────────────

def verify_optimization_map():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  4. 优化 ↔ 瓶颈 ↔ 位置 对应表                                  │")
    print("└─────────────────────────────────────────────────────────────┘")

    table = """
  ┌────────────────┬──────────────┬──────────────────┬────────────────────────┐
  │ 优化             │ 瓶颈          │ 主要影响            │ 代码入口                  │
  ├────────────────┼──────────────┼──────────────────┼────────────────────────┤
  │ Tensor Parallel  │ 算力(compute) │ 吞吐 ↑ 延迟 ↓       │ LLMEngine.__init__       │
  │                  │              │                    │ ModelRunner (shm/NCCL)   │
  ├────────────────┼──────────────┼──────────────────┼────────────────────────┤
  │ CUDA Graph       │ kernel launch│ 延迟 ↓↓(decode)     │ capture_cudagraph()      │
  │                  │              │                    │ run_model replay 条件      │
  ├────────────────┼──────────────┼──────────────────┼────────────────────────┤
  │ torch.compile    │ Python 开销  │ 延迟 ↓ (采样)       │ Sampler.forward           │
  └────────────────┴──────────────┴──────────────────┴────────────────────────┘

  触发条件:
    TP:          tensor_parallel_size > 1
    CUDA Graph:  enforce_eager=False, is_prefill=False, bs ≤ 512
    torch.compile: 始终开启 (无开关)
"""
    print(table)
    print("  [READ]")


def main():
    verify_cudagraph_conditions()
    verify_tp_broadcast()
    verify_torch_compile()
    verify_optimization_map()

    print("\n" + "=" * 64)
    print("L08 全部断言通过 ✓")
    print("=" * 64)


if __name__ == "__main__":
    main()
