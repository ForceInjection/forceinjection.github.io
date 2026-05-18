#!/usr/bin/env python3
"""
L03 练习：Scheduler 的队列、chunked prefill 与 preempt

验证要点：
- prefill 从 waiting 队首取 seq，按 max_num_batched_tokens 限制拼 batch
- 除首个 seq 外不允许 chunked prefill (remaining < num_tokens and scheduled_seqs → break)
- decode 按 FIFO 从 running 取 seq，block 不够时 preempt

依赖：无（纯 Python 模拟）
用法：python L03_scheduler.py
"""

from collections import deque
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


# ── prefill 模拟（对齐 scheduler.py:L29-L55）──────────────────────────

def simulate_prefill(prompt_lens, max_num_batched_tokens,
                     num_cached_tokens=None):
    if num_cached_tokens is None:
        num_cached_tokens = [0] * len(prompt_lens)

    scheduled = []
    remaining = max_num_batched_tokens

    for i, (n, cached) in enumerate(zip(prompt_lens, num_cached_tokens)):
        num_tokens = n - cached
        if remaining == 0:
            break
        if remaining < num_tokens and scheduled:
            break  # L42-L43: only chunked prefill for the first seq
        scheduled_tokens = min(num_tokens, remaining)
        scheduled.append((i, scheduled_tokens))
        remaining -= scheduled_tokens

    return scheduled, remaining


# ── decode 模拟（对齐 scheduler.py:L57-L73）───────────────────────────

def simulate_decode_step(running, free_block_ids, block_size=4):
    """
    模拟一次 decode step（对齐 scheduler.py:L57-L73）。
    关键: preempt 队尾 seq 时会释放它的 block，让当前 seq 可以继续。
    """
    scheduled = []
    preempted = []
    log = []

    free = list(free_block_ids)
    # 每个 seq 占用的 block 数: ceil(length / block_size)
    seq_blocks = {seq_id: (length + block_size - 1) // block_size
                  for seq_id, length in running}

    while running:
        seq_id, length = running.popleft()
        needs_block = (length % block_size == 1)

        # 如果 free 不够且需要新 block，尝试 preempt
        while needs_block and len(free) < 1:
            if running:
                # preempt 队尾 seq，回收它的 blocks
                victim_id, victim_len = running.pop()
                freed = seq_blocks.pop(victim_id)
                for _ in range(freed):
                    free.append(f"b{victim_id}")
                preempted.append(victim_id)
                log.append(f"    preempt seq[{victim_id}] (len={victim_len}, {freed} blocks) → "
                           f"free 增为 {len(free)}")
            else:
                # 只剩自己，自身也被 preempt
                preempted.append(seq_id)
                log.append(f"    seq[{seq_id}] len={length}: 需新 block 但无 free 且无其他 seq → 自身 preempt")
                return scheduled, preempted, log

        # can_append 成功 → 分配并调度
        if needs_block:
            blk = free.pop(0)
            log.append(f"    seq[{seq_id}] len={length}: 跨边界 → 分配 {blk} → free 剩 {len(free)}")
        else:
            log.append(f"    seq[{seq_id}] len={length}: 同 block → 无需分配 → free={len(free)}")
        new_len = length + 1
        scheduled.append((seq_id, new_len))
        seq_blocks[seq_id] = (new_len + block_size - 1) // block_size

    return scheduled, preempted, log


# ── 验证 1: 基本批拼接 ────────────────────────────────────────────────

