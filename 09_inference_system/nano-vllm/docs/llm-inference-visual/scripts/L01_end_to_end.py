#!/usr/bin/env python3
"""
L01 练习：从 LLM.generate 走到 step 循环

验证要点：
- LLM = LLMEngine（类别名）
- generate: for prompt in prompts → add_request → while loop step() → decode
- step: schedule → run → postprocess 三段式
- 返回 {"text": str, "token_ids": list[int]}

依赖：GPU + nano-vllm 包 + Qwen3-0.6B 模型权重
用法：python L01_end_to_end.py [model_path]
"""

import os
import sys

import torch
from nanovllm import LLM, SamplingParams
from nanovllm.engine.llm_engine import LLMEngine


def show_source(file_path, start, end):
    """读取 nano-vllm 源码中的指定行。"""
    # scripts/ → llm-inference-visual/ → docs/ → nano-vllm/
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    full = os.path.join(repo_root, file_path)
    if not os.path.exists(full):
        return []
    with open(full) as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[start - 1:end]]


def show_code_block(title, file_path, lines):
    """打印源码片段。"""
    print(f"  // {title}  ({file_path})")
    for l in lines:
        print(f"  {l}")
    print()


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model_path:
        print("用法: python L01_end_to_end.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model_path = os.path.expanduser(model_path)

    print("=" * 68)
    print("L01 验证：从 LLM.generate 走到 step 循环")
    print(f"模型: {model_path}    GPU: {torch.cuda.get_device_name(0)}")
    print("=" * 68)

    # ═══════════════════════════════════════════════════════════════
    # 1. LLM 就是 LLMEngine
    # ═══════════════════════════════════════════════════════════════
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  1. LLM 是 LLMEngine 的别名入口                              │")
    print("│     nanovllm/llm.py                                        │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("class alias", "nanovllm/llm.py",
                     show_source("nanovllm/llm.py", 1, 6))

    print(f"  >>> from nanovllm import LLM")
    print(f"  >>> issubclass(LLM, LLMEngine)  →  {issubclass(LLM, LLMEngine)}")
    print(f"  >>> LLM 不新增任何方法 (class LLM(LLMEngine): pass)")
    assert issubclass(LLM, LLMEngine)
    print("  [PASS] LLM 仅是 LLMEngine 的继承包装，所有逻辑在引擎中\n")

    # ═══════════════════════════════════════════════════════════════
    # 2. add_request: tokenize → Sequence → scheduler
    # ═══════════════════════════════════════════════════════════════
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  2. add_request: prompt → tokenize → Sequence → waiting     │")
    print("│     llm_engine.py:L43-L47                                  │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("add_request", "nanovllm/engine/llm_engine.py",
                     show_source("nanovllm/engine/llm_engine.py", 43, 48))

    # 初始化引擎
    llm = LLM(model_path, enforce_eager=True, tensor_parallel_size=1)

    # 演示 tokenize
    prompt = "Hello, nano-vllm!"
    token_ids = llm.tokenizer.encode(prompt)
    print(f"  >>> tokenizer.encode('{prompt}')\n"
          f"  {token_ids}\n")

    print(f"  add_request 的输入/输出契约:")
    print(f"    入: prompt(str) → tokenizer.encode → token_ids(list[int])")
    print(f"    入: SamplingParams → 控制温度、max_tokens")
    print(f"    出: Sequence(prompt, sampling_params) → scheduler.add(seq)")
    print(f"    Sequence 被推入 scheduler.waiting 队列 → 等待下一轮 step")
    print("  [READ] 具体 Sequence 字段见 L02\n")

    # ═══════════════════════════════════════════════════════════════
    # 3. step 三段式: schedule → run → postprocess
    # ═══════════════════════════════════════════════════════════════
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  3. step: 一次调度 → 一次执行 → 一次回写                     │")
    print("│     llm_engine.py:L49-L55                                  │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("step", "nanovllm/engine/llm_engine.py",
                     show_source("nanovllm/engine/llm_engine.py", 49, 55))

    print(f"  三段式数据流:")
    print(f"    ① schedule() → 从 waiting/running 选取 seqs, 决定 prefill 还是 decode")
    print(f"    ② model_runner.run() → 拼接张量 → Transformer 前向 → 采样 → token_ids")
    print(f"    ③ postprocess() → 回写 token、计数器、hash_blocks、回收 KV cache")
    print(f"")
    print(f"  num_tokens > 0  → 本轮是 prefill  (num_tokens = Σ num_scheduled_tokens)")
    print(f"  num_tokens < 0  → 本轮是 decode   (num_tokens = -len(seqs), 每 seq 1 token)")
    print("  [READ] 调度细节见 L03, 张量构建见 L05/L06\n")

    # ═══════════════════════════════════════════════════════════════
    # 4. generate 主循环
    # ═══════════════════════════════════════════════════════════════
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  4. generate: for 循环入队 → while step → decode 输出       │")
    print("│     llm_engine.py:L60-L90                                  │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("generate (入队)", "nanovllm/engine/llm_engine.py",
                     show_source("nanovllm/engine/llm_engine.py", 60, 70))
    show_code_block("generate (出队 & 返回)", "nanovllm/engine/llm_engine.py",
                     show_source("nanovllm/engine/llm_engine.py", 84, 91))

    # 跑一次真实推理
    params = SamplingParams(temperature=0.6, max_tokens=32)
    outputs = llm.generate(["Hello, nano-vllm!"], params)

    output = outputs[0]
    print(f"  >>> llm.generate(['Hello, nano-vllm!'], SamplingParams(...))\n"
          f"  >>> type(output) = {type(output).__name__}\n"
          f"  >>> sorted(output.keys()) = {sorted(output.keys())}\n"
          f"  >>> type(output['text']) = {type(output['text']).__name__}\n"
          f"  >>> type(output['token_ids']) = {type(output['token_ids']).__name__}\n"
          f"  >>> output['text'][:60] = {output['text'][:60]!r}\n"
          f"  >>> output['token_ids'][:8] = {output['token_ids'][:8]}\n")

    assert isinstance(output, dict)
    assert "text" in output and "token_ids" in output
    assert isinstance(output["text"], str)
    assert isinstance(output["token_ids"], list)
    print("  [PASS] 返回结构: dict with 'text' (str) + 'token_ids' (list)")

    # 展示 text 来自 tokenizer.decode(token_ids)
    decoded = llm.tokenizer.decode(output["token_ids"])
    print(f"\n  源码 L89: outputs = [{{'text': tokenizer.decode(token_ids), 'token_ids': token_ids}}]")
    print(f"  >>> tokenizer.decode(output['token_ids'])[:60]\n"
          f"  {decoded[:60]!r}")
    print(f"  >>> decoded == output['text']  →  {decoded == output['text']}")
    assert decoded == output["text"]
    print("  [PASS] text = tokenizer.decode(token_ids)\n")

    # ═══════════════════════════════════════════════════════════════
    # 5. prefill/decode 吞吐统计
    # ═══════════════════════════════════════════════════════════════
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  5. prefill/decode 吞吐的分开统计                            │")
    print("│     llm_engine.py:L76-L79 → tqdm 进度条                     │")
    print("└─────────────────────────────────────────────────────────────┘\n")

    show_code_block("throughput counters", "nanovllm/engine/llm_engine.py",
                     show_source("nanovllm/engine/llm_engine.py", 72, 80))

    print(f"  num_tokens > 0  → Prefill  = num_tokens / Δt  (一次性吞 prompt)")
    print(f"  num_tokens < 0  → Decode   = -num_tokens / Δt  (逐 token 产出)")
    print(f"  进度条上 Prefill/Decode 分开显示，可以看到两种模式的吞吐差")
    print("  [READ]")

    print("\n" + "=" * 68)
    print("L01 全部断言通过 ✓")
    print("=" * 68)


if __name__ == "__main__":
    main()
