#!/usr/bin/env python3
"""
PC Bridge — 远程计算机桥接板子到 Lab Orchestrator
用法: python pc_bridge.py --server ws://IP:8000/ws/board --token TOKEN --board-ip PI_IP --board-user USER --board-pwd PWD
依赖: pip install websockets
"""
import asyncio, json, subprocess, argparse, sys, os

async def check_deps():
    """检查依赖"""
    missing = []
    try: import websockets
    except ImportError: missing.append('websockets')
    if subprocess.run(['which','sshpass'], capture_output=True).returncode != 0:
        if subprocess.run(['where','sshpass'], capture_output=True).returncode != 0 if os.name=='nt' else True:
            missing.append('sshpass (apt install sshpass)')
    if missing:
        print(f"缺少依赖: {', '.join(missing)}")
        print(f"安装: pip install websockets && apt install sshpass")
        sys.exit(1)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--board-ip', required=True)
    parser.add_argument('--board-user', default='pi')
    parser.add_argument('--board-pwd', default='')
    args = parser.parse_args()

    await check_deps()
    import websockets

    print(f"目标服务器: {args.server}")
    print(f"板子: {args.board_user}@{args.board_ip}")

    # 先测试 SSH 连通
    print("测试 SSH 连通性...")
    test_cmd = [
        'sshpass','-p',args.board_pwd,
        'ssh','-o','StrictHostKeyChecking=no','-o','ConnectTimeout=5',
        f'{args.board_user}@{args.board_ip}','echo SSH_OK'
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*test_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=10)
        out_str = out.decode().strip()
        if 'SSH_OK' in out_str:
            print(f"SSH 连接成功: {out_str}")
        else:
            print(f"SSH 失败: {out_str} {err.decode()[:200]}")
            print("请检查板子IP、用户名和密码是否正确")
            return
    except asyncio.TimeoutError:
        print("SSH 连接超时，请检查板子 IP 是否正确")
        return
    except Exception as e:
        print(f"SSH 错误: {e}")
        return

    # 测试 WebSocket 连通
    print("连接 Lab Orchestrator...")
    try:
        async with websockets.connect(args.server, close_timeout=5) as ws:
            await ws.send(json.dumps({"type":"register","board_info":{"hostname":args.board_ip,"via":"pc-bridge"}}))
            resp = json.loads(await ws.recv())
            if resp.get('type') == 'error':
                print(f"注册失败: {resp.get('detail','?')}")
                return
            print(f"已注册: board_id={resp.get('board_id','?')}")

            # 命令循环
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get('type') == 'execute':
                    cmd = msg.get('command','')
                    ssh_cmd = ['sshpass','-p',args.board_pwd,'ssh','-o','StrictHostKeyChecking=no','-o','ConnectTimeout=5',f'{args.board_user}@{args.board_ip}',cmd]
                    try:
                        proc = await asyncio.create_subprocess_exec(*ssh_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                        output = stdout.decode(errors='replace')
                    except Exception as e:
                        output = str(e)
                    await ws.send(json.dumps({"type":"result","cmd_id":msg.get('cmd_id',''),"output":output}))

    except Exception as e:
        print(f"连接失败: {e}")
        print(f"请确认服务器地址正确且 Lab Orchestrator 正在运行")
        print(f"尝试: curl {args.server.replace('ws://','http://').replace('ws/board','api/health')}")
        return

if __name__ == '__main__':
    asyncio.run(main())
