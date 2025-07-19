# speak_task.py

import configparser

from pydub import AudioSegment

from voice_assistant.tasks.task_manager4 import AsyncVoiceTask
from voice_assistant.player.mp3_player import MP3Player
from voice_assistant.utils.tts_utils import speech_synthesize
from voice_assistant.tasks.task_manager4 import AudioScheduler

import asyncio
import sys
from pathlib import Path

# （可选）全局配置，比如 TTS 缓存目录
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

class SpeakTextTask(AsyncVoiceTask):
    """
    通用播报任务：
      - text: 需要播报的文字
      - priority: 优先级（> background music）
      - resumable: False（完成后不自己恢复）
    """
    def __init__(
        self,
        text: str,
        *,
        priority: int = 10,
        resumable: bool = False
    ):
        super().__init__(name="SpeakText", priority=priority, resumable=resumable)
        self.text = text
        self.player: MP3Player | None = None
        # 记录入队时背景是否在播放
        self._was_playing: bool = False

    async def execute(self):
        # 1) 记录并中断背景播放
        if self.player is None:
            raise RuntimeError("播放器未注入")
        self._was_playing = bool(
            self.player.play_obj and self.player.play_obj.is_playing()
        )
        print(f"[SpeakTextTask] mp3播放器是否在播放：{self._was_playing}")
        # 2) 合成文字为 MP3（阻塞操作放 executor）
        loop = asyncio.get_running_loop()
        mp3_path: Path = await loop.run_in_executor(
            None,
            speech_synthesize,
            self.text
        )
        print(f"[SpeakTextTask] 合成完毕：{mp3_path.name}")

        # 3) 播放并恢复背景（内部会暂停）
        # 小延迟让 player 准备好
        await asyncio.sleep(0.05)
        print(f"[SpeakTextTask] 播报：{self.text!r}")
        # add 20250719
        if self._was_playing:
            self.player.pause()
            print(f"[SpeakTextTask] player.pause()")

        self.player.play_file(
            was_playing=self._was_playing,
            path=mp3_path,
            resume_playlist=True
        )

        # <—— 新增：根据文件时长同步等待
        seg = await asyncio.get_running_loop().run_in_executor(
            None, AudioSegment.from_file, mp3_path
        )
        duration_s = seg.duration_seconds
        # 多留一点缓冲
        await asyncio.sleep(duration_s + 0.1)
        print("[SpeakTextTask] 播报完成")


async def main():
    # 1) 初始化调度器，开启背景歌单循环（可选）
    scheduler = AudioScheduler(
        mp3_dir=Path("../mp3s"),
        loop_playlist=True
    )
    loop = asyncio.get_running_loop()
    # 启动调度器后台循环
    loop.create_task(scheduler.loop())

    # 2) 可选：先播放背景音乐，测试抢占和恢复
    print("▶️ 启动背景歌单播放")
    scheduler.audio_player.play()

    # 3) 等几秒后发出播报任务
    await asyncio.sleep(3)
    speak_text = "你好，这是对 SpeakTextTask 的一次测试。哎呦，可以呀！！！"
    task = SpeakTextTask(speak_text, priority=15)
    print(f"✨ 入队播报任务：{speak_text!r}")
    scheduler.enqueue(task)

    # 4) 等待任务真正启动
    while task._task is None:
        await asyncio.sleep(0.05)

    # 5) 等待播报任务完成
    try:
        await task._task
    except asyncio.CancelledError:
        pass

    print("✅ 播报任务已完成，退出 Demo")

    # 6) 关闭调度器
    # 取消后台 loop 并停止音乐
    scheduler.audio_player.stop()
    # 如果需要优雅退出，取消 loop 任务
    # loop_task.cancel()
    await asyncio.sleep(0.5)  # 给 stop() 留点时间

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)