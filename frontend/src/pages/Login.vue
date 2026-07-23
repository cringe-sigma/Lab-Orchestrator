<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store'

const router = useRouter()
const user = useUserStore()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const displayName = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function handleSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await user.register(username.value, password.value, displayName.value)
    } else {
      await user.login(username.value, password.value)
    }
    router.push('/dashboard')
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h2>🔬 Lab Orchestrator</h2>
      <p class="subtitle">远程嵌入式实验管理平台</p>

      <form @submit.prevent="handleSubmit" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" required />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" required />
        </div>

        <div v-if="isRegister" class="form-group">
          <label>显示名称（选填）</label>
          <input v-model="displayName" type="text" placeholder="如何称呼你" />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '处理中...' : isRegister ? '注册' : '登录' }}
        </button>
      </form>

      <p class="toggle-text">
        {{ isRegister ? '已有账号？' : '没有账号？' }}
        <a href="#" @click.prevent="isRegister = !isRegister">
          {{ isRegister ? '去登录' : '去注册' }}
        </a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}

.login-card {
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  width: 400px;
}

h2 {
  text-align: center;
  margin-bottom: 4px;
  font-size: 24px;
}

.subtitle {
  text-align: center;
  color: #888;
  font-size: 14px;
  margin-bottom: 24px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 14px;
  color: #555;
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: #1a1a2e;
}

.btn-primary {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 12px;
  border-radius: 6px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #16213e;
}

.btn-primary:disabled {
  background: #888;
  cursor: not-allowed;
}

.error-msg {
  color: #e74c3c;
  font-size: 13px;
  text-align: center;
}

.toggle-text {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #888;
}

.toggle-text a {
  color: #1a1a2e;
  text-decoration: underline;
}
</style>
