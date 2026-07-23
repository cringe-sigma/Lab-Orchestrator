<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { bookingApi, boardApi, type BookingData, type BoardData } from '../api/client'

const bookings = ref<BookingData[]>([])
const boards = ref<BoardData[]>([])
const loading = ref(true)

// 新建预约表单
const showForm = ref(false)
const form = ref({
  board_id: 0,
  title: '',
  start_time: '',
  end_time: '',
})

const statusMap: Record<string, string> = {
  pending: '待开始',
  active: '进行中',
  completed: '已完成',
  cancelled: '已取消',
  expired: '已过期',
}

onMounted(async () => {
  try {
    const [bRes, brRes] = await Promise.all([bookingApi.list(), boardApi.list()])
    bookings.value = bRes.data
    boards.value = brRes.data
  } catch (err) {
    console.error('获取数据失败', err)
  } finally {
    loading.value = false
  }
})

async function createBooking() {
  try {
    const res = await bookingApi.create({
      board_id: form.value.board_id,
      title: form.value.title,
      start_time: new Date(form.value.start_time).toISOString(),
      end_time: new Date(form.value.end_time).toISOString(),
    })
    if (res.data.success) {
      // 刷新列表
      const bRes = await bookingApi.list()
      bookings.value = bRes.data
      showForm.value = false
    }
  } catch (err: any) {
    alert(err.response?.data?.detail || '预约失败')
  }
}

async function cancelBooking(id: number) {
  if (!confirm('确定取消此预约？')) return
  try {
    await bookingApi.cancel(id)
    const bRes = await bookingApi.list()
    bookings.value = bRes.data
  } catch (err: any) {
    alert(err.response?.data?.detail || '取消失败')
  }
}

const now = new Date()
const minStart = now.toISOString().slice(0, 16)
</script>

<template>
  <div class="booking-page">
    <div class="page-header">
      <h2>📅 预约管理</h2>
      <button class="btn-primary" @click="showForm = !showForm">
        {{ showForm ? '取消' : '+ 新建预约' }}
      </button>
    </div>

    <!-- 新建预约 -->
    <div v-if="showForm" class="booking-form card">
      <div class="form-row">
        <div class="form-group">
          <label>板子 *</label>
          <select v-model="form.board_id">
            <option value="0" disabled>选择板子</option>
            <option v-for="b in boards" :key="b.id" :value="b.id">
              {{ b.name }} ({{ b.status }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>标题</label>
          <input v-model="form.title" placeholder="实验名称" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>开始时间 *</label>
          <input v-model="form.start_time" type="datetime-local" :min="minStart" />
        </div>
        <div class="form-group">
          <label>结束时间 *</label>
          <input v-model="form.end_time" type="datetime-local" :min="form.start_time || minStart" />
        </div>
      </div>
      <button class="btn-primary" @click="createBooking" :disabled="!form.board_id || !form.start_time || !form.end_time">
        确认预约
      </button>
    </div>

    <!-- 预约列表 -->
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="bookings.length === 0" class="empty">
      暂无预约记录
    </div>

    <div v-else class="booking-list">
      <div v-for="bk in bookings" :key="bk.id" class="booking-item card">
        <div class="booking-main">
          <span class="booking-title">{{ bk.title || '无标题' }}</span>
          <span class="booking-status" :class="bk.status">
            {{ statusMap[bk.status] || bk.status }}
          </span>
        </div>
        <div class="booking-time">
          {{ new Date(bk.start_time).toLocaleString() }} — {{ new Date(bk.end_time).toLocaleString() }}
        </div>
        <div class="booking-actions">
          <span class="board-ref">板子 #{{ bk.board_id }}</span>
          <button
            v-if="bk.status === 'pending' || bk.status === 'active'"
            class="btn-sm btn-cancel"
            @click="cancelBooking(bk.id)"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}

.booking-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 13px;
  color: #666;
}

.form-group input,
.form-group select {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.booking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.booking-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.booking-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.booking-title {
  font-weight: 600;
  font-size: 15px;
}

.booking-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.booking-status.pending { background: #fff3cd; color: #856404; }
.booking-status.active { background: #d4edda; color: #155724; }
.booking-status.completed { background: #e2e3e5; color: #383d41; }
.booking-status.cancelled { background: #f8d7da; color: #721c24; }

.booking-time {
  font-size: 13px;
  color: #888;
}

.booking-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.board-ref {
  font-size: 12px;
  color: #aaa;
}

.btn-primary {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-sm {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}

.btn-cancel {
  background: #fff;
  border: 1px solid #e74c3c;
  color: #e74c3c;
}

.btn-cancel:hover {
  background: #fde8e8;
}

.loading { text-align: center; padding: 40px; color: #888; }
.empty { text-align: center; padding: 60px; color: #888; }
</style>
