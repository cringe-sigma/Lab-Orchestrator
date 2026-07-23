<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { boardApi, type BoardData } from '../api/client'

const boards = ref<BoardData[]>([])
const loading = ref(true)
const showAddForm = ref(false)

// 添加板子表单
const form = ref({
  name: '',
  board_type: 'linux',
  conn_type: 'ssh',
  host: '',
  port: 22,
  username: '',
  serial_port: '',
  serial_baud: 115200,
  description: '',
})

// 命令执行
const execBoardId = ref<number | null>(null)
const execCommand = ref('')
const execResult = ref('')

onMounted(async () => {
  try {
    const res = await boardApi.list()
    boards.value = res.data
  } catch (err) {
    console.error('获取板子列表失败', err)
  } finally {
    loading.value = false
  }
})

async function addBoard() {
  try {
    const res = await boardApi.create(form.value)
    boards.value.push(res.data)
    showAddForm.value = false
    form.value = { name: '', board_type: 'linux', conn_type: 'ssh', host: '', port: 22, username: '', serial_port: '', serial_baud: 115200, description: '' }
  } catch (err) {
    console.error('添加板子失败', err)
  }
}

async function checkBoard(id: number) {
  try {
    const res = await boardApi.check(id)
    const board = boards.value.find((b) => b.id === id)
    if (board) board.status = res.data.status
  } catch (err) {
    console.error('检查失败', err)
  }
}

async function execOnBoard(id: number) {
  execResult.value = '执行中...'
  try {
    const res = await boardApi.exec(id, execCommand.value)
    execResult.value = res.data.output
  } catch (err: any) {
    execResult.value = err.response?.data?.detail || '执行失败'
  }
}

function getStatusClass(status: string) {
  return { online: 'status-online', offline: 'status-offline', busy: 'status-busy', error: 'status-error' }[status] || ''
}
</script>

<template>
  <div class="boards-page">
    <div class="page-header">
      <h2>📟 板子管理</h2>
      <button class="btn-primary" @click="showAddForm = !showAddForm">
        {{ showAddForm ? '取消' : '+ 添加板子' }}
      </button>
    </div>

    <!-- 添加板子表单 -->
    <div v-if="showAddForm" class="add-form card">
      <div class="form-row">
        <div class="form-group">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="如: ESP32-01" />
        </div>
        <div class="form-group">
          <label>板子类型</label>
          <select v-model="form.board_type">
            <option value="linux">Linux 板</option>
            <option value="mcu">MCU 裸机</option>
          </select>
        </div>
        <div class="form-group">
          <label>连接方式</label>
          <select v-model="form.conn_type">
            <option value="ssh">SSH</option>
            <option value="serial">串口</option>
          </select>
        </div>
      </div>
      <div v-if="form.conn_type === 'ssh'" class="form-row">
        <div class="form-group">
          <label>IP 地址</label>
          <input v-model="form.host" placeholder="192.168.1.100" />
        </div>
        <div class="form-group">
          <label>端口</label>
          <input v-model="form.port" type="number" />
        </div>
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" placeholder="pi" />
        </div>
      </div>
      <div v-if="form.conn_type === 'serial'" class="form-row">
        <div class="form-group">
          <label>串口</label>
          <input v-model="form.serial_port" placeholder="COM3 或 /dev/ttyUSB0" />
        </div>
        <div class="form-group">
          <label>波特率</label>
          <input v-model="form.serial_baud" type="number" />
        </div>
      </div>
      <button class="btn-primary" @click="addBoard">确认添加</button>
    </div>

    <!-- 板子列表 -->
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="boards.length === 0" class="empty">
      还没有添加板子，点击上方按钮添加
    </div>

    <div v-else class="board-grid">
      <div v-for="board in boards" :key="board.id" class="board-card card">
        <div class="board-header">
          <span class="board-name">{{ board.name }}</span>
          <span class="board-status" :class="getStatusClass(board.status)">
            {{ { online: '在线', offline: '离线', busy: '占用中', error: '异常' }[board.status] || board.status }}
          </span>
        </div>
        <div class="board-info">
          <div>{{ board.conn_type === 'ssh' ? board.host : board.serial_port }}</div>
          <div class="board-type">{{ board.board_type === 'linux' ? 'Linux' : 'MCU' }}</div>
          <div v-if="board.locked_by" class="locked">🔒 已被占用</div>
        </div>
        <div class="board-actions">
          <button class="btn-sm" @click="checkBoard(board.id)">检查</button>
          <button class="btn-sm" @click="execBoardId = board.id; execResult = ''">执行命令</button>
        </div>
        <div v-if="execBoardId === board.id" class="exec-panel">
          <input v-model="execCommand" placeholder="输入命令" @keyup.enter="execOnBoard(board.id)" />
          <button class="btn-sm" @click="execOnBoard(board.id)">执行</button>
          <pre v-if="execResult" class="exec-result">{{ execResult }}</pre>
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

.add-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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

.board-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.board-name {
  font-size: 16px;
  font-weight: 600;
}

.board-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.status-online { background: #d4edda; color: #155724; }
.status-offline { background: #f8d7da; color: #721c24; }
.status-busy { background: #fff3cd; color: #856404; }
.status-error { background: #f8d7da; color: #721c24; }

.board-info {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.board-actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  background: #f0f2f5;
  border: 1px solid #ddd;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}

.btn-sm:hover {
  background: #e4e6e9;
}

.exec-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.exec-panel input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.exec-result {
  width: 100%;
  background: #1a1a2e;
  color: #0f0;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow: auto;
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

.loading {
  text-align: center;
  padding: 40px;
  color: #888;
}

.empty {
  text-align: center;
  padding: 60px;
  color: #888;
}

.locked {
  color: #e67e22;
  font-weight: 500;
}
</style>
