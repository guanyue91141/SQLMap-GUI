<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { Activity, ArrowDown, ArrowUp, Check, ChevronRight, CircleHelp, Code2, Copy, Download, FileText, FolderOpen, GripHorizontal, Info, LoaderCircle, Play, RotateCcw, Search, Settings2, ShieldCheck, Square, TerminalSquare, Upload, X, Zap } from 'lucide-vue-next'
import type { Config, Environment, Note, Option, ResultFile, Run, Value } from './types'

const options = ref<Option[]>([])
const tampers = ref<{name: string; description: string}[]>([])
const environment = ref<Environment | null>(null)
const config = reactive<Config>({ values: {}, extra: '' })
const group = ref('Target')
const search = ref('')
const configuredOnly = ref(false)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const toast = ref('')
const preview = ref('')
const previewError = ref('')
const run = ref<Run | null>(null)
const notes = ref<Note[]>([])
const files = ref<ResultFile[]>([])
const truncated = ref(false)
const bottomTab = ref('terminal')
const connected = ref(false)
const replaying = ref(false)
const terminalElement = ref<HTMLDivElement>()
const configFileInput = ref<HTMLInputElement>()
const rawDialog = ref<HTMLDialogElement>()
const rawRequest = ref('')
const rawBusy = ref(false)
const helpDialog = ref<HTMLDialogElement>()
const tamperSearch = ref('')
const terminalHeight = ref(Number(localStorage.getItem('terminalHeight')) || 310)
const currentTime = ref(Date.now())
let term: Terminal
let fit: FitAddon
let socket: WebSocket | undefined
let activeRunId = ''
let lastSequence = 0
let reconnect: ReturnType<typeof setTimeout> | undefined
let polling: ReturnType<typeof setInterval>
let previewTimer: ReturnType<typeof setTimeout>
let toastTimer: ReturnType<typeof setTimeout>
let observer: ResizeObserver
let disposed = false
let previewRevision = 0

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }
  const response = await fetch('/api' + path, { ...init, headers: { ...headers, ...init.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `请求失败（${response.status}）`)
  }
  return response.json()
}
function notify(text: string) {
  toast.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toast.value = '', 3500)
}
const groups = computed(() => [...new Map(options.value.map(o => [o.group, { id: o.group, label: o.groupLabel }])).values()])
const active = (value: Value | undefined) => value !== undefined && value !== false && value !== '' && (!Array.isArray(value) || value.length > 0)
const selectedCount = computed(() => Object.values(config.values).filter(active).length)
const running = computed(() => !!run.value && ['starting', 'running', 'stopping'].includes(run.value.status))
const filtered = computed(() => options.value.filter(o => {
  const query = search.value.trim().toLowerCase()
  return (query ? `${o.label} ${o.description} ${o.flags.join(' ')} ${o.help}`.toLowerCase().includes(query) : o.group === group.value)
    && (!configuredOnly.value || active(config.values[o.id]))
}))
const fields = computed(() => filtered.value.filter(o => !o.tool))
const tools = computed(() => filtered.value.filter(o => o.tool))
const groupLabel = computed(() => search.value ? '搜索参数' : groups.value.find(g => g.id === group.value)?.label || '目标')
const groupDescriptions: Record<string, string> = {
  Target: '从一个地址、一份请求或 API 定义开始。', Request: '配置请求内容、身份认证和连接方式。',
  Injection: '选择测试参数，组合载荷与 Tamper 脚本。', Detection: '调整检测范围与响应判断依据。',
  Enumeration: '选择需要读取的数据库信息与数据。', Miscellaneous: '引擎辅助功能和独立工具操作。',
}
const statusNames: Record<string, string> = { starting: '启动中', running: '运行中', stopping: '结束中', finished: '已完成', failed: '运行失败', interrupted: '已中断' }
const statusName = computed(() => run.value ? statusNames[run.value.status] || run.value.status : '就绪')
const elapsed = computed(() => {
  if (!run.value) return '00:00'
  const seconds = Math.max(0, Math.floor(((run.value.ended ? run.value.ended * 1000 : currentTime.value) - run.value.started * 1000) / 1000))
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
})
const tamperChain = computed(() => String(config.values.tamper || '').split(',').filter(Boolean))
const filteredTampers = computed(() => tampers.value.filter(t => `${t.name} ${t.description}`.toLowerCase().includes(tamperSearch.value.toLowerCase())).slice(0, 14))
function setValue(option: Option, value: Value) {
  if (active(value)) config.values[option.id] = value
  else delete config.values[option.id]
}
function inputValue(option: Option, event: Event) { setValue(option, (event.target as HTMLInputElement).value) }
function isSwitch(option: Option) { return ['store_true', 'store_false', 'help', 'version'].includes(option.action) }
function groupCount(name: string) { return options.value.filter(o => o.group === name && active(config.values[o.id])).length }
function addTamper(name: string) { if (!tamperChain.value.includes(name)) config.values.tamper = [...tamperChain.value, name].join(',') }
function moveTamper(index: number, direction: number) {
  const chain = [...tamperChain.value]
  const target = index + direction
  if (target < 0 || target >= chain.length) return
  ;[chain[index], chain[target]] = [chain[target]!, chain[index]!]
  config.values.tamper = chain.join(',')
}
function removeTamper(index: number) { config.values.tamper = tamperChain.value.filter((_, i) => i !== index).join(',') }
function configuration(): Config { return JSON.parse(JSON.stringify(config)) }
watch(config, () => {
  const revision = ++previewRevision
  clearTimeout(previewTimer)
  previewTimer = setTimeout(async () => {
    try {
      const result = await api<{command: string}>('/preview', { method: 'POST', body: JSON.stringify(configuration()) })
      if (revision === previewRevision) { preview.value = result.command; previewError.value = '' }
    } catch (e) {
      if (revision === previewRevision) { preview.value = ''; previewError.value = (e as Error).message }
    }
  }, 220)
}, { deep: true })

