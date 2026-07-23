<script setup lang="ts">
import { useUserStore } from './store'
import { useRouter } from 'vue-router'

const user = useUserStore()
const router = useRouter()

function handleLogout() {
  user.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header v-if="user.isLoggedIn" class="navbar">
      <div class="nav-left">
        <span class="logo">🔬 Lab Orchestrator</span>
        <nav class="nav-links">
          <router-link to="/dashboard">总览</router-link>
          <router-link to="/boards">板子管理</router-link>
          <router-link to="/bookings">预约</router-link>
          <router-link to="/experiments">实验</router-link>
          <router-link to="/ai-agent">AI 助手</router-link>
        </nav>
      </div>
      <div class="nav-right">
        <span class="user-name">{{ user.userInfo?.display_name || user.userInfo?.username }}</span>
        <button class="btn-logout" @click="handleLogout">退出</button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f0f2f5;
  color: #333;
}

.app-container {
  min-height: 100vh;
}

.navbar {
  background: #1a1a2e;
  color: #fff;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  font-size: 18px;
  font-weight: 600;
}

.nav-links {
  display: flex;
  gap: 16px;
}

.nav-links a {
  color: #ccc;
  text-decoration: none;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-name {
  font-size: 14px;
  color: #ccc;
}

.btn-logout {
  background: transparent;
  color: #ccc;
  border: 1px solid #555;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.btn-logout:hover {
  color: #fff;
  border-color: #fff;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
</style>
