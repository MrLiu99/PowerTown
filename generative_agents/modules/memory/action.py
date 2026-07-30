"""generative_agents.memory.action"""

import datetime

from modules import utils
from .event import Event


class Action:
    def __init__(
        self,
        event,
        obj_event=None,
        start=None,
        duration=0,
    ):
        self.event = event #主要事件，如喝咖啡
        self.obj_event = obj_event # 次要事件，如喝咖啡的地点、对象等
        self.start = start or utils.get_timer().get_date()  # 开始时间
        self.duration = duration        # 持续时间，单位分钟
        self.end = self.start + datetime.timedelta(minutes=self.duration)   # 结束时间

    def abstract(self):
        # 状态表述
        status = "{} [{}~{}]".format(
            "已完成" if self.finished() else "进行中",
            self.start.strftime("%Y%m%d-%H:%M"),
            self.end.strftime("%Y%m%d-%H:%M"),
        )
        info = {"status": status, "event": str(self.event)}
        if self.obj_event:
            info["object"] = str(self.obj_event)
        #返回结构化信息
        return info

    def __str__(self):
        return utils.dump_dict(self.abstract())

    def finished(self):
        if not self.duration: #瞬时行为 self.duration=0
            return True
        if not self.event.address: #没有地点信息，即虚拟行动，如思考
            return True
        return utils.get_timer().get_date() > self.end #当前时间大于结束时间

    def to_dict(self):
        return {
            "event": self.event.to_dict(),
            "obj_event": self.obj_event.to_dict() if self.obj_event else None,
            "start": self.start.strftime("%Y%m%d-%H:%M:%S"),
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, config):
        config["event"] = Event.from_dict(config["event"])
        if config.get("obj_event"):
            config["obj_event"] = Event.from_dict(config["obj_event"])
        config["start"] = utils.to_date(config["start"])
        return cls(**config)
