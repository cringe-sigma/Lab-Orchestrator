<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { bookingApi, boardApi } from '../api/client'

const boards = ref<any[]>([])
const slots = ref<any[]>([])
const weekOffset = ref(0)
const showForm = ref(false)
const bookBoard = ref(0)
const bookDay = ref('')
const bookHour = ref(0)
const bookMin = ref(0)
const bookTitle = ref('')
const shareTarget = ref<any>(null)
const shareUserId = ref('')

const days = ['一','二','三','四','五','六','日']
const hours = [8,9,10,11,12,13,14,15,16,17,18,19,20]

const weekStart = computed(() => {
  const now = new Date()
  now.setDate(now.getDate() + weekOffset.value * 7)
  const day = now.getDay() || 7
  now.setDate(now.getDate() - day + 1)
  now.setHours(0,0,0,0)
  return now
})

function dateStr(d: Date, h: number, m: number) {
  const nd = new Date(d)
  nd.setDate(nd.getDate() + h)
  nd.setHours(Math.floor(m/2)+8, (m%2)*30, 0, 0)
  return nd.toISOString().slice(0,16)
}

function isBooked(boardId: number, d: Date, slot: number) {
  const start = new Date(d); start.setDate(start.getDate() + Math.floor(slot/2))
  start.setHours(8 + (slot % 2) * 0.5, (slot % 2) * 30, 0, 0)
  const end = new Date(start.getTime() + 30*60000)
  return slots.value.find(s =>
    s.board_id === boardId &&
    new Date(s.start) < end && new Date(s.end) > start
  )
}

async function quickBook(boardId: number, dayIdx: number, slotIdx: number) {
  const d = new Date(weekStart.value)
  const start = new Date(d); start.setDate(start.getDate() + dayIdx)
  start.setHours(8 + Math.floor(slotIdx/2), (slotIdx%2)*30, 0, 0)
  const end = new Date(start.getTime() + 30*60000)

  bookBoard.value = boardId
  bookDay.value = start.toISOString().slice(0,10)
  bookHour.value = start.getHours()
  bookMin.value = start.getMinutes()
  bookTitle.value = ''
  showForm.value = true
}

async function submitBooking() {
  const start = new Date(`${bookDay.value}T${String(bookHour.value).padStart(2,'0')}:${String(bookMin.value).padStart(2,'0')}:00+08:00`)
  const end = new Date(start.getTime() + 30*60000)
  try {
    await bookingApi.create({
      board_id: bookBoard.value,
      title: bookTitle.value || '预约',
      start_time: start.toISOString(),
      end_time: end.toISOString(),
    })
    showForm.value = false
    await loadSlots()
  } catch(e: any) { alert(e.response?.data?.detail || '预约失败') }
}

async function shareBooking(booking: any) {
  if (!shareUserId.value) return
  try {
    await fetch(`/api/bookings/${booking.id}/share`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      body: JSON.stringify({ user_ids: [parseInt(shareUserId.value)] }),
    })
    shareTarget.value = null; shareUserId.value = ''
  } catch(e: any) { alert('共享失败') }
}

