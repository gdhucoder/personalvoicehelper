import pvporcupine
import pyaudio
import struct
import configparser
from datetime import datetime

import asyncio
import threading
import time
from pathlib import Path

from voice_assistant.reminder.reminder_manager import ReminderManager
# 来自前面示例
from voice_assistant.tasks.task_manager4 import AudioScheduler, PlayMusicTask
from voice_assistant.tasks.weather_task20250718 import WeatherTask
from voice_assistant.tasks.play_audio_task import PlayAudioTask
from voice_assistant.tasks.llm_task20250718 import LLMConversationTask
from voice_assistant.tasks.speak_task import SpeakTextTask


# nul parser
from voice_assistant.nlu.nlu import CommandParser


from voice_assistant.recognize_speech import recognize_speech
from voice_assistant.web_server.send_socketinfo import WebSocketClient

class AssistantController:
    def __init__(self, config_path: str, mp3_dir: Path):
        # ——— 读取配置 ———
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        self._wake_key     = cfg.get('listener', 'pvporcupine_access_key')
        self._keyword_path = cfg.get('listener', 'custom_keyword_franky')
        self._confirm_mp3  = Path(cfg.get('listener', 'confirm_mp3_path'))

        # ——— 调度器 & 相关组件 ———
        self.scheduler = AudioScheduler(mp3_dir=mp3_dir, loop_playlist=True)
        self.parser    = CommandParser()
        self.rem_mgr   = ReminderManager(self.scheduler)
        self._last_chat = None  # 用于取消老的 LLM 任务

        # ——— Porcupine 唤醒 & PyAudio ———
        self.porcupine = pvporcupine.create(
            keyword_paths=[self._keyword_path],
            access_key=self._wake_key,
            sensitivities=[0.7]
        )
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

        # ——— WebSocket 客户端 ———
        self.ws = WebSocketClient(on_event_callback=self._on_ws_command)
        self.ws.connect()

        self.loop = None

    def start(self):
        """启动调度器循环与语音监听线程"""
        # 1) 保存主线程的 event loop
        self.loop = asyncio.get_event_loop()

        # 2) 启动 scheduler
        self.loop.create_task(self.scheduler.loop())

        # 3) 启动语音唤醒线程
        threading.Thread(
            target=self._voice_loop,
            args=(self.loop,),
            daemon=True
        ).start()

    def _on_ws_command(self, data: str):
        """WebSocket 收到的文本指令也交给同一套处理流程"""
        print(f"[WebSocket] recv: {data!r}")
        # 直接交给 asyncio 线程安全地调度
        self.loop.call_soon_threadsafe(self._handle_command, data)

    def _voice_loop(self, loop: asyncio.AbstractEventLoop):
        """阻塞式唤醒词 + 语音识别主循环"""
        print("▶️ Voice listener started, waiting for wakeword...")
        while True:
            pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            if self.porcupine.process(pcm) >= 0:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] 🔔 Wakeword detected")
                # 播放确认音
                was_playing = bool(self.scheduler.audio_player.play_obj and
                                   self.scheduler.audio_player.play_obj.is_playing())
                loop.call_soon_threadsafe(
                    self.scheduler.enqueue,
                    PlayAudioTask(self._confirm_mp3, was_playing=was_playing)
                )
                from voice_assistant.recognize_speech.recognize_speech import recoginze_speech
                # 识别一轮命令
                cmd = recoginze_speech(self.audio_stream, timeout=3)
                if cmd:
                    print(f"🗣️ Recognized: {cmd!r}")
                    loop.call_soon_threadsafe(self._handle_command, cmd)
                # 避免连环触发
                time.sleep(0.5)

    def _handle_command(self, text: str):
        """
        NLU 解析 + 分发：
          - music / weather / tts / chat_with_ai / reminders / date / time...
        """
        intent, params = self.parser.parse(text)
        print(f"➡️ Intent={intent}, Params={params}")

        if intent == "play_music":
            # 在 asyncio 调度器中创建任务
            # 安全地把 MusicTask 加入主线程的 asyncio 调度器
            self.scheduler.enqueue( PlayMusicTask())
            self.ws.send_status_update('info', f"开始播放")
        elif intent == "pause_music":
            # 在主循环里创建一个 pause() 的协程任务
            # 直接暂停播放器
            self.scheduler.audio_player.pause()
            self.ws.send_status_update('info', f"音乐已暂停")
        elif intent == "resume_music":
            self.scheduler.audio_player.play()
            self.ws.send_status_update('info', f"开始播放")
        elif intent == "next_track":
            self.scheduler.audio_player.next()
            self.ws.send_status_update('info', f"下一曲")
        elif intent == "prev_track":
            self.scheduler.audio_player.prev()
            self.ws.send_status_update('info', f"上一曲")
        elif intent == "stop_music":
            # 停掉任务并停止播放器
            self.scheduler.audio_player.pause()
            self.ws.send_status_update('info', f"停止播放")
        if intent == "chat_with_ai":
            # 构造对话历史
            if self._last_chat:
                self.scheduler.cancel_task(self._last_chat)
            # self.ws.send_status_update('info', f"您说的是：{text}")
            message = [{
                         "role": "user",
                         "content": text
                       },
                        {
                            "role": "system",
                            "content": "所有回答请务必在30个汉字以内"
                        },
            ]
            task = LLMConversationTask(message, self.ws)
            # 将 LLM 对话任务注入
            self._last_chat = task
            self.scheduler.enqueue(task)
        # 关于提醒
        elif intent == "add_reminder":
            when = params['when']
            at_time = params['when'].strftime("%H:%M")
            txt = params['text']
            msg = f"已为您设置提醒：{when.hour}点，{when.minute}分，{txt}"
            self.ws.send_status_update('info', msg)
            self.rem_mgr.add(at_time, f"提醒：{when.hour}点，{when.minute}分，{txt}")

            self.scheduler.enqueue(SpeakTextTask(msg))
        elif intent == "remove_reminder":
            idx = params['idx']
            ok = self.rem_mgr.remove(idx)
            msg = ok and f"已删除第{idx}条提醒" or "未找到提醒"

            self.ws.send_status_update('info', msg)
            self.scheduler.enqueue(SpeakTextTask(msg))
        elif intent == "list_reminders":
            lst = self.rem_mgr.list()
            if not lst:
                self.scheduler.enqueue( SpeakTextTask("当前没有待提醒事项"))
            for i, rm in enumerate(lst, 1):
                reminder_txt = f"第{i}条， {rm.at_time}, {rm.message}"
                self.ws.send_status_update('info', reminder_txt)
                self.scheduler.enqueue( SpeakTextTask(reminder_txt))
        elif intent == "weather":
            # 将 WeatherTask 加入调度器
            was_playing = self.scheduler.audio_player.play_obj and self.scheduler.audio_player.play_obj.is_playing()
            print(f"was_playing: {was_playing}")
            self.scheduler.enqueue(
                WeatherTask(was_playing=was_playing, ws_client=self.ws)
            )
            self.ws.send_status_update('info', "正在播报天气")
        elif intent == "get_date":
            # 将 WeatherTask 加入调度器
            self.scheduler.enqueue(
                SpeakTextTask(params['date_text'])
            )
            self.ws.send_status_update('info', f"当前日期：{params['date_text']}")
        elif intent == "get_time":
            # 将 WeatherTask 加入调度器
            self.scheduler.enqueue(
                SpeakTextTask(params['time_text'])
            )
            self.ws.send_status_update('info', f"当前时间：{params['time_text']}")

if __name__ == "__main__":
    import sys

    # 1) 配置文件路径 & MP3 歌单目录
    cfg_path = "../env/config.ini"
    mp3_dir  = Path("../voice_assistant/mp3s")

    # 2) 初始化调度器
    controller = AssistantController(cfg_path, mp3_dir)

    # 3) 启动
    controller.start()

    # 4) 保持主协程运行
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)