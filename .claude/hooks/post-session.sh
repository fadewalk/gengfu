#!/bin/zsh
# Claude Code Stop Hook - 更新会话到项目 wiki
# 同一 session_id 写同一文件，每次 Stop 覆盖为最新内容

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
MARKER_DIR="$PROJECT_DIR/.claude/hooks/.session"

# 从 stdin 解析 session_id
INPUT=$(cat 2>/dev/null || true)
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")
SESSION_SHORT="${SESSION_ID:0:8}"

MARKER_FILE="$MARKER_DIR/current-${SESSION_SHORT}"

if [ ! -f "$MARKER_FILE" ]; then
    echo "⚠️ 未找到会话标记 [${SESSION_SHORT}]，跳过保存" >&2
    exit 0
fi

# 读取标记
source "$MARKER_FILE"
MD_FILE="${MD_FILE:-}"
if [ -z "$MD_FILE" ]; then
    echo "⚠️ 会话标记无效，跳过保存" >&2
    exit 0
fi

PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-unknown}" 2>/dev/null || echo "unknown")

# 覆盖写入
cat > "$MD_FILE" << HEADER
---
title: "Claude Code Session - ${PROJECT_NAME}"
date: $(date +"%Y-%m-%d %H:%M:%S")
project: "${PROJECT_NAME}"
session: "${SESSION_SHORT}"
tags: [claude-code, session]
---

# Claude Code Session - ${PROJECT_NAME}

> 会话时间：$(date +"%Y-%m-%d %H:%M:%S")
> 项目：\`${PROJECT_NAME}\`
> Session：\`${SESSION_SHORT}\`

---

HEADER

if [ -n "$INPUT" ]; then
    echo "$INPUT" >> "$MD_FILE"
else
    echo "_（自动导出完成）_" >> "$MD_FILE"
fi

echo "✅ 会话已更新 [${SESSION_SHORT}]：$MD_FILE" >&2
