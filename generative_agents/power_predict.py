"""generative_agents.power_predict - 用电量预测工具"""

import argparse
import json
from datetime import datetime, timedelta

from modules.power import EquipmentManager, PowerConsumptionTracker, PowerPredictor


def main():
    parser = argparse.ArgumentParser(description="电力小镇用电量预测工具")
    parser.add_argument("--name", type=str, required=True, help="模拟名称")
    parser.add_argument("--date", type=str, default="", help="预测日期 (格式: YYYYMMDD)")
    parser.add_argument("--location", type=str, default="", help="预测位置（可选）")
    parser.add_argument("--lookback", type=int, default=7, help="回顾天数")
    args = parser.parse_args()
    
    # 初始化系统
    equipment_manager = EquipmentManager()
    power_storage_root = f"results/checkpoints/{args.name}/power"
    power_tracker = PowerConsumptionTracker(power_storage_root, equipment_manager)
    power_tracker.load_from_file()
    
    # 显示数据加载情况
    total_records = len(power_tracker.consumptions)
    print(f"已加载用电量记录: {total_records} 条")
    if total_records > 0:
        latest_record = max(power_tracker.consumptions, key=lambda x: x.timestamp)
        earliest_record = min(power_tracker.consumptions, key=lambda x: x.timestamp)
        print(f"最早记录: {earliest_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"最新记录: {latest_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("警告: 没有找到用电量记录！")
        print("请先运行模拟（start.py）生成用电量数据。")
        return
    
    predictor = PowerPredictor(power_tracker)
    
    # 确定预测日期
    if args.date:
        target_date = datetime.strptime(args.date, "%Y%m%d")
    else:
        target_date = datetime.now() + timedelta(days=1)
    
    print(f"\n{'='*60}")
    print(f"电力小镇用电量预测")
    print(f"{'='*60}")
    print(f"模拟名称: {args.name}")
    print(f"预测日期: {target_date.strftime('%Y-%m-%d')}")
    print(f"回顾天数: {args.lookback}")
    print(f"{'='*60}\n")
    
    if args.location:
        # 预测特定位置的用电量
        consumption = predictor.predict_location_consumption(
            args.location, target_date, args.lookback
        )
        print(f"位置: {args.location}")
        print(f"预测用电量: {consumption:.2f} 千瓦时\n")
    else:
        # 预测整天的用电量
        hourly_predictions = predictor.predict_hourly_consumption(target_date, args.lookback)
        daily_prediction = predictor.predict_daily_consumption(target_date, args.lookback)
        
        print(f"全天预测用电量: {daily_prediction:.2f} 千瓦时\n")
        print("每小时预测用电量:")
        print("-" * 40)
        for hour in sorted(hourly_predictions.keys()):
            print(f"{hour:2d}:00 - {hourly_predictions[hour]:8.2f} 千瓦时")
        
        # 显示趋势
        print(f"\n{'='*60}")
        print("最近7天用电量趋势:")
        print("-" * 40)
        trend = predictor.get_consumption_trend(7)
        for date_str, consumption in sorted(trend.items()):
            print(f"{date_str}: {consumption:.2f} 千瓦时")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()

