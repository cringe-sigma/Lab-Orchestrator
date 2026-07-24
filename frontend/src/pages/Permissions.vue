<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '../api/client'

interface PermDetail { key: string; label: string; has: boolean; source: string | null }
interface MyPermData { role: string; role_label: string; permissions: string[]; details: PermDetail[]; all_permissions: string[] }
interface PermReq { id: number; requested_role: string; reason: string; status: string; created_at: string; review_comment: string }

const data = ref<MyPermData | null>(null)
const myRequests = ref<PermReq[]>([])
const loading = ref(true)
const activeTab = ref<'my'|'apply'|'history'>('my')

// 申请
const applyTarget = ref('')
const applyReason = ref('')
const applyMsg = ref('')
const applyError = ref('')
const applyMode = ref<'role'|'perm'>('perm')

// 角色选项
const roleOptions = ['admin', 'viewer']
const roleLabels: Record<string,string> = { admin:'管理员', user:'普通用户', viewer:'观察者' }
const permOptions = computed(() => data.value?.details?.filter(d => !d.has) || [])
const roleOpts = computed(() => roleOptions.filter(r => r !== data.value?.role))

onMounted(async () => {
  try {
    const [p, h] = await Promise.all([
      api.get('/auth/my-permissions'),
      api.get('/auth/my-permission-requests'),
    ])
    data.value = p.data
    myRequests.value = h.data
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})

async function submitApply() {
  applyMsg.value = ''; applyError.value = ''
  if (!applyTarget.value) { applyError.value = '请选择申请目标'; return }
  try {
    const res = await api.post('/auth/apply-permission', {
      requested_role: applyTarget.value,
      reason: applyReason.value,
    })
    applyMsg.value = res.data.message
    applyReason.value = ''
    const h = await api.get('/auth/my-permission-requests')
    myRequests.value = h.data
  } catch (e: any) { applyError.value = e.response?.data?.detail || '失败' }
}

const sourceLabel: Record<string,string> = { role:'角色默认', grant:'额外授予', revoked:'已被收回' }
</script>

<template>
  <div class="perm-page">
    <h2>🔐 权限管理</h2>

    <div v-if="loading" class="loading">加载中...</div>

    <template v-else-if="data">
      <!-- 角色信息 -->
      <div class="role-card card">
        <span class="role-badge" :class="data.role">{{ data.role_label }}</span>
        <span class="role-desc">有效权限: <strong>{{ data.permissions.length }}</strong> 项</span>
        <span class="role-desc" v-if="data.role !== 'admin'">
          | 可申请 <strong>{{ data.details.filter(d => !d.has).length }}</strong> 项额外权限
        </span>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button :class="{ active: activeTab === 'my' }" @click="activeTab = 'my'">我的权限 ({{ data.details.length }})</button>
        <button :class="{ active: activeTab === 'apply' }" @click="activeTab = 'apply'">申请权限</button>
        <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">申请记录 ({{ myRequests.length }})</button>
      </div>

      <!-- 我的权限列表 -->
      <div v-if="activeTab === 'my'" class="card">
        <div class="perm-table">
          <div class="perm-row header">
            <span>权限</span><span>说明</span><span>状态</span><span>来源</span>
          </div>
          <div v-for="d in data.details" :key="d.key" class="perm-row" :class="{ 'has-perm': d.has, 'no-perm': !d.has }">
            <span class="perm-key">{{ d.key }}</span>
            <span>{{ d.label }}</span>
            <span>{{ d.has ? '✅' : '❌' }}</span>
            <span class="source-tag" :class="d.source||''">{{ sourceLabel[d.source||''] || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- 申请 -->
      <div v-if="activeTab === 'apply'" class="card">
        <h4>申请权限</h4>
        <div class="apply-mode">
          <button :class="{ active: applyMode === 'perm' }" @click="applyMode = 'perm'; applyTarget = ''">单项权限</button>
          <button :class="{ active: applyMode === 'role' }" @click="applyMode = 'role'; applyTarget = ''">角色升级</button>
        </div>

        <div class="apply-form" v-if="applyMode === 'perm'">
          <div class="form-group">
            <label>选择要申请的权限</label>
            <select v-model="applyTarget">
              <option value="" disabled>— 选择权限 —</option>
              <option v-for="d in permOptions" :key="d.key" :value="d.key">{{ d.label }}</option>
            </select>
          </div>
        </div>
        <div class="apply-form" v-else>
          <div class="form-group">
            <label>选择要升级的角色</label>
            <select v-model="applyTarget">
              <option value="" disabled>— 选择角色 —</option>
              <option v-for="r in roleOpts" :key="r" :value="r">{{ roleLabels[r] }}</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>申请理由</label>
          <textarea v-model="applyReason" rows="2" placeholder="说明为什么需要此权限..."></textarea>
        </div>

        <button class="btn-primary" @click="submitApply" :disabled="!applyTarget">提交申请</button>
        <p v-if="applyMsg" class="success">{{ applyMsg }}</p>
        <p v-if="applyError" class="error">{{ applyError }}</p>
      </div>

      <!-- 申请记录 -->
      <div v-if="activeTab === 'history'">
        <div v-if="myRequests.length === 0" class="empty">暂无申请记录</div>
        <div v-for="rq in myRequests" :key="rq.id" class="card rq-card">
          <div class="rq-top">
            <strong>{{ rq.requested_role in roleLabels ? '角色: '+roleLabels[rq.requested_role] : '权限: '+rq.requested_role }}</strong>
            <span class="rq-status" :class="rq.status">{{ ({pending:'审批中',approved:'通过',rejected:'拒绝'})[rq.status] }}</span>
          </div>
          <p v-if="rq.reason" class="rq-reason">{{ rq.reason }}</p>
          <p v-if="rq.review_comment" class="rq-comment">审批: {{ rq.review_comment }}</p>
          <p class="rq-time">{{ new Date(rq.created_at).toLocaleString() }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.role-card { display:flex; align-items:center; gap:16px; }
.role-badge { padding:6px 16px; border-radius:20px; font-size:14px; font-weight:600; }
.role-badge.admin { background:#1a1a2e; color:#fff; }
.role-badge.user { background:#d4edda; color:#155724; }
.role-badge.viewer { background:#e2e3e5; color:#383d41; }
.role-desc { color:#666; font-size:14px; }

.tabs { display:flex; gap:4px; margin:16px 0; background:#fff; padding:4px; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.tabs button { flex:1; padding:10px; border:none; background:transparent; border-radius:6px; font-size:14px; cursor:pointer; color:#666; }
.tabs button.active { background:#1a1a2e; color:#fff; }

.card { background:#fff; border-radius:10px; padding:20px; box-shadow:0 1px 4px rgba(0,0,0,.06); margin-bottom:12px; }

.perm-table { display:flex; flex-direction:column; }
.perm-row { display:grid; grid-template-columns: 200px 1fr 60px 100px; padding:10px 0; border-bottom:1px solid #f0f0f0; font-size:14px; align-items:center; }
.perm-row.header { font-weight:600; color:#666; font-size:13px; border-bottom:2px solid #eee; }
.has-perm { color:#333; }
.no-perm { color:#ccc; }
.perm-key { font-family:monospace; font-size:12px; }
.source-tag { font-size:11px; padding:2px 8px; border-radius:10px; text-align:center; }
.source-tag.role { background:#d4edda; color:#155724; }
.source-tag.grant { background:#cce5ff; color:#004085; }
.source-tag.revoked { background:#f8d7da; color:#721c24; }

.apply-mode { display:flex; gap:8px; margin-bottom:12px; }
.apply-mode button { padding:6px 16px; border:1px solid #ddd; background:#fff; border-radius:6px; font-size:13px; cursor:pointer; }
.apply-mode button.active { background:#1a1a2e; color:#fff; border-color:#1a1a2e; }

.apply-form { display:flex; flex-direction:column; gap:12px; margin-bottom:12px; }
.form-group { display:flex; flex-direction:column; gap:4px; }
.form-group label { font-size:13px; color:#666; }
.form-group select,.form-group textarea { padding:8px 10px; border:1px solid #ddd; border-radius:6px; font-size:14px; }

.btn-primary { background:#1a1a2e; color:#fff; border:none; padding:10px 20px; border-radius:6px; cursor:pointer; font-size:14px; }
.btn-primary:disabled { background:#ccc; cursor:not-allowed; }
.success { color:#27ae60; font-size:14px; }
.error { color:#e74c3c; font-size:14px; }

.rq-card { padding:16px 20px; }
.rq-top { display:flex; justify-content:space-between; margin-bottom:8px; }
.rq-status { font-size:12px; padding:2px 8px; border-radius:10px; }
.rq-status.pending { background:#fff3cd; color:#856404; }
.rq-status.approved { background:#d4edda; color:#155724; }
.rq-status.rejected { background:#f8d7da; color:#721c24; }
.rq-reason { font-size:13px; color:#666; margin:4px 0; }
.rq-comment { font-size:13px; color:#888; font-style:italic; }
.rq-time { font-size:12px; color:#aaa; margin-top:4px; }

.loading { text-align:center; padding:40px; color:#888; }
.empty { text-align:center; padding:40px; color:#888; }
</style>
