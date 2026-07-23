<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { experimentApi, boardApi, type BoardData } from '../api/client'

const boards = ref<BoardData[]>([])
const selectedBoardId = ref<number>(0)
const messages = ref<{ role: string; content: string }[]>([])
const input = ref('')
const sending = ref(false)

onMounted(async () => {
  try {
    const res = await boardApi.list()
    boards.value = res.data
    if (boards.value.length > 0) {
      selectedBoardId.value = boards.value[0].id
    }
  } catch (err) {
    console.error('获取板子列表失败', err)
  }
})

async function sendMessage() {
  if (!input.value.trim() || !selectedBoardId.value) return

  const userMsg = input.value
  input.value = ''
  messages.value.push({ role: 'user', content: userMsg })
  sending.value = true

  try {
    const res = await experimentApi.aiChat(selectedBoardId.value, userMsg)
    messages.value.push({ role: 'assistant', content: res.data.reply })
  } catch (err: any) {
    messages.value.push({
      role: 'assistant',
      content: '❌ 请求失败: ' + (err.response?.data?.detail || err.message),
    })
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="ai-page">
    <div class="page-header">
      <h2>🤖 AI 实验助手</h2>
      <div class="board-selector">
        <label>操作板子：</label>
        <select v-model="selectedBoardId">
          <option v-for="b in boards" :key="b.id" :value="b.id">
            {{ b.name }} ({{ b.status }})
          </option>
        </select>
      </div>
    </div>

    <div class="chat-layout">
      <!-- 聊天区 -->
      <div class="chat-area card">
        <div class="chat-messages" ref="msgContainer">
          <div v-if="messages.length === 0" class="chat-hint">
            <p>💡 你可以这样对 AI 说：</p>
            <ul>
              <li>"列出我所有可用的板子"</li>
              <li>"在板子上跑一个简单的 GPIO 测试"</li>
              <li>"帮我编译这个 C 程序并运行"</li>
              <li>"写一个脚本测试所有 GPIO 引脚输出"</li>
              <li>"帮我创建一个实验：压力测试 CPU 15 分钟"</li>
            </ul>
          </div>
          <div v-for="(msg, i) in messages" :key="i" class="msg" :class="msg.role">
            <div class="msg-label">{{ msg.role === 'user' ? '🧑 你' : '🤖 AI' }}</div>
            <div class="msg-content">{{ msg.content }}</div>
          </div>
          <div v-if="sending" class="msg assistant">
            <div class="msg-label">🤖 AI</div>
            <div class="msg-content thinking">思考中...</div>
          </div>
        </div>

        <div class="chat-input">
          <input
            v-model="input"
            type="text"
            placeholder="输入你的实验需求..."
            @keyup.enter="sendMessage"
            :disabled="sending || !selectedBoardId"
          />
          <button class="btn-send" @click="sendMessage" :disabled="sending || !input.trim() || !selectedBoardId">
            发送
          </button>
        </div>
      </div>

      <!-- 说明区 -->
      <div class="info-panel card">
        <h4>使用说明</h4>
        <ul>
          <li>AI 只能执行软件操作，不会触碰硬件</li>
          <li>高危操作（烧录固件等）需要你二次确认</li>
          <li>每步执行结果都会实时显示</li>
          <li>实验记录会保存到<a href="#/experiments">实验管理</a></li>
        </ul>
        <h4>当前板子</h4>
        <p v-if="selectedBoardId && boards.find(b => b.id === selectedBoardId)">
          {{ boards.find(b => b.id === selectedBoardId)?.name }}
          （{{ boards.find(b => b.id === selectedBoardId)?.host || boards.find(b => b.id === selectedBoardId)?.serial_port || '未配置' }}）
        </p>
        <p v-else class="no-board">请先在板子管理中添加板子</p>
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
  flex-wrap: wrap;
  gap: 12px;
}

.board-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.board-selector select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.chat-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 16px;
  height: calc(100vh - 160px);
}

.card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.chat-area {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-hint {
  color: #888;
  font-size: 14px;
}

.chat-hint ul {
  margin-top: 8px;
  padding-left: 20px;
}

.chat-hint li {
  margin-bottom: 4px;
}

.msg {
  margin-bottom: 16px;
}

.msg-label {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}

.msg-content {
  background: #f0f2f5;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.msg.user .msg-content {
  background: #e3f2fd;
}

.msg.assistant .msg-content {
  background: #f5f5f5;
}

.thinking {
  color: #888;
  font-style: italic;
}

.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #eee;
}

.chat-input input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.chat-input input:focus {
  border-color: #1a1a2e;
}

.btn-send {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-send:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.info-panel {
  padding: 20px;
  font-size: 14px;
  line-height: 1.6;
}

.info-panel h4 {
  margin: 12px 0 8px;
  color: #333;
}

.info-panel h4:first-child {
  margin-top: 0;
}

.info-panel ul {
  padding-left: 16px;
  color: #555;
}

.info-panel li {
  margin-bottom: 6px;
}

.info-panel a {
  color: #1a1a2e;
}

.no-board {
  color: #e67e22;
  font-size: 13px;
}
</style>
