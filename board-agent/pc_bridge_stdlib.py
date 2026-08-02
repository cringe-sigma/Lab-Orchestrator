#!/usr/bin/env python3
"""
PC Bridge (零依赖版) — 远程计算机桥接板子到 Lab Orchestrator
无需 pip install，只使用 Python 标准库

用法:
  python3 pc_bridge_stdlib.py <服务器IP> <板子IP> <板子用户名> <板子密码> <Token>
"""
import subprocess, json, socket, ssl, time, sys, os, hashlib, base64, threading, queue

SERVER = sys.argv[1].strip() if len(sys.argv) > 1 else None
BOARD_IP = sys.argv[2].strip() if len(sys.argv) > 2 else None
BOARD_USER = sys.argv[3].strip() if len(sys.argv) > 3 else "root"
BOARD_PWD = sys.argv[4] if len(sys.argv) > 4 else ""
TOKEN = sys.argv[5].strip() if len(sys.argv) > 5 else None

# 验证 IP 格式
def is_valid_ip(s):
    parts = s.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

if not is_valid_ip(SERVER or ""):
    print(f"错误: 服务器IP格式无效: '{SERVER}'")
    print(f"请确认传入的是IP地址，如 172.31.124.129")
    sys.exit(1)
if not is_valid_ip(BOARD_IP or ""):
    print(f"错误: 板子IP格式无效: '{BOARD_IP}'")
    sys.exit(1)

if not all([SERVER, BOARD_IP, TOKEN]):
    print("用法: python3 pc_bridge_stdlib.py <服务器IP> <板子IP> <用户名> <密码> <Token>")
    print("示例: python3 pc_bridge_stdlib.py 172.31.124.129 10.42.0.174 gjh gejiahao TOKEN")
    sys.exit(1)

# 启动时打印解析到的参数
print(f"服务器: {SERVER}")
print(f"板子:   {BOARD_USER}@{BOARD_IP}")
print(f"Token:  {TOKEN[:10]}...")
print()

# 先测试网络连通性
def can_connect(host, port=8000, timeout=5):
    try:
        s = socket.socket()
        s.settimeout(timeout)
        addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        s.connect(addr[0][4])
        s.close()
        return True
    except socket.gaierror as e:
        print(f"  DNS/地址解析失败: {e}")
        return False
    except Exception as e:
        print(f"  TCP连接失败: {e}")
        return False

print(f"测试到服务器 {SERVER}:8000 的连通性...")
if can_connect(SERVER, 8000):
    print(f"  连接 {SERVER}:8000 OK")
else:
    print(f"  无法连接 {SERVER}:8000")
    print(f"  请确认 Lab Orchestrator 正在运行且端口可达")

print(f"测试到板子 {BOARD_IP}:22 的连通性...")
if can_connect(BOARD_IP, 22):
    print(f"  连接 {BOARD_IP}:22 OK")
else:
    print(f"  无法连接 {BOARD_IP}:22")
    print(f"  请确认板子已开机且SSH服务运行中")
print()

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)

def ssh_exec(cmd):
    """SSH 到板子执行命令并返回输出"""
    ssh_cmd = [
        "sshpass", "-p", BOARD_PWD,
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
        f"{BOARD_USER}@{BOARD_IP}", cmd
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "SSH 超时"
    except FileNotFoundError:
        # sshpass not found, try without password
        if BOARD_PWD:
            log("sshpass 未安装，尝试用密钥认证...")
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
                f"{BOARD_USER}@{BOARD_IP}", cmd
            ]
            try:
                result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
                return result.stdout + result.stderr
            except Exception as e:
                return f"SSH 错误: {e}"
        return "SSH 错误: sshpass 未安装且无密钥"

# Test SSH first
log(f"测试 SSH: {BOARD_USER}@{BOARD_IP}")
test = ssh_exec("echo SSH_OK")
if "SSH_OK" not in test:
    log(f"SSH 测试失败: {test[:200]}")
    log("请确认板子 IP、用户名和密码正确，且 sshpass 已安装")
    sys.exit(1)
log("SSH 连接成功!")

# WebSocket handshake (RFC 6455, minimal implementation)
def ws_connect(host, port, path, token):
    """纯 Python WebSocket 连接"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    # 解析主机名
    try:
        sock.connect((host, port))
    except socket.gaierror:
        log(f"无法解析主机名: {host}")
        log(f"请确认服务器IP: {host} 是否正确")
        sys.exit(1)
    except ConnectionRefusedError:
        log(f"连接被拒绝: {host}:{port}")
        log("请确认 Lab Orchestrator 正在运行")
        sys.exit(1)

    # 生成 WebSocket key
    key = base64.b64encode(os.urandom(16)).decode()

    # 发送 HTTP Upgrade 请求
    request = (
        f"GET {path}?token={token} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    )
    sock.sendall(request.encode())

    # 读取响应
    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)
        if len(response) > 8192:
            log("WebSocket 握手超时")
            sock.close()
            return None

    if b"101" not in response[:30]:
        log(f"服务器返回非 WebSocket 响应: {response[:200]}")
        log("Token 可能无效，请在网页上重新生成")
        sock.close()
        return None

    log(f"已连接到 Lab Orchestrator: {host}:{port}")
    return sock

def ws_send(sock, text):
    """发送 WebSocket 文本帧"""
    data = text.encode()
    frame = bytearray()
    frame.append(0x81)  # text frame, FIN
    length = len(data)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(data)
    sock.sendall(bytes(frame))

def ws_recv(sock):
    """接收 WebSocket 帧并返回文本"""
    try:
        header = sock.recv(2)
        if len(header) < 2:
            return None
        opcode = header[0] & 0x0F
        if opcode == 0x08:  # close
            return None
        masked = header[1] & 0x80
        length = header[1] & 0x7F
        if length == 126:
            length = int.from_bytes(sock.recv(2), 'big')
        elif length == 127:
            length = int.from_bytes(sock.recv(8), 'big')

        payload = b""
        while len(payload) < length:
            chunk = sock.recv(min(length - len(payload), 4096))
            if not chunk:
                break
            payload += chunk

        # Unmask (client->server messages are masked, server->client are not)
        if masked:
            mask_key = payload[:4]
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload[4:]))

        return payload.decode(errors='replace')
    except socket.timeout:
        return None
    except Exception as e:
        return None

# Main loop
PORT = 8000
PATH = f"/ws/board"

while True:
    try:
        log(f"连接 {SERVER}:{PORT}...")
        ws = ws_connect(SERVER, PORT, PATH, TOKEN)
        if not ws:
            log("5秒后重试...")
            time.sleep(5)
            continue

        # 注册
        ws_send(ws, json.dumps({
            "type": "register",
            "board_info": {"hostname": BOARD_IP, "via": "pc-bridge-stdlib"}
        }))

        # 接收注册确认
        time.sleep(1)
        resp = ws_recv(ws)
        if resp:
            try:
                data = json.loads(resp)
                log(f"注册成功: board_id={data.get('board_id', '?')}")
            except:
                pass

        # 命令循环
        while True:
            msg = ws_recv(ws)
            if msg is None:
                log("连接断开")
                break
            try:
                data = json.loads(msg)
                if data.get("type") == "execute":
                    cmd = data.get("command", "")
                    cmd_id = data.get("cmd_id", "")
                    output = ssh_exec(cmd)
                    ws_send(ws, json.dumps({
                        "type": "result",
                        "cmd_id": cmd_id,
                        "output": output
                    }))
            except Exception as e:
                pass

    except Exception as e:
        log(f"错误: {e}")
        try: ws.close()
        except: pass

    log("5秒后重连...")
    time.sleep(5)
