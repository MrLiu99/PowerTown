# 电力小镇使用文档

## 概述

电力小镇是基于生成式智能体（Generative Agents）项目改造的电力消费预测系统。系统通过模拟小镇中不同角色的智能体（居民、学生、工人、教师等）的日常活动，自动记录用电行为，并预测未来的用电量。

## 系统架构

### 核心模块

1. **用电设备管理 (equipment.py)**
   - 管理各种用电设备（家用电器、工业设备、学校设备等）
   - 定义设备的额定功率和使用模式
   - 根据时间和活动计算设备用电量

2. **用电量跟踪 (consumption.py)**
   - 记录每个智能体的用电行为
   - 按位置、时间、设备统计用电量
   - 支持数据持久化

3. **智能体用电行为 (agent_power.py)**
   - 将用电行为集成到智能体活动中
   - 根据活动自动匹配使用的设备
   - 记录智能体的用电历史

4. **用电量预测 (predictor.py)**
   - 基于历史数据预测未来用电量
   - 支持按小时、按天、按位置预测
   - 考虑周末、季节等因素

## 使用方法

### 1. 启动电力小镇模拟

```bash
cd generative_agents
python start.py --name power-town-test --start "20250213-09:30" --step 10 --stride 10
```

系统会自动：
- 初始化设备管理器
- 创建用电量跟踪器
- 为每个智能体配置用电行为
- 在智能体执行活动时记录用电量

### 2. 查看用电量预测

```bash
python power_predict.py --name power-town-test --date 20250214

python power_predict.py --name power-test1 --date 20250128 --lookback 1
```

参数说明：
- `--name`: 模拟名称
- `--date`: 预测日期（格式：YYYYMMDD），默认为明天
- `--location`: 可选，预测特定位置
- `--lookback`: 回顾天数，默认7天

### 3. 查看用电量数据

用电量数据保存在：`results/checkpoints/{simulation_name}/power/power_consumption.json`

## 配置说明

### 设备配置

设备配置文件位于：`frontend/static/assets/village/equipment.json`

系统会自动创建默认设备配置，包括：
- 家用电器：空调、冰箱、洗衣机、电视、电脑、热水器、照明
- 工业设备：生产线设备、空压机、工业照明
- 学校设备：教室照明、投影仪、电脑机房、实验室设备
- 商业设备：商场照明、电梯

### 智能体配置

每个智能体的配置文件位于：`frontend/static/assets/village/agents/{agent_name}/agent.json`

在配置中可以添加：
- `location`: 智能体所在位置（如：小区1-101、工厂A车间）
- `default_equipments`: 默认使用的设备列表

### 活动与设备映射

系统内置了活动与设备的映射关系：
- "睡觉" → ["照明"]
- "在家休息" → ["电视", "照明", "空调"]
- "做饭" → ["热水器", "照明"]
- "看电视" → ["电视", "照明"]
- "使用电脑" → ["电脑", "照明", "空调"]
- "洗衣服" → ["洗衣机", "照明"]
- "工作" → ["电脑", "照明", "空调"]
- "学习" → ["电脑", "照明", "空调"]
- "上课" → ["教室照明", "投影仪"]
- "实验" → ["实验室设备", "照明"]
- "生产" → ["生产线设备", "工业照明"]
- "购物" → ["商场照明"]
- "办公" → ["电脑", "照明", "空调"]

## 扩展开发

### 添加新设备

在 `modules/power/equipment.py` 的 `EquipmentManager._init_default_equipments()` 方法中添加：

```python
self.add_equipment(Equipment("设备名称", 功率(瓦), "类别", 
    {"work_hours": [8, 22], "off_hours_factor": 0.1, "weekend_factor": 1.2}, 
    "设备描述"))
```

### 添加新活动映射

在 `modules/power/agent_power.py` 的 `AgentPowerBehavior._init_activity_equipment_map()` 方法中添加：

```python
"新活动": ["设备1", "设备2"],
```

### 自定义预测算法

在 `modules/power/predictor.py` 中修改 `PowerPredictor` 类，实现更复杂的预测算法（如机器学习模型）。

## 数据格式

### 用电量记录格式

```json
{
  "timestamp": "20250213-09:30:00",
  "agent_name": "张伟",
  "location": "小区1-101",
  "equipment": "电脑",
  "power_kwh": 0.2,
  "activity": "使用电脑"
}
```

### 预测结果格式

```json
{
  "0": 0.05,
  "1": 0.03,
  ...
  "23": 0.08
}
```

## 注意事项

1. 系统会自动保存用电量记录，无需手动保存
2. 预测算法基于历史平均值，可根据需要替换为更复杂的算法
3. 设备功率单位为瓦特（W），用电量单位为千瓦时（kWh）
4. 系统会根据活动自动匹配设备，也可以手动指定设备列表

## 示例场景

### 场景1：预测居民区用电量

```bash
python power_predict.py --name power-town-test --location "小区1" --date 20250214
```

### 场景2：查看全天用电趋势

```bash
python power_predict.py --name power-town-test --date 20250214
```

系统会显示每小时预测用电量和最近7天的用电趋势。

