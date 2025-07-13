# tts_task.py

import asyncio
import configparser
from pathlib import Path

from voice_assistant.tasks.task_manager4 import AsyncVoiceTask, AudioScheduler
from voice_assistant.player.mp3_player import MP3Player
from voice_assistant.utils.tts_utils import speech_synthesize

# 读取全局配置（可选，用于获取 TTS 目录等）
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

class TTSTask(AsyncVoiceTask):
    """
    单步 TTS 播报任务：
      1) 将传入的 text 合成为 mp3
      2) 播放该 mp3，期间暂停背景歌单
      3) 播放结束后恢复歌单（如果调用前在播放）
    """
    def __init__(self, text: str, was_playing: bool = False):
        super().__init__(name="TTS", priority=10, resumable=False)
        self.text = text
        self.was_playing = was_playing
        self.player: MP3Player | None = None

    async def execute(self):
        # 在 executor 中调用阻塞的合成函数
        loop = asyncio.get_running_loop()
        mp3_path = await loop.run_in_executor(None, speech_synthesize, self.text)
        print(f"[TTSTask] 合成完成，文件：{mp3_path}")

        # 播放 TTS 文件
        # 延迟少许确保播放器已注入
        await asyncio.sleep(0.1)
        if self.player is None:
            raise RuntimeError("MP3Player 未注入")
        print(f"[TTSTask] 开始播报：{self.text!r}")
        self.player.play_file(self.was_playing, mp3_path, resume_playlist=True)
        print("[TTSTask] 播报结束")

# ——————————————————————————————————————
# 使用示例
if __name__ == "__main__":
    import sys

    # 初始化：背景歌单目录，可留空或指定
    MP3_DIR = Path("/home/hugd/privateprojects/personalvoicehelper/voice_assistant/mp3s")
    scheduler = AudioScheduler(mp3_dir=MP3_DIR, loop_playlist=True)

    async def main():
        # 启动调度器
        loop_task = asyncio.create_task(scheduler.loop())

        # 假设背景正在播放
        print("▶️ 启动背景歌单播放")
        # scheduler.audio_player.play()

        # 等 2s 后插入 TTS 任务
        await asyncio.sleep(2)
        was_playing = bool(scheduler.audio_player.play_obj and scheduler.audio_player.play_obj.is_playing())
        tts_text = "你好，这是一次语音合成测试。"
        tts_task = TTSTask(tts_text, was_playing=was_playing)
        scheduler.enqueue(tts_task)

        # 等待任务完成
        while tts_task._task is None:
            await asyncio.sleep(10)
        try:
            await tts_task._task
        except asyncio.CancelledError:
            pass

        print("✅ TTSTask 已完成，退出程序")
        loop_task.cancel()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
