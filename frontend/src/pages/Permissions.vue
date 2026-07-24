<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

// 权限中文名
const permLabels: Record<string, string> = {
  'boards:read': '查看板子',
  'boards:create': '添加板子',
  'boards:exec': '操作板子(执行命令)',
  'boards:delete': '删除板子',
  'experiments:read': '查看实验',
  'experiments:create': '创建实验',
  'experiments:run': '运行实验',
  'bookings:read': '查看预约',
  'bookings:create': '创建预约',
  'bookings:cancel': '取消预约',
  'users:read': '查看用户列表',
  'users:manage': '管理用户(改角色/禁用)',
  'permissions:read': '查看权限',
  'permissions:approve': '审批权限申请',
  'ai:chat': '使用AI助手',
}

const roleLabels: Record<string, string> = { admin: '管理员', user: '普通用户', viewer: '观察者' }

interface RoleInfo { role: string; label: string; permissions: string[]; can_apply: boolean }
interface MyPerms { role: string; role_label: string; permissions: string[] }
interface PermRequest {
  id: number; requested_role: string; reason: string; status: string
  review_comment: string; created_at: string; reviewed_at: string | null
}

const myPerms = ref<MyPerms | null>(null)
const roles = ref<RoleInfo[]>([])
const myRequests = ref<PermRequest[]>([])
const loading = ref(true)
const activeTab = ref<'my' | 'all' | 'apply' | 'history'>('my')

// 权限申请表单
const applyRole = ref('admin')
const applyReason = ref('')
const applyMsg = ref('')
const applyError = ref('')