def verify_basic_batching():
    print("=" * 64)
    print("L03 验证：Scheduler — prefill 批拼接 + chunked prefill + preempt")
    print("=" * 64)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. prefill 基本批拼接                                      │")
    print("│     对齐 scheduler.py:L29-L55                               │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("schedule() prefill 分支", "nanovllm/engine/scheduler.py",
                     show_source("nanovllm/engine/scheduler.py", 29, 56))

    for label, prompts, max_batch in [
        ("三条都能塞入", [300, 300, 300], 1000),
        ("第一条被 chunk", [1000, 500, 500], 800),
    ]:
        scheduled, remaining = simulate_prefill(prompts, max_batch)
        print(f"\n  {label}: prompts={prompts}, max_batch={max_batch}")
        print(f"    调度结果: scheduled={scheduled}")
        print(f"    剩余 token 预算: {remaining}")
        for i, tok in scheduled:
            print(f"      seq[{i}] 本轮处理 {tok} token")


# ── 验证 2: chunked prefill 限制 ──────────────────────────────────────

def verify_chunked_prefill_constraint():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  2. chunked prefill 限制: 仅 batch 中第一条可被切分           │")
    print("│     scheduler.py:L42: remaining < num_tokens && scheduled → break │")
    print("└─────────────────────────────────────────────────────────────┘")

    scheduled, remaining = simulate_prefill([300, 800, 200], max_num_batched_tokens=1000)
    print(f"\n  prompts=[300, 800, 200], max_batch=1000")
    print(f"  逐条推演:")
    print(f"    seq[0]: 300 token ≤ 1000 → ✓ scheduled=300, remaining=700")
    print(f"    seq[1]: 800 token > remaining=700 且 scheduled 非空 → ✗ break!")
    print(f"    seq[2]: 永不检查")
    print(f"  结果: scheduled={scheduled}")
    assert scheduled == [(0, 300)]


# ── 验证 3: prefix cache 对批拼接的影响 ───────────────────────────────

def verify_prefix_cache_batching():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  3. prefix cache 命中减少本轮 token 消耗                      │")
    print("│     scheduler.py:L35-L39: num_tokens = n - cached_blocks*block_size │")
    print("└─────────────────────────────────────────────────────────────┘")

    scheduled, remaining = simulate_prefill(
        prompt_lens=[1000, 800],
        max_num_batched_tokens=1000,
        num_cached_tokens=[512, 0],
    )
    print(f"\n  seq[0]: prompt=1000, 已缓存 512 → 还需 488 token")
    print(f"  seq[1]: prompt=800,  未缓存     → 还需 800 token")
    print(f"  488 + 800 = 1288 > max_batch=1000 → seq[1] 放不下")
    print(f"  结果: scheduled={scheduled}, remaining={remaining}")
    assert scheduled == [(0, 488)]
    assert remaining == 512


# ── 验证 4: decode 调度 + preempt ────────────────────────────────────

