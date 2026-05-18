#!/bin/bash
# 远端服务器环境搭建脚本
# 目标环境：RTX 5090, miniconda3 Python 3.12.3, torch 2.8.0+cu128
#
# 用法: 在远端服务器上执行
#   bash setup_remote.sh

set -euo pipefail

# ---------- 环境变量 ----------
CONDA_PYTHON=/root/miniconda3/bin/python
CONDA_PIP=/root/miniconda3/bin/pip
MODEL_DIR=/root/autodl-tmp/Qwen3-0.6B
NANO_VLLM_DIR=/root/nano-vllm

echo "=== Step 1: 安装 modelscope ==="
$CONDA_PIP install modelscope

echo "=== Step 2: 下载 Qwen3-0.6B 模型 (约 1.4GB) ==="
rm -rf "$MODEL_DIR"
mkdir -p "$MODEL_DIR"
$CONDA_PYTHON -c "
from modelscope import snapshot_download
snapshot_download('qwen/Qwen3-0.6B', cache_dir='$MODEL_DIR/')
"
# modelscope 会把文件下载到子目录，需要移动到上层
MODEL_SUBDIR=$(find "$MODEL_DIR" -name "*.safetensors" -type f | head -1 | xargs dirname 2>/dev/null || true)
if [ -n "$MODEL_SUBDIR" ] && [ "$MODEL_SUBDIR" != "$MODEL_DIR" ]; then
    mv "$MODEL_SUBDIR"/* "$MODEL_DIR/" && rm -rf "${MODEL_SUBDIR}" 2>/dev/null || true
fi
echo "Model files:"
ls "$MODEL_DIR"

echo "=== Step 3: 安装 nano-vllm ==="
$CONDA_PIP install -e "$NANO_VLLM_DIR"

echo "=== Step 4: 验证 ==="
$CONDA_PYTHON -c "
import torch
print(f'torch: {torch.__version__}, cuda: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name(0)}')
"
$CONDA_PYTHON -c "from nanovllm import LLM; print('nanovllm import OK')"
echo ""
echo "=== 搭建完成 ==="
echo "模型路径: $MODEL_DIR"
echo "运行脚本: cd $NANO_VLLM_DIR/docs/llm-inference-visual/scripts && bash run_all.sh --all"
