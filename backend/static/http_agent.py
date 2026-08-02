#!/usr/bin/env python3
"""
HTTP Agent — 纯 HTTP 轮询桥接(零依赖, Python标准库)
远程计算机运行此脚本, 将本地SSH板子桥接到Lab Orchestrator

用法: python3 http_agent.py <服务器IP> <板子IP> <用户名> <密码> <TOKEN>
示例: python3 http_agent.py 172.31.124.129 10.42.0.174 gjh gejiahao TOKEN
"""
import subprocess, json, time, sys, re, urllib.request, urllib.error

SERVER = re.sub(r'[^a-zA-Z0-9.\-:_]', '', sys.argv[1]) if len(sys.argv) > 1 else ""
BOARD_IP = re.sub(r'[^a-zA-Z0-9.\-:_]', '', sys.argv[2]) if len(sys.argv) > 2 else ""
BOARD_USER = re.sub(r'[^a-zA-Z0-9.\-:_]', '', sys.argv[3]) if len(sys.argv) > 3 else "root"
BOARD_PWD = sys.argv[4] if len(sys.argv) > 4 else ""
TOKEN = re.sub(r'[^a-zA-Z0-9.\-:_=+]', '', sys.argv[5]) if len(sys.argv) > 5 else ""

if not all([SERVER, BOARD_IP, TOKEN]):
    print("用法: python3 http_agent.py <服务器IP> <板子IP> <用户名> <密码> <TOKEN>")
    sys.exit(1)

print(f"服务器: {SERVER}   板子: {BOARD_USER}@{BOARD_IP}   Token: {TOKEN[:8]}...")

# 测试SSH
test = subprocess.run(
    ["sshpass","-p",BOARD_PWD,"ssh","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=5",
     f"{BOARD_USER}@{BOARD_IP}","echo SSH_OK"],
    capture_output=True, text=True, timeout=10
)
if "SSH_OK" not in test.stdout:
    print(f"SSH测试失败: {test.stdout}{test.stderr}")
    print("请确认板子IP、用户名、密码正确。如无 sshpass: apt install sshpass")
    sys.exit(1)
print("SSH连接成功!")

BASE = f"http://{SERVER}:8000"

while True:
    try:
        # 注册
        print(f"\n注册到 {BASE}/api/boards/register-agent ...")
        req = urllib.request.Request(
            f"{BASE}/api/boards/register-agent",
            data=json.dumps({"token": TOKEN}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        board_id = resp.get("board_id", "?")
        print(f"注册成功: board_id={board_id}")

        # 轮询命令
        while True:
            try:
                req2 = urllib.request.Request(
                    f"{BASE}/api/boards/{board_id}/pending-commands",
                    headers={"Authorization": f"Bearer {TOKEN}"}
                )
                resp2 = json.loads(urllib.request.urlopen(req2, timeout=30).read())

                for cmd in resp2.get("commands", []):
                    cmd_id = cmd["id"]
                    command = cmd["command"]
                    print(f"  执行: {command[:60]}")

                    result = subprocess.run(
                        ["sshpass","-p",BOARD_PWD,"ssh","-o","StrictHostKeyChecking=no",
                         "-o","ConnectTimeout=5",f"{BOARD_USER}@{BOARD_IP}",command],
                        capture_output=True, text=True, timeout=30
                    )
                    output = result.stdout + result.stderr

                    # 回传结果
                    req3 = urllib.request.Request(
                        f"{BASE}/api/boards/{board_id}/command-result",
                        data=json.dumps({"cmd_id": cmd_id, "output": output}).encode(),
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
                        method="POST"
                    )
                    urllib.request.urlopen(req3, timeout=10)
                    print(f"    结果已回传 ({len(output)} 字节)")

                time.sleep(2)  # 2秒轮询间隔

            except urllib.error.URLError:
                time.sleep(3)
            except Exception as e:
                print(f"  轮询错误: {e}")
                time.sleep(5)

    except Exception as e:
        print(f"连接错误: {e}, 5秒后重试...")
        time.sleep(5)
