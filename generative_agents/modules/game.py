"""generative_agents.game"""

import os
import copy

from modules.utils import GenerativeAgentsMap, GenerativeAgentsKey
from modules import utils
from .maze import Maze
from .agent import Agent
from modules.power.equipment import EquipmentManager
from modules.power.consumption import PowerConsumptionTracker


class Game:
    """The Game"""

    def __init__(self, name, static_root, config, conversation, logger=None):
        self.name = name
        self.static_root = static_root
        self.record_iterval = config.get("record_iterval", 30)
        self.logger = logger or utils.IOLogger()
        self.maze = Maze(self.load_static(config["maze"]["path"]), self.logger)
        self.conversation = conversation
        
        # 检查是否启用电力模块
        self.power_enabled = config.get("power_enabled", True)
        
        # 只有在启用电力模块时才初始化电力系统
        if self.power_enabled:
            # 初始化电力系统
            equipment_dir = os.path.join(static_root, "assets", "village", "equipment")
            self.location_equipment_managers = {}  # 存储每个位置的设备管理器
            
            # 加载所有可用的设备配置文件
            if os.path.exists(equipment_dir):
                for file_name in os.listdir(equipment_dir):
                    if file_name.endswith('.json'):
                        location_name = file_name[:-5]  # 移除.json后缀
                        file_path = os.path.join(equipment_dir, file_name)
                        self.location_equipment_managers[location_name] = EquipmentManager(file_path)
                        print(f"[Game] 加载位置 '{location_name}' 的设备配置")
            
            # 创建默认设备管理器（作为后备）
            default_equipment_path = os.path.join(equipment_dir, "default.json")
            if os.path.exists(default_equipment_path):
                self.equipment_manager = EquipmentManager(default_equipment_path)
            else:
                # 如果没有默认配置，使用空的管理器
                self.equipment_manager = EquipmentManager()
                
            power_storage_root = os.path.join(f"results/checkpoints/{name}", "power")
            self.power_tracker = PowerConsumptionTracker(power_storage_root, self.equipment_manager)
        else:
            # 不启用电力模块时，设置为None
            self.location_equipment_managers = {}
            self.equipment_manager = None
            self.power_tracker = None
            print("[Game] 电力模块已禁用")
        
        self.agents = {}
        if "agent_base" in config:
            agent_base = config["agent_base"]
        else:
            agent_base = {}
        storage_root = os.path.join(f"results/checkpoints/{name}", "storage")
        if not os.path.isdir(storage_root):
            os.makedirs(storage_root)
        for name, agent in config["agents"].items():
            agent_config = utils.update_dict(
                copy.deepcopy(agent_base), self.load_static(agent["config_path"])
            )
            agent_config = utils.update_dict(agent_config, agent)

            agent_config["storage_root"] = os.path.join(storage_root, name)
            # 只在电力模块启用时才传递电力系统相关参数
            if self.power_enabled:
                agent_config["equipment_manager"] = self.equipment_manager
                agent_config["power_tracker"] = self.power_tracker
            # 传递 power_enabled 参数给 Agent
            agent_config["power_enabled"] = self.power_enabled
            self.agents[name] = Agent(agent_config, self.maze, self.conversation, self.logger)

    def get_agent(self, name):
        return self.agents[name]

    def agent_think(self, name, status):
        agent = self.get_agent(name)
        plan = agent.think(status, self.agents)
        
        # 记录用电量（如果智能体有用电行为且电力模块已启用）
        # 只在活动变化或记录间隔时记录，避免重复记录
        if self.power_enabled and hasattr(agent, 'power_behavior') and agent.action:
            try:
                # 检查是否应该记录（避免重复记录）
                current_time = utils.get_timer().get_date()
                should_record = False
                
                # 如果距离上次记录超过一定时间（如5分钟），或者活动变化了，则记录
                if not hasattr(agent, '_last_power_record_time'):
                    agent._last_power_record_time = None
                    agent._last_power_activity = None
                
                if agent._last_power_record_time is None:
                    should_record = True
                elif (current_time - agent._last_power_record_time).total_seconds() >= 300:  # 5分钟
                    should_record = True
                else:
                    current_activity = agent.get_event().get_describe(False)
                    if current_activity != agent._last_power_activity:
                        should_record = True
                
                if should_record:
                    # 获取智能体当前活动描述
                    activity = agent.get_event().get_describe(False)
                    
                    # 获取智能体当前位置
                    current_address = agent.get_tile().get_address(as_list=True)
                    location = self._extract_location_from_address(current_address)
                    
                    # 获取智能体的计划信息
                    current_plan = agent.get_current_plan()
                    
                    # 更新智能体的位置（如果位置变化了）
                    if hasattr(agent, 'power_behavior') and location:
                        agent.power_behavior.location = location
                    
                    # 计算活动持续时间（分钟），用于计算用电量
                    duration_minutes = agent.action.duration if agent.action else 10
                    # 将持续时间转换为小时比例
                    duration_hours = duration_minutes / 60.0
                    
                    # 获取时间信息
                    hour = current_time.hour
                    is_weekend = current_time.weekday() >= 5
                    
                    # 使用LLM选择电器并计算用电量
                    # 传递智能体的计划和位置信息给LLM
                    self.logger.info(f"{name} 正在根据活动 '{activity}' 和位置 '{location}' 选择电器...")
                    
                    # 获取当前位置的设备管理器
                    location_equipment_manager = self._get_location_equipment_manager(location)
                    
                    # 临时更新智能体的设备管理器
                    original_manager = agent.power_behavior.equipment_manager
                    agent.power_behavior.equipment_manager = location_equipment_manager
                    
                    # 调用AgentPowerBehavior的get_equipments_for_activity方法
                    # 该方法内部会调用LLM来选择合适的电器及使用时间
                    equipment_list = agent.power_behavior.get_equipments_for_activity(
                        activity=activity,
                        location=location,
                        plan=current_plan
                    )
                    
                    # 恢复原始设备管理器
                    agent.power_behavior.equipment_manager = original_manager
                    
                    # 打印选择的电器及使用时间，方便调试
                    equipment_info = []
                    for item in equipment_list:
                        if isinstance(item, dict):
                            equipment_info.append(f"{item['name']}({item.get('duration_minutes', 30)}分钟)")
                        else:
                            equipment_info.append(f"{item}(30分钟)")  # 兼容旧格式
                    self.logger.info(f"{name} 选择的电器: {', '.join(equipment_info)}")
                    
                    # 计算用电量（使用新的方法，考虑每个设备的具体使用时间）
                    total_consumption = self.power_tracker.calculate_consumption_with_durations(
                        agent_name=name,
                        location=location,
                        activity=activity,
                        equipment_list=equipment_list,
                        hour=hour,
                        is_weekend=is_weekend,
                        usage_factor=1.0,  # 设备使用强度
                        duration_hours=min(duration_hours, 1.0),  # 最多按1小时计算
                        electricity_profile=getattr(agent.power_behavior, 'electricity_profile', {}),
                        simulation_time=current_time
                    )
                    
                    # 记录用电量信息
                    self.logger.info(f"{name} 在 {location} 进行 '{activity}' 活动使用了电器: {', '.join(equipment_info)}, 用电量: {total_consumption:.3f} kWh")
                    
                    # 如果是公共单位，也记录公共单位的用电量（不归属于个人）
                    public_location = self._identify_public_location(current_address)
                    if public_location:
                        self._record_public_location_consumption(
                            public_location, activity, hour, is_weekend, 
                            min(duration_hours, 1.0), agent.power_behavior.equipment_manager,
                            self.power_tracker
                        )
                    
                    agent._last_power_record_time = current_time
                    agent._last_power_activity = activity
                    
            except Exception as e:
                self.logger.warning(f"Failed to record power consumption for {name}: {e}")
        
        info = {
            "currently": agent.scratch.currently,
            "associate": agent.associate.abstract(),
            "concepts": {c.node_id: c.abstract() for c in agent.concepts},
            "chats": [
                {"name": "self" if n == agent.name else n, "chat": c}
                for n, c in agent.chats
            ],
            "action": agent.action.abstract(),
            "schedule": agent.schedule.abstract(),
            "address": agent.get_tile().get_address(as_list=False),
        }
        if (
            utils.get_timer().daily_duration() - agent.last_record
        ) > self.record_iterval:
            info["record"] = True
            agent.last_record = utils.get_timer().daily_duration()
            # 保存用电量记录（仅在电力模块启用时）
            if self.power_enabled and hasattr(self, 'power_tracker'):
                self.power_tracker.save_to_file()
        else:
            info["record"] = False
        if agent.llm_available():
            info["llm"] = agent._llm.get_summary()
        title = "{}.summary @ {}".format(
            name, utils.get_timer().get_date("%Y%m%d-%H:%M:%S")
        )
        self.logger.info("\n{}\n{}\n".format(utils.split_line(title), agent))
        return {"plan": plan, "info": info}

    def _extract_location_from_address(self, address):
        """从地址中提取位置信息"""
        if not address or len(address) < 2:
            return "未知位置"
        
        # 地址格式通常是: [world, sector, arena, object]
        # 提取sector和arena作为位置
        if len(address) >= 2:
            sector = address[1] if len(address) > 1 else ""
            if len(address) >= 3:
                return f"{sector}:{address[2]}"
            return sector
        return address[0] if address else "未知位置"
    
    def _identify_public_location(self, address):
        """识别公共单位位置"""
        if not address:
            return None
        
        # 公共单位关键词
        public_keywords = {
            "咖啡馆": ["咖啡馆", "咖啡", "闪电咖啡馆", "霍布斯咖啡馆"],
            "酒吧": ["酒吧", "玫瑰酒吧"],
            "超市": ["超市", "商场", "家家乐超市", "柳树市场"],
            "学校": ["学院", "学校", "教学楼", "教室", "图书馆"],
            "工厂": ["工厂", "车间", "生产线"],
            "公园": ["公园", "花园"],
        }
        
        address_str = ":".join(address)
        for location_type, keywords in public_keywords.items():
            for keyword in keywords:
                if keyword in address_str:
                    return location_type
        return None
    
    def _record_public_location_consumption(self, public_location, activity, hour, 
                                           is_weekend, duration_hours, 
                                           equipment_manager, consumption_tracker):
        """记录公共单位的用电量"""
        from modules.power.agent_power import AgentPowerBehavior
        
        # 创建临时行为对象用于记录公共单位用电量
        temp_behavior = AgentPowerBehavior(
            agent_name="公共单位",
            location=public_location,
            equipment_manager=equipment_manager,
            consumption_tracker=consumption_tracker,
            default_equipments=[]
        )
        
        # 记录公共单位用电量
        temp_behavior.record_consumption(
            activity, hour, is_weekend,
            usage_factor=1.0,
            duration_hours=duration_hours
        )
    
    def _get_location_equipment_manager(self, location):
        """根据位置获取对应的设备管理器"""
        # 尝试精确匹配
        if location in self.location_equipment_managers:
            return self.location_equipment_managers[location]
        
        # 尝试模糊匹配
        for loc_name, manager in self.location_equipment_managers.items():
            if loc_name in location or location in loc_name:
                print(f"[Game] 使用模糊匹配: '{location}' -> '{loc_name}'")
                return manager
        
        # 返回默认设备管理器
        print(f"[Game] 未找到位置 '{location}' 的设备配置，使用默认配置")
        return self.equipment_manager
    
    def load_static(self, path):
        return utils.load_dict(os.path.join(self.static_root, path))

    def reset_game(self):
        for a_name, agent in self.agents.items():
            agent.reset()
            title = "{}.reset".format(a_name)
            self.logger.info("\n{}\n{}\n".format(utils.split_line(title), agent))


def create_game(name, static_root, config, conversation, logger=None):
    """Create the game"""

    utils.set_timer(**config.get("time", {}))
    GenerativeAgentsMap.set(GenerativeAgentsKey.GAME, Game(name, static_root, config, conversation, logger=logger))
    return GenerativeAgentsMap.get(GenerativeAgentsKey.GAME)


def get_game():
    """Get the gloabl game"""

    return GenerativeAgentsMap.get(GenerativeAgentsKey.GAME)