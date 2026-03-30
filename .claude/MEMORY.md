# Keep 项目记忆

## 分支策略
- `main` - 上游主分支（只同步，不推送）
- `develop` - 本地开发分支（私有，不推送上游）
- 不再使用 `feat/i18n-zh-CN` 分支

## Remote 仓库
- **origin** - GitHub 个人仓库 (https://github.com/fadewalk/keep)
- **gitee** - Gitee 个人仓库 (https://gitee.com/wyule/keep)
- **upstream** - 官方仓库 (https://github.com/keephq/keep)

## 同步上游更新
```bash
git checkout main && git fetch upstream && git merge upstream/main
git push origin main
```

## 相关文档
- Obsidian 笔记目录：`/Users/fadewalk/Documents/mycode/obsidian/03-work/Keep/`
