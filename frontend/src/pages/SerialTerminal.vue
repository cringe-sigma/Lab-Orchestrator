<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import 'xterm/css/xterm.css'
import { boardApi, type BoardData } from '../api/client'

const route = useRoute()
const router = useRouter()
const boardId = Number(route.params.boardId)

const board = ref<BoardData | null>(null)
const terminalEl = ref<HTMLDivElement | null>(null)
const statusText = ref('未连接')
const statusClass = ref('disconnected')
const baudRate = ref(115200)
const connected = ref(false)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

onMounted(async () => {
  try {
    const res = await boardApi.get(boardId)
    board.value = res.data
    baudRate.value = res.data.serial_baud || 115200
  } catch { /* ignore */ }

  await nextTick()
  initTerminal()
})

onUnmounted(() => {
  disconnect()
})

function initTerminal() {
  if (!terminalEl.value) return

  term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'Consolas', 'Courier New', monospace",
    theme: {
      background: '#1a1a2e',
      foreground: '#e0e0e0',
      cursor: '#00ff88',
      selectionBackground: '#334',
      black: '#1a1a2e',
      red: '#e06c75',
      green: '#98c379',
      yellow: '#e5c07b',
      blue: '#61afef',
      magenta: '#c678dd',
      cyan: '#56b6c2',
      white: '#abb2bf',
      brightBlack: '#5c6370',
      brightRed: '#e06c75',
      brightGreen: '#98c379',
      brightYellow: '#e5c07b',
      brightBlue: '#61afef',
      brightMagenta: '#c678dd',
      brightCyan: '#56b6c2',
      brightWhite: '#ffffff',
    },
    allowProposedApi: true,
    scrollback: 5000,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())

  term.open(terminalEl.value)
  fitAddon.fit()

  term.writeln('\x1b[1;36m┌──────────────────────────────────────────────┐\x1b[0m')
  term.writeln('\x1b[1;36m│\x1b[0m  \x1b[1;33mLab Orchestrator - 串口终端\x1b[0m                    \x1b[1;36m│\x1b[0m')
  term.writeln('\x1b[1;36m│\x1b[0m  点击右上角 [连接] 开始串口调试                    \x1b[1;36m│\x1b[0m')
  term.writeln('\x1b[1;36m└──────────────────────────────────────────────┘\x1b[0m')
  term.writeln('')

  // 用户输入 → 发送到串口
  term.onData((data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', text: data }))
    }
  })

  // 窗口大小变化时自适应
  window.addEventListener('resize', () => fitAddon?.fit())
}

function connect() {
  if (!boardId) return

  const token = localStorage.getItem('token')
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const host = location.hostname

  statusText.value = '连接中...'
  statusClass.value = 'connecting'

  ws = new WebSocket(`${protocol}://${host}:8000/ws/terminal/${boardId}?token=${token}`)

  ws.onopen = () => {
    connected.value = true
    statusText.value = `已连接 @ ${baudRate.value}bps`
    statusClass.value = 'connected'
    term?.writeln(`\x1b[1;32m[已连接到 ${board.value?.name || boardId} @ ${baudRate.value}bps]\x1b[0m\r\n`)
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      switch (msg.type) {
        case 'connected':
          statusText.value = `已连接 - ${msg.message}`
          statusClass.value = 'connected'
          break
        case 'data':
          term?.write(msg.text)
          break
        case 'error':
          term?.writeln(`\r\n\x1b[1;31m[错误] ${msg.text}\x1b[0m\r\n`)
          break
        case 'info':
          term?.writeln(`\r\n\x1b[1;33m[${msg.text}]\x1b[0m\r\n`)
          break
      }
    } catch {
      // 原始数据直接显示
      term?.write(event.data)
    }
  }

  ws.onclose = () => {
    connected.value = false
    statusText.value = '已断开'
    statusClass.value = 'disconnected'
    term?.writeln('\r\n\x1b[1;31m[连接已断开]\x1b[0m\r\n')
  }

  ws.onerror = () => {
    statusText.value = '连接失败'
    statusClass.value = 'disconnected'
    term?.writeln('\r\n\x1b[1;31m[连接失败 - 请检查串口和板子状态]\x1b[0m\r\n')
  }
}

function disconnect() {
  if (ws) {
    ws.close()
    ws = null
  }
  connected.value = false
  statusText.value = '未连接'
  statusClass.value = 'disconnected'
}

function sendCtrlC() {
  // 发送 Ctrl+C (0x03)
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', mode: 'hex', text: '03' }))
    term?.writeln(' ^C')
  }
}

function sendCtrlD() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', mode: 'hex', text: '04' }))
    term?.writeln(' ^D')
  }
}

function sendCRLF() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    term?.write('\r\n')
    ws.send('\r\n')
  }
}

function clearTerminal() {
  term?.clear()
}

