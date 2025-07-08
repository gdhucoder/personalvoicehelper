import asyncio
import requests
import configparser
from pathlib import Path
from uuid import uuid4

from voice_assistant.tasks.task_manager4 import AsyncVoiceTask, AudioScheduler

from voice_assistant.player.mp3_player import  MP3Player
from datetime import datetime
from voice_assistant.utils.tts_utils    import speech_synthesize


class PlayAudioTask(AsyncVoiceTask):
    """
    简单任务：播放一个指定的 MP3 文件
    """
    def __init__(self, audio_path: Path, was_playing=False):
        super().__init__(name="PlayAudio", priority=5, resumable=False)
        self.player = None
        self.audio_path = audio_path
        self.was_playing = was_playing

    async def execute(self):
        print(f"[PlayAudioTask] 开始播放音频：{self.audio_path}")
        self.player.play_file(self.was_playing, self.audio_path, resume_playlist=True)
        print("[PlayAudioTask] 播放完成")