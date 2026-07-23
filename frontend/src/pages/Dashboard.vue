<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { boardApi, experimentApi, bookingApi } from '../api/client'
import { useUserStore } from '../store'

const user = useUserStore()
const boardCount = ref(0)
const boardOnline = ref(0)
const expCount = ref(0)
const bookingCount = ref(0)
const loading = ref(true)

onMounted(async () => {
  try {
    const [boards, exps, bookings] = await Promise.all([
      boardApi.list(),
      experimentApi.list(),
      bookingApi.list(),
    ])
    boardCount.value = boards.data.length
    boardOnline.value = boards.data.filter((b) => b.status === 'online').length
    expCount.value = exps.data.length
    bookingCount.value = bookings.data.length
  } catch (err) {
    console.error('获取仪表盘数据失败', err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <h2>总览</h2>
    <p class="welcome">欢迎回来，{{ user.userInfo?.display_name || user.userInfo?.username }}</p>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{{ boardCount }}</div>
        <div class="stat-label">板子总数</div>
      </div>
      <div class="stat-card online">
        <div class="stat-number">{{ boardOnline }}</div>
        <div class="stat-label">在线</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ expCount }}</div>
        <div class="stat-label">实验记录</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ bookingCount }}</div>
        <div class="stat-label">预约记录</div>
      </div>
    </div>

    <div class="quick-links">
      <h3>快速入口</h3>
      <div class="links-grid">
        <router-link to="/boards" class="quick-card">📟 板子管理</router-link>
        <router-link to="/bookings" class="quick-card">📅 预约板子</router-link>
        <router-link to="/experiments" class="quick-card">🧪 实验记录</router-link>
        <router-link to="/ai-agent" class="quick-card">🤖 AI 助手</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
h2 {
  margin-bottom: 4px;
}

.welcome {
  color: #888;
  margin-bottom: 24px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #888;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #fff;
  padding: 24px;
  border-radius: 10px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.stat-card.online .stat-number {
  color: #27ae60;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-label {
  font-size: 14px;
  color: #888;
  margin-top: 4px;
}

.quick-links h3 {
  margin-bottom: 12px;
}

.links-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.quick-card {
  background: #fff;
  padding: 24px;
  border-radius: 10px;
  text-align: center;
  text-decoration: none;
  color: #333;
  font-size: 15px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
}

.quick-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
