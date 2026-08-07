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
const connected = ref(false)
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

onMounted(async () => {
  try { const r = await boardApi.get(boardId); board.value = r.data } catch {}
  await nextTick(); initTerminal()
})
onUnmounted(() => disconnect())

function initTerminal() {
  if (!terminalEl.value) return
  term = new Terminal({
    cursorBlink: true, fontSize: 14,
    fontFamily: "'Cascadia Code', 'Consolas', monospace",
    theme: { background: '#1a1a2e', foreground: '#e0e0e0', cursor: '#00ff88' },
    scrollback: 5000,
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(terminalEl.value)
  fitAddon.fit()
  term.writeln('\x1b[1;36mConnecting...\x1b[0m')
  term.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'input', text: data }))
  })
  window.addEventListener('resize', () => fitAddon?.fit())
  connect()
}

function connect() {
  const token = localStorage.getItem('token')
  const host = location.hostname
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  statusText.value = '连接中...'
  ws = new WebSocket(`${protocol}://${host}:8000/ws/ssh-terminal/${boardId}?token=${token}`)
  ws.onopen = () => { connected.value = true; statusText.value = '已连接' }
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'data') term?.write(msg.text)
      else if (msg.type === 'connected') statusText.value = msg.message
      else if (msg.type === 'error') term?.writeln(`\r\n\x1b[1;31m[${msg.text}]\x1b[0m`)
    } catch { term?.write(e.data) }
  }
  ws.onclose = (ev) => { connected.value = false; statusText.value = 'Disconnected'; term?.writeln('\r\n\x1b[1;31m[Disconnected]\x1b[0m') }
  ws.onerror = () => { statusText.value = 'Connection failed'; term?.writeln('\r\n\x1b[1;31m[Connection failed - check if board is online]\x1b[0m') }
}

function disconnect() { ws?.close(); ws = null; connected.value = false }
</script>

<template>
  <div class="term-page">
    <div class="toolbar">
      <button class="back-btn" @click="router.push('/boards')">← 返回</button>
      <span class="board-name" v-if="board">{{ board.name }} (SSH)</span>
      <span class="status" :style="{color: connected?'#27ae60':'#666'}">{{ statusText }}</span>
      <button v-if="!connected" class="btn-connect" @click="connect">🔌 连接</button>
      <button v-else class="btn-disconnect" @click="disconnect">⏹ 断开</button>
    </div>
    <div class="term-container" ref="terminalEl"></div>
  </div>
</template>

<style scoped>
.term-page { display:flex; flex-direction:column; height:calc(100vh - 100px); background:#0d0d1a; border-radius:10px; overflow:hidden; }
.toolbar { display:flex; align-items:center; gap:16px; padding:10px 16px; background:#16162a; border-bottom:1px solid #2a2a4a; flex-shrink:0; }
.back-btn { background:transparent; color:#888; border:1px solid #444; padding:4px 12px; border-radius:4px; cursor:pointer; font-size:13px; }
.back-btn:hover { color:#fff; }
.board-name { color:#fff; font-weight:600; font-size:14px; flex:1; }
.status { font-size:13px; }
.btn-connect { background:#27ae60; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; font-weight:600; }
.btn-disconnect { background:#c0392b; color:#fff; border:none; padding:6px 16px; border-radius:4px; cursor:pointer; }
.term-container { flex:1; padding:8px; overflow:hidden; }
.term-container :deep(.xterm) { height:100%; }
</style>
