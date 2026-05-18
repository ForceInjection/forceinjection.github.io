#!/usr/bin/env python3
"""
nano-vllm 功能验证脚本，覆盖 README 中描述的典型用法。

用法：
  python verify_nanovllm.py <model_path>
  python verify_nanovllm.py ~/autodl-tmp/Qwen3-0.6B/
"""

import os
import sys
import time


def check_env(model_path):
    """检查环境。"""
    import torch
    print("=" * 64)
    print("nano-vllm 功能验证")
    print(f"模型路径: {model_path}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"显存: {torch.cuda.get_device_properties(0).total_memory // 2**30} GiB")
    assert os.path.isdir(model_path), f"模型路径不存在: {model_path}"


# ── Case 1: Quick Start ──────────────────────────────────────────────

def case_quick_start(llm):
    """README Quick Start 用法：字符串 prompt，单条请求。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 1: Quick Start — 单条字符串 prompt                     │")
    print("└─────────────────────────────────────────────────────────────┘")

    sampling_params = SamplingParams(temperature=0.6, max_tokens=256)
    outputs = llm.generate(["Hello, Nano-vLLM."], sampling_params)
    output = outputs[0]

    print(f"  prompt: 'Hello, Nano-vLLM.'")
    print(f"  completion (前 80 字符): {output['text'][:80]!r}")
    print(f"  token_ids 长度: {len(output['token_ids'])}")
    assert isinstance(output, dict)
    assert "text" in output and "token_ids" in output
    assert len(output["token_ids"]) <= 256
    print("  [PASS]")


# ── Case 2: 多请求并发 ───────────────────────────────────────────────

def case_multi_prompt(llm):
    """多条 prompt 并发推理。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 2: 多请求并发                                          │")
    print("└─────────────────────────────────────────────────────────────┘")

    params = SamplingParams(temperature=0.6, max_tokens=64)
    prompts = [
        "introduce yourself",
        "list all prime numbers within 100",
        "explain what is machine learning",
    ]
    outputs = llm.generate(prompts, params)

    print(f"  请求数: {len(prompts)}")
    for i, out in enumerate(outputs):
        tlen = len(out["token_ids"])
        print(f"    [{i}] 生成 {tlen} tokens: {out['text'][:50]!r}...")
        assert isinstance(out["text"], str)
        assert isinstance(out["token_ids"], list)
        assert 1 <= tlen <= 64
    assert len(outputs) == len(prompts)
    print("  [PASS]")


# ── Case 3: token_ids 输入 ───────────────────────────────────────────

def case_token_ids_input(llm):
    """直接用 token_ids 作为输入（跳过 tokenizer）。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 3: token_ids 输入                                      │")
    print("└─────────────────────────────────────────────────────────────┘")

    prompt = "Hello world"
    token_ids = llm.tokenizer.encode(prompt)
    print(f"  prompt: {prompt!r} → token_ids: {token_ids}")

    params = SamplingParams(temperature=0.6, max_tokens=32)
    outputs = llm.generate([token_ids], params)

    print(f"  completion token_ids: {outputs[0]['token_ids']}")
    assert len(outputs) == 1
    assert len(outputs[0]["token_ids"]) <= 32
    print("  [PASS]")


# ── Case 4: 不同 SamplingParams ──────────────────────────────────────

def case_sampling_params(llm):
    """验证 temperature / max_tokens / ignore_eos 参数。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 4: SamplingParams 参数                                  │")
    print("└─────────────────────────────────────────────────────────────┘")

    prompt = "Once upon a time"
    results = []

    for temp, max_tok, label in [
        (0.6, 16, "temperature=0.6, max_tokens=16"),
        (1.0, 32, "temperature=1.0, max_tokens=32"),
        (0.6, 16, "temperature=0.6, max_tokens=16 (ignore_eos)"),
    ]:
        ignore = (label.endswith("(ignore_eos)"))
        params = SamplingParams(temperature=temp, max_tokens=max_tok, ignore_eos=ignore)
        out = llm.generate([prompt], params)[0]
        tlen = len(out["token_ids"])
        print(f"  {label}: 生成 {tlen} tokens")
        assert tlen <= max_tok
        results.append(tlen)

    # ignore_eos 应该不会因为 EOS 提前停止
    assert results[2] >= results[0] or results[2] == 16  # 可能是 16 或更长，但 ≤16
    print("  [PASS]")


# ── Case 5: 吞吐统计 ─────────────────────────────────────────────────

def case_throughput(llm):
    """验证 prefill/decode 吞吐可观测。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 5: 吞吐统计                                            │")
    print("└─────────────────────────────────────────────────────────────┘")

    # 少量请求快速跑
    params = SamplingParams(temperature=0.6, max_tokens=32)
    t0 = time.perf_counter()
    outputs = llm.generate(["The capital of France is"] * 4, params, use_tqdm=False)
    elapsed = time.perf_counter() - t0
    total_tokens = sum(len(o["token_ids"]) for o in outputs)

    print(f"  4 条请求, 共 {total_tokens} output tokens, 耗时 {elapsed:.2f}s")
    print(f"  吞吐: {total_tokens / elapsed:.1f} tok/s")
    assert len(outputs) == 4
    assert total_tokens > 0
    assert elapsed < 60  # RTX 5090 应该很快
    print("  [PASS]")


# ── Case 6: Chat Template ────────────────────────────────────────────

def case_chat_template(llm):
    """使用 chat template 构造 prompt（对齐 example.py）。"""
    from nanovllm import SamplingParams

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  Case 6: Chat Template                                       │")
    print("└─────────────────────────────────────────────────────────────┘")

    prompt = llm.tokenizer.apply_chat_template(
        [{"role": "user", "content": "What is 2+2?"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    params = SamplingParams(temperature=0.6, max_tokens=64)
    output = llm.generate([prompt], params)[0]

    print(f"  chat prompt (前 60 字符): {prompt[:60]!r}...")
    print(f"  completion: {output['text'][:80]!r}")
    assert len(output["token_ids"]) <= 64
    print("  [PASS]")


# ── 主流程 ───────────────────────────────────────────────────────────

def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model_path:
        print("用法: python verify_nanovllm.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model_path = os.path.expanduser(model_path)

    check_env(model_path)

    from nanovllm import LLM
    llm = LLM(model_path, enforce_eager=True, tensor_parallel_size=1)

    case_quick_start(llm)
    case_multi_prompt(llm)
    case_token_ids_input(llm)
    case_sampling_params(llm)
    case_chat_template(llm)
    case_throughput(llm)

    print("\n" + "=" * 64)
    print("全部 6 个用例通过 ✓")
    print("=" * 64)


if __name__ == "__main__":
    main()
