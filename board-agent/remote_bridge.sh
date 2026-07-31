#!/bin/bash
# Lab Orchestrator Remote Bridge — 一键桥接远程板子
# 在远程计算机上运行此脚本，将板子的 SSH 端口映射到 Lab Orchestrator 服务器
#
# 用法:
#   bash remote_bridge.sh <板子IP> <服务器IP> [板子SSH端口] [映射端口]
#
# 示例:
#   bash remote_bridge.sh 192.168.1.200 172.31.124.129
#   → 远程计算机通过 SSH 隧道将板子的 22 端口映射到服务器的 2222 端口
#   → 在 Lab Orchestrator 中添加板子: host=localhost, port=2222

set -e

BOARD_IP="${1:?请提供板子IP}"
SERVER_IP="${2:?请提供Lab Orchestrator服务器IP}"
BOARD_PORT="${3:-22}"
MAP_PORT="${4:-0}"  # 0 = auto

echo "=== Lab Orchestrator Remote Bridge ==="
echo "  板子: ${BOARD_IP}:${BOARD_PORT}"
echo "  服务器: ${SERVER_IP}"
echo ""

# Auto-assign port based on board IP last octet
if [ "$MAP_PORT" = "0" ]; then
    LAST_OCTET=$(echo "$BOARD_IP" | awk -F. '{print $4}')
    MAP_PORT=$((2200 + LAST_OCTET))
fi
echo "  映射端口: localhost:${MAP_PORT} → ${BOARD_IP}:${BOARD_PORT}"
echo ""

# Keep tunnel alive
echo "正在建立隧道 (保持运行)..."
echo "在 Lab Orchestrator 中添加板子:"
echo "  host=localhost  port=${MAP_PORT}  username=<板子用户名>  password=<板子密码>"
echo ""
ssh -N -R ${MAP_PORT}:${BOARD_IP}:${BOARD_PORT} -o ServerAliveInterval=30 -o StrictHostKeyChecking=no ${SERVER_IP}
