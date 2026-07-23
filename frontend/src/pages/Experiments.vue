<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { experimentApi, boardApi, type ExperimentData, type BoardData } from '../api/client'

const experiments = ref<ExperimentData[]>([])
const boards = ref<BoardData[]>([])
const loading = ref(true)
const showForm = ref(false)
const detailExp = ref<ExperimentData | null>(null)
const runOutput = ref<string[]>([])

const form = ref({
  board_id: 0,
  name: '',
  description: '',
})

const statusMap: Record<string, string> = {
  pending: '待执行',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
}

onMounted(async () => {
  try {
    const [eRes, bRes] = await Promise.all([experimentApi.list(), boardApi.list()])
    experiments.value = eRes.data
    boards.value = bRes.data
  } catch (err) {
    console.error('获取数据失败', err)
  } finally {
    loading.value = false
  }
})

async function createExperiment() {
  try {
    const res = await experimentApi.create({
      board_id: form.value.board_id,
      name: form.value.name,
      description: form.value.description,
      steps: JSON.stringify([]),
    })
    experiments.value.unshift(res.data)
    showForm.value = false
    form.value = { board_id: 0, name: '', description: '' }
  } catch (err) {
    console.error('创建失败', err)
  }
}

async function runExperiment(id: number) {
  runOutput.value = []
  detailExp.value = experiments.value.find((e) => e.id === id) || null
  try {
    const res = await experimentApi.run(id)
    runOutput.value = res.data.results?.map((r: any) => r.output || JSON.stringify(r)) || []
    // 刷新状态
    const eRes = await experimentApi.list()
    experiments.value = eRes.data
  } catch (err: any) {
    runOutput.value = [err.response?.data?.detail || '执行失败']
  }
}

function viewDetail(exp: ExperimentData) {
  detailExp.value = exp
  runOutput.value = []
}
</script>

<template>
  <div class="experiments-page">
    <div class="page-header">
      <h2>🧪 实验管理</h2>
      <button class="btn-primary" @click="showForm = !showForm">
        {{ showForm ? '取消' : '+ 新建实验' }}
      </button>
    </div>

    <!-- 新建实验 -->
    <div v-if="showForm" class="exp-form card">
      <div class="form-row">
        <div class="form-group">
          <label>板子 *</label>
          <select v-model="form.board_id">
            <option value="0" disabled>选择板子</option>
            <option v-for="b in boards" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>实验名称 *</label>
          <input v-model="form.name" placeholder="如: GPIO 测试" />
        </div>
      </div>
      <div class="form-group">
        <label>描述</label>
        <textarea v-model="form.description" placeholder="实验内容描述" rows="2"></textarea>
      </div>
      <button class="btn-primary" @click="createExperiment" :disabled="!form.board_id || !form.name">
        创建
      </button>
    </div>

    <!-- 实验列表 -->
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="experiments.length === 0" class="empty">
      暂无实验记录，可以新建实验或让 AI 助手帮你创建
    </div>

    <div v-else class="exp-list">
      <div v-for="exp in experiments" :key="exp.id" class="exp-item card">
        <div class="exp-header">
          <div>
            <span class="exp-name">{{ exp.name }}</span>
            <span class="exp-board">板子 #{{ exp.board_id }}</span>
          </div>
          <span class="exp-status" :class="exp.status">
            {{ statusMap[exp.status] || exp.status }}
          </span>
        </div>
        <div class="exp-desc" v-if="exp.description">{{ exp.description }}</div>
        <div class="exp-actions">
          <span class="exp-time">{{ new Date(exp.created_at).toLocaleString() }}</span>
          <div class="exp-btns">
            <button class="btn-sm" @click="viewDetail(exp)">详情</button>
            <button
              v-if="exp.status === 'pending'"
              class="btn-sm btn-run"
              @click="runExperiment(exp.id)"
            >
              运行
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailExp" class="modal-overlay" @click.self="detailExp = null">
      <div class="modal">
        <h3>{{ detailExp.name }}</h3>
        <p class="modal-desc">{{ detailExp.description || '无描述' }}</p>
        <div class="modal-section">
          <strong>状态:</strong> {{ statusMap[detailExp.status] }}
        </div>
        <div class="modal-section" v-if="detailExp.result_summary">
          <strong>结果摘要:</strong>
          <pre>{{ detailExp.result_summary }}</pre>
        </div>
        <div class="modal-section" v-if="runOutput.length">
          <strong>运行输出:</strong>
          <pre v-for="(line, i) in runOutput" :key="i" class="output-line">{{ line }}</pre>
        </div>
        <button class="btn-primary" @click="detailExp = null">关闭</button>
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

.exp-form {
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
.form-group select,
.form-group textarea {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.exp-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.exp-name {
  font-weight: 600;
  font-size: 15px;
  margin-right: 8px;
}

.exp-board {
  font-size: 12px;
  color: #aaa;
}

.exp-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.exp-status.pending { background: #fff3cd; color: #856404; }
.exp-status.running { background: #cce5ff; color: #004085; }
.exp-status.completed { background: #d4edda; color: #155724; }
.exp-status.failed { background: #f8d7da; color: #721c24; }

.exp-desc {
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}

.exp-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.exp-time {
  font-size: 12px;
  color: #aaa;
}

.exp-btns {
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

.btn-run {
  background: #1a1a2e;
  color: #fff;
  border: none;
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

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 200;
}

.modal {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h3 {
  margin-bottom: 8px;
}

.modal-desc {
  color: #888;
  font-size: 14px;
  margin-bottom: 12px;
}

.modal-section {
  margin-bottom: 12px;
}

.output-line {
  background: #1a1a2e;
  color: #0f0;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 4px;
  white-space: pre-wrap;
}

.loading { text-align: center; padding: 40px; color: #888; }
.empty { text-align: center; padding: 60px; color: #888; }
</style>
