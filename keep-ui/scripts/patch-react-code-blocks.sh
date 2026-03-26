#!/bin/bash
# Patch react-code-blocks to fix React warnings:
# 1. copied={false} passed to DOM button element
# 2. codeBlock prop passed to DOM div element
# See: https://github.com/keephq/keep/issues

PATCH_FILE="node_modules/react-code-blocks/src/components/CopyBlock.tsx"

if [ ! -f "$PATCH_FILE" ]; then
  echo "react-code-blocks not found, skipping patch"
  exit 0
fi

# Check if already patched
if grep -q "data-copied=" "$PATCH_FILE" 2>/dev/null; then
  echo "react-code-blocks already patched"
  exit 0
fi

# Apply patches using sed
sed -i '' \
  -e 's/<Button aria-label="Copy Code" type="button" onClick={handler} {\.\.\./\{ theme, copied \}>/<Button aria-label="Copy Code" type="button" onClick={handler} theme={theme} data-copied={copied ? "true" : undefined}>/' \
  -e 's/<Snippet {\.\.\./\{ codeBlock \}}/<Snippet style={customStyle} theme={theme} data-codeblock={codeBlock ? "true" : undefined}>/' \
  "$PATCH_FILE"

echo "react-code-blocks patched successfully"
