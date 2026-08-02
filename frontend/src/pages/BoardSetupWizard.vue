<script setup lang="ts">
import { ref } from 'vue'

const mode = ref<'ssh' | 'serial' | 'remote'>('ssh')
const currentStep = ref(1)

const steps: Record<string, string[]> = {
  ssh: ['硬件接线', '启用SSH', '确认IP', '前端添加', '验证连通'],
  serial: ['硬件接线', '安装驱动', '确认串口号', '前端添加', '验证连通'],
  remote: ['添加板子', '获取Token', '安装脚本', '启动代理', '验证上线'],
}

function resetSteps() { currentStep.value = 1 }
watch(mode, resetSteps)

import { watch } from 'vue'
</script>

<template>
  <div class="wizard-page">
    <h2>🔌 板子接线教程</h2>
    <p class="subtitle">交互式教程 — 三种接入方式，跟着步骤操作</p>

    <!-- 模式选择 -->
    <div class="mode-tabs">
      <button
        v-for="m in (['ssh','serial','remote'] as const)"
        :key="m"
        :class="{ active: mode === m }"
        @click="mode = m; resetSteps()"
      >
        <span class="mode-icon">{{ { ssh:'🖥️', serial:'🔌', remote:'🌐' }[m] }}</span>
        <span class="mode-label">{{ { ssh:'SSH 直连', serial:'串口直连', remote:'远程代理' }[m] }}</span>
        <span class="mode-desc">{{ {
          ssh:'Linux 板同局域网',
          serial:'MCU 板 USB 连接',
          remote:'任何网络任何板子'
        }[m] }}</span>
      </button>
    </div>

    <!-- 步骤进度条 -->
    <div class="progress-bar">
      <div
        v-for="(name, idx) in steps[mode]"
        :key="idx"
        class="step-dot"
        :class="{
          done: idx + 1 < currentStep,
          active: idx + 1 === currentStep,
          pending: idx + 1 > currentStep,
        }"
        @click="currentStep = idx + 1"
      >
        <span class="dot-num">{{ idx + 1 }}</span>
        <span class="dot-label">{{ name }}</span>
        <span v-if="idx < steps[mode].length - 1" class="dot-line"></span>
      </div>
    </div>

    <!-- ====== SSH 教程 ====== -->
    <div v-if="mode === 'ssh'" class="tutorial-content">
      <!-- Step 1: 硬件接线 -->
      <div v-if="currentStep === 1" class="card">
        <h3>🖥️ 第1步: 硬件接线</h3>
        <div class="diagram-box">
          <pre class="diagram">┌──────────────┐          ┌──────────┐          ┌──────────────────┐
│              │          │          │          │  Raspberry Pi    │
│   你的电脑    │──网线──→│  交换机   │──网线──→│  ┌────────────┐ │
│  (服务器)    │          │  (路由器) │          │  │  RJ45 网口  │ │
│              │          │          │          │  │  USB-C供电  │─│─→ 电源适配器
└──────────────┘          └──────────┘          │  └────────────┘ │
                                                └──────────────────┘</pre>
        </div>
        <div class="checklist">
          <h4>✅ 检查清单:</h4>
          <ul>
            <li>服务器和板子 <strong>插在同一个交换机/路由器</strong> 上</li>
            <li>板子已插电开机 (指示灯亮)</li>
            <li>网线两端指示灯闪烁 (表示物理连通)</li>
          </ul>
        </div>
        <div class="nav-buttons">
          <span></span>
          <button class="btn-primary" @click="currentStep = 2">下一步 →</button>
        </div>
      </div>

      <!-- Step 2: 启用 SSH -->
      <div v-if="currentStep === 2" class="card">
        <h3>🖥️ 第2步: 在板子上启用 SSH</h3>
        <div class="code-block">
          <div class="code-title">Raspberry Pi:</div>
          <pre>sudo raspi-config
→ Interface Options → SSH → Enable → Finish

