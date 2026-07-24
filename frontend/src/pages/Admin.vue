<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

interface UserItem { id: number; username: string; display_name: string; role: string; is_active: boolean; created_at: string; last_login: string | null }
interface PermReq { id: number; user_id: number; requested_role: string; reason: string; status: string; review_comment: string; created_at: string }
interface PermDetail { key: string; label: string; has: boolean; from_role: boolean; overridden: boolean; override_action: string | null }
interface UserPermData { user_id: number; username: string; role: string; role_label: string; permissions: string[]; details: PermDetail[] }

const users = ref<UserItem[]>([])
const permReqs = ref<PermReq[]>([])
const loading = ref(true)
const activeTab = ref<'users' | 'approvals'>('users')
const reviewComment = ref('')

// 权限管理弹窗
const permModalUser = ref<UserItem | null>(null)
const permModalData = ref<UserPermData | null>(null)
const permModalLoading = ref(false)

const roleLabels: Record<string, string> = { admin: '管理员', user: '普通用户', viewer: '观察者' }

onMounted(async () => {
  try {
    const [u, p] = await Promise.all([
      api.get('/auth/users'),
      api.get('/auth/permission-requests'),
    ])
    users.value = u.data
    permReqs.value = p.data
  } catch (err: any) {
    if (err.response?.status === 403) {
      // 非管理员会跳转
    }
  } finally {
    loading.value = false
  }
})

async function openPermModal(user: UserItem) {
  permModalUser.value = user
  permModalLoading.value = true
  try {
    const res = await api.get(`/auth/users/${user.id}/permissions`)
    permModalData.value = res.data
  } catch (e: any) { alert(e.response?.data?.detail || '获取失败') }
  finally { permModalLoading.value = false }
}

async function grantPerm(userId: number, perm: string) {
  try {
    await api.post(`/auth/users/${userId}/permissions/grant`, { permission: perm })
    // refresh
    if (permModalUser.value) await openPermModal(permModalUser.value)
  } catch (e: any) { alert(e.response?.data?.detail || '失败') }
}

async function revokePerm(userId: number, perm: string) {
  if (!confirm('确认收回此权限？')) return
  try {
    await api.post(`/auth/users/${userId}/permissions/revoke`, { permission: perm })
    if (permModalUser.value) await openPermModal(permModalUser.value)
  } catch (e: any) { alert(e.response?.data?.detail || '失败') }
}

async function resetPerm(userId: number, perm: string) {
  try {
    await api.post(`/auth/users/${userId}/permissions/reset`, { permission: perm })
    if (permModalUser.value) await openPermModal(permModalUser.value)
  } catch (e: any) { alert(e.response?.data?.detail || '失败') }
}

async function changeRole(userId: number, newRole: string) {
  try {
    await api.put(`/auth/users/${userId}/role`, { role: newRole })
    const user = users.value.find(u => u.id === userId)
    if (user) user.role = newRole
  } catch (err: any) {
    alert(err.response?.data?.detail || '操作失败')
  }
}

async function toggleStatus(userId: number, active: boolean) {
  try {
    await api.put(`/auth/users/${userId}/status`, { is_active: active })
    const user = users.value.find(u => u.id === userId)
    if (user) user.is_active = active
  } catch (err: any) {
    alert(err.response?.data?.detail || '操作失败')
  }
}

async function reviewRequest(reqId: number, action: string) {
  try {
    await api.post('/auth/review-permission', {
      request_id: reqId,
      action,
      comment: reviewComment.value,
    })
    const req = permReqs.value.find(r => r.id === reqId)
    if (req) req.status = action === 'approve' ? 'approved' : 'rejected'
    reviewComment.value = ''
    // 刷新用户列表（角色可能变了）
    const u = await api.get('/auth/users')
    users.value = u.data
  } catch (err: any) {
    alert(err.response?.data?.detail || '操作失败')
  }
}
</script>

