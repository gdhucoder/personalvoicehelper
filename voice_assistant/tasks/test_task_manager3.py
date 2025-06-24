# test_scheduler.py
import asyncio
import time
from pathlib import Path

from task_manager3 import AudioScheduler,PlayMusicTask

async def test_playback_flow():
    print("=== 测试: 播放流程开始 ===")
    scheduler = AudioScheduler()
    # 启动调度器主循环
    loop_task = asyncio.create_task(scheduler.loop())

    # 1) Enqueue 播放任务
    mp3_dir = Path("../mp3s")
    play_task = PlayMusicTask(mp3_dir)
    print(">>> Enqueue PlayMusicTask")
    scheduler.enqueue(play_task)

    # 等待播放开始
    await asyncio.sleep(3)

    # 2) 测试暂停
    print(">>> cmd_pause()")
    play_task.cmd_pause()
    await asyncio.sleep(3)

    # 3) 测试恢复
    print(">>> cmd_resume()")
    play_task.cmd_resume()
    await asyncio.sleep(3)

    # 4) 测试下一曲
    print(">>> cmd_next()")
    play_task.cmd_next()
    await asyncio.sleep(3)

    # 5) 测试上一曲
    print(">>> cmd_prev()")
    play_task.cmd_prev()
    await asyncio.sleep(3)

    # 6) **测试音量调节**
    print(">>> cmd_vol_up()")
    play_task.cmd_vol_up()
    await asyncio.sleep(3)
    print(">>> cmd_vol_down()")
    play_task.cmd_vol_down()
    await asyncio.sleep(3)

    # 7) 测试停止
    print(">>> cmd_stop()")
    play_task.cmd_stop()
    await asyncio.sleep(3)

    # 8) 测试可重复使用
    print(">>> 再次 Enqueue PlayMusicTask")
    scheduler.enqueue(PlayMusicTask(mp3_dir))
    await asyncio.sleep(3)
    print(">>> cmd_stop() (再次停止)")
    if isinstance(scheduler.running, PlayMusicTask):
        scheduler.running.cmd_stop()
    await asyncio.sleep(3)

    loop_task.cancel()
    print("=== 测试结束 ===")


def main():
    asyncio.run(test_playback_flow())

if __name__ == "__main__":
    main()
