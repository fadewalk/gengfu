#!/bin/zsh
# Claude Code Stop Hook - 追加/更新会话到项目 wiki
# 同一个会话写入同一个文件，每次 Stop 覆盖为最新内容

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
MARKER_FILE="$PROJECT_DIR/.claude/hooks/.session/current"

# 读取 stdin（Claude Code 通过管道传递 stop 事件的 JSON 数据）
STDIN_DATA=""
if [ ! -t 0 ]; then
    STDIN_DATA=$(cat 2>/dev/null || true)
fi

# 检查会话标记是否存在
if [ ! -f "$MARKER_FILE" ]; then
    echo "⚠️ 未找到会话标记，跳过保存" >&2
    exit 0
fi

# 从标记文件读取会话信息
source "$MARKER_FILE"

# 确保 MD_FILE 变量存在
MD_FILE="${MD_FILE:-}"
if [ -z "$MD_FILE" ]; then
    echo "⚠️ 会话标记无效，跳过保存" >&2
    exit 0
fi

# 确保目录存在
mkdir -p "$(dirname "$MD_FILE")"

# 获取项目名
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-unknown}" 2>/dev/null || echo "unknown")

# 写入文件头 + 最新内容（覆盖模式）
cat > "$MD_FILE" << HEADER
---
title: "Claude Code Session - ${PROJECT_NAME}"
date: $(date +"%Y-%m-%d %H:%M:%S")
project: "${PROJECT_NAME}"
tags: [claude-code, session]
---

# Claude Code Session - ${PROJECT_NAME}

> 会话时间：$(date +"%Y-%m-%d %H:%M:%S")
> 项目：\`${PROJECT_NAME}\`

---

HEADER

# 追加会话数据
if [ -n "$STDIN_DATA" ]; then
    echo "$STDIN_DATA" >> "$MD_FILE"
else
    echo "_（自动导出完成）_" >> "$MD_FILE"
fi

echo "✅ 会话已更新：$MD_FILE" >&2