# 或者直接:
sudo systemctl enable ssh
sudo systemctl start ssh</pre>
        </div>
        <div class="code-block">
          <div class="code-title">其他 Linux 板 (Jetson/Orange Pi):</div>
          <pre>sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh   # 确认运行中</pre>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 1">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 3">下一步 →</button>
        </div>
      </div>

      <!-- Step 3: 确认 IP -->
      <div v-if="currentStep === 3" class="card">
        <h3>🖥️ 第3步: 确认板子 IP 地址</h3>
        <div class="code-block">
          <div class="code-title">在板子上执行:</div>
          <pre>ip addr show | grep "inet "
# 或
ifconfig | grep "inet"

# 你会看到类似:
# inet 192.168.1.101/24</pre>
        </div>
        <div class="tip-box">
          <strong>💡 建议:</strong> 在路由器管理页面设置 <strong>DHCP 地址预留</strong>，
          给板子 MAC 地址绑定固定 IP，避免重启后 IP 变化。
        </div>
        <div class="code-block">
          <div class="code-title">从电脑测试连通:</div>
          <pre>ping 192.168.1.101          # 测试网络连通
ssh pi@192.168.1.101        # 测试 SSH 登录</pre>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 2">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 4">下一步 →</button>
        </div>
      </div>

      <!-- Step 4: 前端添加 -->
      <div v-if="currentStep === 4" class="card">
        <h3>🖥️ 第4步: 在系统中添加板子</h3>
        <ol class="action-list">
          <li>打开 <strong>板子管理</strong> 页面</li>
          <li>点击 <strong>+ 添加板子</strong></li>
          <li>填写表单:
            <div class="form-preview">
              <div>名称: <code>Raspberry Pi 5-01</code></div>
              <div>板子类型: <code>Linux 板</code></div>
              <div>连接方式: <code>SSH (本地)</code></div>
              <div>IP 地址: <code>192.168.1.101</code></div>
              <div>端口: <code>22</code></div>
              <div>用户名: <code>pi</code></div>
            </div>
          </li>
          <li>点击 <strong>确认添加</strong></li>
        </ol>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 3">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 5">下一步 →</button>
        </div>
      </div>

      <!-- Step 5: 验证 -->
      <div v-if="currentStep === 5" class="card">
        <h3>🖥️ 第5步: 验证连通</h3>
        <ol class="action-list">
          <li>在板子卡片上点击 <strong>「检查」</strong> 按钮</li>
          <li>状态变为 <span class="badge online">在线</span> 即成功</li>
          <li>点击 <strong>「执行命令」</strong> → 输入 <code>uname -a</code> → 执行</li>
          <li>确认输出正常</li>
        </ol>
        <div class="success-box">
          <h4>🎉 完成! 板子已成功接入系统</h4>
          <p>现在可以去 <router-link to="/bookings">预约</router-link> 板子使用时间，
          或在 <router-link to="/experiments">实验</router-link> 页面创建实验。</p>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 4">← 上一步</button>
          <span></span>
        </div>
      </div>
    </div>

    <!-- ====== 串口教程 ====== -->
    <div v-if="mode === 'serial'" class="tutorial-content">
      <div v-if="currentStep === 1" class="card">
        <h3>🔌 第1步: 硬件接线</h3>
        <div class="diagram-box">
          <pre class="diagram">┌──────────┐     ┌───────────────┐     ┌──────────────────┐
│  电脑    │     │ USB转串口模块  │     │   MCU 板子        │
│  USB口   │──→  │  ┌─────────┐  │     │  ┌────────────┐  │
│          │     │  │ CH340G  │  │     │  │ STM32/ESP32│  │
│          │     │  │         │  │     │  │            │  │
│          │     │  │ GND ────┼──┼─────┼──→ GND       │  │
│          │     │  │ TXD ────┼──┼─────┼──→ RXD       │  │
│          │     │  │ RXD ────┼──┼─────┼──→ TXD       │  │
│          │     │  │ 5V  ────┼──┼─────┼──→ VCC(可选) │  │
│          │     │  └─────────┘  │     │  └────────────┘  │
└──────────┘     └───────────────┘     └──────────────────┘

