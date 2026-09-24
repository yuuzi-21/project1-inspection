from flask import Flask, render_template, jsonify
import csv
import glob
import os

app = Flask(__name__)
REPORTS_DIR = "reports"


def parse_value(text):
    """'9.8%' -> 9.8；解析不了返回 None"""
    try:
        return float(text.rstrip("%"))
    except ValueError:
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/history")
def api_history():
    """读所有 CSV，整理成每个指标的时间序列"""
    series = {"CPU使用率": [], "内存使用率": [], "磁盘使用率": []}
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "report_*.csv")))
    for fp in files:
        with open(fp, encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if len(row) < 4:
                    continue
                name, value, status, ts = row
                if name in series:
                    num = parse_value(value)
                    if num is not None:
                        series[name].append({"time": ts, "value": num})
    return jsonify(series)


@app.route("/api/latest")
def api_latest():
    """最新一份 CSV 的全部巡检项，给状态卡片用"""
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "report_*.csv")))
    if not files:
        return jsonify({"items": []})
    rows = []
    with open(files[-1], encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) >= 3 and row[0] != "巡检项":
                rows.append({"name": row[0], "value": row[1], "status": row[2]})
    return jsonify({"items": rows})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