def verify_decode_and_preempt():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  4. decode 调度 + preempt（对齐 scheduler.py:L57-L79）        │")
    print("│     can_append: free_blocks >= (len(seq) % block_size == 1) │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("schedule() decode 分支 + preempt()", "nanovllm/engine/scheduler.py",
                     show_source("nanovllm/engine/scheduler.py", 57, 80))

    block_size = 4
    running = deque([(0, 1), (1, 4), (2, 5)])  # (seq_id, current_length)

    # ── 场景 A: 有足够空闲 block ──
    print(f"\n  场景 A: free_blocks=[10, 11], running={list(running)}, block_size={block_size}")
    scheduled, preempted, log = simulate_decode_step(running, [10, 11], block_size)
    print("  ")
    for line in log:
        print(line)
    print(f"  调度结果: scheduled={list(scheduled)}, preempted={preempted}")
    assert len(scheduled) == 3
    assert len(preempted) == 0
    print("  [PASS] 空闲足够 → 三条全部 decode")

    # ── 场景 B: 空闲块不足，触发 preempt ──
    running = deque([(0, 1), (1, 4), (2, 8)])
    print(f"\n  场景 B: free_blocks=[], running={list(running)}, block_size={block_size}")
    print(f"    seq[2] len=8 → 占 2 blocks; seq[1] len=4 → 占 1 block; seq[0] len=1 → 占 1 block")
    scheduled, preempted, log = simulate_decode_step(running, [], block_size)
    print("")
    for line in log:
        print(line)
    print(f"  结果: scheduled={scheduled}, preempted={preempted}")
    # seq[0](len=1): needs_block, free=[] → preempt seq[2](len=8, 2 blocks) → free has 2 blocks
    # seq[0] now can allocate → scheduled
    # seq[1](len=4): no_new_block → scheduled
    # seq[2] was preempted
    assert len(scheduled) == 2, f"expected 2, got {len(scheduled)}"
    assert preempted == [2], f"expected seq[2] preempted, got {preempted}"
    print("  [PASS] seq[2] 被 preempt → 回收 blocks → seq[0]/seq[1] 继续 decode")

    # ── 场景 C: len%4 ≠ 1，不需新 block ──
    print(f"\n  场景 C: free_blocks=[], running=[(0, 6)], block_size={block_size}")
    print(f"    seq[0] len=6, 6%4=2 ≠ 1 → 不需新 block → can_append=True")
    running_c = deque([(0, 6)])
    scheduled, preempted, log = simulate_decode_step(running_c, [], block_size)
    for line in log:
        print(line)
    assert len(scheduled) == 1
    assert len(preempted) == 0
    print(f"  [PASS]")

    # ── 场景 D: 只剩自己且需要新 block，自身被 preempt ──
    print(f"\n  场景 D: free_blocks=[], running=[(0, 5)], block_size={block_size}")
    print(f"    seq[0] len=5, 5%4=1 → 需要新 block, free=[] → 自身 preempt")
    running_d = deque([(0, 5)])
    scheduled, preempted, log = simulate_decode_step(running_d, [], block_size)
    for line in log:
        print(line)
    assert len(scheduled) == 0
    assert preempted == [0]
    print(f"  [PASS]")


# ── 验证 5: preempt 状态机 ────────────────────────────────────────────

def verify_preempt_state_machine():
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  5. preempt 状态机（对齐 scheduler.py:L75-L79）              │")
    print("└─────────────────────────────────────────────────────────────┘")

    print(f"""
    preempt(seq) 四步:
      ① seq.status  = WAITING     # RUNNING → WAITING
      ② seq.is_prefill = True     # 下一轮重新 prefill
      ③ block_manager.deallocate  # 释放所有 KV cache block
      ④ waiting.appendleft(seq)   # 插回队首，优先重试

    类比 OS: preempt ≈ swap out → swap in
    差异: LLM 的 KV cache 可重算，preempt 只释放 block
          不用写"交换区"，下一轮 prefill 重算即可恢复
    """)


# ── 验证 6: 真实 Scheduler 对比 ──────────────────────────────────────