⚠️ 关键: TXD→RXD, RXD→TXD (交叉连接), GND必须接</pre>
        </div>
        <div class="checklist">
          <h4>✅ 检查清单:</h4>
          <ul>
            <li>USB 转串口模块插入电脑 USB 口</li>
            <li>GND 连接板子 GND</li>
            <li>TXD 连接板子 RXD (交叉)</li>
            <li>RXD 连接板子 TXD (交叉)</li>
            <li>板子已通电 (USB供电或外部电源)</li>
          </ul>
        </div>
        <div class="nav-buttons">
          <span></span>
          <button class="btn-primary" @click="currentStep = 2">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 2" class="card">
        <h3>🔌 第2步: 安装驱动</h3>
        <div class="code-block">
          <div class="code-title">Windows:</div>
          <pre>CH340G 驱动下载: https://www.wch.cn/download/CH341SER_EXE.html
下载 → 安装 → 插入模块 → 设备管理器检查
CP2102: 通常自动识别</pre>
        </div>
        <div class="code-block">
          <div class="code-title">Linux:</div>
          <pre># 通常内核自带驱动，无需安装
lsmod | grep ch341     # 检查驱动加载
lsmod | grep cp210x    # CP2102驱动
dmesg | grep tty       # 查看内核识别日志</pre>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 1">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 3">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 3" class="card">
        <h3>🔌 第3步: 确认串口号</h3>
        <div class="code-block">
          <div class="code-title">Windows (PowerShell):</div>
          <pre>Get-WmiObject Win32_SerialPort | Select Name, DeviceID
# 查看设备管理器 → 端口 (COM和LPT)
# 插拔模块对比: 记录出现/消失的 COM 号</pre>
        </div>
        <div class="code-block">
          <div class="code-title">Linux/Mac:</div>
          <pre>ls /dev/ttyUSB*          # CH340/CP2102 → /dev/ttyUSB0
ls /dev/ttyACM*          # 部分板子 → /dev/ttyACM0
ls /dev/cu.*             # macOS</pre>
        </div>
        <div class="tip-box">
          <strong>💡 固定串口名 (Linux):</strong> 创建 udev 规则避免插拔后串口号
          变化。详见 <code>docs/board-setup-guide.md</code>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 2">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 4">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 4" class="card">
        <h3>🔌 第4步: 在系统中添加</h3>
        <ol class="action-list">
          <li>打开 <strong>板子管理</strong> 页面</li>
          <li>点击 <strong>+ 添加板子</strong></li>
          <li>填写表单:
            <div class="form-preview">
              <div>名称: <code>ESP32-S3-01</code></div>
              <div>板子类型: <code>MCU 裸机</code></div>
              <div>连接方式: <code>串口 (本地)</code></div>
              <div>串口: <code>COM3</code> (Windows) 或 <code>/dev/ttyUSB0</code> (Linux)</div>
              <div>波特率: <code>115200</code></div>
            </div>
          </li>
          <li>点击 <strong>确认添加</strong></li>
        </ol>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 3">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 5">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 5" class="card">
        <h3>🔌 第5步: 验证连通</h3>
        <ol class="action-list">
          <li>在板子卡片上点击 <strong>「检查」</strong> 按钮</li>
          <li>输入串口密码 (如有) 或留空</li>
          <li>状态变为 <span class="badge online">在线</span> 即成功</li>
          <li>⚠️ 确认没有其他程序(PuTTY/串口助手)占用该串口</li>
        </ol>
        <div class="success-box">
          <h4>🎉 完成! MCU 板已接入</h4>
          <p>现在可以在实验页面创建串口实验，向板子发送 AT 命令等。</p>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 4">← 上一步</button>
          <span></span>
        </div>
      </div>
    </div>

    <!-- ====== 远程代理教程 ====== -->
    <div v-if="mode === 'remote'" class="tutorial-content">
      <div v-if="currentStep === 1" class="card">
        <h3>🌐 第1步: 在系统中添加远程板子</h3>
        <div class="diagram-box">
          <pre class="diagram">┌────────────────────┐              ┌────────────────────┐
│   服务器 (你的电脑)  │              │  远程板子           │
│                    │              │  (任何地方!)        │
│  添加远程板子       │              │                    │
│  → 生成 Token      │              │  http_agent.ps1  │
│                    │◄──WebSocket──│  --server ws://   │
│  WebSocket        │   (远程电脑   │  服务器IP:8000     │
│  端点 :8000        │   主动连接)   │  --token TOKEN    │
│                    │              │  --board-ip PI_IP │
└────────────────────┘              └────────────────────┘

