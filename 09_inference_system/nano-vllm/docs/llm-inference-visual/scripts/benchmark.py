#!/usr/bin/env python3
"""
nano-vllm 性能基准测试，对齐 bench.py。

用法：
  python benchmark.py <model_path>
  python benchmark.py <model_path> --num-seqs 128 --max-input 512 --max-output 256
  NANOVLLM_MODEL_PATH=/path/to/model python benchmark.py

验证：CUDA Graph + 连续批处理吞吐
"""

import argparse
import os
import sys
import time
from random import randint, seed


def parse_args():
    p = argparse.ArgumentParser(description="nano-vllm benchmark")
    p.add_argument("model", nargs="?", default=None,
                   help="模型路径（或设置 NANOVLLM_MODEL_PATH）")
    p.add_argument("--num-seqs", type=int, default=256,
                   help="总请求数 (default: 256)")
    p.add_argument("--max-input", type=int, default=1024,
                   help="最大输入长度 (default: 1024)")
    p.add_argument("--max-output", type=int, default=1024,
                   help="最大输出长度 (default: 1024)")
    p.add_argument("--max-model-len", type=int, default=4096,
                   help="模型最大上下文长度 (default: 4096)")
    p.add_argument("--no-cuda-graph", action="store_true",
                   help="禁用 CUDA Graph (enforce_eager=True)")
    p.add_argument("--tp", type=int, default=1,
                   help="Tensor Parallel size (default: 1)")
    return p.parse_args()


def main():
    args = parse_args()

    # 模型路径：命令行 > 环境变量
    model = args.model or os.environ.get("NANOVLLM_MODEL_PATH", "")
    if not model:
        print("请指定模型路径: python benchmark.py <model_path>", file=sys.stderr)
        print("或设置环境变量: export NANOVLLM_MODEL_PATH=/path/to/model", file=sys.stderr)
        sys.exit(1)
    model = os.path.expanduser(model)

    import torch
    from nanovllm import LLM, SamplingParams

    print("=" * 60)
    print("nano-vllm Benchmark")
    print(f"Model:       {model}")
    print(f"GPU:         {torch.cuda.get_device_name(0)}")
    print(f"Seqs:        {args.num_seqs}")
    print(f"Input:       [100, {args.max_input}]")
    print(f"Output:      [100, {args.max_output}]")
    print(f"MaxLen:      {args.max_model_len}")
    print(f"CUDA Graph:  {not args.no_cuda_graph}")
    print(f"TP size:     {args.tp}")
    print("=" * 60)

    seed(0)
    llm = LLM(model, enforce_eager=args.no_cuda_graph,
              max_model_len=args.max_model_len,
              tensor_parallel_size=args.tp)

    prompt_token_ids = [
        [randint(0, 10000) for _ in range(randint(100, args.max_input))]
        for _ in range(args.num_seqs)
    ]
    sampling_params = [
        SamplingParams(temperature=0.6, ignore_eos=True,
                       max_tokens=randint(100, args.max_output))
        for _ in range(args.num_seqs)
    ]

    print("\nWarmup...")
    llm.generate(["Benchmark: "], SamplingParams())

    print("Running...")
    t = time.time()
    llm.generate(prompt_token_ids, sampling_params, use_tqdm=True)
    elapsed = time.time() - t

    total_tokens = sum(sp.max_tokens for sp in sampling_params)
    throughput = total_tokens / elapsed

    print(f"\nTotal: {total_tokens} tok  Time: {elapsed:.2f}s  "
          f"Throughput: {throughput:.1f} tok/s")


if __name__ == "__main__":
    main()
