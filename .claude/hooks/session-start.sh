#!/bin/zsh
# Claude Code SessionStart Hook - 创建会话标记
# 记录当前会话的文件名，供 Stop 钩子使用

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
CHAT_DIR="$PROJECT_DIR/wiki/claude-code/sessions"
MARKER_DIR="$PROJECT_DIR/.claude/hooks/.session"

mkdir -p "$CHAT_DIR" "$MARKER_DIR"

SESSION_DATE=$(date +"%Y-%m-%d")
SESSION_TIME=$(date +"%H%M%S")
SESSION_ID="${SESSION_DATE}-${SESSION_TIME}"
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-unknown}" 2>/dev/null || echo "unknown")

# 写入会话标记
cat > "$MARKER_DIR/current" << EOF
SESSION_ID=${SESSION_ID}
PROJECT_NAME=${PROJECT_NAME}
CHAT_DIR=${CHAT_DIR}
MD_FILE=${CHAT_DIR}/${SESSION_ID}-${PROJECT_NAME}.md
EOF

# 创建初始文件
MD_FILE="${CHAT_DIR}/${SESSION_ID}-${PROJECT_NAME}.md"
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

echo "✅ 会话已启动：$MD_FILE" >&2
