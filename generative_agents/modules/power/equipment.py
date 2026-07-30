"""generative_agents.power.equipment - 用电设备管理"""

import json
import os
from typing import Dict, List, Optional


class Equipment:
    """用电设备类"""
    
    def __init__(self, name: str, power_rating: float, category: str, 
                 usage_pattern: Dict = None, description: str = ""):
        """
        初始化用电设备
        
        Args:
            name: 设备名称
            power_rating: 额定功率（瓦特）
            category: 设备类别（如：家用电器、工业设备、办公设备等）
            usage_pattern: 使用模式，如 {"work_hours": [9, 18], "weekend_factor": 0.8}
            description: 设备描述
        """
        self.name = name
        self.power_rating = power_rating  # 瓦特
        self.category = category
        self.usage_pattern = usage_pattern or {}
        self.description = description
    
    def get_power_consumption(self, hour: int, is_weekend: bool = False, 
                              usage_factor: float = 1.0, duration_hours: float = 1.0) -> float:
        """
        获取设备在特定时间的用电量（千瓦时）
        
        Args:
            hour: 当前小时（0-23）
            is_weekend: 是否为周末
            usage_factor: 使用系数（0-1），表示设备使用强度
            duration_hours: 使用时长（小时），默认1小时
        
        Returns:
            用电量（千瓦时）
        """
        # 检查使用模式
        work_hours = self.usage_pattern.get("work_hours", [0, 24])
        if len(work_hours) == 2:
            start_hour, end_hour = work_hours
            if start_hour <= hour < end_hour:
                base_factor = 1.0
            else:
                base_factor = self.usage_pattern.get("off_hours_factor", 0.1)
        else:
            base_factor = 1.0
        
        # 周末因子
        if is_weekend:
            base_factor *= self.usage_pattern.get("weekend_factor", 1.0)
        
        # 计算实际用电量（千瓦时）= 功率(kW) × 时间因子 × 使用系数 × 持续时间
        power_kw = self.power_rating / 1000.0  # 转换为千瓦
        consumption = power_kw * base_factor * usage_factor * duration_hours
        
        return consumption
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "power_rating": self.power_rating,
            "category": self.category,
            "usage_pattern": self.usage_pattern,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Equipment":
        """从字典创建设备"""
        return cls(
            name=data["name"],
            power_rating=data["power_rating"],
            category=data["category"],
            usage_pattern=data.get("usage_pattern", {}),
            description=data.get("description", "")
        )