def verify_with_real_scheduler(model_path):
    """用真实 Scheduler 跑一次，输出和模拟结果对比。"""
    from nanovllm.config import Config
    from nanovllm.engine.scheduler import Scheduler
    from nanovllm.engine.sequence import Sequence
    from nanovllm.sampling_params import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  6. 真实 Scheduler 对比验证                                  │")
    print("│     直接调用 scheduler.add() → schedule() → postprocess()   │")
    print("└─────────────────────────────────────────────────────────────┘")

    # 构造 Config（用真实模型路径，但手动设 num_kvcache_blocks）
    config = Config(model_path, max_num_batched_tokens=1000, max_num_seqs=8,
                    kvcache_block_size=256)
    config.num_kvcache_blocks = 100  # 足够多，避免 preempt 干扰
    Sequence.block_size = config.kvcache_block_size

    scheduler = Scheduler(config)
    print(f"\n  >>> config.max_num_batched_tokens = {config.max_num_batched_tokens}")
    print(f"  >>> config.max_num_seqs = {config.max_num_seqs}")
    print(f"  >>> config.kvcache_block_size = {config.kvcache_block_size}")
    print(f"  >>> config.num_kvcache_blocks = {config.num_kvcache_blocks}")

    # ── 场景: 3 条 seq，max_batch=1000 ──
    print(f"\n  ▸ 场景: 3 条 seq (200, 300, 400 tokens), max_batch=1000")
    sp = SamplingParams(temperature=0.6, max_tokens=64)

    # 构造 prompt token_ids
    seqs = [
        Sequence(list(range(200)), sp),
        Sequence(list(range(300)), sp),
        Sequence(list(range(400)), sp),
    ]

    print(f"    创建 Sequence:")
    for i, s in enumerate(seqs):
        print(f"      seq[{i}]: num_tokens={s.num_tokens}, status={s.status.name}")

    # add 到 scheduler
    for s in seqs:
        scheduler.add(s)
    print(f"    waiting 队列长度: {len(scheduler.waiting)}, running: {len(scheduler.running)}")

    # 调用真实的 schedule()
    scheduled_seqs, is_prefill = scheduler.schedule()
    num_tokens = sum(seq.num_scheduled_tokens for seq in scheduled_seqs) if is_prefill else -len(scheduled_seqs)

    print(f"\n  >>> scheduled_seqs, is_prefill = scheduler.schedule()")
    print(f"      is_prefill = {is_prefill}")
    print(f"      调度了 {len(scheduled_seqs)} 条 seq:")
    for i, s in enumerate(scheduled_seqs):
        print(f"        seq[{i}]: num_tokens={s.num_tokens}, "
              f"num_scheduled_tokens={s.num_scheduled_tokens}, "
              f"num_cached_tokens={s.num_cached_tokens}, "
              f"status={s.status.name}")

    # 对比模拟
    print(f"\n  ▸ 模拟 vs 真实对比:")
    sim_result, _ = simulate_prefill([200, 300, 400], max_num_batched_tokens=1000)
    print(f"    模拟预期: scheduled={sim_result}")
    real_result = [(i, s.num_scheduled_tokens) for i, s in enumerate(scheduled_seqs)]
    print(f"    真实调度: scheduled={real_result}")

    assert len(scheduled_seqs) == 3, f"应调度 3 条, 实际 {len(scheduled_seqs)}"
    assert real_result == sim_result, f"模拟 {sim_result} ≠ 真实 {real_result}"
    print(f"    [PASS] 真实 Scheduler 输出和模拟一致")

    # ── 跑 postprocess + 下一轮 decode ──
    print(f"\n  ▸ 模拟一轮 postprocess + decode:")
    # 假 token_ids（随机）
    token_ids = [100 + i for i in range(len(scheduled_seqs))]
    scheduler.postprocess(scheduled_seqs, token_ids, is_prefill)

    print(f"    postprocess 后:")
    print(f"      waiting: {len(scheduler.waiting)}, running: {len(scheduler.running)}")
    for i, s in enumerate(seqs):
        print(f"      seq[{i}]: status={s.status.name}, num_tokens={s.num_tokens}")

    # 下一轮 decode
    scheduled_seqs2, is_prefill2 = scheduler.schedule()
    print(f"\n    下一轮 schedule(): is_prefill={is_prefill2}, seqs={len(scheduled_seqs2)}")
    for i, s in enumerate(scheduled_seqs2):
        print(f"      seq: num_scheduled_tokens={s.num_scheduled_tokens} (应为 1, decode)")
        assert s.num_scheduled_tokens == 1
    print(f"    [PASS] decode 每 seq 处理 1 token")


def main():
    import sys
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model_path:
        print("用法: python L03_scheduler.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model_path = os.path.expanduser(model_path)

    verify_basic_batching()
    verify_chunked_prefill_constraint()
    verify_prefix_cache_batching()
    verify_decode_and_preempt()
    verify_preempt_state_machine()
    verify_with_real_scheduler(model_path)

    print("\n" + "=" * 64)
    print("L03 全部断言通过 ✓")
    print("=" * 64)


if __name__ == "__main__":
    main()
