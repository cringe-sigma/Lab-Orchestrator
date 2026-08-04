<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { boardApi } from '../api/client'

const route = useRoute(); const router = useRouter()
const boardId = Number(route.params.boardId)
const input = ref('')
const history = ref<string[]>([])
const el = ref<HTMLDivElement|null>(null)

async function send(){
  const cmd = input.value.trim()
  if(!cmd) return
  history.value.push('$ '+cmd)
  input.value = ''
  try {
    const r = await boardApi.exec(boardId, cmd)
    history.value.push(r.data.output)
  } catch(e: any){
    history.value.push(e.response?.data?.detail||'执行失败')
  }
  await nextTick()
  el.value?.scrollTo(0, el.value.scrollHeight)
}
</script>
<template>
<div class="term-page">
  <div class="bar">
    <button @click="router.push('/boards')">← 返回</button>
    <span>远程终端 #{{ boardId }}</span>
  </div>
  <div class="out" ref="el"><pre>{{ history.join('\n') }}</pre></div>
  <div class="inp">
    <span>$</span>
    <input v-model="input" @keyup.enter="send" placeholder="输入命令，回车执行..." autofocus />
    <button @click="send">执行</button>
  </div>
</div>
</template>
<style scoped>
.term-page{display:flex;flex-direction:column;height:calc(100vh - 100px);background:#1a1a2e;border-radius:10px;overflow:hidden}
.bar{display:flex;align-items:center;gap:12px;padding:8px 14px;background:#0d0d1a;border-bottom:1px solid #333;color:#aaa;font-size:13px;flex-shrink:0}
.bar button{padding:4px 12px;border-radius:4px;border:1px solid #444;background:transparent;color:#aaa;cursor:pointer}
.out{flex:1;overflow-y:auto;padding:8px 12px}
.out pre{margin:0;color:#a8d8ff;font:12px 'Consolas',monospace;white-space:pre-wrap}
.inp{display:flex;align-items:center;gap:6px;padding:8px 12px;background:#0d0d1a;border-top:1px solid #333;flex-shrink:0}
.inp span{color:#0f0;font:bold 14px 'Consolas',monospace}
.inp input{flex:1;background:transparent;border:none;color:#fff;font:13px 'Consolas',monospace;outline:none;padding:4px 0}
.inp button{background:#333;color:#0f0;border:1px solid #555;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px}
</style>
