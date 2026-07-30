"""generative_agents.power_post_process - 电力模块后处理工具

该模块用于在基础小镇运行后，单独执行电力模块，通过分析simulation.md文件
来生成与同步运行一致的电力消耗数据。

"""

# python power_post_process.py --simulation d:\Code\GenerativeAgents\generative_agents\results\compressed\4person\simulation.md --output d:\Code\GenerativeAgents\generative_agents\results\checkpoints\4person\power

# python power_post_process.py --simulation d:/Code/GenerativeAgents/generative_agents/results/compressed/7person/simulation.md --output d:\Code\GenerativeAgents\generative_agents\results\checkpoints\7person\power



import argparse
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from modules.power.equipment import EquipmentManager
from modules.power.consumption import PowerConsumptionTracker, PowerConsumption
from modules.model.llm_model import create_llm_model
from modules.prompt.scratch import PowerScratch


class SimulationParser:
    """解析simulation.md文件的类"""
    
    def __init__(self, simulation_file: str):
        """
        初始化解析器
        
        Args:
            simulation_file: simulation.md文件路径
        """
        self.simulation_file = simulation_file
        self.agent_profiles = {}
        self.activities = []
        print(f"[DEBUG] SimulationParser: 初始化，文件路径: {simulation_file}")
        self.parse_simulation()
        print(f"[DEBUG] SimulationParser: 解析完成，共找到 {len(self.agent_profiles)} 个智能体，{len(self.activities)} 条活动记录")
    
    def parse_simulation(self):
        """解析simulation.md文件"""
        print(f"[DEBUG] 开始解析simulation.md文件: {self.simulation_file}")
        
        try:
            with open(self.simulation_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[DEBUG] 文件读取成功，内容长度: {len(content)} 字符")
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {e}")
            raise
        
        # 解析基础人设
        print(f"[DEBUG] 开始解析智能体基础人设...")
        self._parse_agent_profiles(content)
        print(f"[DEBUG] 智能体基础人设解析完成，共 {len(self.agent_profiles)} 个智能体")
        
        # 解析活动记录
        print(f"[DEBUG] 开始解析活动记录...")
        self._parse_activities(content)
        print(f"[DEBUG] 活动记录解析完成，共 {len(self.activities)} 条活动")
    
    def _parse_agent_profiles(self, content: str):
        """解析智能体基础人设"""
        # 使用正则表达式匹配每个智能体的基础信息
        agent_pattern = r"## (.*?)\n\n年龄：(.*?)\n先天：(.*?)\n后天：(.*?)\n生活习惯：(.*?)\n当前状态：(.*?)"
        matches = re.findall(agent_pattern, content)
        
        print(f"[DEBUG] 找到 {len(matches)} 个智能体基础人设匹配")
        
        for i, match in enumerate(matches):
            name, age, innate, learned, lifestyle, currently = match
            self.agent_profiles[name] = {
                "name": name,
                "age": age,
                "innate": innate,
                "learned": learned,
                "lifestyle": lifestyle,
                "currently": currently,
                "electricity_profile": self._load_electricity_profile(name)
            }
        
        print(f"[DEBUG] 智能体列表: {list(self.agent_profiles.keys())}")
    
    def _load_electricity_profile(self, agent_name: str) -> Dict:
        """从agent.json文件中加载electricity_profile信息"""
        # 尝试从agent.json文件中读取electricity_profile
        agent_json_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
        
        if os.path.exists(agent_json_path):
            try:
                with open(agent_json_path, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
                    electricity_profile = agent_data.get("electricity_profile", {})
                    print(f"[DEBUG] 从 {agent_json_path} 加载electricity_profile: {electricity_profile}")
                    return electricity_profile
            except Exception as e:
                print(f"[WARNING] 无法加载 {agent_json_path}: {e}")
        else:
            print(f"[DEBUG] 未找到agent.json文件: {agent_json_path}")
        
        # 返回默认的electricity_profile
        return {
            "energy_awareness": "medium",
            "participates_in_dr": True
        }
    
    def _parse_activities(self, content: str):
        """解析活动记录"""
        # 按时间戳分割内容
        time_sections = re.split(r"# (\d{8}-\d{2}:\d{2})", content)
        
        print(f"[DEBUG] 按时间戳分割内容，共 {len(time_sections)} 个部分")
        
        time_section_count = 0
        for i in range(1, len(time_sections), 2):
            if i+1 < len(time_sections):
                timestamp_str = time_sections[i]
                section_content = time_sections[i+1]
                time_section_count += 1
                
                # 解析时间戳
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H:%M")
                    print(f"[DEBUG] 解析时间戳 {time_section_count}: {timestamp_str} -> {timestamp}")
                except ValueError as e:
                    print(f"[ERROR] 时间戳解析失败: {timestamp_str}, 错误: {e}")
                    continue
                
                # 分离活动记录和对话记录
                # 查找"## 对话记录："的位置，只处理之前的内容
                dialogue_start = section_content.find("## 对话记录：")
                if dialogue_start != -1:
                    activities_content = section_content[:dialogue_start]
                    dialogue_content = section_content[dialogue_start:]
                    print(f"[DEBUG] 时间段 {timestamp_str} 找到对话记录，只处理活动部分")
                else:
                    activities_content = section_content
                    dialogue_content = ""
                
                # 解析每个智能体的活动
                agent_activities = self._parse_agent_activities(activities_content, timestamp)
                print(f"[DEBUG] 时间段 {timestamp_str} 找到 {len(agent_activities)} 个活动")
                self.activities.extend(agent_activities)
        
        print(f"[DEBUG] 共解析 {time_section_count} 个时间段，{len(self.activities)} 个活动")
    
    def _parse_agent_activities(self, content: str, timestamp: datetime) -> List[Dict]:
        """解析特定时间段的智能体活动"""
        activities = []
        
        # 首先按智能体分割内容
        agent_sections = re.split(r"### ", content)
        # 第一个元素通常是空字符串或"活动记录："，跳过
        agent_sections = [s for s in agent_sections if s.strip()]
        
        print(f"[DEBUG] 时间段 {timestamp.strftime('%Y%m%d-%H:%M')} 找到 {len(agent_sections)} 个智能体段落")
        
        for i, section in enumerate(agent_sections):
            # 提取智能体名称（第一行）
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            name = lines[0].strip()
            
            # 跳过非智能体条目
            if not name or name.startswith("##") or "->" in name or "@" in name:
                continue
                
            location = ""
            activity = ""
            
            # 查找位置和活动
            for j, line in enumerate(lines[1:], 1):
                if line.startswith("位置："):
                    location = line.replace("位置：", "").strip()
                elif line.startswith("活动："):
                    # 活动可能跨越多行，收集所有后续行直到下一个智能体或时间戳
                    activity_lines = [line.replace("活动：", "").strip()]
                    # 收集后续非空行作为活动描述
                    for k in range(j+1, len(lines)):
                        if lines[k].strip() and not lines[k].startswith("###") and not lines[k].startswith("# "):
                            activity_lines.append(lines[k].strip())
                        else:
                            break
                    activity = " ".join(activity_lines)
                    break
            
            # 如果找到了位置和活动，添加到列表
            if name and location:
                activities.append({
                    "timestamp": timestamp,
                    "agent_name": name,
                    "location": location,
                    "activity": activity
                })
                
            #     # 打印前几个活动的详细信息用于调试
            #     if i < 3:  # 只打印前3个，避免日志过多
            #         print(f"[DEBUG] 活动 {len(activities)}: {name} 在 {location} 进行 {activity}")
            # else:
            #     print(f"[WARNING] 无法解析智能体活动，名称: '{name}', 位置: '{location}'")
        
        return activities


class PowerPostProcessor:
    """电力后处理器"""
    
    def __init__(self, simulation_file: str, output_dir: str, llm_config: Dict = None):
        """
        初始化电力后处理器
        
        Args:
            simulation_file: simulation.md文件路径
            output_dir: 输出目录
            llm_config: LLM配置
        """
        self.simulation_file = simulation_file
        self.output_dir = output_dir
        
        # 如果没有提供LLM配置，尝试使用默认配置
        if not llm_config:
            default_config_path = "data/config.json"
            if os.path.exists(default_config_path):
                print(f"[DEBUG] 使用默认LLM配置文件: {default_config_path}")
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    llm_config = config_data.get("agent", {}).get("think", {}).get("llm", {})
                    print(f"[DEBUG] 默认LLM配置: {llm_config}")
            else:
                print(f"[DEBUG] 未找到默认LLM配置文件: {default_config_path}")
                llm_config = {}
        else:
            print(f"[DEBUG] 使用提供的LLM配置")
        
        self.llm_config = llm_config
        
        # 初始化组件
        self.parser = SimulationParser(simulation_file)
        self.equipment_manager = EquipmentManager()
        self.consumption_tracker = PowerConsumptionTracker(output_dir, self.equipment_manager)
        
        # 初始化LLM模型（如果配置了）
        self.llm_model = None
        print(f"[DEBUG] 最终LLM配置: {self.llm_config}")
        
        if self.llm_config:
            try:
                print(f"[DEBUG] 尝试初始化LLM模型...")
                self.llm_model = create_llm_model(self.llm_config)
                print(f"[INFO] LLM模型初始化成功: {type(self.llm_model).__name__}")
                print(f"[DEBUG] LLM模型对象: {self.llm_model}")
            except Exception as e:
                print(f"[WARNING] LLM模型初始化失败: {e}，将使用规则回退")
                import traceback
                traceback.print_exc()
                self.llm_model = None
        else:
            print(f"[DEBUG] 未提供LLM配置，将使用规则回退")
        
        # 为每个智能体创建PowerScratch实例
        self.power_scratches = {}
        for name, profile in self.parser.agent_profiles.items():
            self.power_scratches[name] = PowerScratch(name, profile["currently"], profile)
        
        # 记录已加载的设备配置文件，避免重复加载
        self.loaded_config_files = set()
        
        # 记录推迟使用的设备信息
        self.postponed_devices = []
        
        # API调用次数统计
        self.api_call_count = 0
        
        # 设备使用历史跟踪（按智能体分组）
        # 格式：{agent_name: {device_name: {"last_used": timestamp, "usage_count": int, "total_duration": int, "end_time": timestamp, "is_active": bool}}}
        self.device_usage_history = {}
    
    def get_available_devices_for_location(self, location: str) -> List[str]:
        """根据位置获取可用设备列表"""
        # 首先尝试从环境配置文件加载设备列表
        location_devices = self._load_devices_from_location_config(location)
        if location_devices:
            return location_devices
        
        # 如果没有找到配置文件，使用默认规则
        return self._get_default_devices_for_location(location)
    
    def _load_devices_from_location_config(self, location: str) -> List[str]:
        """从位置配置文件加载设备列表"""
        # 设备配置文件基础路径
        equipment_base_path = "frontend/static/assets/village/equipment"
        
        # 按优先级排序的位置映射，更具体的位置优先匹配
        location_mappings = [
            ("刘氏家族的房子", "刘氏家族的房子.json"),
            ("吕布和貂蝉的家", "吕布和貂蝉的家.json"),
            ("李白的公寓+玫瑰酒吧", "李白的公寓+玫瑰酒吧.json"),
            ("欧阳娜的办公室", "欧阳娜的办公室.json"),
            ("欧阳娜的房间", "欧阳娜的房间.json"),
            ("杨贵妃的房间", "杨贵妃的房间.json"),
            ("吴三桂的公寓", "吴三桂的公寓.json"),
            ("李娜的公寓", "李娜的公寓.json"),
            ("电力小镇学院宿舍", "电力小镇学院宿舍.json"),
        ]
        
        # 检查是否有直接匹配（按优先级顺序）
        for location_key, filename in location_mappings:
            if location_key in location:
                config_path = os.path.join(equipment_base_path, filename)
                if os.path.exists(config_path):
                    print(f"[DEBUG] 匹配到位置: {location_key} -> {filename}")
                    return self._load_equipment_from_config(config_path)
        
        # 尝试通过位置关键词匹配配置文件
        location_keywords = [
            ("杨贵妃", "杨贵妃的房间.json"),
            ("吕布", "吕布和貂蝉的家.json"),
            ("貂蝉", "吕布和貂蝉的家.json"),
            ("吴三桂", "吴三桂的公寓.json"),
            ("李娜", "李娜的公寓.json"),
            ("宿舍", "电力小镇学院宿舍.json"),
            ("公寓", "吴三桂的公寓.json"),  # 默认使用吴三桂的公寓配置
            ("刘氏", "刘氏家族的房子.json"),
            ("刘备", "刘氏家族的房子.json"),
            ("刘禅", "刘氏家族的房子.json"),
            ("甘夫人", "刘氏家族的房子.json"),
            ("李白", "李白的公寓+玫瑰酒吧.json"),
            ("酒吧", "李白的公寓+玫瑰酒吧.json"),
            ("欧阳娜", "欧阳娜的房间.json"),
            ("办公室", "欧阳娜的房间.json"),
            ("工厂", "欧阳娜的房间.json"),
            ("工厂宿舍", "欧阳娜的房间.json"),
            # 可以继续添加更多关键词映射
        ]
        
        for keyword, filename in location_keywords:
            if keyword in location:
                config_path = os.path.join(equipment_base_path, filename)
                if os.path.exists(config_path):
                    print(f"[DEBUG] 通过关键词匹配到位置: {keyword} -> {filename}")
                    return self._load_equipment_from_config(config_path)
        
        # 如果没有找到匹配的配置文件，返回空列表，让调用者使用默认规则
        print(f"[DEBUG] 未找到匹配的配置文件，位置: {location}")
        return []
    
    def _load_equipment_from_config(self, config_path: str) -> List[str]:
        """从配置文件加载设备名称列表，并将设备动态添加到设备管理器中"""
        # 检查是否已经加载过这个配置文件
        if config_path in self.loaded_config_files:
            print(f"[DEBUG] 配置文件已加载过: {config_path}")
            # 返回设备管理器中已有的设备名称
            return [name for name in self.equipment_manager.equipments.keys() if self._is_equipment_from_config(name, config_path)]
        
        try:
            print(f"[DEBUG] 开始加载设备配置文件: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 提取设备名称列表
            device_names = []
            
            # 处理每个设备，将其添加到设备管理器中（如果不存在）
            for eq_config in config.get("equipments", []):
                name = eq_config.get("name")
                if not name:
                    continue
                    
                device_names.append(name)
                
                # 如果设备不在设备管理器中，则添加
                if name not in self.equipment_manager.equipments:
                    from modules.power.equipment import Equipment
                    
                    # 创建设备对象
                    equipment = Equipment(
                        name=name,
                        power_rating=eq_config.get("power_rating", 100),
                        category=eq_config.get("category", "未知"),
                        usage_pattern=eq_config.get("usage_pattern", {}),
                        description=eq_config.get("description", "")
                    )
                    
                    # 添加到设备管理器
                    self.equipment_manager.add_equipment(equipment)
                    print(f"[DEBUG] 动态添加设备到管理器: {name} (功率: {equipment.power_rating}W)")
                else:
                    print(f"[DEBUG] 设备已存在于管理器中: {name}")
            
            # 标记此配置文件已加载
            self.loaded_config_files.add(config_path)
            
            # 打印设备管理器中的设备数量
            print(f"[DEBUG] 配置文件加载完成，设备管理器中共有 {len(self.equipment_manager.equipments)} 个设备")
            
            return device_names
        except Exception as e:
            print(f"[ERROR] 加载设备配置文件失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_equipment_from_config(self, equipment_name: str, config_path: str) -> bool:
        """检查设备是否来自指定的配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for eq_config in config.get("equipments", []):
                if eq_config.get("name") == equipment_name:
                    return True
            return False
        except:
            return False
    
    def _get_default_devices_for_location(self, location: str) -> List[str]:
        """获取默认设备列表（基于位置关键词）"""
        available_devices = ["照明"]  # 默认设备
        
        # 家庭位置
        if any(keyword in location for keyword in ["房间", "卧室", "客厅", "厨房", "浴室", "家"]):
            home_devices = ["空调", "电视", "电脑", "热水器", "冰箱"]
            for device in home_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        # 商业位置
        if "咖啡馆" in location or "咖啡" in location:
            cafe_devices = ["咖啡馆照明", "咖啡机", "咖啡馆空调"]
            for device in cafe_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        if "酒吧" in location:
            bar_devices = ["酒吧照明", "酒吧音响", "酒吧空调"]
            for device in bar_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        if "超市" in location or "市场" in location:
            market_devices = ["超市照明", "超市冷柜", "超市空调"]
            for device in market_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        # 学校位置
        if "学院" in location or "学校" in location:
            school_devices = ["教室照明", "投影仪", "电脑机房"]
            for device in school_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        # 工厂位置
        if "工厂" in location:
            factory_devices = ["生产线设备", "空压机", "工业照明"]
            for device in factory_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        # 公共位置
        if "公园" in location:
            public_devices = ["公共照明"]
            for device in public_devices:
                if device in self.equipment_manager.equipments and device not in available_devices:
                    available_devices.append(device)
        
        return available_devices
    
    def _record_device_usage(self, agent_name: str, device_name: str, timestamp: datetime, duration_minutes: int):
        """
        记录设备使用历史
        
        Args:
            agent_name: 智能体名称
            device_name: 设备名称
            timestamp: 使用时间
            duration_minutes: 使用时长（分钟）
        """
        if agent_name not in self.device_usage_history:
            self.device_usage_history[agent_name] = {}
        
        if device_name not in self.device_usage_history[agent_name]:
            self.device_usage_history[agent_name][device_name] = {
                "last_used": timestamp,
                "usage_count": 0,
                "total_duration": 0,
                "end_time": None,
                "is_active": False
            }
        
        # 计算预计结束时间
        end_time = timestamp + timedelta(minutes=duration_minutes)
        
        # 更新使用记录
        self.device_usage_history[agent_name][device_name]["last_used"] = timestamp
        self.device_usage_history[agent_name][device_name]["usage_count"] += 1
        self.device_usage_history[agent_name][device_name]["total_duration"] += duration_minutes
        self.device_usage_history[agent_name][device_name]["end_time"] = end_time
        self.device_usage_history[agent_name][device_name]["is_active"] = True
        
        print(f"[DEBUG] 记录设备使用: {agent_name} 使用 {device_name} 于 {timestamp.strftime('%Y-%m-%d %H:%M')}, 时长 {duration_minutes}分钟, 预计结束时间: {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    def _get_device_usage_summary(self, agent_name: str, timestamp: datetime, hours_back: int = 2) -> str:
        """
        获取设备使用历史摘要，用于传递给LLM
        
        Args:
            agent_name: 智能体名称
            timestamp: 当前时间
            hours_back: 回溯多少小时的历史
            
        Returns:
            设备使用历史摘要字符串
        """
        if agent_name not in self.device_usage_history:
            return "今日尚未使用任何电器"
        
        # 首先检查正在使用的设备
        active_devices = self._get_active_devices(agent_name, timestamp)
        if active_devices:
            active_info = []
            for device_name in active_devices:
                device_info = self.device_usage_history[agent_name][device_name]
                end_time = device_info.get("end_time")
                if end_time:
                    remaining_minutes = int((end_time - timestamp).total_seconds() / 60)
                    active_info.append(f"{device_name}（预计还需{remaining_minutes}分钟结束）")
            
            if active_info:
                active_summary = "当前正在使用：" + "，".join(active_info) + "。"
            else:
                active_summary = ""
        else:
            active_summary = ""
        
        # 计算时间阈值
        time_threshold = timestamp - timedelta(hours=hours_back)
        
        # 筛选最近使用的设备（不包括正在使用的）
        recent_devices = []
        for device_name, usage_info in self.device_usage_history[agent_name].items():
            # 跳过正在使用的设备
            if self._is_device_active(agent_name, device_name, timestamp):
                continue
                
            if usage_info["last_used"] >= time_threshold:
                time_diff = (timestamp - usage_info["last_used"]).total_seconds() / 60  # 分钟
                recent_devices.append({
                    "name": device_name,
                    "last_used": usage_info["last_used"].strftime("%H:%M"),
                    "minutes_ago": int(time_diff),
                    "usage_count": usage_info["usage_count"],
                    "total_duration": usage_info["total_duration"]
                })
        
        if not recent_devices and not active_summary:
            return "今日尚未使用任何电器"
        
        # 生成最近使用设备的摘要
        summary_lines = []
        for device in recent_devices:
            if device["minutes_ago"] < 60:
                time_desc = f"{device['minutes_ago']}分钟前"
            else:
                hours = device['minutes_ago'] // 60
                time_desc = f"{hours}小时前"
            
            summary_lines.append(
                f"{device['name']}（{time_desc}使用过，今日共使用{device['usage_count']}次，总计{device['total_duration']}分钟）"
            )
        
        recent_summary = "，".join(summary_lines) + "。" if summary_lines else ""
        
        # 组合正在使用和最近使用的摘要
        if active_summary and recent_summary:
            return active_summary + " " + recent_summary
        elif active_summary:
            return active_summary
        else:
            return recent_summary
    
    def _is_device_active(self, agent_name: str, device_name: str, timestamp: datetime) -> bool:
        """
        检查设备是否正在使用中
        
        Args:
            agent_name: 智能体名称
            device_name: 设备名称
            timestamp: 当前时间
            
        Returns:
            True表示设备正在使用中，False表示设备未使用
        """
        if agent_name not in self.device_usage_history:
            return False
        
        if device_name not in self.device_usage_history[agent_name]:
            return False
        
        device_info = self.device_usage_history[agent_name][device_name]
        
        # 如果设备标记为活跃状态，检查是否已过预计结束时间
        if device_info.get("is_active", False):
            end_time = device_info.get("end_time")
            if end_time and timestamp < end_time:
                # 当前时间在预计结束时间之前，设备仍在使用中
                print(f"[DEBUG] 设备 {device_name} 仍在使用中，预计结束时间: {end_time.strftime('%Y-%m-%d %H:%M')}, 当前时间: {timestamp.strftime('%Y-%m-%d %H:%M')}")
                return True
            else:
                # 已过预计结束时间，标记为不活跃
                device_info["is_active"] = False
                print(f"[DEBUG] 设备 {device_name} 已过预计结束时间，标记为不活跃")
        
        return False
    
    def _get_active_devices(self, agent_name: str, timestamp: datetime) -> List[str]:
        """
        获取当前正在使用的设备列表
        
        Args:
            agent_name: 智能体名称
            timestamp: 当前时间
            
        Returns:
            正在使用的设备名称列表
        """
        if agent_name not in self.device_usage_history:
            return []
        
        active_devices = []
        for device_name, device_info in self.device_usage_history[agent_name].items():
            if self._is_device_active(agent_name, device_name, timestamp):
                active_devices.append(device_name)
        
        return active_devices
    
    def get_equipments_for_activity(self, agent_name: str, activity: str, location: str, timestamp: datetime) -> List[Dict]:
        """
        根据活动、位置和时间获取使用的设备列表及使用时间
        优先使用LLM决策，失败则回退到规则映射
        
        Returns:
            List[Dict]: 设备字典列表，每个字典包含name和duration_minutes
        """
        # 获取当前位置的可用设备
        available_devices = self.get_available_devices_for_location(location)
        
        # 过滤掉正在使用的设备
        active_devices = self._get_active_devices(agent_name, timestamp)
        if active_devices:
            # 从可用设备中移除正在使用的设备
            available_devices = [d for d in available_devices if d not in active_devices]
            print(f"[DEBUG] 过滤掉正在使用的设备: {active_devices}")
        
        current_time = timestamp.strftime("%Y-%m-%d %H:%M")
        print(f"[DEBUG] 为智能体 {agent_name} 选择设备，活动: {activity}, 位置: {location}, 时间: {current_time}")
        print(f"[DEBUG] 可用设备（已过滤）: {available_devices}")
        
        # 如果有LLM模型，尝试使用LLM决策
        if self.llm_model and agent_name in self.power_scratches:
            try:
                print(f"[DEBUG] 使用LLM为智能体 {agent_name} 选择设备")
                
                # 构建LLM提示
                current_time = timestamp.strftime("%Y-%m-%d %H:%M")
                user_preferences = json.dumps({
                    "energy_awareness": "medium",
                    "participates_in_dr": True
                }, ensure_ascii=False)
                
                context = self.parser.agent_profiles[agent_name]["currently"]
                
                # 获取设备使用历史
                device_usage_summary = self._get_device_usage_summary(agent_name, timestamp, hours_back=2)
                print(f"[DEBUG] 设备使用历史: {device_usage_summary}")
                
                prompt_info = self.power_scratches[agent_name].prompt_select_appliances_for_activity(
                    activity=activity,
                    current_sector=location,
                    current_time=current_time,
                    user_preferences=user_preferences,
                    context=context,
                    available_devices=available_devices,
                    device_usage_history=device_usage_summary
                )
                
                print(f"[DEBUG] LLM提示词长度: {len(prompt_info['prompt'])} 字符")
                
                # 调用LLM
                self.api_call_count += 1
                print(f"[DEBUG] API调用次数: {self.api_call_count}")
                response = self.llm_model.completion(
                    prompt=prompt_info["prompt"],
                    retry=3,
                    caller="power_appliance_selection"
                )
                
                print(f"[DEBUG] LLM响应: {response}")
                
                # 解析响应
                devices_from_llm = prompt_info["callback"](response)
                
                print(f"[DEBUG] LLM解析后的设备: {devices_from_llm}")
                
                # 检查LLM是否成功调用并返回了结构化数据
                if isinstance(devices_from_llm, dict) and "devices" in devices_from_llm:
                    # LLM成功调用并返回了结构化数据
                    actual_devices = devices_from_llm.get("devices", [])
                    
                    # 处理实际使用的设备
                    valid_devices = []  # 在使用前先定义
                    for d in actual_devices:
                        device_name = d["name"] if isinstance(d, dict) else d
                        if device_name in self.equipment_manager.equipments:
                            if isinstance(d, dict):
                                valid_devices.append(d)
                            else:
                                valid_devices.append({
                                    "name": d,
                                    "duration_minutes": 30  # 默认30分钟
                                })
                    
                    # 处理推迟的设备：按照suggested_time重新安排用电时间
                    postponed_list = devices_from_llm.get("postponed", [])
                    if postponed_list:
                        for p in postponed_list:
                            if isinstance(p, dict):
                                device_name = p.get("name", "")
                                suggested_time = p.get("suggested_time", "")
                                
                                if device_name and suggested_time:
                                    # 解析建议的时间
                                    try:
                                        # 尝试解析不同格式的时间
                                        suggested_datetime = None
                                        
                                        # 如果建议时间包含具体日期时间
                                        if "-" in suggested_time and ":" in suggested_time:
                                            # 格式如 "2026-03-09 23:00" 或 "2026-03-09 23:00后"
                                            if "后" in suggested_time:
                                                suggested_time_clean = suggested_time.replace("后", "")
                                            else:
                                                suggested_time_clean = suggested_time
                                            suggested_datetime = datetime.strptime(suggested_time_clean.strip(), "%Y-%m-%d %H:%M")
                                        elif ":" in suggested_time:
                                            # 格式如 "23:00" 或 "23:00后"
                                            if "后" in suggested_time:
                                                suggested_time_clean = suggested_time.replace("后", "")
                                            else:
                                                suggested_time_clean = suggested_time
                                            # 使用当前日期加上建议时间
                                            time_part = datetime.strptime(suggested_time_clean.strip(), "%H:%M").time()
                                            suggested_datetime = datetime.combine(timestamp.date(), time_part)
                                        else:
                                            # 尝试解析 "23:00" 格式的纯时间
                                            time_part = datetime.strptime(suggested_time.strip(), "%H:%M").time()
                                            suggested_datetime = datetime.combine(timestamp.date(), time_part)
                                    except ValueError:
                                        print(f"[WARNING] 无法解析建议时间: {suggested_time}，使用当前时间")
                                        suggested_datetime = timestamp
                                    
                                    # 确保设备存在
                                    if device_name in self.equipment_manager.equipments:
                                        # 获取设备信息
                                        device_info = self.equipment_manager.equipments[device_name]
                                        duration_minutes = p.get("duration_minutes", 30)  # 使用建议的使用时间
                                        
                                        # 计算推迟设备的电力消耗
                                        hour = suggested_datetime.hour
                                        is_weekend = suggested_datetime.weekday() >= 5  # 周六、周日为周末
                                        
                                        # 创建推迟设备的记录
                                        postponed_device_record = {
                                            "name": device_name,
                                            "duration_minutes": duration_minutes
                                        }
                                        
                                        # 计算推迟设备的电力消耗
                                        consumption = self.consumption_tracker.calculate_consumption_with_durations(
                                            agent_name=agent_name,
                                            location=location,
                                            activity=f"推迟使用: {activity}",  # 标记为推迟使用
                                            equipment_list=[postponed_device_record],
                                            hour=hour,
                                            is_weekend=is_weekend,
                                            usage_factor=1.0,
                                            duration_hours=1.0,
                                            electricity_profile={},
                                            simulation_time=suggested_datetime  # 使用建议的时间
                                        )
                                        
                                        print(f"[INFO] 推迟设备 {device_name} 在 {suggested_datetime.strftime('%Y-%m-%d %H:%M')} 已计算电力消耗: {consumption:.2f} kWh")
                                    else:
                                        print(f"[WARNING] 推迟设备 {device_name} 不存在于设备列表中")
                            else:
                                print(f"[WARNING] 无效的推迟设备信息: {p}")
                    
                    # 打印推迟信息
                    if postponed_list:
                        postponed_info = []
                        for p in postponed_list:
                            name = p.get("name", "未知设备")
                            reason = p.get("reason", "电价高峰")
                            suggested_time = p.get("suggested_time", "")
                            info = f"{name}({reason}"
                            if suggested_time:
                                info += f", 建议: {suggested_time}"
                            info += ")"
                            postponed_info.append(info)
                        print(f"[Agent Power] {agent_name} 在 {timestamp.strftime('%H:%M')} 推迟使用设备: {', '.join(postponed_info)}")
                    
                    # 判断LLM的决策类型
                    if valid_devices:
                        print(f"[DEBUG] LLM选择的设备: {valid_devices}")
                        # 记录设备使用历史
                        for device in valid_devices:
                            device_name = device["name"] if isinstance(device, dict) else device
                            duration = device.get("duration_minutes", 30) if isinstance(device, dict) else 30
                            self._record_device_usage(agent_name, device_name, timestamp, duration)
                        return valid_devices
                    else:
                        # LLM明确返回空设备列表，尊重LLM决策
                        print(f"[DEBUG] LLM明确返回空设备列表，尊重LLM决策：当前活动不需要使用电器")
                        return []
                
                # 验证并返回
                if devices_from_llm:
                    # 处理LLM返回的两种可能格式：
                    # 1. 旧格式：直接是设备列表 [{"name": "xxx", "duration_minutes": 30}, ...]
                    # 2. 新格式：包含devices和postponed字段 {"devices": [...], "postponed": [...]}
                    
                    valid_devices = []
                    postponed_devices = []
                    
                    # 判断返回格式
                    if isinstance(devices_from_llm, dict):
                        # 新格式：包含devices和postponed
                        actual_devices = devices_from_llm.get("devices", [])
                        postponed_list = devices_from_llm.get("postponed", [])
                        
                        # 处理实际使用的设备
                        for d in actual_devices:
                            device_name = d["name"] if isinstance(d, dict) else d
                            if device_name in self.equipment_manager.equipments:
                                if isinstance(d, dict):
                                    valid_devices.append(d)
                                else:
                                    valid_devices.append({
                                        "name": d,
                                        "duration_minutes": 30  # 默认30分钟
                                    })
                        
                        # 处理推迟的设备：按照suggested_time重新安排用电时间
                    if postponed_list:
                        for p in postponed_list:
                            if isinstance(p, dict):
                                device_name = p.get("name", "")
                                suggested_time = p.get("suggested_time", "")
                                
                                if device_name and suggested_time:
                                    # 解析建议的时间
                                    try:
                                        # 尝试解析不同格式的时间
                                        suggested_datetime = None
                                        
                                        # 如果建议时间包含具体日期时间
                                        if "-" in suggested_time and ":" in suggested_time:
                                            # 格式如 "2026-03-09 23:00" 或 "2026-03-09 23:00后"
                                            if "后" in suggested_time:
                                                suggested_time_clean = suggested_time.replace("后", "")
                                            else:
                                                suggested_time_clean = suggested_time
                                            suggested_datetime = datetime.strptime(suggested_time_clean.strip(), "%Y-%m-%d %H:%M")
                                        elif ":" in suggested_time:
                                            # 格式如 "23:00" 或 "23:00后"
                                            if "后" in suggested_time:
                                                suggested_time_clean = suggested_time.replace("后", "")
                                            else:
                                                suggested_time_clean = suggested_time
                                            # 使用当前日期加上建议时间
                                            time_part = datetime.strptime(suggested_time_clean.strip(), "%H:%M").time()
                                            suggested_datetime = datetime.combine(timestamp.date(), time_part)
                                        else:
                                            # 尝试解析 "23:00" 格式的纯时间
                                            time_part = datetime.strptime(suggested_time.strip(), "%H:%M").time()
                                            suggested_datetime = datetime.combine(timestamp.date(), time_part)
                                    except ValueError:
                                        print(f"[WARNING] 无法解析建议时间: {suggested_time}，使用当前时间")
                                        suggested_datetime = timestamp
                                    
                                # 确保设备存在
                                if device_name in self.equipment_manager.equipments:
                                    # 获取设备信息
                                    device_info = self.equipment_manager.equipments[device_name]
                                    duration_minutes = p.get("duration_minutes", 30)  # 使用建议的使用时间
                                    
                                    # 计算推迟设备的电力消耗
                                    hour = suggested_datetime.hour
                                    is_weekend = suggested_datetime.weekday() >= 5  # 周六、周日为周末
                                    
                                    # 创建推迟设备的记录
                                    postponed_device_record = {
                                        "name": device_name,
                                        "duration_minutes": duration_minutes
                                    }
                                    
                                    # 计算推迟设备的电力消耗
                                    consumption = self.consumption_tracker.calculate_consumption_with_durations(
                                        agent_name=agent_name,
                                        location=location,
                                        activity=f"推迟使用: {activity}",  # 标记为推迟使用
                                        equipment_list=[postponed_device_record],
                                        hour=hour,
                                        is_weekend=is_weekend,
                                        usage_factor=1.0,
                                        duration_hours=1.0,
                                        electricity_profile={},
                                        simulation_time=suggested_datetime  # 使用建议的时间
                                    )
                                    
                                    print(f"[INFO] 推迟设备 {device_name} 在 {suggested_datetime.strftime('%Y-%m-%d %H:%M')} 已计算电力消耗: {consumption:.2f} kWh")
                                else:
                                    print(f"[WARNING] 推迟设备 {device_name} 不存在于设备列表中")
                            else:
                                print(f"[WARNING] 无效的推迟设备信息: {p}")
                    
                    # 打印推迟信息
                    if postponed_list:
                        postponed_info = []
                        for p in postponed_list:
                            name = p.get("name", "未知设备")
                            reason = p.get("reason", "电价高峰")
                            suggested_time = p.get("suggested_time", "")
                            info = f"{name}({reason}"
                            if suggested_time:
                                info += f", 建议: {suggested_time}"
                            info += ")"
                            postponed_info.append(info)
                        print(f"[Agent Power] {agent_name} 在 {timestamp.strftime('%H:%M')} 推迟使用设备: {', '.join(postponed_info)}")
                    else:
                        # 旧格式：直接是设备列表
                        for d in devices_from_llm:
                            device_name = d["name"] if isinstance(d, dict) else d
                            if device_name in self.equipment_manager.equipments:
                                if isinstance(d, dict):
                                    valid_devices.append(d)
                                else:
                                    valid_devices.append({
                                        "name": d,
                                        "duration_minutes": 30  # 默认30分钟
                                    })
                    
                    # 判断LLM的决策类型
                    if isinstance(devices_from_llm, dict) and "devices" in devices_from_llm:
                        # LLM成功调用并返回了结构化数据
                        actual_devices = devices_from_llm.get("devices", [])
                        
                        if valid_devices:
                            print(f"[DEBUG] LLM选择的设备: {valid_devices}")
                            # 记录设备使用历史
                            for device in valid_devices:
                                device_name = device["name"] if isinstance(device, dict) else device
                                duration = device.get("duration_minutes", 30) if isinstance(device, dict) else 30
                                self._record_device_usage(agent_name, device_name, timestamp, duration)
                            return valid_devices
                        else:
                            # LLM明确返回空设备列表，尊重LLM决策
                            print(f"[DEBUG] LLM明确返回空设备列表，尊重LLM决策：当前活动不需要使用电器")
                            return []
                    else:
                        # LLM返回格式异常，使用规则回退
                        print(f"[DEBUG] LLM返回格式异常，使用规则回退")
                else:
                    # LLM未返回有效设备，使用规则回退
                    print(f"[DEBUG] LLM未返回有效设备，使用规则回退")
            except Exception as e:
                print(f"[WARNING] LLM调用失败: {e}，使用规则回退")
                import traceback
                traceback.print_exc()
                # 只有在LLM调用失败时才使用规则回退
                rule_devices = self._get_equipments_by_rules(activity, location, available_devices)
                print(f"[DEBUG] 规则选择的设备: {rule_devices}")
                # 记录设备使用历史
                for device in rule_devices:
                    device_name = device["name"] if isinstance(device, dict) else device
                    duration = device.get("duration_minutes", 30) if isinstance(device, dict) else 30
                    self._record_device_usage(agent_name, device_name, timestamp, duration)
                return rule_devices
        else:
            if not self.llm_model:
                print(f"[DEBUG] LLM模型未初始化，使用规则回退")
                # LLM模型未初始化，使用规则回退
                rule_devices = self._get_equipments_by_rules(activity, location, available_devices)
                print(f"[DEBUG] 规则选择的设备: {rule_devices}")
                # 记录设备使用历史
                for device in rule_devices:
                    device_name = device["name"] if isinstance(device, dict) else device
                    duration = device.get("duration_minutes", 30) if isinstance(device, dict) else 30
                    self._record_device_usage(agent_name, device_name, timestamp, duration)
                return rule_devices
            elif agent_name not in self.power_scratches:
                print(f"[DEBUG] 智能体 {agent_name} 没有对应的PowerScratch，使用规则回退")
                # 智能体没有对应的PowerScratch，使用规则回退
                rule_devices = self._get_equipments_by_rules(activity, location, available_devices)
                print(f"[DEBUG] 规则选择的设备: {rule_devices}")
                # 记录设备使用历史
                for device in rule_devices:
                    device_name = device["name"] if isinstance(device, dict) else device
                    duration = device.get("duration_minutes", 30) if isinstance(device, dict) else 30
                    self._record_device_usage(agent_name, device_name, timestamp, duration)
                return rule_devices
        
        # 如果执行到这里，说明LLM成功调用但返回了空设备列表
        # 这种情况下不需要使用规则回退，直接返回空列表
        print(f"[DEBUG] LLM成功调用但返回空设备列表，不使用规则回退")
        return []
    
    def _get_equipments_by_rules(self, activity: str, location: str, available_devices: List[str]) -> List[Dict]:
        """使用规则获取设备列表"""
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
        
        # 家庭活动关键词匹配
        activity_equipment_map = {
            "做饭": ["电饭煲", "微波炉", "电热水壶"],
            "洗衣服": ["洗衣机"],
            "看电视": ["电视"],
            "工作": ["电脑"],
            "休息": ["照明", "电视"],
            "睡觉": [],
        }
        
        for key, equipments in activity_equipment_map.items():
            if key in activity:
                # 过滤只保留实际存在的设备，并添加默认使用时间
                valid_devices = []
                for e in equipments:
                    if e in self.equipment_manager.equipments and e in available_devices:
                        valid_devices.append({"name": e, "duration_minutes": 30})
                if valid_devices:
                    return valid_devices
        
        # 最终回退
        if "照明" in self.equipment_manager.equipments and "照明" in available_devices:
            return [{"name": "照明", "duration_minutes": 30}]
        elif available_devices:
            return [{"name": available_devices[0], "duration_minutes": 30}]
        else:
            return [{"name": "照明", "duration_minutes": 30}]
    
    def process_simulation(self):
        """处理整个模拟数据，生成电力消耗记录"""
        print(f"[INFO] 开始处理模拟数据，共 {len(self.parser.activities)} 条活动记录")
        
        # 按时间排序活动
        sorted_activities = sorted(self.parser.activities, key=lambda x: x["timestamp"])
        
        # 处理每个活动
        for i, activity in enumerate(sorted_activities):
            timestamp = activity["timestamp"]
            agent_name = activity["agent_name"]
            location = activity["location"]
            activity_desc = activity["activity"]
            
            # 获取设备列表
            equipment_list = self.get_equipments_for_activity(agent_name, activity_desc, location, timestamp)
            
            # 添加调试信息
            print(f"[DEBUG] 智能体 {agent_name} 的设备列表: {equipment_list}")
            print(f"[DEBUG] 设备管理器中的设备数量: {len(self.equipment_manager.equipments)}")
            
            # 计算用电量
            hour = timestamp.hour
            is_weekend = timestamp.weekday() >= 5  # 周六、周日为周末
            
            # 直接使用LLM返回的设备列表，每个设备都有自己的使用时间
            # 不需要推测活动持续时间，直接传递设备列表给计算函数
            consumption = self.consumption_tracker.calculate_consumption_with_durations(
                agent_name=agent_name,
                location=location,
                activity=activity_desc,
                equipment_list=equipment_list,
                hour=hour,
                is_weekend=is_weekend,
                usage_factor=1.0,
                duration_hours=1.0,  # 活动持续时间设为1小时，每个设备使用自己的duration_minutes
                electricity_profile={},
                simulation_time=timestamp
            )
            
            print(f"[DEBUG] 活动用电量: {consumption} 千瓦时")
            print(f"[DEBUG] 当前总用电记录数: {len(self.consumption_tracker.consumptions)}")
            
            # 打印进度
            if (i + 1) % 100 == 0 or i == len(sorted_activities) - 1:
                print(f"[INFO] 已处理 {i + 1}/{len(sorted_activities)} 条活动记录")
        
        # 保存结果
        self.consumption_tracker.save_to_file()
        print(f"[INFO] 电力消耗数据已保存到: {os.path.join(self.output_dir, 'power_consumption.json')}")
        
        
        # 推迟设备的统计信息（仅用于日志）
        if self.postponed_devices:
            print(f"[INFO] 总推迟设备次数: {len(self.postponed_devices)}")
            
            # 按智能体统计推迟次数
            postponed_by_agent = {}
            for p in self.postponed_devices:
                agent = p["agent_name"]
                if agent not in postponed_by_agent:
                    postponed_by_agent[agent] = []
                postponed_by_agent[agent].append(p)
            
            print(f"[INFO] 各智能体推迟次数:")
            for agent, devices in sorted(postponed_by_agent.items()):
                print(f"  - {agent}: {len(devices)} 次")
        else:
            print(f"[INFO] 没有设备被推迟使用")
        
        # 打印统计信息
        total_consumption = self.consumption_tracker.get_total_consumption()
        print(f"[INFO] 总用电量: {total_consumption:.2f} 千瓦时")
        print(f"[INFO] 总用电记录数: {len(self.consumption_tracker.consumptions)}")
        print(f"[INFO] 总API调用次数: {self.api_call_count}")


def main():
    parser = argparse.ArgumentParser(description="电力模块后处理工具")
    parser.add_argument("--simulation", type=str, required=True, help="simulation.md文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出目录")
    parser.add_argument("--llm_config", type=str, help="LLM配置文件路径（可选，不提供则使用默认配置）")
    
    args = parser.parse_args()
    
    # 加载LLM配置（如果提供了）
    llm_config = None
    if args.llm_config and os.path.exists(args.llm_config):
        print(f"[DEBUG] 加载LLM配置文件: {args.llm_config}")
        with open(args.llm_config, 'r', encoding='utf-8') as f:
            llm_config = json.load(f)
        print(f"[DEBUG] LLM配置内容: {llm_config}")
    else:
        if args.llm_config:
            print(f"[DEBUG] 提供的LLM配置文件不存在: {args.llm_config}")
        else:
            print(f"[DEBUG] 未提供LLM配置文件，将尝试使用默认配置")
        # 不设置llm_config，让PowerPostProcessor自行加载默认配置
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 初始化处理器
    processor = PowerPostProcessor(args.simulation, args.output, llm_config)
    
    # 处理模拟数据
    processor.process_simulation()


if __name__ == "__main__":
    main()