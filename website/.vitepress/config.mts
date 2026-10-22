import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'
import { defineConfig } from 'vitepress'

const here = dirname(fileURLToPath(import.meta.url))
const websiteDir = resolve(here, '..')
const docsZhDir = resolve(websiteDir, '../docs-zh')

// 侧边栏完全由 docs-zh/mint.json 的导航驱动，标题取各文档 frontmatter 的 title
const mint = JSON.parse(readFileSync(resolve(docsZhDir, 'mint.json'), 'utf8'))

function pageTitle(relPath) {
  for (const ext of ['.mdx', '.md']) {
    const file = resolve(docsZhDir, relPath + ext)
    if (existsSync(file)) {
      const head = readFileSync(file, 'utf8').slice(0, 600)
      for (const key of ['title', 'sidebarTitle']) {
        const m = head.match(new RegExp(`^${key}:\\s*["']?(.+?)["']?\\s*$`, 'm'))
        if (m) return m[1]
      }
    }
  }
  return relPath.split('/').pop()
}

function toSidebar(items) {
  const out = []
  for (const item of items) {
    if (typeof item === 'string') {
      out.push({ text: pageTitle(item), link: '/' + item })
    } else {
      out.push({
        text: item.group,
        collapsed: true,
        items: toSidebar(item.pages),
      })
    }
  }
  return out
}

export default defineConfig({
  base: '/gengfu/',
  lang: 'zh-CN',
  title: '更夫 Gengfu',
  description:
    '更夫 Gengfu — 开源的告警聚合与 AI 事件管理平台，面向中国企业场景的 Keep 中文发行版。降噪去重、值班通知、事件管理、AI 分析、自动化处置。',
  cleanUrls: true,
  srcDir: '.',
  ignoreDeadLinks: [
    // 上游文档里残留的指向 keephq 官网的相对路径，转换为外部链接处理不了，忽略
    /^\/(playground|platform|docs)/,
    'https://platform.keephq.dev',
    // 文档里的本机示例地址
    /^https?:\/\/(localhost|127\.0\.0\.1)/,
  ],
  head: [['link', { rel: 'icon', type: 'image/svg+xml', href: '/gengfu/favicon.svg' }]],

  themeConfig: {
    logo: '/favicon.svg',
    siteTitle: '更夫 Gengfu',
    nav: [
      { text: '首页', link: '/' },
      { text: '快速上手', link: '/quickstart' },
      { text: '接入夜莺', link: '/nightingale' },
      {
        text: '使用文档',
        items: [
          { text: '平台概览', link: '/overview/introduction' },
          { text: '告警', link: '/alerts/overview' },
          { text: '事件', link: '/incidents/overview' },
          { text: '工作流', link: '/workflows/overview' },
          { text: 'Providers', link: '/providers/overview' },
          { text: '部署', link: '/deployment/docker' },
          { text: 'Keep CLI', link: '/cli/overview' },
        ],
      },
    ],
    sidebar: toSidebar(mint.navigation),
    socialLinks: [{ icon: 'github', link: 'https://github.com/fadewalk/gengfu' }],
    search: { provider: 'local', options: { translations: { button: { buttonText: '搜索' } } } },
    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一页', next: '下一页' },
    lastUpdated: false,
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色',
    darkModeSwitchTitle: '切换到深色',
    footer: {
      message: '基于 MIT 协议开源的 Keep · 由更夫社区维护',
      copyright: '© 2025-2026 更夫 Gengfu',
    },
  },
})
