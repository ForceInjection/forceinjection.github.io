#!/usr/bin/env python3
"""
L04 练习：BlockManager 与 prefix caching

验证要点：
- compute_hash(token_ids, prefix) 构造链式哈希
- can_allocate 逐块检查 prefix cache 命中，用 token_ids 全等做二次校验
- hash_blocks 只对"已完成的整块"写回 hash_to_block_id
- ref_count 记录 block 被多少个 seq 引用

依赖：nano-vllm 包（xxhash + numpy）
用法：python L04_block_manager.py
"""

import os
from nanovllm.engine.block_manager import BlockManager


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


def verify_hash_chain():
    """验证链式哈希：前缀哈希作为下一块计算的 seed。"""
    print("=" * 60)
    print("L04 验证：BlockManager 哈希链与 prefix cache")
    print("=" * 60)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. 哈希链构造: compute_hash & Block 元数据                  │")
    print("│     block_manager.py:L8-L41                                │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("Block & compute_hash", "nanovllm/engine/block_manager.py",
                     show_source("nanovllm/engine/block_manager.py", 8, 42))

    print("  >>> 验证：链式哈希 ≠ 直接哈希")
    block0 = [1, 2, 3, 4]
    block1 = [5, 6, 7, 8]

    h0 = BlockManager.compute_hash(block0, prefix=-1)
    h1 = BlockManager.compute_hash(block1, prefix=h0)
    h1_direct = BlockManager.compute_hash(block1, prefix=-1)

    print(f"  h0 = BlockManager.compute_hash({block0}, prefix=-1)")
    print(f"    = {h0}")
    print(f"  h1 = BlockManager.compute_hash({block1}, prefix=h0)")
    print(f"    = {h1}")
    print(f"  h1_direct = BlockManager.compute_hash({block1}, prefix=-1)")
    print(f"    = {h1_direct}")

    assert h0 != -1, "h0 应不等于 -1"
    assert h1 != h1_direct, (
        "链式哈希与直接哈希应不同（prefix 参与计算，将前缀信息注入当前块）"
    )
    print("  [PASS] 链式哈希 ≠ 直接哈希 — prefix 影响了当前块的哈希值")

    # 验证相同的 token_ids + prefix → 相同 hash
    h0_b = BlockManager.compute_hash(block0, prefix=-1)
    h1_b = BlockManager.compute_hash(block1, prefix=h0_b)
    assert h0 == h0_b, "相同输入应产生相同 hash"
    assert h1 == h1_b, "相同链应产生相同 hash"
    print("  [PASS] 确定性验证：相同输入 → 相同 hash")


