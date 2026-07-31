#!/usr/bin/env python3
"""
PC Bridge — 远程计算机上的板子桥接
运行在远程计算机上，将本地可 SSH 的板子桥接到 Lab Orchestrator

用法 (单行):
  python pc_bridge.py --server ws://IP:8000/ws/board --token TOKEN --board-ip PI_IP --board-user USER --board-pwd PWD

依赖: pip install websockets sshpass
  Lab Orchestrator ← WebSocket ← 远程计算机 ← SSH → Pi/板子
"""
import asyncio, json, subprocess, argparse, sys

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True, help='Lab Orchestrator WebSocket URL')
    parser.add_argument('--token', required=True, help='板子Token（在Web界面添加远程板子获得）')
    parser.add_argument('--board-ip', required=True, help='板子IP')
    parser.add_argument('--board-user', default='pi')
    parser.add_argument('--board-pwd', default='')
    args = parser.parse_args()

    import websockets

    while True:
        try:
            async with websockets.connect(args.server) as ws:
                # 注册
                await ws.send(json.dumps({
                    "type": "register",
                    "board_info": {"hostname": args.board_ip, "via": "pc-bridge"}
                }))
                resp = json.loads(await ws.recv())
                print(f"已注册: {resp.get('board_id', '?')}")

                # 接收命令执行
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get('type') == 'execute':
                        cmd = msg.get('command', '')
                        # SSH 到板子执行
                        ssh_cmd = [
                            'sshpass', '-p', args.board_pwd,
                            'ssh', '-o', 'StrictHostKeyChecking=no',
                            '-o', 'ConnectTimeout=10',
                            f'{args.board_user}@{args.board_ip}',
                            cmd
                        ]
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                *ssh_cmd, stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.STDOUT
                            )
                            stdout, _ = await asyncio.wait_for(
                                proc.communicate(), timeout=30
                            )
                            output = stdout.decode(errors='replace')
                        except Exception as e:
                            output = str(e)

                        await ws.send(json.dumps({
                            "type": "result",
                            "cmd_id": msg.get('cmd_id', ''),
                            "output": output,
                        }))

        except Exception as e:
            print(f"连接断开: {e}, 5秒后重连...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
