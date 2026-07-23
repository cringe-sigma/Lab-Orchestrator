"""实验计划模板 — 预定义的常见嵌入式实验"""
from __future__ import annotations

from agent_core import ExperimentStep, ExperimentPlan


def gpio_basic_test(board_id: int, pin: int = 18) -> ExperimentPlan:
    """GPIO 输出测试"""
    return ExperimentPlan(
        name="GPIO 基础输出测试",
        board_id=board_id,
        description=f"测试 GPIO {pin} 引脚的输出功能",
        steps=[
            ExperimentStep(1, "exec_command", {"command": "gpio export 18 out"}, "配置 GPIO 为输出模式"),
            ExperimentStep(2, "exec_command", {"command": "gpio write 18 1"}, "输出高电平"),
            ExperimentStep(3, "exec_command", {"command": "gpio read 18"}, "读取并验证输出状态"),
            ExperimentStep(4, "exec_command", {"command": "gpio write 18 0"}, "输出低电平"),
            ExperimentStep(5, "exec_command", {"command": "gpio read 18"}, "验证低电平状态"),
        ],
        risk_level="low",
    )


def cpu_stress_test(board_id: int, duration_sec: int = 60) -> ExperimentPlan:
    """CPU 压力测试"""
    return ExperimentPlan(
        name="CPU 稳定性测试",
        board_id=board_id,
        description=f"运行 stress 工具进行 {duration_sec} 秒 CPU 压力测试",
        steps=[
            ExperimentStep(1, "exec_command", {"command": "which stress || apt-get install -y stress"}, "确保 stress 工具已安装"),
            ExperimentStep(2, "exec_command", {"command": f"stress --cpu 4 --timeout {duration_sec}s &"}, "启动压力测试"),
            ExperimentStep(3, "exec_command", {"command": "top -bn1 | head -10"}, "查看 CPU 占用"),
            ExperimentStep(4, "exec_command", {"command": "cat /proc/cpuinfo | grep temperature || cat /sys/class/thermal/thermal_zone0/temp"}, "检查温度"),
        ],
        risk_level="low",
    )


def memory_test(board_id: int, size_mb: int = 128) -> ExperimentPlan:
    """内存测试"""
    return ExperimentPlan(
        name="内存读写测试",
        board_id=board_id,
        description=f"分配 {size_mb}MB 内存进行读写速度测试",
        steps=[
            ExperimentStep(1, "exec_command", {"command": "which mbw || apt-get install -y mbw"}, "安装内存测试工具"),
            ExperimentStep(2, "exec_command", {"command": f"mbw -n 5 {size_mb}"}, "运行内存带宽测试"),
            ExperimentStep(3, "exec_command", {"command": "free -m"}, "查看内存使用情况"),
        ],
        risk_level="low",
    )


def network_benchmark(board_id: int, target_host: str = "localhost") -> ExperimentPlan:
    """网络性能测试"""
    return ExperimentPlan(
        name="网络吞吐测试",
        board_id=board_id,
        description=f"测试与 {target_host} 之间的网络性能",
        steps=[
            ExperimentStep(1, "exec_command", {"command": f"ping -c 10 {target_host}"}, "测试网络延迟和丢包率"),
            ExperimentStep(2, "exec_command", {"command": "which iperf3 || apt-get install -y iperf3"}, "安装网络测试工具"),
        ],
        risk_level="low",
    )


def firmware_flash_template(board_id: int, firmware_path: str, tool: str = "stm32flash") -> ExperimentPlan:
    """固件烧录模板 — 注意这是高危操作"""
    return ExperimentPlan(
        name="固件烧录",
        board_id=board_id,
        description=f"烧录固件 {firmware_path}",
        steps=[
            ExperimentStep(1, "check_board_status", {}, f"确认板子 {board_id} 处于可烧录状态"),
            ExperimentStep(2, "flash_firmware", {"firmware_path": firmware_path, "tool": tool}, "执行烧录"),
            ExperimentStep(3, "exec_command", {"command": "dmesg | tail -20"}, "检查系统日志确认烧录成功"),
        ],
        risk_level="high",
    )


# 实验模板注册表
EXPERIMENT_TEMPLATES = {
    "gpio_test": gpio_basic_test,
    "cpu_stress": cpu_stress_test,
    "memory_test": memory_test,
    "network_bench": network_benchmark,
    "flash_firmware": firmware_flash_template,
}


def get_template_names() -> list[str]:
    return list(EXPERIMENT_TEMPLATES.keys())


def create_from_template(name: str, board_id: int, **kwargs) -> ExperimentPlan | None:
    """从模板创建实验计划"""
    factory = EXPERIMENT_TEMPLATES.get(name)
    if not factory:
        return None
    return factory(board_id, **kwargs)
