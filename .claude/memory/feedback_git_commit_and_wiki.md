---
name: git-commit-and-wiki
description: 每次完成设计、需求、修复后必须自动提交 git 并更新 wiki 文档
type: feedback
---

完成设计、需求实现、bug 修复后，必须：
1. **自动提交 git** — 不要等用户提醒，完成后立即 stage + commit
2. **更新 wiki 文档** — 路径格式 `wiki/YYMMDD-HHMMSS-文档名称.md`

**Why:** 用户明确要求以后不要每次都提醒提交，应该主动完成。
**How to apply:** 每当完成一个功能或修复，在工作收尾阶段自动执行 git add/commit，并撰写/更新对应的 wiki 设计文档。
