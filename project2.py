import platform
import subprocess
import datetime
import json
import csv
import socket
import psutil
import requests
import logging

# 配置日志系统：同时输出到终端 + 写入文件
logging.basicConfig(
    level=logging.INFO,  # 只记录 INFO 及以上级别（DEBUG < INFO < WARNING < ERROR）
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("inspect.log", encoding="utf-8"),  # 写入文件
        logging.StreamHandler()                                 # 同时显示在终端
    ]
)
logger = logging.getLogger("巡检系统")

def send_alerts(alerts, webhook_url=None):
    """
    汇总所有告警并通知
    alerts: 告警内容列表，如 ["CPU使用率 92% 超过阈值85%"]
    """
    if not alerts:
        logger.info("本次巡检无告警 ✅")
        return

    message = "🚨 巡检告警通知\n" + "\n".join(f"  • {a}" for a in alerts)
    logger.warning(message)

def load_config(path="config.json"):
    """从 JSON 文件加载配置"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  找不到配置文件 {path}，使用默认配置")
        return {
            "ping_targets": [{"name": "百度", "host": "www.baidu.com"}],
            "thresholds": {"cpu": 85, "memory": 85, "disk": 90}
        }


def save_report(data, base_dir="reports"):
    """把巡检结果写入 CSV 文件，文件名带时间戳"""
    import os
    # 如果 reports 文件夹不存在，自动创建
    os.makedirs(base_dir, exist_ok=True)

    now = datetime.datetime.now()
    filename = now.strftime("report_%Y-%m-%d_%H-%M-%S.csv")
    filepath = os.path.join(base_dir, filename)

    # 写入 CSV
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["巡检项", "值", "状态", "时间"])
        for row in data:
            writer.writerow(row)

    print(f"\n📁 报告已保存: {filepath}")
    return filepath

def check_local_ip():
    """获取本机 IP 地址和网卡信息"""
    info_list = []
    # net_if_addrs() 返回所有网卡的信息（名字、IP、MAC地址）
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            # AF_INET 表示 IPv4 地址
            if addr.family == socket.AF_INET:
                # 跳过回环地址 127.0.0.1（那是本机自娱自乐的地址）
                if addr.address != "127.0.0.1":
                    info_list.append(f"网卡[{name}] IP: {addr.address}")
    return info_list

# ---------- 1. 系统资源检查 ----------

def check_cpu():
    """CPU 使用率，interval=1 表示采样1秒，数值更真实"""
    return psutil.cpu_percent(interval=1)

def check_memory():
    """内存使用率(%)"""
    return psutil.virtual_memory().percent

def check_disk():
    """磁盘使用率(%)，Windows 看 C 盘，Linux/Mac 看根目录 /"""
    path = "C:\\" if platform.system().lower() == "windows" else "/"
    return psutil.disk_usage(path).percent

# ---------- 2. 网络连通性检查 ----------

def ping_host(host="114.114.114.114"):
    """ping 一个地址，通则返回 True"""
    # Windows 用 -n 计数，Linux/Mac 用 -c —— 这就是运维要懂的系统差异
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(
        ["ping", count_flag, "1", host],
        capture_output=True  # 不打印黑框框，结果存进变量
    )
    # returncode 是程序的退出码：0 表示成功
    return result.returncode == 0

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

def generate_excel(report_rows, base_dir="reports"):
    """把当次巡检结果生成格式化的 Excel，告警行标红"""
    import os
    os.makedirs(base_dir, exist_ok=True)

    now = datetime.datetime.now()
    filepath = os.path.join(base_dir, now.strftime("report_%Y-%m-%d_%H-%M-%S.xlsx"))

    wb = Workbook()
    ws = wb.active
    ws.title = "巡检报告"

    # 表头样式：加粗 + 灰底
    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="DDDDDD")
    # 告警行样式：红底
    alert_fill = PatternFill("solid", fgColor="FFC7CE")

    # 写入表头
    headers = ["巡检项", "值", "状态", "时间"]
    ws.append(headers)
    for cell in ws[1]:  # 第1行的所有单元格
        cell.font = header_font
        cell.fill = header_fill

    # 写入数据行，含"告警/故障/异常"字样的行标红
    for row in report_rows:
        ws.append(row)
        if any(k in str(row[2]) for k in ["告警", "故障", "异常"]):
            for cell in ws[ws.max_row]:
                cell.fill = alert_fill

    # 自动调整列宽（粗略版）
    for col in ws.columns:
        max_len = max(len(str(c.value)) for c in col if c.value)
        ws.column_dimensions[col[0].column_letter].width = max_len + 4

    wb.save(filepath)
    logger.info(f"📊 Excel 报告已生成: {filepath}")
    return filepath


# ---------- 网络巡检目标配置 ----------
# 为什么用三个目标？分别验证不同层面的网络健康
PING_TARGETS = [
    ("网关(内网)",   "192.168.1.1"),      # ← 改成你自己的网关，查看方法见下方
    ("公网IP",       "223.5.5.5"),        # 阿里公共DNS，响应率高，比114靠谱
    ("公网域名",     "www.baidu.com"),    # 同时验证 DNS 解析 + 外网连通
]

def check_network():
    """多目标综合判定网络状态"""
    print("----- 网络连通性检测 -----")
    passed = 0
    for name, host in PING_TARGETS:
        ok = ping_host(host)
        print(f"  {name} ({host}): {'✅ 通' if ok else '❌ 不通'}")
        if ok:
            passed += 1

    # 判定逻辑：过半数目标通 = 网络基本正常
    total = len(PING_TARGETS)
    healthy = passed > total / 2

    # 根据结果给出排障方向 —— 这就是把"人工排障思路"写进代码
    if passed == total:
        print("网络状态: 完全正常 ✅")
    elif PING_TARGETS[0][1] and not healthy:
        print("网络状态: 异常 ⚠️  连网关都不通，检查网线/WiFi/网卡")
    else:
        print("网络状态: 部分异常 ⚠️  内网通但外网异常，检查路由器/运营商线路")

    return healthy


def main():
    config = load_config()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 【M3新增】日志器代替 print，自动带时间+级别，且同时写进 inspect.log
    logger.info(f"===== 巡检开始  {now_str} =====")

    report_rows = []
    alerts = []  # 【M3新增】告警收集袋，所有问题都 append 到这里

    # ========== 1. 系统资源检查 ==========
    cpu = check_cpu()
    mem = check_memory()
    disk = check_disk()
    thresholds = config["thresholds"]

    logger.info("----- 系统资源 -----")
    for name, value, limit in [
        ("CPU使用率", cpu, thresholds["cpu"]),
        ("内存使用率", mem, thresholds["memory"]),
        ("磁盘使用率", disk, thresholds["disk"])
    ]:
        if value <= limit:
            status = "正常"
        else:
            status = "⚠️ 告警"
            # 【M3新增】超阈值 → 记进告警袋（这条会出现在通知和日志里）
            alerts.append(f"{name} {value}% 超过阈值 {limit}%")

        logger.info(f"{name}: {value}%  {status}")
        report_rows.append([name, f"{value}%", status, now_str])

    # ========== 2. 网络连通性检查 ==========
    logger.info("----- 网络连通性检测 -----")
    net_passed = 0
    for item in config["ping_targets"]:
        try:
            ok = ping_host(item["host"])
            status = "通" if ok else "不通"
            if ok:
                net_passed += 1
            else:
                # 【M3新增】目标不可达 → 记进告警袋
                alerts.append(f"{item['name']}({item['host']}) ping 不可达")

            logger.info(f"  {item['name']} ({item['host']}): {status}")
            report_rows.append([item["name"], status, "正常" if ok else "故障", now_str])
        except Exception as e:
            logger.error(f"  {item['name']} ({item['host']}): 检测异常 - {e}")
            alerts.append(f"{item['name']}({item['host']}) 检测异常: {e}")
            report_rows.append([item["name"], "异常", f"错误: {e}", now_str])

    # 网络综合判定
    total = len(config["ping_targets"])
    healthy = net_passed > total / 2
    net_status = "完全正常 ✅" if healthy else "异常 ⚠️"
    if not healthy:
        # 【M3新增】整体异常 → 也记一条总结性告警
        alerts.append(f"网络整体异常：仅 {net_passed}/{total} 个目标可达")

    logger.info(f"网络状态: {net_status}")
    report_rows.append(["网络综合状态", f"{net_passed}/{total}台", net_status, now_str])

    # ========== 3. HTTP 探测（你自己加的功能，保留）==========
    try:
        import requests
        resp = requests.get("https://www.baidu.com", timeout=5)
        http_ok = resp.status_code == 200
        if not http_ok:
            # 【M3新增】HTTP 异常也纳入告警
            alerts.append(f"HTTP 探测异常，状态码 {resp.status_code}")
        logger.info(f"HTTP 访问百度: {resp.status_code}  {'✅ 正常' if http_ok else '❌ 异常'}")
        report_rows.append(["HTTP探测", str(resp.status_code), "正常" if http_ok else "异常", now_str])
    except Exception as e:
        logger.error(f"HTTP 探测失败: {e}")
        alerts.append(f"HTTP 探测失败: {e}")
        report_rows.append(["HTTP探测", "失败", f"错误: {e}", now_str])

    # ========== 4. 本机 IP 信息 ==========
    logger.info("----- 网络信息 -----")
    for line in check_local_ip():
        logger.info(f"  {line}")
        report_rows.append(["本机IP", line, "信息", now_str])

    # ========== 5. 【M3新增】收尾：先告警，再存档 ==========
    send_alerts(alerts)  # 有告警就 WARNING + 可选通知，没有就记录"无告警"
    save_report(report_rows)  # CSV 照常存档
    generate_excel(report_rows)
    logger.info("===== 巡检完成 =====")



if __name__ == "__main__":
    main()
