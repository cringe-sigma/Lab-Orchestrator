<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { boardApi, type BoardData } from '../api/client'

const boards = ref<BoardData[]>([])
const loading = ref(true)
const showAddForm = ref(false)

// 删除弹窗
const deleteTarget = ref<BoardData | null>(null)
const deletePassword = ref('')
const deleteError = ref('')

async function confirmDelete() {
  deleteError.value = ''
  if (!deleteTarget.value) return
  try {
    await boardApi.delete(deleteTarget.value.id, deletePassword.value)
    boards.value = boards.value.filter(b => b.id !== deleteTarget.value!.id)
    deleteTarget.value = null
    deletePassword.value = ''
  } catch (e: any) {
    deleteError.value = e.response?.data?.detail || '删除失败'
  }
}

// 服务器地址（动态获取）
import { bookingApi } from '../api/client'

const serverHost = window.location.hostname
const serverUrl = `http://${serverHost}:8000`
const wsUrl = `ws://${serverHost}:8000/ws/board`

// 活跃预约检查
const activeBookings = ref<Set<number>>(new Set())

onMounted(async () => {
  try {
    const bRes = await boardApi.list()
    boards.value = bRes.data
  } catch (err) {
    console.error('获取板子列表失败', err)
  } finally {
    loading.value = false
  }
  // 独立加载预约信息（失败不影响板子列表）
  try {
    const bkRes = await bookingApi.list()
    bkRes.data.filter((bk: any) => bk.status === 'active').forEach((bk: any) => activeBookings.value.add(bk.board_id))
  } catch (err) {
    console.error('获取预约数据失败', err)
  }
})

// 添加板子表单
const form = ref({
  name: '',
  board_type: 'linux',
  conn_type: 'ssh',
  host: '',
  port: 22,
  username: '',
  ssh_password: '',
  use_jump: false,
  jump_host: '',
  jump_port: 22,
  jump_username: '',
  jump_password: '',
  serial_port: '',
  serial_baud: 115200,
  description: '',
})

