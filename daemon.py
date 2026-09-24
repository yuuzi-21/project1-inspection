import time
import schedule
from project2 import main  # 复用我们写好的巡检函数

# 每 10 分钟执行一次巡检（开发测试阶段别设太短）
schedule.every(10).minutes.do(main)
# schedule.every().day.at("09:00").do(main)  # 或每天上午9点

logger_info = "定时巡检服务已启动..."
print(logger_info)

while True:
    schedule.run_pending()
    time.sleep(30)  # 每30秒醒一次看看有没有到点
