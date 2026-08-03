<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const route = useRoute(); const router = useRouter()
const boardId = Number(route.params.boardId)
const termEl = ref<HTMLDivElement|null>(null)
const status = ref('未连接')
let term: Terminal|null=null; let ws: WebSocket|null=null

onMounted(async()=>{await nextTick(); initTerm()})
onUnmounted(()=>disconnect())

function initTerm(){
  if(!termEl.value)return
  term=new Terminal({cursorBlink:true,fontSize:14,fontFamily:"'Consolas',monospace",theme:{background:'#1a1a2e',foreground:'#e0e0e0',cursor:'#00ff88'},scrollback:5000})
  term.loadAddon(new FitAddon())
  term.open(termEl.value);(term as any)._addon.fit()
  term.writeln('\x1b[1;36m=== Remote Terminal ===\x1b[0m')
  term.writeln('点击 [连接] 开始')
  term.onData(d=>{if(ws?.readyState===WebSocket.OPEN)ws.send(d)})
  window.addEventListener('resize',()=>(term as any)._addon?.fit())
}

function connect(){
  const t=localStorage.getItem('token')
  const p=location.protocol==='https:'?'wss':'ws'
  ws=new WebSocket(`${p}://${location.hostname}:8000/ws/bridge-terminal/${boardId}`)
  ws.onopen=()=>{status.value='已连接'}
  ws.onmessage=e=>{try{term?.write(e.data)}catch{term?.write(e.data)}}
  ws.onclose=()=>{status.value='断开'}
  status.value='连接中...'
}
function disconnect(){ws?.close();status.value='未连接'}
</script>
<template>
<div class="page">
  <div class="bar">
    <button @click="router.push('/boards')">← 返回</button>
    <span>远程板子 #{{ boardId }}</span>
    <span>{{ status }}</span>
    <button v-if="!ws||ws.readyState!==1" @click="connect" class="go">🔌 连接</button>
    <button v-else @click="disconnect" class="stop">⏹ 断开</button>
  </div>
  <div class="term" ref="termEl"></div>
</div>
</template>
<style scoped>
.page{display:flex;flex-direction:column;height:calc(100vh - 100px);background:#0d0d1a;border-radius:10px;overflow:hidden}
.bar{display:flex;align-items:center;gap:12px;padding:8px 14px;background:#16162a;border-bottom:1px solid #2a2a4a;flex-shrink:0;color:#aaa;font-size:13px}
.bar button{padding:4px 12px;border-radius:4px;border:1px solid #444;background:transparent;color:#aaa;cursor:pointer;font-size:12px}
.bar button:hover{color:#fff}
.go{background:#27ae60!important;color:#fff!important;border:none!important}
.stop{background:#c0392b!important;color:#fff!important;border:none!important}
.term{flex:1;padding:6px}
</style>
