import pvporcupine
import pyaudio
import struct
import configparser
from datetime import datetime

import asyncio
import threading
import time
from pathlib import Path
# 来自前面示例
from voice_assistant.tasks.task_manager4 import AudioScheduler, PlayMusicTask
from voice_assistant.tasks.weather_task2 import WeatherTask

from voice_assistant.recognize_speech import recognize_speech

# config parser
config = configparser.ConfigParser()
# load config
config.read('../env/config.ini')

porcupine_access_key = config.get('listener', 'pvporcupine_access_key') # key

custom_keyword_franky_path = config.get('listener', 'custom_keyword_franky')




porcupine = pvporcupine.create(keyword_paths=[custom_keyword_franky_path],
                               keywords=["franky"],
                               access_key=porcupine_access_key,
                               sensitivities=[0.7])

pa = pyaudio.PyAudio()

audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length)

def wake_and_recognize(loop: asyncio.AbstractEventLoop, scheduler: AudioScheduler):
    print("Listening for 'picovoice'...")

    try:
        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            result = porcupine.process(pcm)

            if result >= 0:
                # 获取当前日期和时间
                now = datetime.now()
                # 格式化为字符串
                formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
                print(f'🔔{formatted_date} 唤醒词检测到！执行唤醒动作...')

                from voice_assistant.recognize_speech.recognize_speech import recoginze_speech
                recognized_command = recoginze_speech(audio_stream, timeout=3)

                print(recognized_command)

                # 调用你助手的主逻辑模块
                # 简单命令解析 —— 播放音乐
                text = recognized_command
                if "play" in text or "音乐" in text:
                    # 在 asyncio 调度器中创建任务
                    # 安全地把 MusicTask 加入主线程的 asyncio 调度器
                    loop.call_soon_threadsafe(scheduler.enqueue, PlayMusicTask())
                elif "暂停" in text or "pause" in text:
                    # 在主循环里创建一个 pause() 的协程任务
                    if isinstance(scheduler.running, PlayMusicTask):
                        loop.call_soon_threadsafe(asyncio.create_task,
                                              scheduler.running.pause())
                elif "继续" in text or "resume" in text:
                    if isinstance(scheduler.running, PlayMusicTask):
                        loop.call_soon_threadsafe(
                            asyncio.create_task,
                            scheduler.running.resume()
                        )
                elif "下一曲" in text or "next" in text:
                    if isinstance(scheduler.running, PlayMusicTask):
                        scheduler.running.cmd_next()
                elif "上一曲" in text or "previous" in text:
                    if isinstance(scheduler.running, PlayMusicTask):
                        scheduler.running.cmd_prev()
                elif "停止" in text or "stop" in text:
                    if isinstance(scheduler.running, PlayMusicTask):
                        loop.call_soon_threadsafe(
                            asyncio.create_task,
                            scheduler.running.cmd_stop()
                        )
                elif "天气" in text or "weather" in text:
                    # 将 WeatherTask 加入调度器
                    loop.call_soon_threadsafe(
                        scheduler.enqueue,
                        WeatherTask()
                    )
                time.sleep(1)

    except KeyboardInterrupt:
        print("关闭中...")

    finally:
        audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()
        porcupine.delete()


# === 5. 启动 ===
async def main():
    scheduler = AudioScheduler(mp3_dir=Path("../voice_assistant/mp3s"), loop_playlist=True)
    # 启动调度器循环
    asyncio.create_task(scheduler.loop())

    # 获取当前事件循环并传入识别线程
    loop = asyncio.get_running_loop()
    threading.Thread(target=wake_and_recognize, args=(loop, scheduler), daemon=True).start()

    # 主协程不退出
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())