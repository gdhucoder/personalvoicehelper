# main.py

import asyncio
from pathlib import Path

from voice_assistant.tasks.task_manager4 import AudioScheduler
from reminder_manager import ReminderManager

async def main():
    # 1) 初始化语音调度器（假设背景音乐目录在 ./mp3s）
    scheduler = AudioScheduler(mp3_dir=Path("../mp3s"), loop_playlist=True)
    asyncio.create_task(scheduler.loop())

    # 2) 初始化提醒管理器
    rm = ReminderManager(scheduler)

    # 示例：添加两个提醒
    rm.add("09:57", "开会了，请前往会议室")
    rm.add("16:20", "该休息了，别忘了放松一下")
    rm.add("16:20", "该休息了，别忘了放松一下")
    rm.add("16:20", "该休息了，别忘了放松一下")
    rm.add("16:20", "该休息了，别忘了放松一下")

    print("当前提醒列表：", rm.list())
    # 4. 通过序号删除第1条
    rm.remove(1)  # or rem_mgr.remove(1)
    print("当前提醒列表：", rm.list())

    for i, ent in enumerate(rm.list(),1):
        print(f"第{i}条， {ent.at_time}, {ent.message}")

    # 3) 你的其它逻辑…或者仅仅保持运行
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