// 命令执行
const execBoardId = ref<number | null>(null)
const execCommand = ref('')
const execHistory = ref<string[]>([])

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
  const cmd = execCommand.value.trim()
  if (!cmd) return
  execHistory.value.push(`$ ${cmd}`)
  execCommand.value = ''
  try {
    const res = await boardApi.exec(id, cmd)
    execHistory.value.push(res.data.output)
  } catch (err: any) {
    execHistory.value.push(err.response?.data?.detail || '执行失败')
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
      <div class="header-buttons">
        <router-link to="/board-setup" class="btn-tutorial">🔌 接线教程</router-link>
        <button class="btn-primary" @click="showAddForm = !showAddForm">
          {{ showAddForm ? '取消' : '+ 添加板子' }}
        </button>
      </div>
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
            <option value="ssh">SSH (本地)</option>
            <option value="serial">串口 (本地)</option>
            <option value="remote">远程代理 (board-agent)</option>
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
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.ssh_password" type="password" placeholder="SSH密码（可选）" />
        </div>
      </div>
      <!-- 跳板开关 -->
      <div v-if="form.conn_type === 'ssh'" class="jump-toggle">
        <label>
          <input type="checkbox" v-model="form.use_jump" />
          通过跳板 (jump host) 连接 — 适用 Pi 在远程计算机后面的场景
        </label>
      </div>
      <div v-if="form.conn_type === 'ssh' && form.use_jump" class="form-row jump-fields">
        <div class="form-group">
          <label>跳板 IP</label>
          <input v-model="form.jump_host" placeholder="192.168.1.100" />
        </div>
        <div class="form-group">
          <label>跳板端口</label>
          <input v-model="form.jump_port" type="number" />
        </div>
        <div class="form-group">
          <label>跳板用户名</label>
          <input v-model="form.jump_username" placeholder="user" />
        </div>
        <div class="form-group">
          <label>跳板密码</label>
          <input v-model="form.jump_password" type="password" placeholder="跳板SSH密码" />
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
      <div v-if="form.conn_type === 'remote'" class="remote-note">
        <p>💡 远程板子添加后，系统会自动生成连接 Token。</p>

        <p>💡 Token generated. On the remote Windows machine:</p>
        <ol>
          <li>Download: <code>Invoke-WebRequest {{ serverUrl }}/static/bridge.ps1 -OutFile bridge.ps1</code></li>
          <li>Edit <code>bridge.ps1</code>: update <code>$b</code> <code>$u</code> <code>$t</code></li>
          <li>Run: <code>.\bridge.ps1</code></li>
        </ol>
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
          <div v-if="board.conn_type === 'ssh'">{{ board.host }}:{{ board.port }}</div>
          <div v-else-if="board.conn_type === 'serial'">{{ board.serial_port }}</div>
          <div v-else>🌐 远程连接</div>
          <div class="board-type">{{ { linux: 'Linux', mcu: 'MCU' }[board.board_type] || board.board_type }}</div>
          <div class="conn-type-badge">{{ { ssh: 'SSH', serial: '串口', remote: '远程' }[board.conn_type] || board.conn_type }}</div>
          <div v-if="board.locked_by" class="locked">🔒 已被占用</div>
        </div>
        <div v-if="board.board_token" class="token-display">
          <span class="token-label">🔑 Token: {{ board.board_token }}</span>
          <p class="token-hint">
            <strong>Remote machine:</strong><br/>
            1. Download: <code>Invoke-WebRequest {{ serverUrl }}/static/bridge.ps1 -OutFile bridge.ps1</code><br/>
            2. Edit <code>bridge.ps1</code>: set $b $u $t<br/>
            3. Run: <code>.\bridge.ps1</code>
          </p>
        </div>
        <div class="board-info-row">
          <span v-if="activeBookings.has(board.id)" class="booking-badge">📅 已预约</span>
          <span v-else class="booking-badge no-booking">⚠️ 未预约</span>
        </div>
        <div class="board-actions">
          <button class="btn-sm" @click="checkBoard(board.id)">检查</button>
          <button class="btn-sm" @click="execBoardId = board.id; execHistory = []">执行命令</button>
          <router-link
            v-if="board.conn_type === 'serial'"
            :to="'/terminal/' + board.id"
            class="btn-sm btn-terminal"
          >🖥️ 串口终端</router-link>
          <router-link
            v-if="board.conn_type === 'ssh'"
            :to="'/ssh-terminal/' + board.id"
            class="btn-sm btn-terminal"
          >💻 SSH 终端</router-link>
          <router-link
            v-if="board.conn_type === 'remote' && board.status === 'online'"
            :to="'/bridge-terminal/' + board.id"
            class="btn-sm btn-terminal"
          >💻 终端</router-link>
          <button class="btn-sm btn-delete" @click="deleteTarget = board; deleteInput = ''; deleteError = ''">🗑 删除</button>
        </div>
        <div v-if="execBoardId === board.id" class="exec-panel">
          <div class="term-output" v-if="execHistory.length"><pre>{{ execHistory.join('\n') }}</pre></div>
          <div class="term-input">
            <span class="prompt">$</span>
            <input ref="cmdInput" v-model="execCommand" placeholder="输入命令..." @keyup.enter="execOnBoard(board.id)" />
            <button class="btn-sm" @click="execOnBoard(board.id)">执行</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 删除确认弹窗 ===== -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="delete-modal">
        <h3>⚠️ 确认删除板子</h3>
        <p>即将删除: <strong>{{ deleteTarget.name }}</strong></p>
        <p class="hint">此操作不可撤销，请输入当前账号密码确认:</p>
        <input
          v-model="deletePassword"
          type="password"
          placeholder="输入密码确认"
          class="delete-input"
          @keyup.enter="confirmDelete"
        />
        <p v-if="deleteError" class="delete-error">{{ deleteError }}</p>
        <div class="delete-buttons">
          <button class="btn-cancel" @click="deleteTarget = null">取消</button>
          <button
            class="btn-danger"
            :disabled="!deletePassword"
            @click="confirmDelete"
          >确认删除</button>
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

.header-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.btn-tutorial {
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-tutorial:hover {
  background: #bbdefb;
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

.btn-terminal {
  background: #1a1a2e;
  color: #fff;
  text-decoration: none;
  display: inline-block;
}

.btn-terminal:hover {
  background: #2a2a4e;
}

.exec-panel {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eee;
}

.term-output {
  width: 100%;
  background: #1a1a2e;
  color: #a8d8ff;
  padding: 8px 12px;
  border-radius: 6px 6px 0 0;
  font-size: 12px;
  font-family: 'Consolas', 'Courier New', monospace;
  min-height: 60px;
  max-height: 240px;
  overflow-y: auto;
}

.term-output pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.term-input {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #1a1a2e;
  padding: 6px 12px;
  border-radius: 0 0 6px 6px;
  border-top: 1px solid #333;
}

.term-input .prompt {
  color: #0f0;
  font-weight: bold;
  font-family: 'Consolas', monospace;
  font-size: 13px;
}

.term-input input {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  outline: none;
  padding: 4px 0;
}

.term-input .btn-sm {
  background: #333;
  color: #0f0;
  border: 1px solid #555;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
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

.booking-badge { font-size:11px; padding:2px 8px; border-radius:10px; }
.booking-badge:not(.no-booking) { background:#d4edda; color:#155724; }
.booking-badge.no-booking { background:#fff3cd; color:#856404; }

.board-info-row { margin: 4px 0; }

.btn-delete { color: #e74c3c; border-color: #e74c3c; background: #fff; }
.btn-delete:hover { background: #fde8e8; }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.4); display:flex; justify-content:center; align-items:center; z-index:300; }
.delete-modal { background:#fff; padding:28px; border-radius:12px; width:440px; box-shadow:0 8px 32px rgba(0,0,0,0.2); }
.delete-modal h3 { margin-bottom:12px; color:#c0392b; }
.delete-modal p { margin-bottom:8px; font-size:14px; color:#666; }
.delete-name { background:#fef3e2; padding:8px 12px; border-radius:6px; font-size:15px; color:#e67e22; margin:8px 0; }
.delete-input { width:100%; padding:10px 12px; border:1px solid #ddd; border-radius:6px; font-size:14px; margin:8px 0; }
.delete-input:focus { border-color:#e74c3c; outline:none; }
.delete-error { color:#e74c3c; font-size:13px; }
.delete-buttons { display:flex; gap:10px; justify-content:flex-end; margin-top:12px; }
.btn-cancel { background:#f0f0f0; border:1px solid #ddd; padding:8px 20px; border-radius:6px; cursor:pointer; }
.btn-danger { background:#e74c3c; color:#fff; border:none; padding:8px 20px; border-radius:6px; cursor:pointer; font-weight:600; }
.btn-danger:disabled { background:#f5b7b1; cursor:not-allowed; }

.conn-type-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e8f0fe;
  color: #1967d2;
}

.remote-note {
  background: #e3f2fd;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #1565c0;
  line-height: 1.6;
}

.conn-method {
  background: #e8f5e9;
  border: 1px solid #a5d6a7;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 8px 0;
}

.conn-method pre {
  background: #1a1a2e;
  color: #a8d8ff;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 11px;
  overflow-x: auto;
  margin: 8px 0;
  white-space: pre-wrap;
  word-break: break-all;
  max-width: 100%;
}

.conn-method small {
  color: #666;
  font-size: 11px;
}

.remote-note code {
  background: #bbdefb;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.jump-toggle { margin: 4px 0; }
.jump-toggle label { font-size: 13px; color: #666; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.jump-toggle input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; }
.jump-fields { background: #f0f4ff; padding: 12px; border-radius: 8px; border: 1px dashed #90caf9; }

.token-display {
  background: #fef3e2;
  padding: 10px 14px;
  border-radius: 6px;
  margin-top: 8px;
  font-size: 13px;
}

.token-label {
  font-weight: 600;
  color: #e67e22;
}

.token-display code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  word-break: break-all;
  color: #333;
  border: 1px solid #f0c06d;
}

.token-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #888;
}

.token-hint code {
  background: #f5f5f5;
  border: 1px solid #ddd;
  padding: 1px 4px;
  border-radius: 3px;
}
</style>