class EquipmentManager:
    """设备管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化设备管理器
        
        Args:
            config_path: 设备配置文件路径
        """
        self.equipments: Dict[str, Equipment] = {}
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
        else:
            self._init_default_equipments()
    
    def _init_default_equipments(self):
        """初始化默认设备配置"""
        # 家用电器
        self.add_equipment(Equipment("空调", 1500, "家用电器", 
            {"work_hours": [8, 23], "off_hours_factor": 0.3, "weekend_factor": 1.2}, 
            "家用空调，夏季使用频繁"))
        
        self.add_equipment(Equipment("冰箱", 150, "家用电器", 
            {"work_hours": [0, 24], "off_hours_factor": 1.0, "weekend_factor": 1.0}, 
            "冰箱24小时运行"))

        # self.add_equipment(Equipment("冰箱", 63.7, "家用电器", 
        #     {"work_hours": [0, 24], "off_hours_factor": 1.0, "weekend_factor": 1.0}, 
        #     "冰箱24小时运行"))

        # self.add_equipment(Equipment("冰柜1", 71.9, "家用电器", 
        #     {"work_hours": [0, 24], "off_hours_factor": 1.0, "weekend_factor": 1.0}, 
        #     "冰柜1，24小时运行"))

        # self.add_equipment(Equipment("冰柜2", 758.9, "家用电器", 
        #     {"work_hours": [12, 16], "off_hours_factor": 0.1, "weekend_factor": 1.0}, 
        #     "冰柜2，主要在中午运行"))
        
        self.add_equipment(Equipment("洗衣机", 2000, "家用电器", 
            {"work_hours": [8, 22], "off_hours_factor": 0.0, "weekend_factor": 1.5}, 
            "洗衣机，主要在白天使用"))

        # self.add_equipment(Equipment("洗衣机", 777.1, "家用电器", 
        #     {"work_hours": [10, 13], "off_hours_factor": 0.0, "weekend_factor": 1.5}, 
        #     "洗衣机，主要在上午使用"))

        # self.add_equipment(Equipment("滚筒式烘干机", 2214.9, "家用电器", 
        #     {"work_hours": [2, 5], "off_hours_factor": 0.1, "weekend_factor": 1.0}, 
        #     "滚筒式烘干机，主要在凌晨运行"))
        
        # self.add_equipment(Equipment("洗碗机", 29.1, "家用电器", 
        #     {"work_hours": [18, 21], "off_hours_factor": 0.1, "weekend_factor": 1.0}, 
        #     "洗碗机，主要在晚餐时间使用"))
        
        # self.add_equipment(Equipment("电视", 77.9, "家用电器", 
        #     {"work_hours": [18, 23], "off_hours_factor": 0.1, "weekend_factor": 1.5}, 
        #     "电视，主要在晚上观看"))
        
        
        self.add_equipment(Equipment("电视", 150, "家用电器", 
            {"work_hours": [18, 23], "off_hours_factor": 0.1, "weekend_factor": 1.5}, 
            "电视，主要在晚上观看"))
        
        self.add_equipment(Equipment("电脑", 200, "家用电器", 
            {"work_hours": [9, 22], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "个人电脑，工作和娱乐使用"))

        self.add_equipment(Equipment("电脑", 50, "家用电器", 
            {"work_hours": [9, 22], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "个人电脑，工作和娱乐使用"))

        self.add_equipment(Equipment("电暖器", 994.4, "家用电器", 
            {"work_hours": [0, 24], "off_hours_factor": 1.0, "weekend_factor": 1.0}, 
            "电暖器，全天运行"))
        
        self.add_equipment(Equipment("热水器", 2000, "家用电器", 
            {"work_hours": [6, 9], "off_hours_factor": 0.5, "weekend_factor": 1.0}, 
            "电热水器，主要在早晨和晚上使用"))

        
        self.add_equipment(Equipment("照明", 100, "家用电器", 
            {"work_hours": [18, 23], "off_hours_factor": 0.3, "weekend_factor": 1.0}, 
            "室内照明"))
        
        # 工业设备
        self.add_equipment(Equipment("生产线设备", 50000, "工业设备", 
            {"work_hours": [8, 20], "off_hours_factor": 0.0, "weekend_factor": 0.0}, 
            "工厂生产线主要设备"))
        
        self.add_equipment(Equipment("空压机", 10000, "工业设备", 
            {"work_hours": [8, 20], "off_hours_factor": 0.0, "weekend_factor": 0.0}, 
            "工厂空压机"))
        
        self.add_equipment(Equipment("工业照明", 2000, "工业设备", 
            {"work_hours": [8, 20], "off_hours_factor": 0.0, "weekend_factor": 0.0}, 
            "工厂照明系统"))
        
        # 学校设备
        self.add_equipment(Equipment("教室照明", 800, "学校设备", 
            {"work_hours": [8, 17], "off_hours_factor": 0.0, "weekend_factor": 0.0}, 
            "教室照明系统"))
        
        self.add_equipment(Equipment("投影仪", 300, "学校设备", 
            {"work_hours": [8, 17], "off_hours_factor": 0.0, "weekend_factor": 0.0}, 
            "教室投影设备"))
        
        self.add_equipment(Equipment("电脑机房", 5000, "学校设备", 
            {"work_hours": [8, 21], "off_hours_factor": 0.1, "weekend_factor": 0.5}, 
            "学校计算机机房"))
        
        self.add_equipment(Equipment("实验室设备", 3000, "学校设备", 
            {"work_hours": [8, 18], "off_hours_factor": 0.1, "weekend_factor": 0.3}, 
            "实验室实验设备"))
        
        # 商业设备
        self.add_equipment(Equipment("商场照明", 5000, "商业设备", 
            {"work_hours": [9, 22], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "商场照明系统"))
        
        self.add_equipment(Equipment("电梯", 3000, "商业设备", 
            {"work_hours": [7, 22], "off_hours_factor": 0.3, "weekend_factor": 1.1}, 
            "商业建筑电梯"))
        
        # 咖啡馆设备
        self.add_equipment(Equipment("咖啡馆照明", 2000, "商业设备", 
            {"work_hours": [7, 22], "off_hours_factor": 0.3, "weekend_factor": 1.2}, 
            "咖啡馆照明系统"))
        
        self.add_equipment(Equipment("咖啡机", 1500, "商业设备", 
            {"work_hours": [7, 22], "off_hours_factor": 0.1, "weekend_factor": 1.3}, 
            "咖啡馆咖啡机"))
        
        self.add_equipment(Equipment("咖啡馆空调", 3000, "商业设备", 
            {"work_hours": [7, 22], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "咖啡馆空调系统"))
        
        # 酒吧设备
        self.add_equipment(Equipment("酒吧照明", 2500, "商业设备", 
            {"work_hours": [18, 2], "off_hours_factor": 0.2, "weekend_factor": 1.3}, 
            "酒吧照明系统"))
        
        self.add_equipment(Equipment("酒吧音响", 500, "商业设备", 
            {"work_hours": [18, 2], "off_hours_factor": 0.1, "weekend_factor": 1.3}, 
            "酒吧音响设备"))
        
        self.add_equipment(Equipment("酒吧空调", 3000, "商业设备", 
            {"work_hours": [18, 2], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "酒吧空调系统"))
        
        # 超市设备
        self.add_equipment(Equipment("超市照明", 4000, "商业设备", 
            {"work_hours": [8, 22], "off_hours_factor": 0.2, "weekend_factor": 1.2}, 
            "超市照明系统"))
        
        self.add_equipment(Equipment("超市冷柜", 5000, "商业设备", 
            {"work_hours": [8, 22], "off_hours_factor": 1.0, "weekend_factor": 1.0}, 
            "超市冷藏设备"))
        
        self.add_equipment(Equipment("超市空调", 4000, "商业设备", 
            {"work_hours": [8, 22], "off_hours_factor": 0.3, "weekend_factor": 1.2}, 
            "超市空调系统"))
        
        # 公共设施设备
        self.add_equipment(Equipment("公共照明", 800, "公共设施", 
            {"work_hours": [18, 23], "off_hours_factor": 0.4, "weekend_factor": 1.0}, 
            "公共区域照明"))
        
        self.add_equipment(Equipment("公共空调", 2000, "公共设施", 
            {"work_hours": [8, 22], "off_hours_factor": 0.3, "weekend_factor": 1.1}, 
            "公共区域空调"))
    
    def add_equipment(self, equipment: Equipment):
        """添加设备"""
        self.equipments[equipment.name] = equipment
    
    def get_equipment(self, name: str) -> Optional[Equipment]:
        """获取设备"""
        return self.equipments.get(name)
    
    def get_equipments_by_category(self, category: str) -> List[Equipment]:
        """根据类别获取设备列表"""
        return [eq for eq in self.equipments.values() if eq.category == category]
    
    def load_from_file(self, config_path: str):
        """从文件加载设备配置"""
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for eq_data in data.get("equipments", []):
                equipment = Equipment.from_dict(eq_data)
                self.add_equipment(equipment)
    
    def save_to_file(self, config_path: str):
        """保存设备配置到文件"""
        data = {
            "equipments": [eq.to_dict() for eq in self.equipments.values()]
        }
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)