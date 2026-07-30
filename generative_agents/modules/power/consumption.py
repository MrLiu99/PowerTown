"""generative_agents.power.consumption - 用电量计算和跟踪"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from .equipment import Equipment, EquipmentManager


class PowerConsumption:
    """用电量记录"""
    
    # 峰谷电价定义
    PEAK_HOURS = [(8, 12), (18, 22)]  # 高峰时段：8:00-12:00，18:00-22:00
    FLAT_HOURS = [(12, 18)]  # 平时段：12:00-18:00
    VALLEY_HOURS = [(22, 24), (0, 8)]  # 谷时段：22:00-24:00，0:00-8:00
    
    PEAK_PRICE = 1.2  # 高峰电价：1.2元/度
    FLAT_PRICE = 1.0  # 平段电价：1.0元/度
    VALLEY_PRICE = 0.6  # 谷电价：0.6元/度
    
    @classmethod
    def get_electricity_price(cls, hour: int) -> float:
        """获取指定小时的电价
        
        Args:
            hour: 小时（0-23）
            
        Returns:
            电价（元/度）
        """
        # 检查是否在高峰时段
        for start, end in cls.PEAK_HOURS:
            if start <= hour < end:
                return cls.PEAK_PRICE
        
        # 检查是否在平时段
        for start, end in cls.FLAT_HOURS:
            if start <= hour < end:
                return cls.FLAT_PRICE
        
        # 否则是谷时段
        return cls.VALLEY_PRICE
    
    @classmethod
    def get_price_period(cls, hour: int) -> str:
        """获取指定小时的电价时段
        
        Args:
            hour: 小时（0-23）
            
        Returns:
            电价时段：'peak'（高峰）、'flat'（平段）或'valley'（谷段）
        """
        # 检查是否在高峰时段
        for start, end in cls.PEAK_HOURS:
            if start <= hour < end:
                return 'peak'
        
        # 检查是否在平时段
        for start, end in cls.FLAT_HOURS:
            if start <= hour < end:
                return 'flat'
        
        # 否则是谷时段
        return 'valley'
    
    def __init__(self, timestamp: datetime, agent_name: str, location: str,
                 equipment: str, power_kwh: float, activity: str = "", duration_minutes: float = 30.0):
        """
        初始化用电量记录
        
        Args:
            timestamp: 时间戳
            agent_name: 智能体名称
            location: 位置（如：小区1-101、工厂A车间、学校教学楼等）
            equipment: 设备名称
            power_kwh: 用电量（千瓦时）
            activity: 活动描述
            duration_minutes: 设备使用持续时间（分钟），默认30分钟
        """
        self.timestamp = timestamp
        self.agent_name = agent_name
        self.location = location
        self.equipment = equipment
        self.power_kwh = power_kwh
        self.activity = activity
        self.duration_minutes = duration_minutes
        self.hour = timestamp.hour
        self.price = self.get_electricity_price(self.hour)
        self.cost = self.power_kwh * self.price  # 电费成本
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.strftime("%Y%m%d-%H:%M:%S"),
            "agent_name": self.agent_name,
            "location": self.location,
            "equipment": self.equipment,
            "power_kwh": self.power_kwh,
            "activity": self.activity,
            "duration_minutes": self.duration_minutes,
            "hour": self.hour,
            "price": self.price,
            "cost": self.cost
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PowerConsumption":
        """从字典创建用电量记录"""
        # 创建基本对象
        consumption = cls(
            timestamp=datetime.strptime(data["timestamp"], "%Y%m%d-%H:%M:%S"),
            agent_name=data["agent_name"],
            location=data["location"],
            equipment=data["equipment"],
            power_kwh=data["power_kwh"],
            activity=data.get("activity", ""),
            duration_minutes=data.get("duration_minutes", 30.0)  # 向后兼容，默认30分钟
        )
        
        # 如果字典中包含价格和成本信息，则使用它们
        # 这是为了向后兼容旧数据
        if "price" in data:
            consumption.price = data["price"]
        if "cost" in data:
            consumption.cost = data["cost"]
            
        return consumption


class PowerConsumptionTracker:
    """用电量跟踪器"""
    
    def __init__(self, storage_root: str, equipment_manager: EquipmentManager):
        """
        初始化用电量跟踪器
        
        Args:
            storage_root: 存储根目录
            equipment_manager: 设备管理器
        """
        self.storage_root = storage_root
        self.equipment_manager = equipment_manager
        self.consumptions: List[PowerConsumption] = []
        os.makedirs(storage_root, exist_ok=True)
    
    def calculate_consumption(self, agent_name: str, location: str, 
                             activity: str, equipment_names: List[str],
                             hour: int, is_weekend: bool = False,
                             usage_factor: float = 1.0, duration_hours: float = 1.0,
                             electricity_profile: Dict = None, 
                             simulation_time: datetime = None) -> float:
        """
        计算用电量
        
        Args:
            agent_name: 智能体名称
            location: 位置
            activity: 活动描述
            equipment_names: 使用的设备名称列表
            hour: 当前小时（0-23）
            is_weekend: 是否为周末
            usage_factor: 使用系数
            duration_hours: 使用时长（小时）
            electricity_profile: 电力配置文件
        
        Returns:
            总用电量（千瓦时）
        """
        total_consumption = 0.0
        # 使用模拟器时间，如果没有提供则使用系统时间（作为后备）
        timestamp = simulation_time if simulation_time is not None else datetime.now()
        
        # 如果没有设备，返回0
        if not equipment_names:
            return 0.0
        
        # 根据electricity_profile调整使用系数
        adjusted_usage_factor = usage_factor
        if electricity_profile:
            # 检查是否是高峰时段
            peak_hours = electricity_profile.get("peak_hours", [])
            if hour in peak_hours:
                # 高峰时段使用系数可能更高
                adjusted_usage_factor *= 1.2
            
            # # 根据节能意识调整使用系数
            # energy_awareness = electricity_profile.get("energy_awareness", "medium")
            # if energy_awareness == "high":
            #     adjusted_usage_factor *= 0.8  # 节能意识高，用电量少
            # elif energy_awareness == "low":
            #     adjusted_usage_factor *= 1.2  # 节能意识低，用电量多
        
        for eq_name in equipment_names:
            equipment = self.equipment_manager.get_equipment(eq_name)
            if equipment:
                power_kwh = equipment.get_power_consumption(
                    hour, is_weekend, adjusted_usage_factor, duration_hours
                )
                # 创建用电量记录，传入默认持续时间30分钟
                consumption = PowerConsumption(
                    timestamp=timestamp,
                    agent_name=agent_name,
                    location=location,
                    equipment=eq_name,
                    power_kwh=power_kwh,
                    activity=activity,
                    duration_minutes=30.0  # 默认30分钟
                )
                self.consumptions.append(consumption)
                total_consumption += power_kwh
        
        return total_consumption
    
    def calculate_consumption_with_durations(self, agent_name: str, location: str, 
                                           activity: str, equipment_list: List[Dict],
                                           hour: int, is_weekend: bool = False,
                                           usage_factor: float = 1.0, duration_hours: float = 1.0,
                                           electricity_profile: Dict = None, 
                                           simulation_time: datetime = None) -> float:
        """
        计算用电量（考虑每个设备的具体使用时间）
        
        Args:
            agent_name: 智能体名称
            location: 位置
            activity: 活动描述
            equipment_list: 设备列表，每个元素包含name和duration_minutes
            hour: 当前小时（0-23）
            is_weekend: 是否为周末
            usage_factor: 使用系数
            duration_hours: 活动总时长（小时）
            electricity_profile: 电力配置文件
            simulation_time: 模拟时间
        
        Returns:
            总用电量（千瓦时）
        """
        total_consumption = 0.0
        # 使用模拟器时间，如果没有提供则使用系统时间（作为后备）
        timestamp = simulation_time if simulation_time is not None else datetime.now()
        
        # 如果没有设备，返回0
        if not equipment_list:
            return 0.0
        
        # 根据electricity_profile调整使用系数
        adjusted_usage_factor = usage_factor
        if electricity_profile:
            # 检查是否是高峰时段
            peak_hours = electricity_profile.get("peak_hours", [])
            if hour in peak_hours:
                # 高峰时段使用系数可能更高
                adjusted_usage_factor *= 1
        
        for equipment_info in equipment_list:
            # 处理新旧格式
            if isinstance(equipment_info, dict) and "name" in equipment_info:
                equipment_name = equipment_info["name"]
                # 获取设备使用时间（分钟），默认30分钟
                duration_minutes = equipment_info.get("duration_minutes", 30)
                # 转换为小时
                equipment_duration_hours = duration_minutes / 60.0
                # 确保设备使用时间不超过活动总时间
                equipment_duration_hours = min(equipment_duration_hours, duration_hours)

            else:
                # 兼容旧格式（字符串）
                equipment_name = equipment_info
                duration_minutes = 30  # 默认30分钟
            
            # 转换为小时
            equipment_duration_hours = duration_minutes / 60.0
            
            # 确保设备使用时间不超过活动总时间
            equipment_duration_hours = min(equipment_duration_hours, duration_hours)
            
            equipment = self.equipment_manager.get_equipment(equipment_name)
            if equipment:
                power_kwh = equipment.get_power_consumption(
                    hour, is_weekend, adjusted_usage_factor, equipment_duration_hours
                )
                # 创建用电量记录，传入设备使用持续时间
                consumption = PowerConsumption(
                    timestamp=timestamp,
                    agent_name=agent_name,
                    location=location,
                    equipment=equipment_name,
                    power_kwh=power_kwh,
                    activity=activity,
                    duration_minutes=duration_minutes
                )
                self.consumptions.append(consumption)
                total_consumption += power_kwh
        
        return total_consumption
    
    def get_consumption_by_location(self, location: str, 
                                   start_time: datetime = None,
                                   end_time: datetime = None) -> List[PowerConsumption]:
        """根据位置获取用电量记录"""
        results = []
        for cons in self.consumptions:
            if cons.location == location:
                if start_time and cons.timestamp < start_time:
                    continue
                if end_time and cons.timestamp > end_time:
                    continue
                results.append(cons)
        return results
    
    def get_consumption_by_agent(self, agent_name: str,
                                 start_time: datetime = None,
                                 end_time: datetime = None) -> List[PowerConsumption]:
        """根据智能体获取用电量记录"""
        results = []
        for cons in self.consumptions:
            if cons.agent_name == agent_name:
                if start_time and cons.timestamp < start_time:
                    continue
                if end_time and cons.timestamp > end_time:
                    continue
                results.append(cons)
        return results
    
    def get_total_consumption(self, start_time: datetime = None,
                             end_time: datetime = None) -> float:
        """获取总用电量"""
        total = 0.0
        for cons in self.consumptions:
            if start_time and cons.timestamp < start_time:
                continue
            if end_time and cons.timestamp > end_time:
                continue
            total += cons.power_kwh
        return total
    
    def get_consumption_by_hour(self, date: datetime = None) -> Dict[int, float]:
        """按小时统计用电量"""
        if date is None:
            date = datetime.now()
        
        hourly_consumption = defaultdict(float)
        for cons in self.consumptions:
            if cons.timestamp.date() == date.date():
                hour = cons.timestamp.hour
                hourly_consumption[hour] += cons.power_kwh
        
        return dict(hourly_consumption)
    
    def get_consumption_by_price_period(self, date: datetime = None) -> Dict[str, float]:
        """按电价时段统计用电量"""
        if date is None:
            date = datetime.now()
        
        period_consumption = defaultdict(float)
        for cons in self.consumptions:
            if cons.timestamp.date() == date.date():
                period = PowerConsumption.get_price_period(cons.hour)
                period_consumption[period] += cons.power_kwh
        
        return dict(period_consumption)
    
    def get_total_cost(self, start_time: datetime = None,
                      end_time: datetime = None) -> float:
        """获取总电费成本"""
        total_cost = 0.0
        for cons in self.consumptions:
            if start_time and cons.timestamp < start_time:
                continue
            if end_time and cons.timestamp > end_time:
                continue
            total_cost += cons.cost
        return total_cost
    
    def get_cost_by_price_period(self, date: datetime = None) -> Dict[str, float]:
        """按电价时段统计电费成本"""
        if date is None:
            date = datetime.now()
        
        period_cost = defaultdict(float)
        for cons in self.consumptions:
            if cons.timestamp.date() == date.date():
                period = PowerConsumption.get_price_period(cons.hour)
                period_cost[period] += cons.cost
        
        return dict(period_cost)
    
    def save_to_file(self, filename: str = "power_consumption.json"):
        """保存用电量记录到文件"""
        filepath = os.path.join(self.storage_root, filename)
        data = {
            "consumptions": [cons.to_dict() for cons in self.consumptions]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filename: str = "power_consumption.json"):
        """从文件加载用电量记录"""
        filepath = os.path.join(self.storage_root, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.consumptions = [
                    PowerConsumption.from_dict(cons_data)
                    for cons_data in data.get("consumptions", [])
                ]