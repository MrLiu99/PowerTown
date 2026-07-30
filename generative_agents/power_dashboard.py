"""电力小镇用电量展示面板"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.power import EquipmentManager, PowerConsumptionTracker

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static",
    static_url_path="/static",
)


def load_power_data(simulation_name):
    """加载用电量数据"""
    equipment_manager = EquipmentManager()
    power_storage_root = f"results/checkpoints/{simulation_name}/power"
    power_tracker = PowerConsumptionTracker(power_storage_root, equipment_manager)
    power_tracker.load_from_file()
    return power_tracker


@app.route("/power", methods=['GET'])
def power_dashboard():
    """用电量展示面板主页"""
    simulation_name = request.args.get("name", "")
    if not simulation_name:
        return "请提供模拟名称 (name参数)"
    
    return render_template("power_dashboard.html", simulation_name=simulation_name)


@app.route("/api/power/data", methods=['GET'])
def get_power_data():
    """获取用电量数据API"""
    simulation_name = request.args.get("name", "")
    if not simulation_name:
        return jsonify({"error": "请提供模拟名称"}), 400
    
    try:
        power_tracker = load_power_data(simulation_name)
        
        # 按位置分组统计
        location_data = defaultdict(lambda: {
            "total_consumption": 0.0,
            "agents": defaultdict(lambda: {
                "total": 0.0,
                "activities": []
            })
        })
        
        # 获取最近的记录（最近24小时，或者所有数据）
        current_time = datetime.now()
        # 不限制时间，显示所有数据，或者可以设置显示最近24小时
        # one_hour_ago = datetime.now() - timedelta(hours=24)
        
        for cons in power_tracker.consumptions:
            # 显示所有数据（不限制时间）
            location = cons.location
            agent_name = cons.agent_name
            
            location_data[location]["total_consumption"] += cons.power_kwh
            location_data[location]["agents"][agent_name]["total"] += cons.power_kwh
            
            # 记录活动
            activity_info = {
                "activity": cons.activity,
                "equipment": cons.equipment,
                "power_kwh": cons.power_kwh,
                "timestamp": cons.timestamp.strftime("%Y-%m-%d %H:%M:%S")  # 显示完整时间
            }
            location_data[location]["agents"][agent_name]["activities"].append(activity_info)
        
        # 添加调试信息
        print(f"Loaded {len(power_tracker.consumptions)} consumption records")
        print(f"Found {len(location_data)} locations")
        
        # 转换为可序列化的格式
        result = {}
        for location, data in location_data.items():
            result[location] = {
                "total_consumption": round(data["total_consumption"], 2),
                "agents": {}
            }
            for agent_name, agent_data in data["agents"].items():
                # 按时间倒序排列，返回最近的活动
                sorted_activities = sorted(
                    agent_data["activities"], 
                    key=lambda x: x["timestamp"], 
                    reverse=True
                )[:20]  # 返回最近20条活动
                result[location]["agents"][agent_name] = {
                    "total": round(agent_data["total"], 2),
                    "activities": sorted_activities
                }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/power/history", methods=['GET'])
def get_power_history():
    """获取历史用电量数据"""
    simulation_name = request.args.get("name", "")
    location = request.args.get("location", "")
    hours = int(request.args.get("hours", 24))
    
    if not simulation_name:
        return jsonify({"error": "请提供模拟名称"}), 400
    
    try:
        power_tracker = load_power_data(simulation_name)
        
        # 按小时统计
        from datetime import timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        hourly_data = defaultdict(lambda: defaultdict(float))
        
        for cons in power_tracker.consumptions:
            if cons.timestamp >= start_time and cons.timestamp <= end_time:
                if not location or cons.location == location:
                    hour_key = cons.timestamp.strftime("%Y-%m-%d %H:00")
                    hourly_data[hour_key][cons.location] += cons.power_kwh
        
        result = []
        for hour, locations in sorted(hourly_data.items()):
            result.append({
                "hour": hour,
                "locations": {loc: round(cons, 2) for loc, cons in locations.items()},
                "total": round(sum(locations.values()), 2)
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)

