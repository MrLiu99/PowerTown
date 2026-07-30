"""generative_agents.utils.arguments"""

import os
import json
import copy
from typing import Any


def load_dict(str_dict: str, flavor: str = "json") -> dict:
    """
    将字符串/文件加载到字典。

    参数
    ----------
        str_dict: 字符串
        文件路径或字符串对象。
        flavor: 字符串
        加载的 flavor。

    返回
    -------
        dict_obj: 字典
        已加载的字典。
    """

    if not str_dict:
        return {}
    # 情况1: 文件路径
    if isinstance(str_dict, str) and os.path.isfile(str_dict):
        with open(str_dict, "r", encoding="utf-8") as f:
            dict_obj = json.load(f)
    #  情况2: JSON字符串
    elif isinstance(str_dict, str):
        dict_obj = json.loads(str_dict)
    # 情况3: 已经是字典对象
    elif isinstance(str_dict, dict):
        dict_obj = copy_dict(str_dict)
    else:
        raise Exception("Unexpected str_dict {}({})".format(str_dict, type(str_dict)))
    assert flavor == "json", "Unexpected flavor for load_dict: " + str(flavor)
    return dict_obj


def save_dict(dict_obj: Any, path: str, indent: int = 2) -> str:
    """
    将字典保存为JSON文件
    
    dict_obj: 字典对象或可转换为字典的对象
    path: 输出文件路径
    indent: JSON缩进空格数
    """

    with open(path, "w") as f:
        f.write(json.dumps(load_dict(dict_obj), indent=indent, ensure_ascii=False))
    return path


def update_dict(src_dict: dict, new_dict: dict, soft_update: bool = False) -> dict:
    """使用 new_dict 更新 src_dict。

    参数
    ----------
    src_dict: dict
    源字典。
    new_dict: dict
    新的字典。
    soft_update: bool
    是否更新源字典，False 则强制更新。

    返回
    -------
    dict_obj: dict
    更新后的字典。
    """

    if not src_dict:
        return new_dict
    if not new_dict:
        return src_dict
    assert isinstance(src_dict, dict) and isinstance(
        new_dict, dict
    ), "update_dict only support dict, get src {} and new {}".format(
        type(src_dict), type(new_dict)
    )
    for k, v in new_dict.items():
        if not src_dict.get(k):
            src_dict[k] = v
        elif isinstance(v, dict):
            v = update_dict(src_dict.get(k, {}), v, soft_update)
            src_dict[k] = v
        elif not soft_update:
            src_dict[k] = v
    return src_dict


def dump_dict(dict_obj: dict, flavor: str = "table:2") -> str:
    """将配置转储为字符串。

    参数
    ----------
    src_dict: dict
    源字典。
    flavor: str
    转储的 flavor。

    返回值
    -------
    str_dict: string
    转储后的字符串。
    """

    if not dict_obj:
        return ""
    if flavor.startswith("table:"):

        def _get_lines(value, indent=0):
            max_size = int(flavor.split(":")[1]) - indent - 2
            lines = []
            for k, v in value.items():
                if v is None:
                    continue
                if isinstance(v, (dict, tuple, list, set)) and not v:
                    continue
                if isinstance(v, dict) and len(str(k) + str(v)) > max_size:
                    lines.append("{}{}:".format(indent * " ", k))
                    lines.extend(_get_lines(v, indent + 2))
                elif (
                    isinstance(v, (tuple, list, set))
                    and len(str(k) + str(v)) > max_size
                ):
                    lines.append("{}{}:".format(indent * " ", k))
                    for idx, ele in enumerate(v):
                        if isinstance(ele, dict) and len(str(ele)) > max_size:
                            lines.append(
                                "{}[{}.{}]:".format((indent + 2) * " ", k, idx)
                            )
                            lines.extend(_get_lines(ele, indent + 4))
                        else:
                            lines.append(
                                "{}<{}>{}".format((indent + 2) * " ", idx, ele)
                            )
                elif isinstance(v, bool):
                    lines.append(
                        "{}{}: {}".format(indent * " ", k, "true" if v else "false")
                    )
                elif hasattr(v, "__name__"):
                    lines.append(
                        "{}{}: {}({})".format(indent * " ", k, v.__name__, type(v))
                    )
                else:
                    lines.append("{}{}: {}".format(indent * " ", k, v))
            return lines

        lines = _get_lines(dict_obj) or [
            "  {}: {}".format(k, v) for k, v in dict_obj.items()
        ]
        return "\n".join(lines)
    return json.dumps(dict_obj, ensure_ascii=False)


def dict_equal(dict_a: dict, dict_b: dict) -> bool:
    """检查两个字典是否相同

    Parameters
    ----------
    dict_a: dict
        The A dict.
    dict_b: dict
        The B dict.

    Returns
    -------
    equal: bool
        Whether two dicts are the same.
    """

    if not isinstance(dict_a, dict) or not isinstance(dict_b, dict):
        return False
    if dict_a.keys() != dict_b.keys():
        return False
    for k, v in dict_a.items():
        if not isinstance(v, type(dict_b[k])):
            return False
        if isinstance(v, dict) and not dict_equal(v, dict_b[k]):
            return False
        if v != dict_b[k]:
            return False
    return True


def copy_dict(dict_obj: dict) -> dict:
    """深度复制字典对象，尝试使用copy.deepcopy,失败则手动递归复制

    Parameters
    ----------
    dict_obj: dict
        The source dict.

    Returns
    -------
    dict_obj: dict
        The copied dict.
    """

    if not dict_obj:
        return {}
    try:
        return copy.deepcopy(dict_obj)
    except:  # pylint: disable=bare-except
        new_dict = {}
        for k, v in dict_obj.items():
            if isinstance(v, (list, tuple)):
                new_dict[k] = [copy_dict(e) for e in v]
            elif isinstance(v, dict):
                new_dict[k] = copy_dict(v)
            else:
                new_dict[k] = v
        return new_dict


def map_dict(dict_obj: dict, mapper: callable) -> dict:
    """将映射器应用于字典对象
    对字典的所有值应用mapper函数
    递归处理嵌套字典和列表

    Parameters
    ----------
    dict_obj: dict
        The source dict.
    mapper: callable
        The mapper function.

    Returns
    -------
    new_dict: dict
        The mapped dict.
    """

    if not dict_obj:
        return {}
    new_dict = {}
    for k, v in dict_obj.items():
        # 列表/元组
        if isinstance(v, (tuple, list)):
            new_dict[k] = [
                map_dict(mapper(e), mapper) if isinstance(e, dict) else mapper(e)
                for e in v
            ]
        # 嵌套字典
        elif isinstance(v, dict):
            new_dict[k] = map_dict(mapper(v), mapper)
        # 普通值
        else:
            new_dict[k] = mapper(v)
    return new_dict