原理: 板子不需要公网IP，主动向服务器发起 WebSocket 连接
      服务器无法主动连接板子，但可以通过 WS 下发命令</pre>
        </div>
        <ol class="action-list">
          <li>打开 <strong>板子管理</strong> → <strong>+ 添加板子</strong></li>
          <li>连接方式选择 <strong>「远程代理 (board-agent)」</strong></li>
          <li>填写板子名称和类型</li>
          <li>确认 → 系统自动生成 <strong>连接 Token</strong></li>
          <li>记录 Token (如: <code>Xy3kPqR8...aB9</code>)</li>
        </ol>
        <div class="nav-buttons">
          <span></span>
          <button class="btn-primary" @click="currentStep = 2">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 2" class="card">
        <h3>🌐 第2步: 远程 Windows PowerShell 一行运行</h3>
        <div class="code-block">
          <div class="code-title">复制粘贴到PowerShell (替换TOKEN):</div>
          <pre>$s="服务器IP";$b="板子IP";$u="用户名";$p="密码";$t="TOKEN";$r=Invoke-RestMethod -Uri "http://$s`:8000/api/boards/register-agent" -Method Post -Body "{`"token`":`"$t`"}" -ContentType "application/json";while($true){$c=Invoke-RestMethod -Uri "http://$s`:8000/api/boards/$($r.board_id)/pending-commands";foreach($x in $c.commands){$o=ssh -o StrictHostKeyChecking=no "$u@$b" $x.command 2>&1|Out-String;Invoke-RestMethod -Uri "http://$s`:8000/api/boards/$($r.board_id)/command-result" -Method Post -Body "{`"cmd_id`":`"$($x.id)`",`"output`":`"$($o-replace '\"','\\\"')`"}" -ContentType "application/json"};sleep 2}</pre>
        </div>
        <div class="tip-box">
          <strong>💡 只需改4个变量:</strong> $b=板子IP, $u=SSH用户名, $p=SSH密码, $t=网页上显示的Token
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 1">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 3">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 3" class="card">
        <h3>🌐 第3步: 确认上线</h3>
        <div class="code-block">
          <div class="code-title">期望看到:</div>
          <pre>board_id=5
  执行: echo SSH_OK
    结果已回传</pre>
        </div>
        <div class="tip-box">
          <strong>💡 板子状态变为在线后</strong>，即可预约、执行命令、打开SSH终端。
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 2">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 4">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 4" class="card">
        <h3>🌐 第4步: 设置开机自启 (推荐)</h3>
        <div class="code-block">
          <div class="code-title">使用 systemd (Linux 板):</div>
          <pre>sudo cp board-agent/lab-agent.service /etc/systemd/system/
sudo nano /etc/systemd/system/lab-agent.service
# 修改 YOUR_SERVER_IP 和 YOUR_BOARD_TOKEN

sudo systemctl daemon-reload
sudo systemctl enable lab-agent
sudo systemctl start lab-agent
sudo systemctl status lab-agent    # 确认运行中</pre>
        </div>
        <div class="checklist">
          <h4>✅ 检查清单:</h4>
          <ul>
            <li><code>systemctl status lab-agent</code> 显示 active</li>
            <li>前端板子卡片显示 <span class="badge online">在线</span></li>
            <li>断开板子网络后自动重连</li>
          </ul>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 3">← 上一步</button>
          <button class="btn-primary" @click="currentStep = 5">下一步 →</button>
        </div>
      </div>

      <div v-if="currentStep === 5" class="card">
        <h3>🌐 第5步: 验证远程连接</h3>
        <ol class="action-list">
          <li>在前端板子管理页面 → 板子状态显示 <span class="badge online">在线</span></li>
          <li>点击「检查」 → 返回 online</li>
          <li>点击「执行命令」 → 输入 <code>uname -a</code> → 确认返回正确</li>
        </ol>
        <div class="success-box">
          <h4>🎉 完成! 远程板子已接入</h4>
          <p>远程板子和本地板子使用体验完全一样: 预约 → 实验 → AI 操作。</p>
        </div>
        <div class="nav-buttons">
          <button class="btn-outline" @click="currentStep = 4">← 上一步</button>
          <span></span>
        </div>
      </div>
    </div>

    <!-- 底部快速快捷方式 -->
    <div class="quick-links-bar">
      <router-link to="/boards" class="quick-link">📟 去板子管理</router-link>
      <router-link to="/bookings" class="quick-link">📅 去预约</router-link>
      <router-link to="/manual" class="quick-link">📖 完整手册</router-link>
    </div>
  </div>
