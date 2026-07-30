import os
import json
from typing import List, Dict, Any

MAZE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "frontend",
    "static",
    "assets",
    "village",
    "maze.json",
)
AGENTS_ROOT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "frontend",
    "static",
    "assets",
    "village",
    "agents",
)

# 住居相关关键词（中文地图）
HOME_SECTOR_KEYWORDS = ["公寓", "宿舍", "住宅", "小区", "房", "家"]
HOME_ARENA_KEYWORDS = ["主人房", "房间", "卧室", "起居室", "客厅"]
HOME_OBJECT_KEYWORDS = ["床", "书桌", "沙发", "冰箱"]

# 仅调整这些新建的电力小镇角色（避免影响原有人物）
POWER_TOWN_NAMES = [
    "张伟", "李娜", "王强", "刘老师", "陈经理", "赵大妈",
    "孙工程师", "周师傅", "吴同学", "郑医生", "钱教授", "冯工人",
]


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any):
    # 尽量保留中文可读
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_home_address(address: List[str]) -> bool:
    # 地址结构: [world, sector, arena, game_object]
    if not address:
        return False
    sector = address[1] if len(address) > 1 else ""
    arena = address[2] if len(address) > 2 else ""
    obj = address[3] if len(address) > 3 else ""

    def has_any(s: str, keywords: List[str]) -> bool:
        return any(k in s for k in keywords)

    return (
        has_any(sector, HOME_SECTOR_KEYWORDS)
        or has_any(arena, HOME_ARENA_KEYWORDS)
        or has_any(obj, HOME_OBJECT_KEYWORDS)
    )


def collect_home_tiles(maze: Dict[str, Any]) -> List[List[int]]:
    tiles = maze.get("tiles", [])
    coords: List[List[int]] = []
    for t in tiles:
        address = t.get("address") or []
        # maze.json 单个 tile 的地址字段可能为 list 或 dict，这里处理 list 形式
        if isinstance(address, list) and is_home_address(address):
            if not t.get("collision", False):
                coord = t.get("coord")
                if isinstance(coord, list) and len(coord) == 2:
                    coords.append(coord)
    return coords


def find_agent_dirs(root: str) -> List[str]:
    dirs = []
    for name in POWER_TOWN_NAMES:
        d = os.path.join(root, name)
        if os.path.isdir(d):
            dirs.append(d)
    return dirs


def adjust_agents_coords():
    if not os.path.exists(MAZE_PATH):
        print(f"未找到 maze.json: {MAZE_PATH}")
        return
    maze = load_json(MAZE_PATH)
    home_coords = collect_home_tiles(maze)
    if not home_coords:
        print("未在地图中找到可用的居住坐标（带床/房间/宿舍等标识）。")
        return

    agent_dirs = find_agent_dirs(AGENTS_ROOT)
    if not agent_dirs:
        print("未找到电力小镇智能体目录。")
        return

    # 简单分配：依次取可用坐标
    idx = 0
    total = 0
    for d in agent_dirs:
        agent_path = os.path.join(d, "agent.json")
        if not os.path.exists(agent_path):
            continue
        try:
            agent = load_json(agent_path)
            coord = home_coords[idx % len(home_coords)]
            agent["coord"] = coord
            save_json(agent_path, agent)
            idx += 1
            total += 1
            print(f"已为 {os.path.basename(d)} 设置坐标: {coord}")
        except Exception as e:
            print(f"更新 {agent_path} 失败: {e}")

    print(f"完成：已更新 {total} 个智能体坐标。")


if __name__ == "__main__":
    adjust_agents_coords()
