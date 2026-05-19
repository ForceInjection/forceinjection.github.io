# 常见问题与排障指南

## 环境搭建

### flash-attn 编译占用内存过大或卡住

`pip install` 默认从源码编译 flash-attn，CPU 和内存开销极高（16 核 + 32GB 以下可能 OOM）。

**解决**：下载预编译 wheel 安装，不要从源码编译。

```bash
# 确认环境：Python 版本、CUDA 版本、PyTorch 版本
python -c "import sys; print(sys.version.split()[0])"
python -c "import torch; print(torch.__version__)"
# 输出示例：CPython 3.12, torch 2.8.0+cu128

# 去 GitHub releases 下载对应的 wheel（替换 cp312 / cu12 / torch2.8 为你的版本）
wget https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/\
flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl

# 如果 GitHub 不通，用代理
wget https://ghproxy.net/https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/\
flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl

# 安装
pip install flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl
```

### pip 安装 nano-vllm 时报 `ModuleNotFoundError: No module named 'torch'`

这是 flash-attn 的 `setup.py` 在构建时需要 torch，但 pip 还没有安装它。

**解决**：先安装 torch，再安装 nano-vllm。

```bash
pip install torch triton transformers
pip install flash_attn-xxx.whl   # 预编译 wheel，见上一条
pip install -e .                  # 最后装 nano-vllm
```

### Hugging Face 模型下载太慢或超时

从 Hugging Face 直接下载在国内网络下可能很慢或失败。

**解决 1**：用 modelscope 镜像（推荐）。

```bash
pip install modelscope
python -c "from modelscope import snapshot_download; \
  snapshot_download('qwen/Qwen3-0.6B', cache_dir='./Qwen3-0.6B/')"
# 下载后把子目录里的文件移到上层
mv ./Qwen3-0.6B/qwen/Qwen3-0___6B/* ./Qwen3-0.6B/
rm -rf ./Qwen3-0.6B/qwen/
```

**解决 2**：用 HF 镜像端点。

```bash
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download Qwen/Qwen3-0.6B \
  --local-dir ./Qwen3-0.6B/ --local-dir-use-symlinks False
```

### pip install 报 `externally-managed-environment` 或 `--break-system-packages`

macOS Homebrew Python 和某些 Linux 发行版会阻止全局 pip 安装。

**解决**：加 `--break-system-packages` 参数，或使用虚拟环境。

```bash
pip install --break-system-packages -e .
# 或
python -m venv .venv && source .venv/bin/activate && pip install -e .
```

## 运行时问题

### 运行脚本报 `ModuleNotFoundError: No module named 'nanovllm'`

需要在 nano-vllm 仓库根目录下以 editable 模式安装：

```bash
cd /path/to/nano-vllm
pip install -e .
```

### 运行 L01 或 verify_nanovllm.py 时 CUDA out of memory

Qwen3-0.6B 约需 1.4GB 显存放模型权重，加上 KV cache 约 3-4GB。4GB 以上显存可运行单个请求。

如果多请求并发 OOM，减少 `max_model_len` 或设置 `gpu_memory_utilization`：

```python
llm = LLM(model_path, enforce_eager=True, tensor_parallel_size=1,
          max_model_len=2048, gpu_memory_utilization=0.7)
```

### 脚本报 `用法: python xxx.py <model_path>` 但已设置了路径

需要先设置环境变量或传命令行参数：

```bash
# 方式 1：命令行参数
python L01_end_to_end.py /path/to/Qwen3-0.6B/

# 方式 2：环境变量
export NANOVLLM_MODEL_PATH=/path/to/Qwen3-0.6B/
python L01_end_to_end.py
```

在远端服务器上也可以用 `rsync` 同步脚本后运行：

```bash
rsync -avz docs/llm-inference-visual/scripts/ user@server:/path/to/scripts/
ssh user@server "cd /path/to/scripts && NANOVLLM_MODEL_PATH=/path/to/model bash run_all.sh --all"
```

## 脚本相关问题

### L02 / L04 脚本需要 nano-vllm 包，能不能不装就跑？

L02 和 L04 使用 `from nanovllm.engine.sequence import Sequence` 等真实 nano-vllm 模块来验证行为。如果想纯 Python 体验这些概念，可以只用 L03/L05/L06/L07/L08 里的前几节（纯 Python 模拟部分），它们不依赖 GPU。

### run_all.sh 中 L01 跑失败了

L01 需要 GPU。如果只想跑 CPU 脚本，不加 `--all`：

```bash
bash run_all.sh        # 仅 L02-L08，CPU 或 torch
bash run_all.sh --all  # 全部，含 L01 (GPU)
```
