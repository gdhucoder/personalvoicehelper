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
from voice_assistant.tasks.play_audio_task import PlayAudioTask
from voice_assistant.tasks.llm_task import LLMConversationTask
from voice_assistant.tasks.speak_task import SpeakTextTask


# nul parser
from voice_assistant.nlu.nlu import CommandParser


from voice_assistant.recognize_speech import recognize_speech

# config parser
config = configparser.ConfigParser()
# load config
config.read('../env/config.ini')

porcupine_access_key = config.get('listener', 'pvporcupine_access_key') # key

custom_keyword_franky_path = config.get('listener', 'custom_keyword_franky')

confirm_mp3_path = config.get('listener', 'confirm_mp3_path')


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
    nlu_parser = CommandParser()

    in_chat_session = False
    chat_session_history = []

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

                _was_playing = scheduler.audio_player.play_obj and scheduler.audio_player.play_obj.is_playing()
                print(f"_was_playing: {_was_playing}")

                confirm_mp3 = Path(confirm_mp3_path)
                loop.call_soon_threadsafe(
                    scheduler.enqueue,
                    PlayAudioTask(confirm_mp3, was_playing=_was_playing)
                )

                from voice_assistant.recognize_speech.recognize_speech import recoginze_speech
                recognized_command = recoginze_speech(audio_stream, timeout=3)
                print(f"🗣️ 识别到: {recognized_command!r}")
                # 2) call NLU
                intent, params = nlu_parser.parse(recognized_command)
                print(f"🔍 识别意图：Intent={intent}, Params={params}")

                # 调用你助手的主逻辑模块
                # 简单命令解析 —— 播放音乐
                text = recognized_command
                if intent == "play_music":
                    # 在 asyncio 调度器中创建任务
                    # 安全地把 MusicTask 加入主线程的 asyncio 调度器
                    loop.call_soon_threadsafe(scheduler.enqueue, PlayMusicTask())
                elif intent == "pause_music":
                    # 在主循环里创建一个 pause() 的协程任务
                    # 直接暂停播放器
                    loop.call_soon_threadsafe(scheduler.pause_music)
                elif intent == "resume_music":
                    loop.call_soon_threadsafe(scheduler.resume_music)
                elif intent == "next_track":
                    loop.call_soon_threadsafe(scheduler.next_track)
                elif intent == "prev_track":
                    loop.call_soon_threadsafe(scheduler.prev_track)
                elif intent == "stop_music":
                    # 停掉任务并停止播放器
                    loop.call_soon_threadsafe(scheduler.audio_player.pause_music)
                if intent == "chat_with_ai":
                    # 构造对话历史
                    history = [{"role": "user", "content": recognized_command}]
                    # 将 LLM 对话任务注入
                    loop.call_soon_threadsafe(scheduler.enqueue, LLMConversationTask(history))
                elif intent == "weather":
                    # 将 WeatherTask 加入调度器
                    was_playing = scheduler.audio_player.play_obj and scheduler.audio_player.play_obj.is_playing()
                    print(f"was_playing: {was_playing}")
                    loop.call_soon_threadsafe(
                        scheduler.enqueue,
                        WeatherTask(was_playing=was_playing)
                    )
                elif intent == "get_date":
                    # 将 WeatherTask 加入调度器
                    loop.call_soon_threadsafe(
                        scheduler.enqueue,
                        SpeakTextTask(params['date_text'])
                    )
                elif intent == "get_time":
                    # 将 WeatherTask 加入调度器
                    loop.call_soon_threadsafe(
                        scheduler.enqueue,
                        SpeakTextTask(params['time_text'])
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