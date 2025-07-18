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

# 读取配置
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

class WeatherTask(AsyncVoiceTask):
    """
    三步任务流：
      1) 查询天气
      2) TTS 生成 MP3
      3) 中断歌单播放并播放 TTS，结束后恢复
    """
    def __init__(self, was_playing=False, ws_client=None):
        super().__init__(name="Weather", priority=10, resumable=False)
        self.player = None
        self.api_key =  cfg.get('weather', 'api_key')
        self.base_url =  cfg.get('weather', 'base_url')
        self.was_playing = was_playing
        self.ws_client = ws_client


    async def execute(self):
        # --- 1) 查询天气 ---
        weather_text = await self._query_weather()
        print(f"[WeatherTask] API 返回: {weather_text}")

        # --- 2) 生成 TTS MP3 ---
        tts_file = await asyncio.get_running_loop().run_in_executor(
            None, speech_synthesize, weather_text
        )
        print(f"[WeatherTask] 生成 TTS 文件: {tts_file.name}")

        # --- 3) 播放 TTS 并自动恢复歌单 ---
        # 假设你的 MP3Player 有 is_playing() 方法
        self.player.play_file(self.was_playing,tts_file, resume_playlist=True)
        print("[WeatherTask] 播放 TTS，任务完成")

    async def _query_weather(self) -> str:
        """获取深圳市的当前天气信息"""
        city = "Shenzhen"  # 城市名称
        params = {
            "q": city,  # 查询城市
            "appid": self.api_key,  # API 密钥
            "units": "metric",  # 温度单位：metric 表示摄氏度
            "lang": "zh_cn"  # 返回中文描述
        }
        # 获取当前时间
        now = datetime.now()

        # 格式化时间戳
        # timestamp = now.strftime('%m月%d日 %H时%M分')
        timestamp = now.strftime('%m月%d日 %H时')
        # 发送 HTTP 请求
        response = requests.get(self.base_url, params=params)
        weather_shenzhen = ""
        # 检查响应状态
        if response.status_code == 200:
            data = response.json()
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]

            # 提取天气信息
            temp = int(main.get("temp"))  # 当前温度
            feels_like = int(main.get("feels_like"))  # 体感温度
            humidity = int(main.get("humidity"))  # 湿度
            description = weather.get("description")  # 天气描述

            # 输出天气信息
            print(f"深圳市当前天气：")
            print(f"温度：{temp}°C")
            print(f"体感温度：{feels_like}°C")
            print(f"湿度：{humidity}%")
            print(f"天气状况：{description}")

            weather_shenzhen = f"今日是：{timestamp}，深圳市当前天气情况：{description}，温度：{temp}度，体感温度：{feels_like}度，湿度百分之：{humidity}。"
            print(weather_shenzhen)
            self.ws_client.send_status_update('info', weather_shenzhen)

        return weather_shenzhen

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
        wt = WeatherTask()
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

        print("✅ WeatherTask 已完成，退出程序")
        # 取消调度器 loop 并退出
        loop_task.cancel()


    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)