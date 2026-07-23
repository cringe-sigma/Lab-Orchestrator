<script setup lang="ts">
import { ref } from 'vue'

const activeSection = ref('quickstart')

const sections = {
  quickstart: {
    title: '🚀 快速开始',
    content: `
      1. 注册账号 — 打开页面，点击"去注册"创建账号
      2. 添加板子 — 进入"板子管理" → 点击"添加板子" → 填写板子信息
      3. 检查连通 — 添加后在板子卡片上点击"检查"确认连接正常
      4. 开始实验 — 进入"AI 助手"或"实验管理"创建实验
    `,
  },
  boards: {
    title: '📟 板子管理',
    content: `
      添加板子时需要填写：

      Linux 板（SSH 连接）：
      · 名称 —— 方便识别的标签（如 "RPi-01"）
      · IP 地址 —— 板子在局域网中的 IP
      · 端口 —— SSH 端口（默认 22）
      · 用户名 —— SSH 登录用户名

      MCU 板（串口连接）：
      · 名称 —— 方便识别的标签（如 "STM32-01"）
      · 串口 —— 串口路径（Windows: COM3, Linux: /dev/ttyUSB0）
      · 波特率 —— 串口通信速率（默认 115200）

      每块板子卡片上可以：
      · 检查连接状态
      · 直接执行命令（测试连通）
      · 查看在线/离线/占用状态
    `,
  },
  booking: {
    title: '📅 预约系统',
    content: `
      预约流程：
      1. 进入"预约"页面
      2. 点击"新建预约"
      3. 选择板子、填写标题、设置开始和结束时间
      4. 确认提交

      注意事项：
      · 同一时段一块板子只能被一个人预约
      · 预约开始后状态变为"进行中"
      · 可以取消未开始的预约
      · 预约结束后状态变为"已完成"
      · 板子被预约期间，其他人无法操作
    `,
  },
  experiments: {
    title: '🧪 实验操作',
    content: `
      手动创建实验：
      1. 进入"实验"页面 → 新建实验
      2. 选择板子、填写实验名称和描述
      3. 创建后点击"运行"执行

      实验状态说明：
      · 待执行 —— 已创建，等待运行
      · 运行中 —— 正在执行步骤
      · 已完成 —— 所有步骤执行完毕
      · 失败 —— 执行过程中出错

      查看实验结果：
      · 点击实验卡片上的"详情"查看完整输出
      · 运行输出会保存在实验记录中
    `,
  },
  ai: {
    title: '🤖 AI 助手',
    content: `
      AI 助手可以帮你自动完成实验操作。

      使用方法：
      1. 进入"AI 助手"页面
      2. 选择要操作的板子
      3. 用自然语言描述你的需求

      示例指令：
      · "列出我所有可用的板子"
      · "在板子上跑一个 GPIO 测试"
      · "帮我编译这个 C 程序并运行"
      · "写一个脚本测试 CPU 性能"
      · "创建一个实验：压力测试 5 分钟"

      ⚠️ 安全说明：
      · AI 只能执行软件操作，不会触碰硬件
      · 高危操作（如烧录固件）会要求你二次确认
      · 所有操作都有日志记录
    `,
  },
  faq: {
    title: '❓ 常见问题',
    content: `
      Q: 板子显示"离线"怎么办？
      A: 检查板子是否开机、网络是否连通、IP 是否正确。点击"检查"按钮重试。

      Q: 预约时间到了但还没用完怎么办？
      A: 可以创建新的预约延长使用时间。当前预约结束后板子会自动释放。

      Q: AI 助手不回复？
      A: 检查 .env 文件中是否正确配置了 ANTHROPIC_API_KEY。

      Q: 实验执行卡住了？
      A: 检查板子是否在线，命令是否超时。可以在板子管理页面直接执行命令测试连通。

      Q: 如何添加更多板子？
      A: 进入"板子管理"页面，点击"添加板子"填写信息。

      Q: 如何查看操作日志？
      A: 所有操作记录保存在后端的数据库中，管理员可以通过 API 查看完整日志。
    `,
  },
}

const sectionKeys = Object.keys(sections)
const activeContent = ref(sections.quickstart.content)

function switchSection(key: string) {
  activeSection.value = key
  activeContent.value = sections[key as keyof typeof sections].content
}
</script>

<template>
  <div class="manual-page">
    <h2>📖 用户手册</h2>
    <p class="subtitle">了解如何使用 Lab Orchestrator 进行远程实验</p>

    <div class="manual-layout">
      <!-- 侧边目录 -->
      <div class="toc">
        <div
          v-for="key in sectionKeys"
          :key="key"
          class="toc-item"
          :class="{ active: activeSection === key }"
          @click="switchSection(key)"
        >
          {{ sections[key as keyof typeof sections].title }}
        </div>
      </div>

      <!-- 内容区 -->
      <div class="content card">
        <h3>{{ sections[activeSection as keyof typeof sections].title }}</h3>
        <pre class="manual-content">{{ activeContent }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.subtitle {
  color: #888;
  margin-bottom: 20px;
}

.manual-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  align-items: start;
}

.toc {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 80px;
}

.toc-item {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  color: #555;
}

.toc-item:hover {
  background: #f0f2f5;
  color: #333;
}

.toc-item.active {
  background: #1a1a2e;
  color: #fff;
}

.card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.content h3 {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.manual-content {
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  font-family: inherit;
  color: #444;
}
</style>
