# reminder_manager.py

import threading
import time
import uuid
import schedule
from typing import Dict, List, Union
from datetime import datetime

from voice_assistant.tasks.speak_task import SpeakTextTask
from voice_assistant.tasks.task_manager4 import AudioScheduler

class Reminder:
    def __init__(self, at_time: str, message: str):
        """
        :param at_time: "HH:MM" 格式的 24h 时间
        :param message: 提醒内容
        """
        self.id      = str(uuid.uuid4())[:8]
        self.at_time = at_time
        self.message = message

    def __repr__(self):
        return f"<Reminder {self.id} @ {self.at_time} → {self.message!r}>"

class ReminderManager:
    def __init__(self, scheduler: AudioScheduler):
        self.scheduler = scheduler
        self.reminders: Dict[str, Reminder] = {}
        self.jobs:      Dict[str, schedule.Job] = {}

        # 启动后台线程运行 schedule
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()

    def _run_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def add(self, at_time: str, message: str) -> str:
        """
        添加一个新提醒，返回该提醒的 id
        """
        r = Reminder(at_time, message)
        job = schedule.every().day.at(r.at_time).do(self._fire, r.id)
        self.reminders[r.id] = r
        self.jobs[r.id] = job
        print(f"[ReminderManager] Added {r}")
        return r.id

    def list(self) -> List[Reminder]:
        """
        返回当前所有提醒列表，保持插入顺序
        """
        return list(self.reminders.values())

    def remove(self, key: Union[str, int]) -> bool:
        """
        删除一个提醒，key 可以是 uuid str 或者 1-based 的序号(int or digit string)
        返回 True/False
        """
        # 如果是数字，转成对应的 uuid
        if isinstance(key, str) and key.isdigit():
            idx = int(key) - 1
            keys = list(self.reminders.keys())
            if 0 <= idx < len(keys):
                rid = keys[idx]
            else:
                return False
        elif isinstance(key, int):
            keys = list(self.reminders.keys())
            if 0 <= key-1 < len(keys):
                rid = keys[key-1]
            else:
                return False
        else:
            rid = key  # assume it's the uuid

        if rid not in self.reminders:
            return False

        # 取消 schedule job
        job = self.jobs.pop(rid)
        schedule.cancel_job(job)
        # 删除数据
        r = self.reminders.pop(rid)
        print(f"[ReminderManager] Removed {r}")
        return True

    def _fire(self, rid: str):
        """
        schedule 到点后调用，把提醒交给语音助手播报
        """
        r = self.reminders.get(rid)
        if not r:
            return
        now = datetime.now().strftime("%H点%M分")
        text = f"现在是{now}，提醒您：{r.message}"
        print(f"[ReminderManager] 🔔 Fire {r}")
        # 播报一次后，如果想每天重复就注释掉 next 两行
        self.scheduler.enqueue(SpeakTextTask(text, priority=20,resumable=True))
        # 如果只提醒一次，取消并移除
        # schedule.cancel_job(self.jobs.pop(rid))
        # self.reminders.pop(rid, None)
