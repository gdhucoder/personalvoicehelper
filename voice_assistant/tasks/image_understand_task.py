# weather_task.py

import asyncio
import requests
import configparser
from pathlib import Path
from uuid import uuid4

from voice_assistant.tasks.task_manager4 import AsyncVoiceTask, AudioScheduler

from voice_assistant.player.mp3_player import  MP3Player
from datetime import datetime
from voice_assistant.utils.tts_utils    import speech_synthesize
from voice_assistant.utils.image_utils import img_to_base64_uri
from dashscope import MultiModalConversation

import os, glob
import dashscope

# 读取配置
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

# 如未配置环境变量，可直接写死
dashscope.api_key = cfg.get('llmapi', 'aliyun_api_key')
IMAGE_DIR = cfg.get('image', 'upload_dir')

class ImageUnderstandTask(AsyncVoiceTask):
    """
    三步任务流：
      1) 查询天气
      2) TTS 生成 MP3
      3) 中断歌单播放并播放 TTS，结束后恢复
    """
    def __init__(self, was_playing=False, prompt = "这个图里有什么", ws_client=None):
        super().__init__(name="Weather", priority=15, resumable=False)
        self.player = None
        self.was_playing = was_playing
        self.ws_client = ws_client
        self.prompt = prompt


    async def execute(self):
        # --- 1) 查询天气 ---
        latest_file = max(glob.glob(f"{IMAGE_DIR}/*"), key=os.path.getmtime)
        result = await self._understand(latest_file, self.prompt)
        self.ws_client.send_status_update('info', f"{result}")
        print(f"[ImageUnderstandTask] 图片理解结果：{result}")

    async def _understand(self, image_path: str, prompt: str) -> str:
        # 本地图片需 file:// 协议
        print(image_path)
        local_url = img_to_base64_uri(image_path)
        messages = [
            {"role": "system", "content": [{"text": "You are a helpful assistant."}]},
            {
                "role": "user",
                "content": [
                    {"image": local_url},
                    {"text": prompt}
                ]
            }
        ]
        response = MultiModalConversation.call(
            # model = "qwen-vl-plus",
            model="qwen2.5-vl-3b-instruct",  # 也可换成 qwen2.5-vl-3b-instruct
            messages=messages
        )
        print(response)
        result = response["output"]["choices"][0]["message"]["content"][0]["text"]

        return result

# 使用示例
if __name__ == "__main__":

    import sys

    # 1) mp3 目录，可放几首 mp3 做背景歌单，也可留空
    MP3_DIR = Path("/home/hugd/privateprojects/personalvoicehelper/voice_assistant/mp3s")

    # 2) 初始化调度器，不自动播放背景歌单
    scheduler = AudioScheduler(mp3_dir=MP3_DIR, loop_playlist=False)


    async def main():
        # 启动调度器循环
        loop_task = asyncio.create_task(scheduler.loop())

        # 3) 创建并入队 WeatherTask
        wt = ImageUnderstandTask()
        scheduler.enqueue(wt)
        # 等待完成
        await asyncio.sleep(120)

        # 4) 等待任务真正启动
        while wt._task is None:
            await asyncio.sleep(0.05)
        # 5) 等待 WeatherTask 执行结束
        try:
            await wt._task
        except asyncio.CancelledError:
            pass

        print("✅ ImageUnderstandTask 已完成，退出程序")
        # 取消调度器 loop 并退出
        loop_task.cancel()


    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)