<template>
  <div class="admin-page">
    <h2>🛡️ 管理后台</h2>
    <p class="subtitle">用户管理 & 权限审批</p>

    <div v-if="loading" class="loading">加载中...</div>

    <template v-else>
      <div class="tabs">
        <button :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">
          用户列表 ({{ users.length }})
        </button>
        <button :class="{ active: activeTab === 'approvals' }" @click="activeTab = 'approvals'">
          待审批 ({{ permReqs.filter(r => r.status === 'pending').length }})
        </button>
      </div>

      <!-- 用户管理 -->
      <div v-if="activeTab === 'users'" class="users-tab">
        <table class="user-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>显示名</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.display_name }}</td>
              <td>
                <select :value="u.role" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)">
                  <option value="admin">管理员</option>
                  <option value="user">普通用户</option>
                  <option value="viewer">观察者</option>
                </select>
              </td>
              <td>
                <span class="status-dot" :class="u.is_active ? 'active' : 'inactive'"></span>
                {{ u.is_active ? '正常' : '已禁用' }}
              </td>
              <td class="time-cell">{{ new Date(u.created_at).toLocaleDateString() }}</td>
              <td>
                <button class="btn-sm btn-perm" @click="openPermModal(u)">🔐 权限</button>
                <button
                  v-if="u.is_active"
                  class="btn-sm btn-warn"
                  @click="toggleStatus(u.id, false)"
                >禁用</button>
                <button
                  v-else
                  class="btn-sm btn-ok"
                  @click="toggleStatus(u.id, true)"
                >启用</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 权限审批 -->
      <div v-if="activeTab === 'approvals'" class="approvals-tab">
        <div v-if="permReqs.length === 0" class="empty">暂无权限申请</div>
        <div v-for="rq in permReqs" :key="rq.id" class="approval-card card">
          <div class="card-top">
            <div>
              <span class="rq-user">用户 #{{ rq.user_id }}</span>
              <span class="rq-arrow">→</span>
              <span class="rq-to">{{ roleLabels[rq.requested_role] || rq.requested_role }}</span>
            </div>
            <span class="rq-status" :class="rq.status">
              {{ { pending: '待审批', approved: '已通过', rejected: '已拒绝' }[rq.status] }}
            </span>
          </div>
          <p v-if="rq.reason" class="rq-reason">理由: {{ rq.reason }}</p>
          <p class="rq-time">提交: {{ new Date(rq.created_at).toLocaleString() }}</p>

          <div v-if="rq.status === 'pending'" class="review-section">
            <input v-model="reviewComment" placeholder="审批意见（选填）" class="review-input" />
            <div class="review-btns">
              <button class="btn-sm btn-approve" @click="reviewRequest(rq.id, 'approve')">
                ✅ 通过
              </button>
              <button class="btn-sm btn-reject" @click="reviewRequest(rq.id, 'reject')">
                ❌ 拒绝
              </button>
            </div>
          </div>
          <div v-else-if="rq.review_comment" class="review-comment">
            💬 审批意见: {{ rq.review_comment }}
          </div>
        </div>
      </div>
    </template>

    <!-- ===== 权限管理弹窗 ===== -->
    <div v-if="permModalUser" class="modal-overlay" @click.self="permModalUser = null">
      <div class="perm-modal">
        <div class="modal-header">
          <h3>🔐 权限管理: {{ permModalUser.username }}</h3>
          <span>角色: {{ roleLabels[permModalUser.role] || permModalUser.role }}</span>
          <button class="close-btn" @click="permModalUser = null">✕</button>
        </div>

        <div v-if="permModalLoading" class="loading">加载中...</div>

        <div v-else-if="permModalData" class="perm-list">
          <div class="perm-row header">
            <span>权限</span><span>说明</span><span>状态</span><span>来源</span><span>操作</span>
          </div>
          <div v-for="d in permModalData.details" :key="d.key" class="perm-row" :class="{ 'has': d.has, 'no': !d.has }">
            <span class="perm-key">{{ d.key }}</span>
            <span>{{ d.label }}</span>
            <span>{{ d.has ? '✅' : '❌' }}</span>
            <span>
              <span v-if="d.overridden" class="tag" :class="d.has ? 'granted' : 'revoked'">
                {{ d.has ? '额外授予' : '已被收回' }}
              </span>
              <span v-else class="tag role">角色默认</span>
            </span>
            <td class="perm-actions">
              <button v-if="!d.has" class="btn-xs btn-grant" @click="grantPerm(permModalUser!.id, d.key)">授予</button>
              <button v-if="d.has && !d.overridden" class="btn-xs btn-revoke-sm" @click="revokePerm(permModalUser!.id, d.key)">收回</button>
              <button v-if="d.has && d.overridden" class="btn-xs btn-revoke-sm" @click="revokePerm(permModalUser!.id, d.key)">收回</button>
              <button v-if="d.overridden" class="btn-xs btn-reset" @click="resetPerm(permModalUser!.id, d.key)">恢复默认</button>
            </td>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.subtitle { color: #888; margin-bottom: 16px; }

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
}

