"""诊断脚本 — 只测连通性，不做任何其他事情"""
import sys, socket, re

SERVER = sys.argv[1] if len(sys.argv) > 1 else ""
SERVER = re.sub(r'[^a-zA-Z0-9.\-:_]', '', SERVER)
print(f"目标服务器: {repr(SERVER)}")

# 测试1: socket raw connect
print("\n1) socket.connect()...")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((SERVER, 8000))
    print("   OK")
    s.close()
except Exception as e:
    print(f"   FAIL: {e}")

# 测试2: getaddrinfo
print("\n2) getaddrinfo()...")
try:
    ai = socket.getaddrinfo(SERVER, 8000, socket.AF_INET, socket.SOCK_STREAM)
    print(f"   OK → {ai[0][4]}")
except Exception as e:
    print(f"   FAIL: {e}")

# 测试3: HTTP
print("\n3) HTTP GET...")
import http.client
try:
    conn = http.client.HTTPConnection(SERVER, 8000, timeout=5)
    conn.request("GET", "/api/health")
    resp = conn.getresponse()
    print(f"   OK → {resp.status} {resp.read().decode()[:100]}")
except Exception as e:
    print(f"   FAIL: {e}")
