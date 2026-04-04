#!/bin/zsh
# Claude Code SessionStart Hook - 创建会话标记
# stdin 接收 JSON，含 session_id 字段

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
CHAT_DIR="$PROJECT_DIR/wiki/claude-code/sessions"
MARKER_DIR="$PROJECT_DIR/.claude/hooks/.session"

mkdir -p "$CHAT_DIR" "$MARKER_DIR"

# 从 stdin 解析 session_id
INPUT=$(cat 2>/dev/null || true)
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")

PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-unknown}" 2>/dev/null || echo "unknown")

# 用 session_id 作为文件名，同一会话始终同一个文件
MD_FILE="${CHAT_DIR}/${SESSION_ID:0:8}-${PROJECT_NAME}.md"

# 写入会话标记
cat > "$MARKER_DIR/current-${SESSION_ID:0:8}" << EOF
SESSION_ID=${SESSION_ID}
PROJECT_NAME=${PROJECT_NAME}
MD_FILE=${MD_FILE}
EOF

# 创建初始文件
cat > "$MD_FILE" << HEADER
---
title: "Claude Code Session - ${PROJECT_NAME}"
date: $(date +"%Y-%m-%d %H:%M:%S")
project: "${PROJECT_NAME}"
session: "${SESSION_ID:0:8}"
tags: [claude-code, session]
---

# Claude Code Session - ${PROJECT_NAME}

> 会话时间：$(date +"%Y-%m-%d %H:%M:%S")
> 项目：\`${PROJECT_NAME}\`
> Session：\`${SESSION_ID:0:8}\`

---

HEADER

echo "✅ 会话已启动 [${SESSION_ID:0:8}]：$MD_FILE" >&2