async function loadSlots() {
  try {
    const date = weekStart.value.toISOString().slice(0,10)
    const r = await fetch(`/api/bookings/schedule?date=${date}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
    slots.value = (await r.json()).slots
  } catch {}
}

onMounted(async () => {
  try { boards.value = (await boardApi.list()).data } catch {}
  await loadSlots()
})
</script>

<template>
  <div class="cal-page">
    <div class="cal-header">
      <h2>📅 预约日历</h2>
      <div class="week-nav">
        <button @click="weekOffset--; loadSlots()">◀</button>
        <span>{{ weekStart.toLocaleDateString('zh-CN') }} — {{ new Date(weekStart.getTime()+6*86400000).toLocaleDateString('zh-CN') }}</span>
        <button @click="weekOffset++; loadSlots()">▶</button>
        <button @click="weekOffset=0; loadSlots()">本周</button>
      </div>
    </div>

    <div class="cal-grid">
      <div class="cal-corners">
        <div class="corner">板子</div>
        <div v-for="d in 7" :key="d" class="day-header">
          {{ days[d-1] }}<br/>
          <small>{{ new Date(weekStart.getTime()+(d-1)*86400000).toLocaleDateString('zh-CN',{month:'short',day:'numeric'}) }}</small>
        </div>
      </div>

      <div v-for="board in boards" :key="board.id" class="cal-row">
        <div class="board-label">
          <strong>{{ board.name }}</strong>
          <small :class="board.status==='online'?'online':'offline'">{{ board.status==='online'?'在线':'离线' }}</small>
        </div>
        <div v-for="dayIdx in 7" :key="dayIdx" class="day-col">
          <div
            v-for="slotIdx in 24"
            :key="slotIdx"
            class="slot"
            :class="{ booked: isBooked(board.id, weekStart, (dayIdx-1)*24 + slotIdx-1) }"
            @click="quickBook(board.id, dayIdx-1, slotIdx-1)"
            :title="'8:00起每30分钟'"
          >
            <span v-if="isBooked(board.id, weekStart, (dayIdx-1)*24 + slotIdx-1)" class="booked-mark">⚫</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷预约弹窗 -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm=false">
      <div class="modal">
        <h3>新建预约</h3>
        <p>时间: {{ bookDay }} {{ String(bookHour).padStart(2,'0') }}:{{ String(bookMin).padStart(2,'0') }}</p>
        <input v-model="bookTitle" placeholder="预约标题" class="inp" />
        <div class="btn-row">
          <button @click="showForm=false">取消</button>
          <button class="btn-ok" @click="submitBooking">确认</button>
        </div>
      </div>
    </div>

    <!-- 共享弹窗 -->
    <div v-if="shareTarget" class="modal-overlay" @click.self="shareTarget=null">
      <div class="modal">
        <h3>共享预约</h3>
        <p>{{ shareTarget.title }}</p>
        <input v-model="shareUserId" type="number" placeholder="输入用户ID" class="inp" />
        <div class="btn-row">
          <button @click="shareTarget=null">取消</button>
          <button class="btn-ok" @click="shareBooking(shareTarget)">共享</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cal-page { max-width: 100%; overflow-x: auto; }
.cal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px; }
.week-nav { display:flex; align-items:center; gap:8px; }
.week-nav button { padding:6px 12px; border:1px solid #ddd; background:#fff; border-radius:4px; cursor:pointer; }

.cal-grid { display:flex; flex-direction:column; gap:0; background:#fff; border-radius:10px; overflow:hidden; box-shadow:0 1px 6px rgba(0,0,0,.08); }
.cal-corners { display:flex; }
.corner { width:140px; min-width:140px; padding:8px; font-weight:600; font-size:13px; background:#f8f9fa; border-bottom:1px solid #eee; }
.day-header { flex:1; min-width:60px; padding:8px 4px; text-align:center; font-size:12px; background:#f8f9fa; border-bottom:1px solid #eee; border-left:1px solid #eee; }

.cal-row { display:flex; border-bottom:1px solid #f0f0f0; }
.board-label { width:140px; min-width:140px; padding:8px; font-size:12px; display:flex; flex-direction:column; }
.board-label .online { color:#27ae60; }
.board-label .offline { color:#e74c3c; }
.day-col { flex:1; min-width:60px; display:flex; flex-direction:column; border-left:1px solid #f0f0f0; }

.slot { height:18px; border-bottom:1px solid #fafafa; cursor:pointer; transition:background .1s; display:flex; align-items:center; justify-content:center; }
.slot:hover { background:#e3f2fd; }
.slot.booked { background:#e8e8e8; cursor:default; }
.slot:nth-child(even) { border-bottom:1px solid #eee; }
.booked-mark { font-size:8px; color:#888; }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; justify-content:center; align-items:center; z-index:300; }
.modal { background:#fff; padding:24px; border-radius:12px; width:360px; }
.modal h3 { margin-bottom:12px; }
.inp { width:100%; padding:8px 10px; border:1px solid #ddd; border-radius:6px; font-size:14px; margin:8px 0; }
.btn-row { display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }
.btn-row button { padding:8px 16px; border-radius:6px; border:1px solid #ddd; cursor:pointer; }
.btn-ok { background:#1a1a2e; color:#fff; border:none; }
</style>
