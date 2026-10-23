#!/usr/bin/env node
/**
 * docs-zh (Mintlify MDX) -> website (VitePress markdown)
 *
 * 单一数据源仍是 docs-zh/（上游文档中文翻译）与 docs/zh/（更夫自有指南），
 * 本脚本每次构建时全量重新生成 website 下的内容目录，产物不进 git。
 */
import {
  readdirSync,
  readFileSync,
  writeFileSync,
  mkdirSync,
  rmSync,
  existsSync,
  cpSync,
} from 'node:fs'
import { join, relative, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const websiteDir = resolve(here, '..')
const repoDir = resolve(websiteDir, '..')
const docsZhDir = resolve(repoDir, 'docs-zh')
const docsZhGuidesDir = resolve(repoDir, 'docs', 'zh')

// docs-zh 里这些目录整体映射进 website，其余（snippets、mint.json 等）不作为页面输出
const CONTENT_DIRS = [
  'overview',
  'alerts',
  'incidents',
  'workflows',
  'alertevaluation',
  'providers',
  'deployment',
  'development',
  'cli',
  'images',
  'logo',
]

const FOLDER_LINKS = {
  '/overview': '/overview/introduction',
  '/providers': '/providers/overview',
  '/workflows': '/workflows/overview',
  '/alerts': '/alerts/overview',
  '/incidents': '/incidents/overview',
  '/cli': '/cli/overview',
  '/deployment': '/deployment/configuration',
}

// ---------- MDX -> markdown 转换 ----------

function attr(tag, name) {
  const m = tag.match(new RegExp(`${name}=["']([^"']*)["']`))
  return m ? m[1] : null
}

// 定位 JSX 开标签的结束 ">"，跳过 icon={<img .../>} 这类大括号嵌套
function findTagEnd(src, start) {
  let depth = 0
  for (let i = start; i < src.length; i++) {
    const ch = src[i]
    if (ch === '{') depth++
    else if (ch === '}') depth = Math.max(0, depth - 1)
    else if (ch === '>' && depth === 0) return i + 1
  }
  return -1
}

// 扫描器版标签替换：replacer(openTag, bodyOrNull)，body 为 null 表示自闭合
function replaceComponent(src, tagName, replacer) {
  const openRe = new RegExp(`<${tagName}(?=[\\s/>])`, 'g')
  let out = ''
  let last = 0
  let m
  while ((m = openRe.exec(src)) !== null) {
    const openStart = m.index
    const openEnd = findTagEnd(src, openStart)
    if (openEnd === -1) break
    const openTag = src.slice(openStart, openEnd)
    if (/\/>\s*$/.test(openTag)) {
      out += src.slice(last, openStart) + replacer(openTag, null)
      last = openEnd
    } else {
      const closeTag = `</${tagName}>`
      const closeIdx = src.indexOf(closeTag, openEnd)
      if (closeIdx === -1) break
      out += src.slice(last, openStart) + replacer(openTag, src.slice(openEnd, closeIdx))
      last = closeIdx + closeTag.length
    }
    openRe.lastIndex = last
  }
  return out + src.slice(last)
}

function unwrap(src, tagName, wrap) {
  return replaceComponent(src, tagName, (open, body) => {
    const s = wrap ? wrap(open, body ?? '') : (body ?? '')
    return `\n${s.trim()}\n`
  })
}

function convertContainer(src, tag, type, fallbackTitle) {
  return replaceComponent(src, tag, (open, body) => {
    const title = attr(open, 'title') || fallbackTitle
    const inner = title ? `::: ${type} ${title}\n${body.trim()}\n:::\n` : `::: ${type}\n${body.trim()}\n:::\n`
    return `\n${inner}`
  })
}

function convertCard(src) {
  // 自闭合卡片（网格里的链接列表）转成列表项
  src = replaceComponent(src, 'Card', (open, body) => {
    if (body === null) {
      const title = attr(open, 'title') || '未命名'
      const href = attr(open, 'href')
      return href ? `\n- [${title}](${href})` : `\n- **${title}**`
    }
    const title = attr(open, 'title')
    return title
      ? `\n**${title}**\n\n${body.trim()}\n`
      : `\n${body.trim()}\n`
  })
  return unwrap(src, 'CardGroup')
}

function convertAccordion(src) {
  src = unwrap(src, 'AccordionGroup')
  return replaceComponent(src, 'Accordion', (open, body) => {
    const title = attr(open, 'title') || '详情'
    return `\n<details>\n<summary>${title}</summary>\n\n${body.trim()}\n\n</details>\n`
  })
}

function convertTabs(src) {
  src = unwrap(src, 'Tabs')
  return replaceComponent(src, 'Tab', (open, body) => {
    const title = attr(open, 'title') || ''
    return `\n**${title}**\n\n${body.trim()}\n`
  })
}

function convertFrame(src) {
  return replaceComponent(src, 'Frame', (open, body) => {
    const caption = attr(open, 'caption')
    const inner = body ? body.trim() : ''
    return `\n${inner}${caption ? `\n\n*${caption}*` : ''}\n`
  })
}

function stripStrayTags(src) {
  return src
    .replace(/<(Icon|Badge|Tooltip|Check|Update|Zoom|ParamField|ResponseField)\b[^>]*\/?>\s*/g, '')
    .replace(/<\/(Icon|Badge|Tooltip|Check|Update|Zoom)>\s*/g, '')
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
}

function rewriteAssetPaths(src, outFilePath) {
  const rel = relative(dirname(outFilePath), websiteDir).replaceAll('\\', '/')
  const prefix = rel ? `${rel}/` : './'
  // <img src="/images/x.png"> 与 markdown 里的 ](/images/x.png)
  return src.replace(
    /(src="|href="|\]\(|\()\/(images|logo)\//g,
    (_m, lead, dir) => `${lead}${prefix}${dir}/`,
  )
}

function fixFolderLinks(src) {
  for (const [from, to] of Object.entries(FOLDER_LINKS)) {
    // 匹配 ](/overview) 与 ](/overview#anchor) 两种形态
    src = src.split(`](${from})`).join(`](${to})`)
    src = src.split(`](${from}#`).join(`](${to}#`)
  }
  return src
}

function collectImports(src) {
  const imports = {}
  const stripped = src.replace(
    /^import\s+(\w+)\s+from\s+['"](.+?)['"];?\s*$/gm,
    (_m, name, path) => {
      imports[name] = path
      return ''
    },
  )
  return { imports, stripped }
}

// Keep 工作流语法里的 {{ }} 会被 Vue 当模板插值。围栏代码块 VitePress 自动 v-pre；
// 纯文本转义成 \{\{；行内代码替换为 <code v-pre>。
function escapeVueMoustache(src) {
  const lines = src.split('\n')
  let inFence = false
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*(```|~~~)/.test(lines[i])) {
      inFence = !inFence
      continue
    }
    if (inFence) continue
    lines[i] = lines[i].replace(/(`[^`]*`)|\{\{/g, (m, code) => {
      if (code !== undefined) {
        if (!code.includes('{{')) return code
        const inner = code
          .slice(1, -1)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
        return `<code v-pre>${inner}</code>`
      }
      return '\\{\\{'
    })
  }
  return lines.join('\n')
}

// 上游衍生文档页顶部注入内核说明；更夫自有指南（docs/zh）与已重写的简介页不加
const KERNEL_NOTE = `::: info 关于本页
本页介绍更夫所基于的开源内核 [Keep](https://github.com/keephq/keep) 的通用能力。更夫在其上提供国内化增强：钉钉/企业微信/飞书通知、国产大模型接入、LDAP 认证与值班管理。部署与上手请看[快速上手](/quickstart)。
:::
`

// 已重写为更夫叙事的页面不再注入
const NO_KERNEL_NOTE = new Set([
  'overview/introduction.md',
  'overview/faq.md',
  'overview/support.md',
  'overview/playground.md',
])

function injectKernelNote(src, relOut) {
  if (NO_KERNEL_NOTE.has(relOut.replaceAll('\\', '/'))) return src
  const m = src.match(/^---\n[\s\S]*?\n---\n/)
  if (!m) return `${KERNEL_NOTE}\n${src}`
  return src.slice(0, m[0].length) + `\n${KERNEL_NOTE}\n` + src.slice(m[0].length)
}

function convertSource(src, outFilePath, importsMap = {}) {
  let out = src
  const { imports, stripped } = collectImports(out)
  Object.assign(importsMap, imports)
  out = stripped

  out = convertTabs(out)
  out = convertAccordion(out)
  out = convertCard(out)
  out = convertFrame(out)
  out = convertContainer(out, 'Tip', 'tip', null)
  out = convertContainer(out, 'Info', 'info', null)
  out = convertContainer(out, 'Note', 'note', null)
  out = convertContainer(out, 'Warning', 'warning', '注意')
  out = stripStrayTags(out)

  // 自定义组件：<AutoGeneratedSnippet /> 内联对应 snippet（本身已是纯 markdown）
  out = out.replace(/<AutoGeneratedSnippet\s*\/>\s*/g, () => {
    const snippetRel = imports['AutoGeneratedSnippet']
    if (!snippetRel) return ''
    const snippetAbs = resolve(docsZhDir, snippetRel.replace(/^\//, ''))
    if (!existsSync(snippetAbs)) {
      console.warn(`  ! snippet 不存在: ${snippetRel}`)
      return ''
    }
    const snippetSrc = readFileSync(snippetAbs, 'utf8')
    return `\n${stripStrayTags(convertTabs(convertFrame(snippetSrc))).trim()}\n`
  })

  out = fixFolderLinks(out)
  out = rewriteAssetPaths(out, outFilePath)
  out = escapeVueMoustache(out)
  // 压掉 3 个以上连续空行
  out = out.replace(/\n{4,}/g, '\n\n\n')
  return out.trimEnd() + '\n'
}

// ---------- 目录处理 ----------

for (const dir of CONTENT_DIRS) {
  rmSync(join(websiteDir, dir), { recursive: true, force: true })
}

function walkMdx(dir) {
  const files = []
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, name.name)
    if (name.isDirectory()) {
      if (name.name === 'snippets') continue // snippet 只被内联，不单独成页
      files.push(...walkMdx(full))
    } else if (/\.(mdx|md)$/.test(name.name) && name.name !== 'README.md') {
      files.push(full)
    }
  }
  return files
}

let converted = 0
for (const dir of CONTENT_DIRS) {
  const srcDir = join(docsZhDir, dir)
  if (!existsSync(srcDir)) continue
  for (const file of walkMdx(srcDir)) {
    const rel = relative(docsZhDir, file).replace(/\.mdx$/, '.md')
    const outPath = join(websiteDir, rel)
    mkdirSync(dirname(outPath), { recursive: true })
    let content = convertSource(readFileSync(file, 'utf8'), outPath)
    content = injectKernelNote(content, rel)
    writeFileSync(outPath, content)
    converted++
  }
}

// docs-zh 的图片资源整体拷贝（构建产物，不进 git）
for (const dir of ['images', 'logo']) {
  if (existsSync(join(docsZhDir, dir))) {
    cpSync(join(docsZhDir, dir), join(websiteDir, dir), { recursive: true })
  }
}

// 更夫自有指南（docs/zh）拷贝为站点顶层页面
for (const guide of ['quickstart.md', 'nightingale.md', 'oncall-roadmap.md']) {
  const src = join(docsZhGuidesDir, guide)
  if (existsSync(src)) {
    const outPath = join(websiteDir, guide)
    writeFileSync(outPath, convertSource(readFileSync(src, 'utf8'), outPath))
    converted++
  }
}

// landing 页截图
if (existsSync(join(repoDir, 'assets', 'sneaknew.png'))) {
  cpSync(join(repoDir, 'assets', 'sneaknew.png'), join(websiteDir, 'sneaknew.png'))
}

console.log(`✓ 转换完成：${converted} 个文档 + images/logo 资源`)
