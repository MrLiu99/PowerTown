"""generative_agents.power.agent_power - 智能体用电行为集成"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from .equipment import EquipmentManager
from .consumption import PowerConsumptionTracker
from ..prompt.scratch import PowerScratch


class AgentPowerBehavior:
    """智能体用电行为管理"""
    
    def __init__(self, agent_name: str, location: str, 
                 equipment_manager: EquipmentManager,
                 consumption_tracker: PowerConsumptionTracker,
                 default_equipments: List[str] = None,
                 electricity_profile: Dict = None,
                 llm_model=None,
                currently: str = ""):
        """
        初始化智能体用电行为
        
        Args:
            agent_name: 智能体名称
            location: 智能体所在位置（如：小区1-101、工厂A车间等）
            equipment_manager: 设备管理器
            consumption_tracker: 用电量跟踪器
            default_equipments: 默认使用的设备列表
            electricity_profile: 电力配置文件，包含典型设备、高峰时段等信息
        """
        self.agent_name = agent_name
        self.location = location
        self.equipment_manager = equipment_manager
        self.consumption_tracker = consumption_tracker
        self.default_equipments = default_equipments or []
        self.electricity_profile = electricity_profile or {}
        self.llm_model = llm_model  # 存储 LLM 模型实例
        self.currently = currently
        
        # 初始化 PowerScratch
        self.power_scratch = PowerScratch(agent_name, currently, {})

        # 初始化活动-设备映射（用于回退）
        self.activity_equipment_map = self._init_activity_equipment_map()
        
        # 验证LLM模型是否可用
        if self.llm_model is None:
            print(f"[WARNING] Agent {agent_name}: LLM model is None, will use rule-based fallback")
        else:
            print(f"[INFO] Agent {agent_name}: LLM model initialized successfully")
    
    def _init_activity_equipment_map(self) -> Dict[str, List[str]]:
        """初始化默认活动到设备的映射（回退用）"""
        return {
            "做饭": ["电饭煲", "微波炉", "电热水壶"],
            "洗衣服": ["洗衣机"],
            "看电视": ["电视"],
            "工作": ["电脑"],
            "休息": ["照明", "电视"],
            "睡觉": [],
            "购物": ["超市照明"],
            "喝咖啡": ["咖啡机"],
            "喝酒": ["酒吧照明"],
        }
    
    def get_peak_hours(self) -> List[int]:
        """获取用电高峰时段"""
        return self.electricity_profile.get("peak_hours", [18, 19, 20])
    
    def get_energy_awareness(self) -> str:
        """获取节能意识水平"""
        return self.electricity_profile.get("energy_awareness", "medium")
    
    def get_flexible_loads(self) -> List[str]:
        """获取可灵活调整的电器"""
        return self.electricity_profile.get("flexible_loads", [])

    def participates_in_dr(self) -> bool:
        """是否参与需求响应"""
        return self.electricity_profile.get("participates_in_dr", False)
    
    def is_peak_hour(self, hour: int) -> bool:
        """判断是否是高峰时段"""
        from .consumption import PowerConsumption
        return PowerConsumption.get_price_period(hour) == 'peak'
    
    def is_valley_hour(self, hour: int) -> bool:
        """判断是否是谷时段"""
        from .consumption import PowerConsumption
        return PowerConsumption.get_price_period(hour) == 'valley'
    
    def should_postpone_activity(self, activity: str, equipment_list: List[Dict], hour: int) -> List[Dict]:
        """
        根据节能意识和电价时段判断是否应该推迟某些用电活动
        
        Args:
            activity: 活动描述
            equipment_list: 设备列表
            hour: 当前小时
            
        Returns:
            需要推迟的设备列表
        """
        # 如果节能意识不高，不推迟任何活动
        if self.get_energy_awareness() != "high":
            return []
        
        # 如果不是高峰时段，不推迟任何活动
        if not self.is_peak_hour(hour):
            return []
        
        # 定义高耗能且可推迟的设备
        high_energy_postponable = [
            "洗衣机", "烘干机", "洗碗机", "电热水器", 
            "游戏机", "直播设备", "电视"
        ]
        
        # 定义必要且不可推迟的设备
        essential_equipment = [
            "照明", "冰箱", "路由器", "网络设备"
        ]
        
        postponed = []
        for equipment_info in equipment_list:
            if isinstance(equipment_info, dict) and "name" in equipment_info:
                equipment_name = equipment_info["name"]
            else:
                equipment_name = equipment_info
            
            # 如果是高耗能且可推迟的设备，则推迟
            if equipment_name in high_energy_postponable:
                postponed.append(equipment_info)
            # 如果是必要设备，则不推迟
            elif equipment_name in essential_equipment:
                continue
            # 其他设备，根据功率判断
            else:
                from .equipment import Equipment
                equipment = self.equipment_manager.get_equipment(equipment_name)
                if equipment and equipment.power_rating > 1000:  # 功率大于1kW的设备考虑推迟
                    postponed.append(equipment_info)
        
        return postponed


    def _call_llm(self, prompt: str) -> str:
        """调用大模型获取响应"""
        if self.llm_model is None:
            print(f"[LLM Error] LLM model not provided for agent {self.agent_name}")
            return ""
        
        try:
            # 添加调试信息
            print(f"\n[LLM Debug] 为智能体 {self.agent_name} 调用LLM选择电器...")
            print(f"[LLM Debug] LLM模型类型: {type(self.llm_model)}")
            print(f"[LLM Debug] 提示词长度: {len(prompt)} 字符")
                        
            # 实际调用
            print(f"[LLM Debug] 进行实际调用...")
            response = self.llm_model.completion(
                prompt=prompt,
                retry=3,
                caller="power_appliance_selection"
            )
            
            print(f"[LLM Debug] LLM响应类型: {type(response)}")
            print(f"[LLM Debug] LLM响应内容: {response}")
            return response or ""
        except Exception as e:
            import traceback
            print(f"[LLM Error] Failed to call LLM: {e}")
            print(f"[LLM Error] 异常类型: {type(e).__name__}")
            print(f"[LLM Error] 异常详情: {str(e)}")
            print(f"[LLM Error] 堆栈跟踪:\n{traceback.format_exc()}")
            return ""

    def get_equipments_for_activity(self, activity: str, location: str = None, plan: Dict = None) -> List[Dict]:
        """
        根据活动、位置和计划获取使用的设备列表及使用时间
        优先使用 LLM 决策，失败则回退到规则映射
        
        Returns:
            List[Dict]: 设备字典列表，每个字典包含 name 和 duration_minutes
        """
        if location is None:
            location = self.location

        # === 第一阶段：尝试使用 LLM 决策 ===
        try:
            # 获取当前时间（假设你有全局 timer）
            from ..utils import get_timer
            timer = get_timer()
            current_time = timer.get_date().strftime("%Y-%m-%d %H:%M")
        except Exception:
            current_time = "未知时间"

        user_preferences = str({
            "energy_awareness": self.get_energy_awareness(),
            "flexible_loads": self.get_flexible_loads(),
            "peak_hours": self.get_peak_hours()
        })

        context = self.electricity_profile.get("context", self.currently)
        
        # 添加计划信息到上下文
        if plan:
            plan_info = f"当前计划: {plan.get('description', '')}"
            if plan.get('start_time') is not None:
                plan_info += f", 开始时间: {plan.get('start_time')}"
            if plan.get('duration'):
                plan_info += f", 持续时间: {plan.get('duration')}分钟"
            context = f"{context}\n{plan_info}"

        # 获取当前位置的可用设备
        available_devices = list(self.equipment_manager.equipments.keys())

        # 构建 LLM 提示
        prompt_info = self.power_scratch.prompt_select_appliances_for_activity(
            activity=activity,
            current_sector=location,
            current_time=current_time,
            user_preferences=user_preferences,
            context=context,
            available_devices=available_devices
        )

        print(f"[Prompt Debug] 完整提示词:\n{prompt_info['prompt']}")

        # 调用 LLM
        llm_response = self._call_llm(prompt_info["prompt"])
        
        # 打印LLM原始响应，方便调试
        print(f"\n[LLM Response Debug] 智能体 {self.agent_name} 的LLM原始响应:")
        print(f"[LLM Response Debug] {llm_response}")

        # 解析响应
        devices_from_llm = prompt_info["callback"](llm_response)
        
        # 打印解析后的设备列表，方便调试
        print(f"[LLM Response Debug] 解析后的设备列表: {devices_from_llm}")
        
        # 检查是否有推迟使用的设备
        postponed_devices = []
        if isinstance(devices_from_llm, dict) and "devices" in devices_from_llm:
            actual_devices = devices_from_llm["devices"]
            postponed_devices = devices_from_llm.get("postponed", [])
        else:
            actual_devices = devices_from_llm

        # 验证并返回
        if actual_devices:
            # 现在actual_devices已经是包含name和duration_minutes的字典列表
            valid_devices = []
            for d in actual_devices:
                device_name = d["name"] if isinstance(d, dict) else d
                if device_name in self.equipment_manager.equipments:
                    if isinstance(d, dict):
                        valid_devices.append(d)
                    else:
                        # 兼容旧格式，添加默认使用时间
                        valid_devices.append({
                            "name": d,
                            "duration_minutes": 30  # 默认30分钟
                        })
            
            # 记录推迟使用的设备
            if postponed_devices:
                postponed_info = []
                for p in postponed_devices:
                    if isinstance(p, dict):
                        name = p.get("name", "未知设备")
                        reason = p.get("reason", "电价高峰")
                    else:
                        name = p
                        reason = "电价高峰"
                    postponed_info.append(f"{name}({reason})")
                print(f"[Agent Power] {self.agent_name} 推迟使用设备: {', '.join(postponed_info)}")
            
            if valid_devices:
                return valid_devices

        # === 第二阶段：回退到规则逻辑 ===
        # 商业场所特殊处理
        if "咖啡馆" in location or "咖啡" in location:
            if any(kw in activity for kw in ["咖啡", "喝", "用餐"]):
                return [
                    {"name": "咖啡馆照明", "duration_minutes": 60},
                    {"name": "咖啡机", "duration_minutes": 20},
                    {"name": "咖啡馆空调", "duration_minutes": 60}
                ]
            return [
                {"name": "咖啡馆照明", "duration_minutes": 60},
                {"name": "咖啡馆空调", "duration_minutes": 60}
            ]
        if "酒吧" in location:
            if "喝" in activity:
                return [
                    {"name": "酒吧照明", "duration_minutes": 120},
                    {"name": "酒吧音响", "duration_minutes": 120},
                    {"name": "酒吧空调", "duration_minutes": 120}
                ]
            return [
                {"name": "酒吧照明", "duration_minutes": 120},
                {"name": "酒吧空调", "duration_minutes": 120}
            ]
        if "超市" in location or "市场" in location:
            if any(kw in activity for kw in ["购物", "购买"]):
                return [
                    {"name": "超市照明", "duration_minutes": 120},
                    {"name": "超市冷柜", "duration_minutes": 120},
                    {"name": "超市空调", "duration_minutes": 120}
                ]
            return [
                {"name": "超市照明", "duration_minutes": 120},
                {"name": "超市空调", "duration_minutes": 120}
            ]
        if "公园" in location:
            return [{"name": "公共照明", "duration_minutes": 60}]

        # 活动关键词匹配
        for key, equipments in self.activity_equipment_map.items():
            if key in activity:
                # 过滤只保留实际存在的设备，并添加默认使用时间
                return [
                    {"name": e, "duration_minutes": 30} 
                    for e in equipments if e in self.equipment_manager.equipments
                ]

        # 最终回退
        if self.default_equipments:
            return [
                {"name": e, "duration_minutes": 30} 
                for e in self.default_equipments if e in self.equipment_manager.equipments
            ]
        
        if "照明" in self.equipment_manager.equipments:
            return [{"name": "照明", "duration_minutes": 30}]
        elif available_devices:
            return [{"name": available_devices[0], "duration_minutes": 30}]
        else:
            return [{"name": "照明", "duration_minutes": 30}]

    def record_consumption(
        self,
        activity: str,
        hour: int,
        is_weekend: bool = False,
        duration_hours: float = 1.0,
        location: Optional[str] = None
    ) -> float:
        """记录用电行为并计算消耗"""
        if location is None:
            location = self.location

        # 获取设备列表及使用时间（现在由 LLM + 回退机制决定）
        equipment_list = self.get_equipments_for_activity(activity, location)
        
        # 提取设备名称列表（兼容旧格式）
        equipment_names = []
        if equipment_list:
            for item in equipment_list:
                if isinstance(item, dict) and "name" in item:
                    equipment_names.append(item["name"])
                else:
                    # 兼容旧格式（字符串）
                    equipment_names.append(item)

        # 计算用电量
        total_consumption = self.consumption_tracker.calculate_consumption_with_durations(
            agent_name=self.agent_name,
            location=location,
            activity=activity,
            equipment_list=equipment_list,  # 传递完整的设备列表，包含使用时间
            hour=hour,
            is_weekend=is_weekend,
            usage_factor=1.0,  # 默认使用系数
            duration_hours=duration_hours,
            electricity_profile=self.electricity_profile
        )

        return total_consumption

    def get_daily_consumption(self, date: datetime = None) -> float:
        """获取智能体一天的用电量"""
        if date is None:
            # 获取模拟器当前时间
            from ..utils import get_timer
            timer = get_timer()
            date = timer.get_date()
        
        start_time = datetime.combine(date.date(), datetime.min.time())
        end_time = datetime.combine(date.date(), datetime.max.time())
        
        consumptions = self.consumption_tracker.get_consumption_by_agent(
            self.agent_name, start_time, end_time
        )
        
        return sum(cons.power_kwh for cons in consumptions)