def verify_can_allocate_full_hit():
    """手算 prefix cache 命中场景：两条请求共享前缀。"""
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  2. can_allocate & allocate: 逐块命中 + 引用计数复用        │")
    print("│     block_manager.py:L58-L93                               │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("can_allocate", "nanovllm/engine/block_manager.py",
                     show_source("nanovllm/engine/block_manager.py", 58, 87))
    show_code_block("allocate", "nanovllm/engine/block_manager.py",
                     show_source("nanovllm/engine/block_manager.py", 88, 93))

    print("  >>> 验证：两条 seq 共享前缀\n")

    block_size = 4
    num_blocks = 4  # BlockManager 初始化需要的 block 总数
    bm = BlockManager(num_blocks, block_size)

    print(f"  block_size = {block_size}")
    print(f"  num_blocks = {num_blocks}")
    print()
    print("  场景：两条请求共享前缀")
    print("    seq_a: [1,2,3,4, 5,6,7,8, 9,10] → 3 blocks (前两块整块, 第三块未满)")
    print("    seq_b: [1,2,3,4, 5,6,7,8, 11,12,13,14] → 4 blocks (前两块与 seq_a 一致)")

    # 构造 seq_a 并分配
    from nanovllm.engine.sequence import Sequence
    Sequence.block_size = block_size
    seq_a = Sequence([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    # can_allocate: 首次无 prefix cache，不应命中
    cached_a = bm.can_allocate(seq_a)
    print(f"\n  seq_a can_allocate: num_cached_blocks = {cached_a}")
    assert cached_a == 0, "首次分配不应有 prefix cache 命中"
    bm.allocate(seq_a, cached_a)
    print(f"  seq_a.block_table: {seq_a.block_table}")

    # 模拟 seq_a 一次 prefill 处理完前 8 个 token（两整块）
    # hash_blocks 用 num_cached_tokens(前) + num_scheduled_tokens(本轮) 确定区间
    seq_a.num_cached_tokens = 0
    seq_a.num_scheduled_tokens = 8
    bm.hash_blocks(seq_a)
    seq_a.num_cached_tokens = 8
    seq_a.num_scheduled_tokens = 0
    print(f"  hash_blocks 后 hash_to_block_id 条数: {len(bm.hash_to_block_id)}")
    assert len(bm.hash_to_block_id) == 2, "应写回 2 个整块的 hash"
    print(f"  [OK] 2 个整块已写入 hash_to_block_id")

    # 构造 seq_b：与 seq_a 共享前两块前缀
    seq_b = Sequence([1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14])

    cached_b = bm.can_allocate(seq_b)
    print(f"\n  seq_b can_allocate: num_cached_blocks = {cached_b}")
    assert cached_b == 2, (
        f"seq_b 前两块与 seq_a 完全一致，应命中 2 blocks，实际 {cached_b}"
    )
    print(f"  [OK] seq_b 命中 {cached_b} 个 cached blocks")

    # 分配 seq_b：前两块复用，剩余两块新分配
    bm.allocate(seq_b, cached_b)
    print(f"  seq_b.block_table: {seq_b.block_table}")
    # block_table 长度应为 4 (num_blocks of seq_b)
    assert len(seq_b.block_table) == seq_b.num_blocks, (
        f"block_table 长度应为 {seq_b.num_blocks}"
    )
    # 前两块应与 seq_a 相同（复用）
    assert seq_b.block_table[:2] == seq_a.block_table[:2], (
        "前两块应复用 seq_a 的 block"
    )
    # ref_count 应增加
    assert bm.blocks[seq_b.block_table[0]].ref_count == 2, (
        "共享 block 的 ref_count 应为 2"
    )
    print(f"  [OK] 前两块复用 seq_a，ref_count = {bm.blocks[seq_b.block_table[0]].ref_count}")

    # seq_b.num_cached_tokens 应设为 cached_blocks * block_size
    expected_cached = cached_b * block_size
    print(f"  seq_b.num_cached_tokens = {seq_b.num_cached_tokens}")
    assert seq_b.num_cached_tokens == expected_cached, (
        f"num_cached_tokens 应为 {expected_cached}"
    )
    print(f"  [OK] num_cached_tokens = {cached_b} * {block_size} = {expected_cached}")


def verify_hash_blocks_only_full_blocks():
    """验证 hash_blocks 只对完整 block 写回哈希。"""
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  3. hash_blocks: 只对完整 block 写回                        │")
    print("│     block_manager.py:L110-L120                             │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("hash_blocks", "nanovllm/engine/block_manager.py",
                     show_source("nanovllm/engine/block_manager.py", 110, 121))

    print("  >>> 验证：未满 block 不参与 hash 写回\n")

    block_size = 4
    bm = BlockManager(5, block_size)

    from nanovllm.engine.sequence import Sequence
    Sequence.block_size = block_size

    # 构造一个 seq：2 整块 + 1 未满块
    seq = Sequence([1, 2, 3, 4, 5, 6, 7, 8, 9])  # 9 tokens → 3 blocks
    bm.allocate(seq, 0)

    # 第 1 轮 prefill: 处理 6 tokens → 完成 1 整块 + 2 tokens（第 2 块未满）
    seq.num_cached_tokens = 0
    seq.num_scheduled_tokens = 6
    bm.hash_blocks(seq)  # hash_blocks: start=0//4=0, end=(0+6)//4=1 → 只写回 block 0
    seq.num_cached_tokens = 6
    seq.num_scheduled_tokens = 0

    hash_count = len(bm.hash_to_block_id)
    print(f"  第1轮 prefill (6 tokens) → 写入 hash_to_block_id 的块数: {hash_count}")
    assert hash_count == 1, (
        f"只有 1 个整块 (tokens 0-3)，应写回 1 条，实际 {hash_count}"
    )
    print("  [PASS] 仅完整 block 参与 hash_blocks 写回，未满 block 不写回")

    # 第 2 轮 prefill: 再处理 2 tokens → 第 2 块也变完整
    seq.num_scheduled_tokens = 2
    bm.hash_blocks(seq)  # hash_blocks: start=6//4=1, end=(6+2)//4=2 → 写回 block 1
    seq.num_cached_tokens = 8
    seq.num_scheduled_tokens = 0
    hash_count = len(bm.hash_to_block_id)
    print(f"  第2轮 prefill (2 tokens) → 写入 hash_to_block_id 的总块数: {hash_count}")
    assert hash_count == 2, f"应有 2 条 hash 记录，实际 {hash_count}"
    print("  [PASS] 第 2 个完整 block 也被写回")


def verify_block_ref_count():
    """验证 ref_count 的增减逻辑：deallocate 时递减，为 0 时回收。"""
    print("\n--- 4. ref_count 引用计数 ---")

    block_size = 4
    bm = BlockManager(8, block_size)

    from nanovllm.engine.sequence import Sequence
    Sequence.block_size = block_size

    # 分配 seq_a 并模拟完成两整块的 prefill
    seq_a = Sequence([1, 2, 3, 4, 5, 6, 7, 8])
    bm.allocate(seq_a, 0)
    seq_a.num_cached_tokens = 0
    seq_a.num_scheduled_tokens = 8
    bm.hash_blocks(seq_a)
    seq_a.num_cached_tokens = 8
    seq_a.num_scheduled_tokens = 0

    for i, bid in enumerate(seq_a.block_table):
        print(f"  seq_a block[{i}]: id={bid}, ref_count={bm.blocks[bid].ref_count}")
        assert bm.blocks[bid].ref_count == 1

    # seq_b 共享 seq_a 的前缀
    seq_b = Sequence([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    cached_b = bm.can_allocate(seq_b)
    assert cached_b == 2
    bm.allocate(seq_b, cached_b)

    for i, bid in enumerate(seq_b.block_table[:2]):
        print(f"  seq_b 共享 block[{i}]: id={bid}, ref_count={bm.blocks[bid].ref_count}")
        assert bm.blocks[bid].ref_count == 2, (
            f"共享 block ref_count 应为 2，实际 {bm.blocks[bid].ref_count}"
        )

    # 释放 seq_a
    bm.deallocate(seq_a)
    for i, bid in enumerate(seq_b.block_table[:2]):
        print(f"  deallocate seq_a 后 block[{i}]: id={bid}, ref_count={bm.blocks[bid].ref_count}")
        assert bm.blocks[bid].ref_count == 1, (
            f"释放 seq_a 后 ref_count 应为 1，实际 {bm.blocks[bid].ref_count}"
        )
    print("  [PASS] ref_count 增减与共享/释放逻辑一致")


def main():
    verify_hash_chain()
    verify_can_allocate_full_hit()
    verify_hash_blocks_only_full_blocks()
    verify_block_ref_count()

    print("\n" + "=" * 60)
    print("L04 验证完成：所有断言通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
