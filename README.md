# 系统巡检系统 System Inspection

一个面向服务器与个人主机的**自动化巡检工具**：定时采集 CPU、内存、磁盘与网络连通性数据，超阈值自动告警，生成 CSV / Excel 报告，并提供 Web 可视化面板查看历史趋势。

## 功能特性

- **系统资源巡检**：CPU / 内存 / 磁盘使用率采集（`psutil`），阈值可配置
- **网络连通性巡检**：多目标 ping（内网网关 → 公网 IP → 公网域名），逐层验证网络健康；跨平台兼容 Windows 与 Linux
- **HTTP 探测**：验证应用层可用性（状态码判定），覆盖"网络通但服务异常"的场景
- **阈值告警**：资源超限、目标不可达自动收集告警并输出
- **双格式报告**：CSV 时间戳存档 + Excel 报告（告警行自动标红）
- **定时调度**：基于 `schedule` 每 10 分钟自动巡检（可配置每日定点执行）
- **Web 可视化面板**：Flask + ECharts，实时状态卡片 + CPU/内存/磁盘历史趋势折线图，5 秒自动刷新
- **容器化部署**：Dockerfile 一键构建运行（含 ping 依赖）

## 技术栈

Python 3.10 · Flask · psutil · schedule · openpyxl · requests · Docker

## 目录结构

```
project1-inspection/
├── project2.py            # 巡检核心逻辑（资源/网络/HTTP/告警/报告）
├── daemon.py              # 定时调度入口（schedule，每10分钟）
├── app.py                 # Flask 面板后端（历史/最新数据 API）
├── templates/
│   └── index.html         # 可视化面板前端（ECharts）
├── config.json            # 运行配置（ping 目标、阈值）
├── config.example.json    # 配置样例（可复制为 config.json）
├── requirements.txt       # 依赖清单
├── Dockerfile             # 容器化部署
├── reports/               # CSV / Excel 报告输出目录
└── inspect.log            # 巡检日志（自动生成）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制配置样例并按需修改：

```bash
cp config.example.json config.json
```

```json
{
    "ping_targets": [
        {"name": "网关(内网)", "host": "192.168.1.1"},
        {"name": "公网IP", "host": "223.5.5.5"},
        {"name": "公网域名", "host": "www.baidu.com"}
    ],
    "thresholds": {"cpu": 85, "memory": 85, "disk": 90},
    "remote_hosts": [],
    "webhook_url": ""
}
```

- `ping_targets`：网络巡检目标，建议覆盖内网网关、公网 IP、公网域名三层
- `thresholds`：CPU / 内存 / 磁盘告警阈值（%）
- `remote_hosts` / `webhook_url`：预留的远程主机检查与消息推送配置

### 3. 手动执行一次巡检

```bash
python project2.py
```

将输出巡检结果，并在 `reports/` 生成 CSV 与 Excel 报告。

### 4. 启动定时巡检（每 10 分钟）

```bash
python daemon.py
```

如需改为每日定点执行，编辑 `daemon.py` 中注释的 `schedule.every().day.at("09:00")` 行。

### 5. 启动可视化面板

```bash
python app.py
```

浏览器访问 <http://127.0.0.1:5000>，查看实时状态卡片与历史趋势图。

## 输出说明

| 输出 | 位置 | 说明 |
|---|---|---|
| CSV 报告 | `reports/report_时间戳.csv` | 每次巡检一行记录，含巡检项/值/状态/时间 |
| Excel 报告 | `reports/report_时间戳.xlsx` | 告警行自动标红，表头加粗灰底 |
| 日志 | `inspect.log` | 终端 + 文件双输出，带时间与级别 |
| Web 面板 | `http://127.0.0.1:5000` | 状态卡片 + 趋势图，5 秒自动刷新 |

## 面板 API

| 接口 | 说明 |
|---|---|
| `GET /api/latest` | 最新一次巡检的全部指标，供状态卡片渲染 |
| `GET /api/history` | 所有历史 CSV 的时间序列，供趋势折线图渲染 |

## Docker 部署

```bash
docker build -t inspection .
docker run -d --name inspection inspection
```

镜像基于 `python:3.10-slim`，内置 `iputils-ping`，依赖使用清华镜像源安装，时区预设为 Asia/Shanghai。

## 注意事项

- `config.json` 若含内网地址或推送地址，请勿提交到公开仓库
- `daemon.py` 开发测试阶段调度间隔不宜过短（当前 10 分钟）
- 本项目为学习/求职展示项目，可直接作为"自动化运维"方向的实践案例
