"""generative_agents.power.predictor - 用电量预测"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from .consumption import PowerConsumptionTracker


class PowerPredictor:
    """用电量预测器"""
    
    def __init__(self, consumption_tracker: PowerConsumptionTracker):
        """
        初始化预测器
        
        Args:
            consumption_tracker: 用电量跟踪器
        """
        self.tracker = consumption_tracker
    
    def predict_hourly_consumption(self, target_date: datetime, 
                                   lookback_days: int = 7) -> Dict[int, float]:
        """
        预测指定日期的小时用电量
        
        Args:
            target_date: 目标日期
            lookback_days: 回顾天数（用于计算历史平均值）
        
        Returns:
            每小时预测用电量字典 {hour: consumption_kwh}
        """
        # 获取历史数据
        start_date = target_date - timedelta(days=lookback_days)
        historical_data = self._get_historical_hourly_data(start_date, target_date)
        
        # 计算每小时的平均用电量
        hourly_avg = defaultdict(list)
        for date, hourly_cons in historical_data.items():
            for hour, consumption in hourly_cons.items():
                hourly_avg[hour].append(consumption)
        
        # 预测（使用平均值）
        predictions = {}
        for hour in range(24):
            if hour in hourly_avg:
                # 使用中位数作为预测值（更稳健）
                predictions[hour] = np.median(hourly_avg[hour])
            else:
                predictions[hour] = 0.0
        
        # 考虑周末因素
        if target_date.weekday() >= 5:  # 周六或周日
            for hour in range(8, 23):  # 白天时间
                predictions[hour] *= 1.2  # 周末用电量增加
        
        return predictions
    
    def predict_daily_consumption(self, target_date: datetime,
                                  lookback_days: int = 7) -> float:
        """
        预测指定日期的总用电量
        
        Args:
            target_date: 目标日期
            lookback_days: 回顾天数
        
        Returns:
            预测的总用电量（千瓦时）
        """
        hourly_predictions = self.predict_hourly_consumption(target_date, lookback_days)
        return sum(hourly_predictions.values())
    
    def predict_location_consumption(self, location: str, target_date: datetime,
                                    lookback_days: int = 7) -> float:
        """
        预测指定位置的用电量
        
        Args:
            location: 位置名称
            target_date: 目标日期
            lookback_days: 回顾天数
        
        Returns:
            预测的用电量（千瓦时）
        """
        # 获取该位置的历史数据
        start_date = target_date - timedelta(days=lookback_days)
        location_consumptions = self.tracker.get_consumption_by_location(
            location, start_date, target_date
        )
        
        if not location_consumptions:
            return 0.0
        
        # 按日期分组
        daily_consumption = defaultdict(float)
        for cons in location_consumptions:
            date_key = cons.timestamp.date()
            daily_consumption[date_key] += cons.power_kwh
        
        # 计算平均值
        if daily_consumption:
            avg_consumption = np.mean(list(daily_consumption.values()))
            # 周末调整
            if target_date.weekday() >= 5:
                avg_consumption *= 1.1
            return avg_consumption
        
        return 0.0
    
    def _get_historical_hourly_data(self, start_date: datetime,
                                   end_date: datetime) -> Dict[datetime.date, Dict[int, float]]:
        """获取历史小时数据"""
        historical_data = {}
        current_date = start_date
        
        while current_date < end_date:
            hourly_cons = self.tracker.get_consumption_by_hour(current_date)
            historical_data[current_date.date()] = hourly_cons
            current_date += timedelta(days=1)
        
        return historical_data
    
    def get_consumption_trend(self, days: int = 7) -> Dict[str, float]:
        """
        获取用电量趋势
        
        Args:
            days: 天数
        
        Returns:
            趋势数据 {"date": consumption}
        """
        trend = {}
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=i)
            consumption = self.tracker.get_total_consumption(
                datetime.combine(date.date(), datetime.min.time()),
                datetime.combine(date.date(), datetime.max.time())
            )
            trend[date.strftime("%Y-%m-%d")] = consumption
        
        return trend