onMounted(async () => {
  try {
    const [p, r, h] = await Promise.all([
      api.get('/auth/my-permissions'),
      api.get('/auth/roles'),
      api.get('/auth/my-permission-requests'),
    ])
    myPerms.value = p.data
    roles.value = r.data
    myRequests.value = h.data
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
})

async function submitApply() {
  applyMsg.value = ''
  applyError.value = ''
  try {
    const res = await api.post('/auth/apply-permission', {
      requested_role: applyRole.value,
      reason: applyReason.value,
    })
    applyMsg.value = res.data.message
    applyReason.value = ''
    // 刷新申请记录
    const h = await api.get('/auth/my-permission-requests')
    myRequests.value = h.data
  } catch (err: any) {
    applyError.value = err.response?.data?.detail || '申请失败'
  }
}

const statusLabels: Record<string, string> = { pending: '审批中', approved: '已通过', rejected: '已拒绝' }
</script>

<template>
  <div class="perm-page">
    <h2>🔐 权限管理</h2>

    <div v-if="loading" class="loading">加载中...</div>

    <template v-else>
      <!-- 顶部信息卡片 -->
      <div class="role-card card">
        <div class="role-badge" :class="myPerms?.role">
          {{ myPerms?.role_label }}
        </div>
        <div class="role-desc">
          当前角色: <strong>{{ myPerms?.role }}</strong>
          &nbsp;|&nbsp; 拥有 <strong>{{ myPerms?.permissions.length }}</strong> 项权限
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tabs">
        <button :class="{ active: activeTab === 'my' }" @click="activeTab = 'my'">我的权限</button>
        <button :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">所有角色</button>
        <button :class="{ active: activeTab === 'apply' }" @click="activeTab = 'apply'">申请升级</button>
        <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">申请记录</button>
      </div>

      <!-- Tab 1: 我的权限列表 -->
      <div v-if="activeTab === 'my'" class="tab-content card">
        <h4>我拥有的权限</h4>
        <div class="perm-grid">
          <div v-for="p in myPerms?.permissions" :key="p" class="perm-item">
            <span class="perm-icon">✅</span>
            <span>{{ permLabels[p] || p }}</span>
          </div>
        </div>
      </div>

      <!-- Tab 2: 所有角色对比 -->
      <div v-if="activeTab === 'all'" class="tab-content">
        <div v-for="r in roles" :key="r.role" class="role-detail card">
          <div class="role-header">
            <span class="role-badge" :class="r.role">{{ r.label }}</span>
            <span class="can-apply" v-if="r.can_apply">可申请</span>
            <span class="current-badge" v-else>当前角色</span>
          </div>
          <div class="perm-grid">
            <div v-for="p in r.permissions" :key="p" class="perm-item small">
              <span class="perm-icon">✅</span>
              <span>{{ permLabels[p] || p }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 3: 申请升级 -->
      <div v-if="activeTab === 'apply'" class="tab-content card">
        <h4>申请角色升级</h4>
        <p class="hint">当前角色: {{ myPerms?.role_label }}。你可以申请升级到更高权限的角色。</p>

        <div class="apply-form">
          <div class="form-group">
            <label>申请角色</label>
            <select v-model="applyRole">
              <option v-for="r in roles.filter(r => r.can_apply)" :key="r.role" :value="r.role">
                {{ r.label }} ({{ r.role }})
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>申请理由</label>
            <textarea v-model="applyReason" rows="3" placeholder="请说明为什么需要升级权限..."></textarea>
          </div>

          <button class="btn-primary" @click="submitApply" :disabled="!applyReason.trim()">
            提交申请
          </button>

          <p v-if="applyMsg" class="success-msg">{{ applyMsg }}</p>
          <p v-if="applyError" class="error-msg">{{ applyError }}</p>
        </div>
      </div>

      <!-- Tab 4: 申请记录 -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div v-if="myRequests.length === 0" class="empty">暂无申请记录</div>
        <div v-for="rq in myRequests" :key="rq.id" class="request-item card">
          <div class="rq-header">
            <span class="rq-role">申请 {{ roleLabels[rq.requested_role] || rq.requested_role }}</span>
            <span class="rq-status" :class="rq.status">{{ statusLabels[rq.status] }}</span>
          </div>
          <div class="rq-body">
            <p v-if="rq.reason"><strong>理由:</strong> {{ rq.reason }}</p>
            <p v-if="rq.review_comment"><strong>审批意见:</strong> {{ rq.review_comment }}</p>
            <p class="rq-time">提交于 {{ new Date(rq.created_at).toLocaleString() }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.role-card {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.role-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.role-badge.admin { background: #1a1a2e; color: #fff; }
.role-badge.user { background: #d4edda; color: #155724; }
.role-badge.viewer { background: #e2e3e5; color: #383d41; }

.role-desc { color: #666; font-size: 14px; }

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: #fff;
  padding: 4px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.tabs button {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}

.tabs button.active {
  background: #1a1a2e;
  color: #fff;
}

.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  margin-bottom: 12px;
}

.tab-content h4 { margin-bottom: 12px; font-size: 16px; }

.perm-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.perm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  padding: 6px 0;
}

.perm-item.small { font-size: 13px; }

.perm-icon { font-size: 14px; }

.role-detail {
  margin-bottom: 12px;
}

.role-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.can-apply { font-size: 12px; color: #e67e22; background: #fff3cd; padding: 2px 8px; border-radius: 10px; }
.current-badge { font-size: 12px; color: #155724; background: #d4edda; padding: 2px 8px; border-radius: 10px; }

.apply-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label { font-size: 13px; color: #666; }
.form-group select, .form-group textarea {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.btn-primary {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:disabled { background: #ccc; cursor: not-allowed; }

.hint { color: #888; font-size: 13px; margin-bottom: 8px; }

.success-msg { color: #27ae60; font-size: 14px; }
.error-msg { color: #e74c3c; font-size: 14px; }

.request-item { padding: 16px 20px; }

.rq-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rq-role { font-weight: 600; }
.rq-status { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.rq-status.pending { background: #fff3cd; color: #856404; }
.rq-status.approved { background: #d4edda; color: #155724; }
.rq-status.rejected { background: #f8d7da; color: #721c24; }

.rq-body { font-size: 13px; color: #666; }
.rq-body p { margin-bottom: 4px; }
.rq-time { font-size: 12px; color: #aaa; margin-top: 8px; }

.loading { text-align: center; padding: 40px; color: #888; }
.empty { text-align: center; padding: 40px; color: #888; }
</style>
