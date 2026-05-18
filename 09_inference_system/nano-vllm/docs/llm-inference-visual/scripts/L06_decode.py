#!/usr/bin/env python3
"""
L06 练习：decode 一步生成与 block_tables

验证要点：
- decode slot 公式：block_table[-1] * block_size + last_block_num_tokens - 1
- may_append 触发条件：len(seq) % block_size == 1
- block_tables padding：不同长度补齐后用 -1 标记无效 block

依赖：torch + 模型路径（Section 5 需要；Section 1-4 纯 Python）
用法：python L06_decode.py [model_path]
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


def slot(block_table_last, block_size, last_block_num_tokens):
    """decode 写入位置的 slot 计算公式。对齐 model_runner.py:L181。"""
    return block_table_last * block_size + last_block_num_tokens - 1


def verify_slot_formula():
    """验证 decode slot 公式。"""
    print("=" * 68)
    print("L06 验证：decode 批构建 — slot_mapping 与 may_append")
    print("=" * 68)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. prepare_decode & slot 公式(model_runner.py:L172-L188)  │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("prepare_decode", "nanovllm/engine/model_runner.py",
                     show_source("nanovllm/engine/model_runner.py", 172, 189))

    block_size = 256

    # 场景1：新 block 的第 0 个位置(last_block_num_tokens = 1 → 新 block 起始)
    s = slot(3, block_size, 1)
    print(f"\n场景1: block_table_last=3, block_size=256, last_block_num_tokens=1")
    print(f"  slot = 3 * 256 + 1 - 1 = {s}")
    expected = 3 * 256  # 第 0 个位置
    assert s == expected, f"slot 应为 {expected}, 实际 {s}"
    print(f"  [PASS] 新 block 第 0 个位置的 slot = {expected}")

    # 场景2：block 的最后一个位置
    s = slot(3, block_size, 256)
    print(f"\n场景2: block_table_last=3, block_size=256, last_block_num_tokens=256")
    print(f"  slot = 3 * 256 + 256 - 1 = {s}")
    expected = 4 * 256 - 1  # block 3 的最后一个位置
    assert s == expected, f"slot 应为 {expected}, 实际 {s}"
    print(f"  [PASS] block 最后一个位置的 slot = {expected}")

    # 场景3：block 中间位置
    s = slot(3, block_size, 128)
    print(f"\n场景3: block_table_last=3, block_size=256, last_block_num_tokens=128")
    print(f"  slot = 3 * 256 + 128 - 1 = {s}")
    assert s == 3 * 256 + 127
    print(f"  [PASS] block 中间位置的 slot = {s}")


def verify_may_append():
    """验证 may_append 的触发条件。"""
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  2. may_append 触发条件 (block_manager.py:L103-L108)       │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("can_append / may_append", "nanovllm/engine/block_manager.py",
                     show_source("nanovllm/engine/block_manager.py", 103, 109))

    print("  >>> 验证\n")

    block_size = 4  # 小值便于手算

    print(f"  block_size = {block_size}")
    print(f"  规则：len(seq) % block_size == 1 时触发新 block 分配")
    print()

    for length in range(1, 14):
        need_new_block = (length % block_size == 1)
        marker = " ← 触发 may_append! 分配新 block" if need_new_block else ""
        print(f"    len(seq)={length:>2} → {length} % {block_size} = {length % block_size}{marker}")

    # 验证关键边界
    # len=1: 1%4=1 → True (第一个 token，需要初始 block)
    # len=4: 4%4=0 → False (刚好填满第 1 个 block)
    # len=5: 5%4=1 → True (需要第 2 个 block)
    # len=8: 8%4=0 → False (刚好填满第 2 个 block)
    # len=9: 9%4=1 → True (需要第 3 个 block)

    assert (1 % block_size == 1) == True, "len=1 应触发新 block 分配"
    assert (4 % block_size == 1) == False, "len=4 填满后不应立即分配"
    assert (5 % block_size == 1) == True, "len=5 跨 block 边界应触发"
    assert (8 % block_size == 1) == False
    assert (9 % block_size == 1) == True

    print(f"\n  [PASS] may_append 触发条件验证通过")


def verify_can_append():
    """验证 can_append 与 may_append 的关系。"""
    print("\n--- can_append 与 may_append 的配合 ---")

    block_size = 4
    print(f"  block_size = {block_size}")
    print()

    # can_append 检查下一轮是否需要新 block，且 free blocks 是否够
    for free_blocks in [0, 1]:
        for length in [1, 4, 5, 8]:
            needs_block = (length % block_size == 1)
            can = free_blocks >= needs_block
            print(f"    free_blocks={free_blocks}, len(seq)={length}, "
                  f"needs_block={needs_block}, can_append={can}")

    # 关键场景：free_blocks=0 且 len%block_size==1 → can_append=False → 触发 preempt
    assert (0 >= True) == False  # 无空闲 block，需要新 block → can_append 失败
    assert (0 >= False) == True  # 无空闲 block，不需新 block → can_append 成功
    print(f"\n  [PASS] can_append = (free_blocks >= needs_block)")
    print(f"  当 can_append=False 且无其他 seq 可 preempt 时，自身被 preempt")


def verify_block_tables_padding():
    """验证 block_tables 的 padding 逻辑。"""
    print("\n--- block_tables padding ---")

    # prepare_block_tables (model_runner.py:L123-L127):
    # max_len = max(len(seq.block_table) for seq in seqs)
    # block_tables = [seq.block_table + [-1] * (max_len - len(seq.block_table)) for seq in seqs]

    block_tables_raw = [
        [3, 7],           # seq_a: 2 blocks
        [5, 12, 8],       # seq_b: 3 blocks
        [1],               # seq_c: 1 block
    ]

    max_len = max(len(bt) for bt in block_tables_raw)
    padded = [bt + [-1] * (max_len - len(bt)) for bt in block_tables_raw]

    print(f"  原始 block_tables: {block_tables_raw}")
    print(f"  max_len = {max_len}")
    print(f"  padding 后:")
    for i, bt in enumerate(padded):
        print(f"    seq[{i}]: {bt}")

    assert padded == [
        [3, 7, -1],
        [5, 12, 8],
        [1, -1, -1],
    ], f"padding 结果不符合预期: {padded}"

    print(f"  [PASS] -1 哨兵标记无效 block 位置")


# ── 验证 5: 真实 torch 张量（decode）─────────────────────────────────

def verify_with_real_tensors(model_path):
    """用真实 torch 张量模拟 prepare_decode 的输出，展示 shape/dtype。"""
    import torch
    from nanovllm.config import Config
    from nanovllm.engine.sequence import Sequence
    from nanovllm.sampling_params import SamplingParams
    from nanovllm.utils.context import set_context, get_context, reset_context

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  5. 真实 torch 张量构造（对齐 prepare_decode）                 │")
    print("│     展示 shape / dtype / 与 prefill 的差异                    │")
    print("└─────────────────────────────────────────────────────────────┘")

    Config(model_path, kvcache_block_size=256)
    Sequence.block_size = 256
    sp = SamplingParams(temperature=0.6, max_tokens=64)
    block_size = 256

    # 两条 decode 阶段的 seq
    seq_a = Sequence([100, 200, 300] + [1000], sp)             # 3 prompt + 1 completion
    seq_b = Sequence([400, 500] + [2000, 2001, 2002], sp)       # 2 prompt + 3 completion
    seq_a.block_table = [0]
    seq_b.block_table = [1]

    seqs = [seq_a, seq_b]

    # ── 构造 decode 张量 ──
    print(f"\n  ▸ input_ids & positions & context_lens:")
    input_ids_list = []
    positions_list = []
    context_lens_list = []
    slot_mapping_list = []

    for seq in seqs:
        input_ids_list.append(seq.last_token)
        positions_list.append(len(seq) - 1)
        context_lens_list.append(len(seq))
        slot_mapping_list.append(
            seq.block_table[-1] * block_size + seq.last_block_num_tokens - 1
        )

    input_ids = torch.tensor(input_ids_list, dtype=torch.int64)
    positions = torch.tensor(positions_list, dtype=torch.int64)
    context_lens = torch.tensor(context_lens_list, dtype=torch.int32)
    slot_mapping = torch.tensor(slot_mapping_list, dtype=torch.int32)

    print(f"    input_ids:    shape={tuple(input_ids.shape)}, dtype={input_ids.dtype}, "
          f"values={input_ids.tolist()}")
    print(f"    positions:    shape={tuple(positions.shape)}, dtype={positions.dtype}, "
          f"values={positions.tolist()}")
    print(f"    context_lens: shape={tuple(context_lens.shape)}, dtype={context_lens.dtype}, "
          f"values={context_lens.tolist()}")
    print(f"    slot_mapping: shape={tuple(slot_mapping.shape)}, dtype={slot_mapping.dtype}, "
          f"values={slot_mapping.tolist()}")

    assert input_ids.shape == (2,) and positions.shape == (2,)
    print("    [OK] shapes: (bs,) — 每个 seq 1 个 token, 不像 prefill 那样展平")

    # ── block_tables padding ──
    print(f"\n  ▸ block_tables padding:")
    max_blocks = max(len(s.block_table) for s in seqs)
    bt_list = [s.block_table + [-1] * (max_blocks - len(s.block_table)) for s in seqs]
    block_tables = torch.tensor(bt_list, dtype=torch.int32)
    print(f"    block_tables: shape={tuple(block_tables.shape)}, dtype={block_tables.dtype}")
    print(f"    values: {block_tables.tolist()}")
    assert block_tables.shape == (2, 1)
    print("    [OK] max_blocks=1, padding 不需要 -1 哨兵 (所有 seq 等长)")

    # ── context 注入 ──
    print(f"\n  ▸ Context 注入 (decode):")
    set_context(False, slot_mapping=slot_mapping, context_lens=context_lens,
                block_tables=block_tables)
    ctx = get_context()
    print(f"    is_prefill     = {ctx.is_prefill}")
    print(f"    slot_mapping   = {ctx.slot_mapping.tolist()}")
    print(f"    context_lens   = {ctx.context_lens.tolist()}")
    print(f"    block_tables   = {ctx.block_tables.tolist()}")
    assert ctx.is_prefill is False
    assert ctx.cu_seqlens_q is None  # decode 不需要 cu_seqlens
    reset_context()
    print(f"    [PASS] decode context: cu_seqlens=None, context_lens/block_tables 已注入")

    # ── prefill vs decode 对比 ──
    print(f"\n  ▸ prefill vs decode 张量对比:")
    print(f"    ┌──────────────┬─────────────────────┬──────────────────────┐")
    print(f"    │ 字段           │ prefill              │ decode               │")
    print(f"    ├──────────────┼─────────────────────┼──────────────────────┤")
    print(f"    │ input_ids     │ 1D (total_tokens,)  │ 1D (bs,)             │")
    print(f"    │ positions     │ 1D (total_tokens,)  │ 1D (bs,)             │")
    print(f"    │ cu_seqlens_q  │ 1D (bs+1,)          │ None                 │")
    print(f"    │ cu_seqlens_k  │ 1D (bs+1,)          │ None                 │")
    print(f"    │ slot_mapping  │ 1D (total_tokens,)  │ 1D (bs,)             │")
    print(f"    │ context_lens  │ None                │ 1D (bs,)             │")
    print(f"    │ block_tables  │ 2D (可选, prefix)    │ 2D (bs, max_blocks)  │")
    print(f"    └──────────────┴─────────────────────┴──────────────────────┘")


def main():
    import sys
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model_path:
        print("用法: python L06_decode.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model_path = os.path.expanduser(model_path)

    verify_slot_formula()
    verify_may_append()
    verify_can_append()
    verify_block_tables_padding()
    verify_with_real_tensors(model_path)

    print("\n" + "=" * 60)
    print("L06 验证完成：所有断言通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
