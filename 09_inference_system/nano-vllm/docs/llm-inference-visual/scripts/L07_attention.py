#!/usr/bin/env python3
"""
L07 练习：Attention — KV 写入与算子分支

验证要点：
- store_kvcache 用 slot_mapping 驱动写入，slot == -1 时跳过
- prefill 分支：flash_attn_varlen_func（变长批注意力）
- decode 分支：flash_attn_with_kvcache（增量生成注意力）
- prefix cache 命中时 K/V 直接使用 k_cache/v_cache

依赖：torch + 模型路径（仅 Section 4 需要；Section 1-3 纯 Python）
用法：python L07_attention.py [model_path]
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


# ── KV cache 写入模拟（对齐 attention.py:L10-L30）─────────────────────

def store_kv_sim(cache, slot_mapping, keys, values):
    """模拟 Triton kernel: slot == -1 时跳过。"""
    for idx, slot in enumerate(slot_mapping):
        if slot == -1:
            continue
        cache[slot] = (keys[idx], values[idx])
    return cache


# ── 注意力分支决策（对齐 attention.py:L59-L75）─────────────────────────

def attention_branch(context):
    """
    模拟 Attention.forward 的分支选择。
    context 包含: is_prefill, has_cache, has_block_tables
    返回调用的 API 名称和参数特征。
    """
    steps = []

    # Step 1: 是否绑定了 KV cache?
    if context["has_cache"]:
        steps.append("k_cache/v_cache 已绑定 → 调用 store_kvcache(k, v)")
    else:
        steps.append("k_cache/v_cache 未绑定 → 跳过 KV 写入（warmup 阶段）")

    # Step 2: prefill or decode?
    if context["is_prefill"]:
        if context.get("has_block_tables"):
            steps.append("is_prefill=True, block_tables≠None → prefix cache 分支")
            steps.append("  k, v = k_cache, v_cache  ← K/V 直接用缓存的")
            api = "flash_attn_varlen_func(q, k_cache, v_cache, cu_seqlens_q, cu_seqlens_k, block_table=...)"
        else:
            steps.append("is_prefill=True, block_tables=None → 普通 prefill")
            steps.append("  k, v 使用本轮新计算的")
            api = "flash_attn_varlen_func(q, k, v, cu_seqlens_q, cu_seqlens_k)"
    else:
        steps.append("is_prefill=False → decode 分支")
        steps.append("  q.unsqueeze(1)  ← 每个 seq 只有 1 token")
        api = "flash_attn_with_kvcache(q.unsqueeze(1), k_cache, v_cache, context_lens, block_table=...)"

    return api, steps


# ── 验证 1: slot_mapping 的 -1 哨兵 ───────────────────────────────────

def verify_slot_mapping_sentinel():
    print("=" * 64)
    print("L07 验证：Attention — KV 写入 + 算子分支选择")
    print("=" * 64)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. store_kvcache 的 -1 哨兵（对齐 attention.py:L21-L24）   │")
    print("└─────────────────────────────────────────────────────────────┘")

    cache = {}
    store_kv_sim(cache,
        slot_mapping=[10, -1, 12, -1, 15],
        keys=["k0", "k1", "k2", "k3", "k4"],
        values=["v0", "v1", "v2", "v3", "v4"],
    )

    print(f"\n  slot_mapping = [10, -1, 12, -1, 15]")
    print(f"  写入结果:")
    for slot, (k, v) in sorted(cache.items()):
        print(f"    slot {slot:>3}: ({k}, {v})")
    print(f"  跳过的: idx=1 (slot=-1), idx=3 (slot=-1)")
    assert len(cache) == 3
    assert 10 in cache and 12 in cache and 15 in cache
    print("  [PASS]")

    # CUDA Graph 场景展示
    total = 8
    bs = 3
    slot_mapping_graph = [-1] * total
    slot_mapping_graph[:bs] = [20, 21, 22]
    print(f"\n  CUDA Graph 场景（对齐 model_runner.py:L206-L208）:")
    print(f"    total_slots={total}, bs={bs}")
    print(f"    fill_(-1) → [{', '.join(str(s) for s in slot_mapping_graph)}]")
    print(f"    slot_mapping[:bs] = [20, 21, 22]")

    cache2 = {}
    store_kv_sim(cache2, slot_mapping_graph,
                 [f"k{i}" for i in range(total)],
                 [f"v{i}" for i in range(total)])
    print(f"    写入 {len(cache2)} 个 slot: {sorted(cache2.keys())}")
    assert len(cache2) == 3
    print("  [PASS] CUDA Graph 场景: 仅前 bs 个 slot 有效")


# ── 验证 2: 注意力分支决策树 ──────────────────────────────────────────

def verify_attention_branches():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  2. Attention.forward 分支决策（对齐 attention.py:L59-L75）  │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("Attention.forward", "nanovllm/layers/attention.py",
                     show_source("nanovllm/layers/attention.py", 59, 76))

    scenarios = [
        {
            "label": "普通 prefill（warmup）",
            "ctx": {"is_prefill": True, "has_cache": False, "has_block_tables": False},
        },
        {
            "label": "普通 prefill（有 KV cache）",
            "ctx": {"is_prefill": True, "has_cache": True, "has_block_tables": False},
        },
        {
            "label": "prefix cache 命中 prefill",
            "ctx": {"is_prefill": True, "has_cache": True, "has_block_tables": True},
        },
        {
            "label": "decode",
            "ctx": {"is_prefill": False, "has_cache": True, "has_block_tables": True},
        },
    ]

    for s in scenarios:
        api, steps = attention_branch(s["ctx"])
        print(f"\n  ▸ {s['label']}")
        for step in steps:
            print(f"      {step}")
        print(f"      → {api}")

    print("\n  关系总结:")
    print("    prefill 用 flash_attn_varlen_func: 变长序列, 需要 cu_seqlens 定界")
    print("    decode  用 flash_attn_with_kvcache: 每 seq 1 token, 历史 K/V 已在 cache")
    print("    prefix cache 命中时: K/V 改用 k_cache/v_cache, block_tables 传入")


# ── 验证 3: prefix cache 触发条件 ────────────────────────────────────

def verify_prefix_cache_trigger():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  3. prefix cache 触发条件（model_runner.py:L162-L163）       │")
    print("└─────────────────────────────────────────────────────────────┘")

    cases = [
        # (cu_seqlens_q, cu_seqlens_k, expected)
        ([0, 3, 8], [0, 8, 13], True),
        ([0, 3, 8], [0, 3, 8], False),
    ]

    for cu_q, cu_k, expected in cases:
        needs_bt = cu_k[-1] > cu_q[-1]
        status = "✓ 触发" if needs_bt == expected else "✗ 错误"
        print(f"\n  cu_seqlens_q={cu_q}, cu_seqlens_k={cu_k}")
        print(f"    cu_seqlens_k[-1]({cu_k[-1]}) > cu_seqlens_q[-1]({cu_q[-1]})? {needs_bt}")
        print(f"    → {'需要构造 block_tables' if needs_bt else '不需要 block_tables'}  {status}")
        assert needs_bt == expected

    print("\n  直观理解:")
    print("    cu_seqlens_k > cu_seqlens_q 意味着某些 seq 的 cache 侧比 query 侧")
    print("    更长 → 有 prefix cache 数据 → 需要用 block_tables 查表定位")


# ── 验证 4: 真实 Context 类 + store_kvcache 张量模拟 ─────────────────

def verify_with_real_context(model_path):
    """用真实的 Context 类和张量模拟 store_kvcache 的完整生命周期。"""
    import torch
    from nanovllm.config import Config
    from nanovllm.utils.context import Context, set_context, get_context, reset_context

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  4. 真实 Context 类 + store_kvcache 张量模拟                 │")
    print("│     对齐 context.py, attention.py:L59-L75                  │")
    print("└─────────────────────────────────────────────────────────────┘")

    # 加载 hf_config 验证模型路径有效
    Config(model_path, kvcache_block_size=256)

    # ── Context 完整生命周期 ──
    print(f"\n  ▸ Context 注入 → 读取 → 清空（真实 nanovllm 代码路径）:")

    show_code_block("Context dataclass & set/get/reset", "nanovllm/utils/context.py",
                     show_source("nanovllm/utils/context.py", 1, 28))

    # prefill context: 2 条 seq, 总 7 tokens
    cu_q = torch.tensor([0, 3, 7], dtype=torch.int32)
    cu_k = torch.tensor([0, 3, 7], dtype=torch.int32)
    slot_map = torch.randint(0, 1000, (7,), dtype=torch.int32)

    set_context(True, cu_seqlens_q=cu_q, cu_seqlens_k=cu_k,
                max_seqlen_q=4, max_seqlen_k=4,
                slot_mapping=slot_map, context_lens=None, block_tables=None)
    ctx = get_context()
    print(f"    >>> set_context(is_prefill=True, ...)")
    print(f"    >>> ctx = get_context()")
    print(f"        ctx.is_prefill   = {ctx.is_prefill}")
    print(f"        ctx.cu_seqlens_q = {ctx.cu_seqlens_q.tolist()}")
    print(f"        ctx.cu_seqlens_k = {ctx.cu_seqlens_k.tolist()}")
    print(f"        ctx.max_seqlen_q = {ctx.max_seqlen_q}")
    print(f"        ctx.max_seqlen_k = {ctx.max_seqlen_k}")
    print(f"        ctx.slot_mapping[:4] = {ctx.slot_mapping[:4].tolist()}")
    print(f"        ctx.context_lens    = {ctx.context_lens}")
    print(f"        ctx.block_tables    = {ctx.block_tables}")

    # decode context
    context_lens = torch.tensor([10, 15], dtype=torch.int32)
    bt = torch.tensor([[0, 1, -1], [2, -1, -1]], dtype=torch.int32)
    slot_map_d = torch.tensor([150, 220], dtype=torch.int32)

    set_context(False, slot_mapping=slot_map_d, context_lens=context_lens,
                block_tables=bt)
    ctx = get_context()
    print(f"\n    >>> set_context(is_prefill=False, ...)")
    print(f"    >>> ctx = get_context()")
    print(f"        ctx.is_prefill   = {ctx.is_prefill}")
    print(f"        ctx.cu_seqlens_q = {ctx.cu_seqlens_q}  ← decode 不需要")
    print(f"        ctx.slot_mapping = {ctx.slot_mapping.tolist()}")
    print(f"        ctx.context_lens = {ctx.context_lens.tolist()}")
    print(f"        ctx.block_tables = {ctx.block_tables.tolist()}")

    # reset
    reset_context()
    ctx = get_context()
    print(f"\n    >>> reset_context()")
    print(f"    >>> ctx = get_context()")
    print(f"        ctx.is_prefill = {ctx.is_prefill}")
    print(f"        ctx.cu_seqlens_q = {ctx.cu_seqlens_q}")
    print(f"        ctx.slot_mapping = {ctx.slot_mapping}")
    assert ctx.is_prefill is False and ctx.slot_mapping is None
    print(f"    [PASS] Context 生命周期: set → get → reset")

    # ── store_kvcache 张量模拟 ──
    print(f"\n  ▸ store_kvcache 张量写入模拟:")
    # 模拟 KV cache: [num_blocks, block_size, num_kv_heads, head_dim]
    num_blocks = 4
    block_size = 256
    num_kv_heads = 8
    head_dim = 128

    # k_cache 形状: (num_blocks, block_size, num_kv_heads, head_dim)
    k_cache = torch.zeros(num_blocks, block_size, num_kv_heads, head_dim)
    v_cache = torch.zeros(num_blocks, block_size, num_kv_heads, head_dim)
    print(f"    KV cache 形状: ({num_blocks}, {block_size}, {num_kv_heads}, {head_dim})")
    print(f"    k_cache.shape  = {tuple(k_cache.shape)}")
    print(f"    k_cache.dtype  = {k_cache.dtype}")
    print(f"    k_cache 占用:  {k_cache.element_size() * k_cache.numel() / 1024 / 1024:.1f} MB × 2 = "
          f"{2 * k_cache.element_size() * k_cache.numel() / 1024 / 1024:.1f} MB")

    # 模拟 store_kvcache: 用 slot_mapping 写入
    # token 0 → slot 10, token 1 → slot 256 (block 1 pos 0), token 2 → slot 511 (block 1 pos 255)
    k_new = torch.randn(3, num_kv_heads, head_dim)
    v_new = torch.randn(3, num_kv_heads, head_dim)
    slots = torch.tensor([10, 256 + 0, 256 + 255], dtype=torch.int32)  # 3 tokens

    # 展开写入: k_cache[slot // block_size, slot % block_size] = k_new[idx]
    block_ids = slots // block_size  # [0, 1, 1]
    positions = slots % block_size    # [10, 0, 255]
    for idx in range(3):
        k_cache[block_ids[idx], positions[idx]] = k_new[idx]
        v_cache[block_ids[idx], positions[idx]] = v_new[idx]

    print(f"\n    写入 3 个 token 到 KV cache:")
    for idx in range(3):
        bid = block_ids[idx].item()
        pos = positions[idx].item()
        print(f"      token[{idx}] → slot={slots[idx].item()} → block[{bid}][{pos}] "
              f"k={k_new[idx, 0, :3].tolist()}")
    assert not k_cache[block_ids[0], positions[0]].eq(0).all()
    assert k_cache[0, 0].eq(0).all()  # 未写入位置仍为 0
    print(f"    [PASS] slot_mapping → block/position → KV cache 写入")
    print(f"    这正是 attention.py:L11-L30 Triton kernel 做的事：")
    print(f"      for each token: slot = slot_mapping[idx]; write(key, k_cache[slot * D])")


def main():
    import sys
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model_path:
        print("用法: python L07_attention.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model_path = os.path.expanduser(model_path)

    verify_slot_mapping_sentinel()
    verify_attention_branches()
    verify_prefix_cache_trigger()
    verify_with_real_context(model_path)

    print("\n" + "=" * 64)
    print("L07 全部断言通过 ✓")
    print("=" * 64)


if __name__ == "__main__":
    main()
