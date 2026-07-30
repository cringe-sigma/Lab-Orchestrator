# InterAgent i.MX8MM Demo

跨核 cache/memory timing hazard 自动发现实验

## Quick Start

```bash
# 1. 编译
cd src && make

# 2. 采集环境
bash scripts/env_collect.sh

# 3. 基线 (10次隔离运行)
bash scripts/baseline.sh

# 4. 搜索 (30次实验)
bash scripts/search.sh 30

# 5. 确认候选
bash scripts/confirm.sh

# 6. 生成 hazard record
bash scripts/generate_hazard.sh
```

## 目录

| path | 说明 |
|------|------|
| src/ | C 源码 (victim, cache/memory attacker) |
| bin/ | 编译产物 |
| contracts/ | YAML 干扰契约 |
| scripts/ | 实验脚本 |
| results/ | 所有实验数据 |
