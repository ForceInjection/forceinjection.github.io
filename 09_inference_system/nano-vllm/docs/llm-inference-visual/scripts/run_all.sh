#!/bin/bash
# run_all.sh — 运行所有课程练习脚本
# 用法:
#   ./run_all.sh           # 仅运行 CPU-only 脚本 (L02-L08)
#   ./run_all.sh --all     # 包含 L01 (需要 GPU + 模型)
#   ./run_all.sh L03 L05   # 运行指定脚本

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

run_script() {
    local script="$1"
    echo -e "${GREEN}=== Running: $(basename "$script") ===${NC}"
    if python "$script"; then
        echo -e "${GREEN}=== $(basename "$script"): PASS ===${NC}\n"
    else
        echo -e "${RED}=== $(basename "$script"): FAIL ===${NC}\n"
        return 1
    fi
}

if [ $# -eq 0 ]; then
    # 默认：运行所有 CPU-only 脚本
    SCRIPTS=(L02_sequence.py L03_scheduler.py L04_block_manager.py L05_prefill_batching.py L06_decode.py L07_attention.py L08_optimizations.py)
elif [ "$1" = "--all" ]; then
    SCRIPTS=(L01_end_to_end.py L02_sequence.py L03_scheduler.py L04_block_manager.py L05_prefill_batching.py L06_decode.py L07_attention.py L08_optimizations.py)
else
    SCRIPTS=()
    for arg in "$@"; do
        # 支持 L03 或 L03_scheduler.py 两种形式
        if [[ "$arg" != *.py ]]; then
            matches=("$SCRIPT_DIR"/${arg}_*.py)
            if [ ${#matches[@]} -eq 1 ]; then
                SCRIPTS+=("${matches[0]}")
            else
                echo "No unique match for: $arg"
                exit 1
            fi
        else
            SCRIPTS+=("$SCRIPT_DIR/$arg")
        fi
    done
fi

FAILED=0
for script in "${SCRIPTS[@]}"; do
    run_script "$script" || ((FAILED++))
done

echo "========================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All ${#SCRIPTS[@]} scripts passed${NC}"
else
    echo -e "${RED}${FAILED}/${#SCRIPTS[@]} scripts failed${NC}"
    exit 1
fi