async function saveConfig() {
  try { await api('/config', { method: 'PUT', body: JSON.stringify(configuration()) }); notify('当前配置已保存到本机') }
  catch (e) { error.value = (e as Error).message }
}
function downloadJSON() {
  const url = URL.createObjectURL(new Blob([JSON.stringify(configuration(), null, 2)], { type: 'application/json' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'sqlmap-config.json'; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
async function importConfig(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const parsed = JSON.parse(await file.text())
    if (!parsed.values || typeof parsed.values !== 'object' || Array.isArray(parsed.values) || typeof parsed.extra !== 'string') throw new Error('配置文件需要包含 values 对象和 extra 字符串')
    for (const [key, value] of Object.entries(parsed.values)) {
      if (!options.value.some(o => o.id === key) || !(typeof value === 'string' || typeof value === 'boolean' || typeof value === 'number' || (Array.isArray(value) && value.every(v => typeof v === 'string')))) throw new Error(`配置参数无效：${key}`)
    }
    config.values = parsed.values; config.extra = parsed.extra
    notify('配置已导入，请检查命令预览')
  } catch (e) { error.value = `导入失败：${(e as Error).message}` }
  input.value = ''
}
async function uploadFile(event: Event, option: Option) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const form = new FormData(); form.append('file', file)
  try { const result = await api<{path: string}>('/upload', { method: 'POST', body: form }); config.values[option.id] = result.path; notify('文件已上传到本机工作目录') }
  catch (e) { error.value = (e as Error).message }
  input.value = ''
}
async function useRawRequest() {
  if (!rawRequest.value.trim()) return
  rawBusy.value = true
  try {
    const form = new FormData(); form.append('file', new Blob([rawRequest.value], { type: 'text/plain' }), 'request.txt')
    const result = await api<{path: string}>('/upload', { method: 'POST', body: form })
    config.values.requestFile = result.path; delete config.values.url
    rawDialog.value?.close(); notify('HTTP 报文已载入，原有 URL 参数已移除')
  } catch (e) { error.value = (e as Error).message }
  finally { rawBusy.value = false }
}
function reset() { config.values = {}; config.extra = ''; search.value = ''; configuredOnly.value = false; notify('表单已重置，运行中的任务不会改变') }
async function copyCommand() {
  try { await navigator.clipboard.writeText(preview.value || run.value?.command || ''); notify('命令已复制') }
  catch { error.value = '复制失败，请手动选中命令复制' }
}
async function start(tool?: Option) {
  busy.value = true; error.value = ''
  try {
    const payload = tool ? { values: { [tool.id]: true }, extra: '' } : configuration()
    if (tool && ['updateAll', 'purge', 'gui'].includes(tool.id)) {
      pendingTool.value = tool; toolDialog.value?.showModal(); return
    }
    await launch(payload)
  } catch (e) { error.value = (e as Error).message }
  finally { busy.value = false }
}
const pendingTool = ref<Option>()
const toolDialog = ref<HTMLDialogElement>()
async function confirmTool() {
  if (!pendingTool.value) return
  busy.value = true; toolDialog.value?.close()
  try { await launch({ values: { [pendingTool.value.id]: true }, extra: '' }) }
  catch (e) { error.value = (e as Error).message }
  finally { busy.value = false }
}
async function launch(payload: Config) {
  const result = await api<Run>('/run', { method: 'POST', body: JSON.stringify(payload) })
  run.value = result; bottomTab.value = 'terminal'; attach(result.id)
  await nextTick(); fit?.fit(); term?.focus()
}
async function stop(force = false) {
  try { run.value = await api<Run>('/run/stop', { method: 'POST', body: JSON.stringify({ force }) }) }
  catch (e) { error.value = (e as Error).message }
}
function send(message: unknown) { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message)) }
function attach(id: string) {
  if (activeRunId !== id) {
    clearTimeout(reconnect); socket?.close(); socket = undefined
    activeRunId = id; lastSequence = 0; notes.value = []; files.value = []; term?.reset()
  } else if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
  const ws = new WebSocket(`ws://${location.host}/api/terminal/${id}?after=${lastSequence}`)
  socket = ws
  ws.onopen = () => { replaying.value = true; connected.value = true; fit?.fit(); send({ type: 'resize', rows: term.rows, cols: term.cols }) }
  ws.onmessage = event => {
    if (ws !== socket) return
    const message = JSON.parse(event.data)
    if (message.type === 'output') {
      term.write(message.data, () => {
        lastSequence = Math.max(lastSequence, message.seq)
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ack', seq: message.seq }))
      })
      return
    }
    if (message.seq) lastSequence = Math.max(lastSequence, message.seq)
    if (message.type === 'status') { run.value = message.run; if (!running.value) void loadFiles() }
    if (message.type === 'replay_end') replaying.value = false
    if (message.type === 'annotation') notes.value = [...notes.value.slice(-49), { title: message.title, text: message.text }]
    if (message.type === 'notice') notes.value.push({ title: '终端回放', text: message.message })
    if (message.type === 'error') notify(message.message)
  }
  ws.onclose = event => {
    if (ws !== socket) return
    connected.value = false; socket = undefined
    if (!disposed && activeRunId === id && event.code !== 1008) reconnect = setTimeout(() => attach(id), 1800)
  }
  ws.onerror = () => { connected.value = false }
}
async function loadFiles() {
  try { const result = await api<{files: ResultFile[]; truncated: boolean}>('/results'); files.value = result.files; truncated.value = result.truncated }
  catch (e) { error.value = (e as Error).message }
}
function fileURL(file: ResultFile) { return `/api/download?root=${encodeURIComponent(file.root)}&path=${encodeURIComponent(file.path)}` }
function sizeLabel(size: number) { return size < 1024 ? `${size} B` : size < 1024 ** 2 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1024 ** 2).toFixed(1)} MB` }
function resizeTerminal(event: PointerEvent) {
  const start = event.clientY, height = terminalHeight.value
  const move = (e: PointerEvent) => { terminalHeight.value = Math.max(180, Math.min(window.innerHeight * 0.7, height + start - e.clientY)) }
  const end = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', end); localStorage.setItem('terminalHeight', String(terminalHeight.value)) }
  window.addEventListener('pointermove', move); window.addEventListener('pointerup', end)
}
watch(bottomTab, async value => { await nextTick(); if (value === 'terminal') fit?.fit(); if (value === 'results') void loadFiles() })

onMounted(async () => {
  term = new Terminal({ fontFamily: 'Cascadia Code, Consolas, monospace', fontSize: 12, lineHeight: 1.35, cursorBlink: true, scrollback: 5000, convertEol: false, allowProposedApi: false, theme: { background: '#0e1419', foreground: '#c5d1da', cursor: '#77dfbd', selectionBackground: '#34554e', black: '#172128', red: '#ef9191', green: '#80d6a9', yellow: '#e4c283', blue: '#89b9ec', magenta: '#cca5d9', cyan: '#80d8d2', white: '#e0e8ee' } })
  fit = new FitAddon(); term.loadAddon(fit); term.open(terminalElement.value!); fit.fit()
  // Replaying old device queries must not send xterm's automatic responses back
  // to the live Shell. That would insert escape sequences into the user's line.
  term.onData(data => { if (running.value && !replaying.value) send({ type: 'input', data }) })
  term.onResize(({ rows, cols }) => send({ type: 'resize', rows, cols }))
  observer = new ResizeObserver(() => { if (bottomTab.value === 'terminal') fit.fit() }); observer.observe(terminalElement.value!)
  try {
    const [catalog, saved, current] = await Promise.all([
      api<{options: Option[]; tampers: {name: string; description: string}[]; environment: Environment}>('/catalog'), api<Config>('/config'), api<Run | null>('/run'),
    ])
    options.value = catalog.options; tampers.value = catalog.tampers; environment.value = catalog.environment
    config.values = saved.values; config.extra = saved.extra
    run.value = current
    if (current) attach(current.id)
    else term.writeln('\x1b[38;2;119;223;189m  sqlmap 中文工作台\x1b[0m\r\n\r\n  配置目标后点击「开始运行」。\r\n  引擎提示、交互输入和 Shell 会在这里显示。\r\n')
  } catch (e) { error.value = `初始化失败：${(e as Error).message}` }
  finally { loading.value = false }
  polling = setInterval(async () => {
    currentTime.value = Date.now()
    try { const latest = await api<Run | null>('/run'); run.value = latest; if (latest) attach(latest.id) }
    catch { /* An existing terminal will show its disconnected indicator. */ }
  }, 2000)
})
onBeforeUnmount(() => { disposed = true; clearTimeout(reconnect); clearTimeout(previewTimer); clearTimeout(toastTimer); clearInterval(polling); socket?.close(); observer?.disconnect(); term?.dispose() })
</script>

<template>
  <div class="workbench" :style="{ '--terminal-height': terminalHeight + 'px' }">
    <a class="skip-link" href="#configuration">跳转到参数配置</a>
    <header class="topbar">
      <div class="brand"><div class="brand-mark"><Code2 :size="23" /></div><div><strong>sqlmap<span class="brand-dot">.</span></strong><span class="brand-subtitle">中文工作台</span></div><span class="local-badge"><span />本机运行</span></div>
      <div class="top-actions"><button class="icon-button" title="使用帮助" aria-label="使用帮助" @click="helpDialog?.showModal()"><CircleHelp :size="18" /></button><span class="version">引擎 v{{ environment?.sqlmap || '…' }}</span><span class="top-divider" /><span class="ready-status" :class="{ working: running }"><i />{{ statusName }}</span></div>
    </header>
    <div class="main-layout">
      <aside class="sidebar" aria-label="功能分类">
        <div class="sidebar-heading"><span>功能目录</span><span class="muted">{{ options.length }} 参数</span></div>
        <nav class="group-nav" aria-label="sqlmap 功能">
          <button v-for="(item, index) in groups" :key="item.id" :class="{ selected: group === item.id && !search }" :aria-current="group === item.id && !search ? 'page' : undefined" @click="group = item.id; search = ''">
            <span class="nav-number">{{ String(index + 1).padStart(2, '0') }}</span><span>{{ item.label }}</span><span v-if="groupCount(item.id)" class="nav-count">{{ groupCount(item.id) }}</span><ChevronRight v-else :size="13" class="nav-arrow" />
          </button>
        </nav>
        <div class="sidebar-footer"><ShieldCheck :size="17" /><div>本地独立环境<span>127.0.0.1 : 9955</span></div></div>
      </aside>
      <main id="configuration" class="workspace">
        <section class="configuration-area">
          <div class="page-heading"><div><div class="eyebrow">SQLMAP WORKBENCH <span>/</span> 参数配置</div><h1>{{ groupLabel }}<span class="heading-count">{{ filtered.length }}</span></h1><p>{{ search ? '按中文名称、说明或命令参数搜索全部功能。' : groupDescriptions[group] || '按需配置参数，所有选项都映射到真实 sqlmap 命令。' }}</p></div><div class="run-actions"><button class="button secondary" :disabled="!running" @click="stop(false)"><Square :size="14" />中断</button><button class="button primary" :disabled="busy || running || loading || !!previewError" @click="start()"><LoaderCircle v-if="busy" :size="16" class="spin" /><Play v-else :size="15" fill="currentColor" />{{ running ? '正在运行' : '开始运行' }}</button></div></div>
          <div class="toolbar"><div class="search-box"><Search :size="16" /><input v-model="search" aria-label="搜索全部参数" placeholder="搜索功能、中文说明或 --参数…" /><button v-if="search" class="icon-button small" aria-label="清空搜索" @click="search = ''"><X :size="14" /></button><kbd v-else>{{ options.length }}</kbd></div><label class="configured-filter"><input v-model="configuredOnly" type="checkbox" />只看已配置<span>{{ selectedCount }}</span></label><span class="toolbar-divider" /><button class="text-button" @click="reset"><RotateCcw :size="14" />重置</button><details class="config-menu"><summary class="text-button"><Settings2 :size="14" />配置</summary><div class="menu-content"><button @click="saveConfig">保存到本机</button><button @click="configFileInput?.click()">导入 JSON 配置</button><button @click="downloadJSON">导出 JSON 配置</button></div></details><input ref="configFileInput" type="file" accept=".json" hidden @change="importConfig" /></div>
          <div v-if="error" class="error-banner" role="alert"><Info :size="16" /><span>{{ error }}</span><button class="icon-button" aria-label="关闭错误" @click="error = ''"><X :size="15" /></button></div>
          <div v-if="loading" class="empty-state"><LoaderCircle class="spin" :size="24" /><p>正在读取引擎与参数目录…</p></div>
          <div v-else class="field-scroll">
            <div v-if="group === 'Target' && !search" class="target-intro"><div class="intro-icon"><Zap :size="18" /></div><div><strong>选择一种目标输入方式</strong><p>填写 URL，或载入已捕获的 HTTP 请求。其余参数按需配置。</p></div><button class="button secondary" @click="rawDialog?.showModal()"><FileText :size="14" />粘贴 HTTP 请求</button></div>
            <div class="fields-grid">
              <div v-for="option in fields" :key="option.id" class="field-card" :class="{ 'switch-card': isSwitch(option), configured: active(config.values[option.id]), 'wide-field': option.multiline || option.id === 'tamper' || option.id === 'url' }">
                <div class="field-heading"><label :for="'field-' + option.id">{{ option.label }}</label><code>{{ option.flags.join(' / ') }}</code><button v-if="active(config.values[option.id])" class="clear-field" :aria-label="'清除' + option.label" @click="delete config.values[option.id]"><X :size="12" /></button></div>
                <p :id="'help-' + option.id" class="field-description">{{ option.description }}</p>
                <div v-if="isSwitch(option)" class="switch-wrapper"><input :id="'field-' + option.id" type="checkbox" class="switch" :checked="config.values[option.id] === true" :aria-describedby="'help-' + option.id" @change="setValue(option, ($event.target as HTMLInputElement).checked)" /></div>
                <template v-else-if="option.id === 'tamper'">
                  <input :id="'field-' + option.id" :value="config.values.tamper || ''" :aria-describedby="'help-' + option.id" placeholder="例如 space2comment,between，或填写脚本路径" @input="inputValue(option, $event)" />
                  <div v-if="tamperChain.length" class="tamper-chain"><div v-for="(name, index) in tamperChain" :key="index" class="tamper-chip"><span class="muted">{{ index + 1 }}</span><span>{{ name }}</span><button :disabled="index === 0" :aria-label="'上移 ' + name" @click="moveTamper(index, -1)"><ArrowUp :size="12" /></button><button :disabled="index === tamperChain.length - 1" :aria-label="'下移 ' + name" @click="moveTamper(index, 1)"><ArrowDown :size="12" /></button><button :aria-label="'移除 ' + name" @click="removeTamper(index)"><X :size="12" /></button></div></div>
                  <div class="tamper-picker"><div class="search-box"><Search :size="14" /><input v-model="tamperSearch" aria-label="搜索 Tamper 脚本" placeholder="搜索 84 个内置脚本…" /></div><div class="tamper-options"><button v-for="item in filteredTampers" :key="item.name" :disabled="tamperChain.includes(item.name)" :title="item.description" @click="addTamper(item.name)"><Check v-if="tamperChain.includes(item.name)" :size="12" /><span v-else>+</span>{{ item.name }}</button></div><span class="field-footnote">按链中顺序传入引擎；脚本依赖与优先级由 sqlmap 检查。</span></div>
                </template>
                <textarea v-else-if="option.multiline" :id="'field-' + option.id" :value="String(config.values[option.id] ?? '')" :aria-describedby="'help-' + option.id" rows="3" placeholder="填写参数内容…" spellcheck="false" @input="inputValue(option, $event)" />
                <select v-else-if="option.choices" :id="'field-' + option.id" :value="config.values[option.id] || ''" :aria-describedby="'help-' + option.id" @change="inputValue(option, $event)"><option value="">使用引擎默认值</option><option v-for="choice in option.choices" :key="choice" :value="choice">{{ choice }}</option></select>
                <div v-else class="input-with-action"><input :id="'field-' + option.id" :type="['int', 'float'].includes(option.type) ? 'number' : 'text'" :step="option.type === 'float' ? 'any' : 1" :value="config.values[option.id] ?? ''" :placeholder="option.default !== null ? '引擎默认：' + option.default : option.file ? '填写本机文件绝对路径，或上传文件' : '未设置'" :aria-describedby="'help-' + option.id" spellcheck="false" @input="inputValue(option, $event)" /><label v-if="option.file" class="upload-button" :title="'上传' + option.label"><Upload :size="14" /><span>上传</span><input type="file" :aria-label="'上传' + option.label" @change="uploadFile($event, option)" /></label></div>
                <p v-if="option.dependency" class="dependency-note"><Info :size="12" />{{ option.dependency }}</p>
                <p class="english-help" :title="option.help">{{ option.help }}</p>
              </div>
            </div>
            <section v-if="tools.length" class="tools-section"><div class="section-title"><TerminalSquare :size="16" /><h2>独立工具操作</h2><span>单独运行，不携带当前表单参数</span></div><div class="tools-grid"><article v-for="tool in tools" :key="tool.id" class="tool-card"><div><strong>{{ tool.label }}</strong><code>{{ tool.flag }}</code></div><p>{{ tool.description }}</p><button class="text-button" :disabled="running || busy" @click="start(tool)">运行<ChevronRight :size="14" /></button></article></div></section>
            <div v-if="!filtered.length" class="empty-state"><Search :size="28" /><strong>没有匹配的参数</strong><p>换个关键词，或取消“只看已配置”。</p></div>
            <details class="advanced-section"><summary><Settings2 :size="15" /><span>额外命令参数</span><span class="muted">高级输入</span><ChevronRight :size="14" /></summary><div><label for="extra-args">在分类表单之外补充参数</label><textarea id="extra-args" v-model="config.extra" rows="2" spellcheck="false" placeholder="例如 --technique=BEU --timeout=15" /><p>使用完整参数名；带空格或 Windows 路径的值请用引号包住。重复参数会提示冲突。</p></div></details>
          </div>
        </section>
        <section class="execution-area" aria-label="命令与运行终端">
          <div class="resize-handle" role="separator" aria-label="调整终端高度" aria-orientation="horizontal" tabindex="0" @pointerdown.prevent="resizeTerminal" @keydown.up.prevent="terminalHeight = Math.min(600, terminalHeight + 30)" @keydown.down.prevent="terminalHeight = Math.max(180, terminalHeight - 30)"><GripHorizontal :size="20" /></div>
          <div class="command-preview"><div class="command-label"><Code2 :size="14" /><span>命令预览</span><span class="muted">PowerShell</span></div><code :class="{ 'preview-placeholder': !preview }">{{ preview || previewError || '等待参数配置…' }}</code><button class="icon-button" :disabled="!preview" aria-label="复制命令" title="复制命令" @click="copyCommand"><Copy :size="15" /></button></div>
          <div class="terminal-tabs"><div role="tablist" aria-label="执行面板"><button id="tab-terminal" role="tab" :aria-selected="bottomTab === 'terminal'" aria-controls="panel-terminal" :class="{ active: bottomTab === 'terminal' }" @click="bottomTab = 'terminal'"><TerminalSquare :size="15" />交互终端<span v-if="running" class="live-dot" /></button><button id="tab-results" role="tab" :aria-selected="bottomTab === 'results'" aria-controls="panel-results" :class="{ active: bottomTab === 'results' }" @click="bottomTab = 'results'"><FolderOpen :size="15" />结果文件<span v-if="files.length" class="tab-count">{{ files.length }}</span></button><button id="tab-environment" role="tab" :aria-selected="bottomTab === 'environment'" aria-controls="panel-environment" :class="{ active: bottomTab === 'environment' }" @click="bottomTab = 'environment'"><Activity :size="15" />运行环境</button></div><div class="terminal-meta"><span class="connection-status" :class="{ online: connected }">{{ activeRunId ? connected ? replaying ? '正在回放' : '终端已连接' : '终端未连接' : '等待启动' }}</span><span class="elapsed">{{ elapsed }}</span><a v-if="run" href="/api/download?root=run&path=terminal.log" class="icon-button" aria-label="下载完整终端日志" title="下载日志"><Download :size="14" /></a><button v-if="running" class="text-button danger" @click="stop(true)">强制结束</button></div></div>
          <div class="terminal-content">
            <div id="panel-terminal" v-show="bottomTab === 'terminal'" class="terminal-panel" role="tabpanel" aria-labelledby="tab-terminal"><div ref="terminalElement" class="terminal-host" aria-label="sqlmap 交互终端" /><aside class="annotations" aria-label="中文提示旁注"><div class="annotations-heading"><Info :size="14" />中文旁注<span>本地解释</span></div><div v-if="!notes.length" class="annotations-empty"><span class="note-line" /><p>保留每一行原始输出。<br />常见日志与问答的中文解释<br />会显示在这里。</p><span class="note-tag">输入直接发送到引擎</span></div><div v-for="(note, index) in notes" :key="index" class="note"><strong>{{ note.title }}</strong><p>{{ note.text }}</p></div></aside></div>
            <div id="panel-results" v-show="bottomTab === 'results'" class="results-panel" role="tabpanel" aria-labelledby="tab-results"><div class="results-heading"><span>{{ run?.message || '运行后生成结果文件' }}</span><button class="text-button" @click="loadFiles"><RotateCcw :size="13" />刷新</button></div><p v-if="run?.output" class="output-path">输出目录：{{ run.output }}</p><table v-if="files.length"><thead><tr><th scope="col">文件</th><th scope="col">大小</th><th scope="col">操作</th></tr></thead><tbody><tr v-for="file in files" :key="file.root + file.path"><td><FileText :size="13" /><span>{{ file.path }}</span></td><td>{{ sizeLabel(file.size) }}</td><td><a :href="fileURL(file)" class="text-button"><Download :size="13" />下载</a></td></tr></tbody></table><div v-else class="empty-state compact"><FolderOpen :size="24" /><p>暂无结果文件</p></div><p v-if="truncated" class="muted">最多显示 1000 个文件，可在输出目录中查看全部结果。</p></div>
            <div id="panel-environment" v-show="bottomTab === 'environment'" class="environment-panel" role="tabpanel" aria-labelledby="tab-environment"><template v-if="environment"><div class="environment-grid"><article><span>SQLMAP</span><strong>{{ environment.sqlmap }}</strong><p>{{ environment.sqlmap === environment.expectedVersion ? '与锁定版本一致' : '版本已变化，请重新锁定依赖并检查参数目录' }}</p></article><article><span>PYTHON</span><strong>{{ environment.python }}</strong><p>{{ environment.pythonPath }}</p></article><article><span>终端后端</span><strong>{{ environment.terminal }}</strong><p>同一任务 · 双向输入 · 刷新重连</p></article></div><div class="optional-dependencies"><span>可选依赖</span><span v-for="(available, name) in environment.optional" :key="name" class="dependency-badge" :class="{ available }"><i />{{ name }}<small>{{ available ? '已检测到' : '未检测到' }}</small></span></div><p class="environment-footnote">检测结果基于当前 Python 环境与 PATH；自定义路径中的工具可由引擎使用。完整检查请运行“检测可选依赖”。</p></template></div>
          </div>
        </section>
      </main>
    </div>
    <footer class="statusbar"><span><span class="live-dot" />本地服务 · 9955</span><span>{{ selectedCount }} 项已配置<span class="status-separator">/</span>{{ options.length }} 个公开参数</span><span class="statusbar-right">UTF-8<span class="status-separator">·</span>ConPTY<span class="status-separator">·</span>仅本机访问</span></footer>
    <div v-if="toast" class="toast" role="status"><Check :size="16" />{{ toast }}</div>
    <dialog ref="rawDialog" class="modal raw-modal"><div class="modal-heading"><div><h2>载入原始 HTTP 请求</h2><p>粘贴从代理或抓包工具复制的完整报文。</p></div><button class="icon-button" aria-label="关闭" @click="rawDialog?.close()"><X :size="18" /></button></div><label for="raw-http">HTTP 请求报文</label><textarea id="raw-http" v-model="rawRequest" rows="13" spellcheck="false" placeholder="GET /item?id=1 HTTP/1.1&#10;Host: 127.0.0.1:8000&#10;Cookie: session=...&#10;&#10;" /><div class="modal-footer"><span>载入后使用 -r，移除表单中的 URL。</span><button class="button primary" :disabled="!rawRequest.trim() || rawBusy" @click="useRawRequest"><Upload :size="14" />{{ rawBusy ? '载入中…' : '载入请求' }}</button></div></dialog>
    <dialog ref="helpDialog" class="modal help-modal"><div class="modal-heading"><h2>开始使用中文工作台</h2><button class="icon-button" aria-label="关闭帮助" @click="helpDialog?.close()"><X :size="18" /></button></div><ol class="help-steps"><li><strong>配置目标</strong><p>填写 URL、上传请求文件或粘贴 HTTP 报文。</p></li><li><strong>选择功能</strong><p>按分类配置参数，或通过搜索查找选项。空白项使用引擎默认行为。</p></li><li><strong>检查并运行</strong><p>命令预览与表单同步；运行后的实际命令保存在结果文件 run.json 中，包含自动设置的独立输出目录。</p></li><li><strong>直接交互</strong><p>点击终端输入回答。Enter 提交，Ctrl+C 中断，方向键交给引擎处理。若引擎仍在等待，可使用强制结束。</p></li></ol><p class="help-note">工作台保留原始输出，中文旁注仅解释常见提示；不替换未知日志。一次运行一个任务，关闭网页不停止任务。配置通过“配置 → 保存到本机”保存；运行时也会自动保存。</p><p class="help-note">只在获得授权的系统上使用。请求、凭据及日志保存在本机 .data 中，不进入 Git。</p></dialog>
    <dialog ref="toolDialog" class="modal tool-modal"><div class="modal-heading"><h2>{{ pendingTool?.label }}</h2><button class="icon-button" aria-label="关闭工具操作" @click="toolDialog?.close()"><X :size="18" /></button></div><p>{{ pendingTool?.description }}</p><p v-if="pendingTool?.id === 'updateAll'" class="help-note">此操作由 sqlmap 执行，并可能修改 .venv 内的版本。uv.lock 不会自动更新；后续请使用 uv add sqlmap==新版本 重新锁定，并重启工作台核对参数。</p><div class="modal-footer"><button class="button secondary" @click="toolDialog?.close()">取消</button><button class="button primary" @click="confirmTool">运行此操作</button></div></dialog>
  </div>
</template>