.tabs button.active { background: #1a1a2e; color: #fff; }

.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  margin-bottom: 12px;
}

/* 用户表格 */
.user-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.user-table th {
  background: #f8f9fa;
  padding: 12px 14px;
  text-align: left;
  font-size: 13px;
  color: #666;
  border-bottom: 1px solid #eee;
}

.user-table td {
  padding: 12px 14px;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
}

.user-table select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-dot.active { background: #27ae60; }
.status-dot.inactive { background: #e74c3c; }

.time-cell { font-size: 13px; color: #888; }

.btn-sm {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #ddd;
}

.btn-warn { color: #e67e22; border-color: #e67e22; background: #fff; }
.btn-ok { color: #27ae60; border-color: #27ae60; background: #fff; }

/* 审批卡片 */
.approval-card { padding: 16px 20px; }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rq-user { font-weight: 600; color: #1a1a2e; }
.rq-arrow { margin: 0 8px; color: #aaa; }
.rq-to { font-weight: 600; color: #e67e22; }

.rq-status { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.rq-status.pending { background: #fff3cd; color: #856404; }
.rq-status.approved { background: #d4edda; color: #155724; }
.rq-status.rejected { background: #f8d7da; color: #721c24; }

.rq-reason { font-size: 13px; color: #666; margin: 4px 0; }
.rq-time { font-size: 12px; color: #aaa; }

.review-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }

.review-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 8px;
}

.review-btns { display: flex; gap: 8px; }

.btn-approve { background: #27ae60; color: #fff; border: none; }
.btn-reject { background: #e74c3c; color: #fff; border: none; }

.review-comment { margin-top: 8px; font-size: 13px; color: #666; font-style: italic; }

.loading { text-align: center; padding: 40px; color: #888; }
.empty { text-align: center; padding: 40px; color: #888; }

.btn-perm { background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; margin-right: 4px; }

/* 权限管理弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; justify-content: center; align-items: center; z-index: 300; }
.perm-modal { background: #fff; border-radius: 12px; width: 800px; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; align-items: center; gap: 16px; padding: 20px; border-bottom: 1px solid #eee; position: sticky; top: 0; background: #fff; z-index: 1; }
.modal-header h3 { flex: 1; }
.close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #888; }

.perm-list { padding: 0; }
.perm-list .perm-row { display: grid; grid-template-columns: 180px 1fr 50px 90px 150px; padding: 10px 20px; border-bottom: 1px solid #f0f0f0; font-size: 13px; align-items: center; }
.perm-list .perm-row.header { background: #f8f9fa; font-weight: 600; color: #666; font-size: 12px; }
.perm-list .perm-row.has { color: #333; }
.perm-list .perm-row.no { color: #ccc; }
.perm-key { font-family: monospace; font-size: 11px; }

.tag { font-size: 11px; padding: 1px 6px; border-radius: 8px; }
.tag.role { background: #e2e3e5; color: #666; }
.tag.granted { background: #d4edda; color: #155724; }
.tag.revoked { background: #f8d7da; color: #721c24; }

.perm-actions { display: flex; gap: 4px; }
.btn-xs { padding: 3px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; border: none; }
.btn-grant { background: #27ae60; color: #fff; }
.btn-revoke-sm { background: #e74c3c; color: #fff; }
.btn-reset { background: #f0f0f0; color: #666; border: 1px solid #ddd; }
</style>