function flushBuffers() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'flush' }))
  }
}

function changeBaud(newBaud: number) {
  baudRate.value = newBaud
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'baud', value: newBaud }))
  }
}

function toggleDTR() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ctrl', signal: 'dtr' }))
  }
}

function toggleRTS() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ctrl', signal: 'rts' }))
  }
}
</script>

<template>
  <div class="terminal-page">
    <!-- 顶部工具栏 -->
    <div class="terminal-toolbar">
      <div class="toolbar-left">
        <button class="back-btn" @click="router.push('/boards')">← 返回</button>
        <span class="board-name" v-if="board">{{ board.name }}</span>
        <span class="board-port" v-if="board">{{ board.serial_port || '?' }}</span>
      </div>

      <div class="toolbar-center">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>

      <div class="toolbar-right">
        <select :value="baudRate" @change="changeBaud(Number(($event.target as any).value))" class="baud-select" title="波特率">
          <option :value="9600">9600</option>
          <option :value="19200">19200</option>
          <option :value="38400">38400</option>
          <option :value="57600">57600</option>
          <option :value="115200">115200</option>
          <option :value="230400">230400</option>
          <option :value="460800">460800</option>
          <option :value="921600">921600</option>
        </select>

        <button v-if="!connected" class="btn-connect" @click="connect">🔌 连接</button>
        <button v-else class="btn-disconnect" @click="disconnect">⏹ 断开</button>
      </div>
    </div>

    <!-- 快捷按钮栏 -->
    <div class="quick-buttons">
      <button @click="sendCtrlC" title="发送 Ctrl+C (终止)">Ctrl+C</button>
      <button @click="sendCtrlD" title="发送 Ctrl+D (EOF)">Ctrl+D</button>
      <button @click="sendCRLF" title="发送回车换行">⏎ CRLF</button>
      <button @click="flushBuffers" title="清空串口缓冲区">🗑 清缓冲</button>
      <button @click="clearTerminal" title="清空终端显示">🧹 清屏</button>
      <button @click="toggleDTR" title="切换 DTR 信号">DTR</button>
      <button @click="toggleRTS" title="切换 RTS 信号">RTS</button>
    </div>

    <!-- 终端 -->
    <div class="terminal-container" ref="terminalEl"></div>

    <!-- 底部提示 -->
    <div class="terminal-footer">
      <span>{{ connected ? '🟢 已连接 — 直接在终端中键入命令' : '⚪ 未连接 — 点击右上角 [连接] 开始' }}</span>
      <span class="footer-hint">Ctrl+C 终止 · 支持 ANSI 颜色 · 可粘贴</span>
    </div>
  </div>
</template>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  background: #0d0d1a;
  border-radius: 10px;
  overflow: hidden;
}

/* 工具栏 */
.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #16162a;
  border-bottom: 1px solid #2a2a4a;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  background: transparent;
  color: #888;
  border: 1px solid #444;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.back-btn:hover { color: #fff; border-color: #888; }

.board-name { color: #fff; font-weight: 600; font-size: 14px; }
.board-port { color: #888; font-size: 12px; }

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.status-dot.connected { background: #27ae60; box-shadow: 0 0 6px #27ae60; }
.status-dot.connecting { background: #f39c12; animation: blink 0.5s infinite; }
.status-dot.disconnected { background: #666; }

@keyframes blink { 50% { opacity: 0.3; } }

.status-text { color: #aaa; font-size: 13px; }

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.baud-select {
  background: #1a1a2e;
  color: #ccc;
  border: 1px solid #444;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.btn-connect {
  background: #27ae60;
  color: #fff;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.btn-disconnect {
  background: #c0392b;
  color: #fff;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

/* 快捷按钮 */
.quick-buttons {
  display: flex;
  gap: 6px;
  padding: 6px 12px;
  background: #111;
  border-bottom: 1px solid #2a2a4a;
  flex-shrink: 0;
}

.quick-buttons button {
  background: #1a1a2e;
  color: #aaa;
  border: 1px solid #333;
  padding: 3px 10px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  font-family: monospace;
}

.quick-buttons button:hover { background: #2a2a4a; color: #fff; }

/* 终端容器 */
.terminal-container {
  flex: 1;
  padding: 8px;
  overflow: hidden;
}

.terminal-container :deep(.xterm) {
  height: 100%;
}

.terminal-container :deep(.xterm-viewport) {
  scrollbar-width: thin;
  scrollbar-color: #444 #1a1a2e;
}

/* 底部提示 */
.terminal-footer {
  display: flex;
  justify-content: space-between;
  padding: 6px 16px;
  background: #111;
  border-top: 1px solid #2a2a4a;
  font-size: 11px;
  color: #666;
  flex-shrink: 0;
}

.footer-hint { color: #444; }
</style>