</template>

<style scoped>
.subtitle { color: #888; margin-bottom: 20px; }

/* 模式选择 */
.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.mode-tabs button {
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px 16px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.mode-tabs button:hover { border-color: #1a1a2e; }
.mode-tabs button.active { border-color: #1a1a2e; background: #f8f9ff; box-shadow: 0 2px 12px rgba(26,26,46,0.1); }

.mode-icon { font-size: 32px; }
.mode-label { font-size: 15px; font-weight: 600; color: #333; }
.mode-desc { font-size: 12px; color: #888; }

/* 进度条 */
.progress-bar {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  overflow-x: auto;
}

.step-dot {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  cursor: pointer;
}

.dot-num {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.step-dot.done .dot-num { background: #27ae60; color: #fff; }
.step-dot.active .dot-num { background: #1a1a2e; color: #fff; }
.step-dot.pending .dot-num { background: #e0e0e0; color: #999; }

.dot-label { font-size: 13px; white-space: nowrap; }
.step-dot.pending .dot-label { color: #bbb; }
.step-dot.active .dot-label { color: #1a1a2e; font-weight: 600; }

.dot-line {
  width: 30px; height: 2px;
  background: #e0e0e0;
  margin: 0 8px;
}
.step-dot.done + .step-dot .dot-line,
.step-dot.done .dot-line { background: #27ae60; }

/* 内容区 */
.tutorial-content { margin-bottom: 24px; }

.card {
  background: #fff;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  margin-bottom: 16px;
}

.card h3 { margin-bottom: 16px; font-size: 18px; }

.diagram-box {
  margin-bottom: 20px;
}

.diagram {
  background: #1a1a2e;
  color: #a8d8ff;
  padding: 16px 20px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre;
  font-family: 'Consolas', 'Courier New', monospace;
}

.code-block {
  margin-bottom: 16px;
}

.code-title {
  background: #333;
  color: #fff;
  padding: 6px 14px;
  font-size: 13px;
  border-radius: 6px 6px 0 0;
  display: inline-block;
}

.code-block pre {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px 18px;
  border-radius: 0 6px 6px 6px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
}

.tip-box {
  background: #e3f2fd;
  border-left: 4px solid #1976d2;
  padding: 12px 16px;
  border-radius: 6px;
  margin: 12px 0;
  font-size: 14px;
}

.checklist {
  background: #f5f5f5;
  padding: 14px 18px;
  border-radius: 8px;
  margin: 12px 0;
}

.checklist h4 { margin-bottom: 8px; font-size: 14px; }

.checklist ul {
  padding-left: 20px;
}

.checklist li {
  margin-bottom: 6px;
  font-size: 14px;
}

.action-list {
  padding-left: 20px;
}

.action-list li {
  margin-bottom: 10px;
  font-size: 14px;
  line-height: 1.6;
}

.form-preview {
  background: #fafafa;
  border: 1px solid #eee;
  padding: 12px 16px;
  border-radius: 6px;
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.8;
}

.form-preview code {
  background: #eee;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 13px;
}

.success-box {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  padding: 16px 20px;
  border-radius: 8px;
  margin: 16px 0;
}

.success-box h4 { color: #155724; margin-bottom: 8px; }

.success-box p { color: #155724; font-size: 14px; }
.success-box a { color: #0b5ed7; font-weight: 600; }

.badge { display: inline; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.online { background: #d4edda; color: #155724; }

.nav-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.btn-primary {
  background: #1a1a2e;
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-outline {
  background: #fff;
  color: #1a1a2e;
  border: 1px solid #1a1a2e;
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

/* 快捷入口 */
.quick-links-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.quick-link {
  background: #1a1a2e;
  color: #fff;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  transition: transform 0.2s;
}

.quick-link:hover { transform: translateY(-2px); }
</style>
