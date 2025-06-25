# weather_task.py

import asyncio
import requests
import configparser
from pathlib import Path
from uuid import uuid4

from task_manager3 import AsyncVoiceTask, AudioScheduler

from voice_assistant.player.mp3_player import  MP3Player
from datetime import datetime


# 读取配置
cfg = configparser.ConfigParser()
cfg.read('../../env/config.ini')

def generate_tts_mp3(text: str, out_dir: Path = Path("/tmp")) -> Path:

    return None

class WeatherTask(AsyncVoiceTask):
    """
    三步任务流：
      1) 查询天气
      2) TTS 生成 MP3
      3) 中断歌单播放并播放 TTS，结束后恢复
    """
    def __init__(self, player: MP3Player):
        super().__init__(name="Weather", priority=10, resumable=False)
        self.player = player
        self.api_key =  cfg.get('weather', 'api_key')
        self.base_url =  cfg.get('weather', 'base_url')


    async def execute(self):
        # --- 1) 查询天气 ---
        weather = await self._query_weather()
        print(f"[WeatherTask] API 返回: {weather}")

        # --- 2) 生成 TTS MP3 ---
        tts_file = await asyncio.get_running_loop().run_in_executor(
            None, generate_tts_mp3, weather
        )
        print(f"[WeatherTask] 生成 TTS 文件: {tts_file.name}")

        # --- 3) 播放 TTS 并自动恢复歌单 ---
        self.player.play_file(tts_file, resume_playlist=True)
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
        timestamp = now.strftime('%m月%d日 %H时%M分')
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

        return weather_shenzhen

# 使用示例
if __name__ == "__main__":
    import asyncio

    # 初始化播放器（后台歌单）
    player = MP3Player(list(Path("../mp3s").glob("*.mp3")), loop=True)
    scheduler = AudioScheduler()

    async def main():
        # 启动歌单
        player.play()
        # 启动调度器
        asyncio.create_task(scheduler.loop())
        # Enqueue 天气任务
        scheduler.enqueue(WeatherTask(player))
        # 等待完成
        await asyncio.sleep(10)

    asyncio.run(main())
