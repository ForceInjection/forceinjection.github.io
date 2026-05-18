#!/usr/bin/env python3
"""
L02 练习：Sequence 数据结构与请求生命周期

验证要点：
- num_blocks = (num_tokens + block_size - 1) // block_size
- last_block_num_tokens = num_tokens - (num_blocks - 1) * block_size
- block(i) 返回第 i 个 block 的 token_ids 切片
- pickle 协议: prefill 传全量 token_ids, decode 只传 last_token

依赖：nano-vllm 包（仅需 CPU）
用法：python L02_sequence.py
"""

import os
import pickle
from nanovllm.engine.sequence import Sequence


def show_source(file_path, start, end):
    """读取源码指定行。"""
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


def main():
    print("=" * 68)
    print("L02 验证：Sequence 数据结构与请求生命周期")
    print("=" * 68)

    # ═══════════════════════════════════════════════════════════════
    # 1. Sequence 字段
    # ═══════════════════════════════════════════════════════════════
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. Sequence 构造 & 字段（sequence.py:L14-L31）               │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("__init__ + 字段声明", "nanovllm/engine/sequence.py",
                     show_source("nanovllm/engine/sequence.py", 14, 32))

    print("  三类信息:")
    print("    ① token 序列: token_ids, last_token, num_prompt_tokens")
    print("    ② 调度计数器: num_cached_tokens, num_scheduled_tokens, is_prefill")
    print("    ③ KV cache 映射: block_table, block_size (类变量, 共享)\n")

    # ═══════════════════════════════════════════════════════════════
    # 2. block 切分公式
    # ═══════════════════════════════════════════════════════════════
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  2. block 切分: num_blocks / last_block_num_tokens / block(i) │")
    print("│     sequence.py:L55-L66                                    │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("block 切分", "nanovllm/engine/sequence.py",
                     show_source("nanovllm/engine/sequence.py", 54, 66))

    Sequence.block_size = 4
    print("  >>> Sequence.block_size = 4  (设为小值便于手算)\n")

    test_cases = [(1, 1, 1), (4, 1, 4), (5, 2, 1), (8, 2, 4), (9, 3, 1)]

    print("  num_tokens → num_blocks, last_block_num_tokens, blocks:")
    for n, exp_blocks, exp_last in test_cases:
        seq = Sequence(list(range(n)))
        blocks = [seq.block(i) for i in range(seq.num_blocks)]
        print(f"    n={n:>2}: num_blocks={seq.num_blocks}, "
              f"last_block_num_tokens={seq.last_block_num_tokens}, "
              f"blocks={blocks}")
        assert seq.num_blocks == exp_blocks
        assert seq.last_block_num_tokens == exp_last

    print(f"\n  公式:")
    print(f"    num_blocks = (num_tokens + block_size - 1) // block_size")
    print(f"    last_block_num_tokens = num_tokens - (num_blocks - 1) * block_size")
    print(f"    末块 token 数 ∈ [1, block_size]")
    print("  [PASS]")

    # ═══════════════════════════════════════════════════════════════
    # 3. append_token & completion 分离
    # ═══════════════════════════════════════════════════════════════
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  3. append_token & prompt/completion 分离                   │")
    print("│     sequence.py:L67-L71, L51-L53                           │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("append_token", "nanovllm/engine/sequence.py",
                     show_source("nanovllm/engine/sequence.py", 67, 71))

    Sequence.block_size = 256
    seq = Sequence([1, 2, 3])
    print(f"  初始: token_ids={seq.token_ids}, num_prompt_tokens={seq.num_prompt_tokens}")
    print(f"        num_completion_tokens={seq.num_completion_tokens}")

    seq.append_token(4)
    seq.append_token(5)
    print(f"  append 4,5 后: token_ids={seq.token_ids}")
    print(f"    num_prompt_tokens={seq.num_prompt_tokens} (不变)")
    print(f"    num_completion_tokens={seq.num_completion_tokens}")
    print(f"    prompt_token_ids={seq.prompt_token_ids}")
    print(f"    completion_token_ids={seq.completion_token_ids}  ← L01 generate 返回的就是这个")
    assert seq.num_completion_tokens == 2
    assert seq.completion_token_ids == [4, 5]
    print("  [PASS]")

    # ═══════════════════════════════════════════════════════════════
    # 4. pickle 序列化协议
    # ═══════════════════════════════════════════════════════════════
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  4. pickle 协议: prefill 传全部 / decode 只传 last_token     │")
    print("│     sequence.py:L72-L83 → TP 跨进程通信 (见 L08)             │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("__getstate__ / __setstate__", "nanovllm/engine/sequence.py",
                     show_source("nanovllm/engine/sequence.py", 72, 84))

    Sequence.block_size = 256

    # prefill
    s1 = Sequence([1, 2, 3])
    s1.is_prefill = True
    d1 = pickle.dumps(s1)
    r1 = pickle.loads(d1)
    print(f"  prefill: pickle size={len(d1)} B, restored token_ids={r1.token_ids}")
    assert r1.token_ids == [1, 2, 3]

    # decode
    s2 = Sequence([1, 2, 3])
    s2.is_prefill = False
    d2 = pickle.dumps(s2)
    r2 = pickle.loads(d2)
    print(f"  decode:  pickle size={len(d2)} B, restored last_token={r2.last_token}, token_ids={r2.token_ids}")
    assert r2.last_token == 3
    assert r2.token_ids == []

    print(f"  原因: prefill 子进程需要全部 token_ids 做 batch 拼接")
    print(f"        decode 子进程只需 last_token (1 个 int), 大幅减少 IPC 带宽")
    print("  [PASS]")

    print("\n" + "=" * 68)
    print("L02 全部断言通过 ✓")
    print("=" * 68)


if __name__ == "__main__":
    main()
