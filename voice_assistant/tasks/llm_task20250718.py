# voice_assistant/tasks/llm_task.py

import asyncio
import threading
import pyaudio
from http import HTTPStatus
import dashscope
from dashscope import Generation
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback
import configparser
from voice_assistant.tasks.task_manager4 import AsyncVoiceTask

# 读取配置
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

dashscope.api_key = cfg.get('llmapi', 'aliyun_api_key')

# TTS 参数
TTS_MODEL = "cosyvoice-v2"
TTS_VOICE = "longxiaochun_v2"

# LLM 参数
LLM_MODEL = "qwen-turbo"



class _StreamCallback(ResultCallback):
    """
    1) 在 on_open 时只打开一次 PyAudio 输出流
    2) on_data 直接非阻塞写入
    3) on_close 时统一清理
    """
    def __init__(self):
        self._stop = threading.Event()
        self._player = None
        self._stream = None

    def on_open(self):
        # 只打开 output=True 的流，不打开 capture
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=22050,
            output=True,
            frames_per_buffer=1024  # 小 buffer，低延迟
        )

    def on_data(self, data: bytes):
        if self._stop.is_set():
            return
        # 非阻塞写入
        try:
            self._stream.write(data, exception_on_underflow=False)
        except Exception:
            pass

    def on_close(self):
        # 合成完成或打断后只做一次清理
        if self._stream:
            try: self._stream.stop_stream()
            except: pass


    def stop(self):
        # 打断合成：后续 on_data 直接丢弃
        self._stop.set()


class LLMConversationTask(AsyncVoiceTask):
    """
    流式 LLM + TTS 任务，可以通过 AsyncVoiceTask.cancel() 打断，
    打断后 on_close 会释放流；调度器 resume() 时再继续对话。
    """
    def __init__(self, messages: list[dict], ws_client):
        super().__init__(name="LLMChat", priority=3, resumable=False)
        self.messages = messages
        self._callback = None
        self._synthesizer = None
        self.ws_client = ws_client

    async def execute(self):
        loop = asyncio.get_running_loop()
        # 在 executor 中运行同步流式代码
        await loop.run_in_executor(None, self._run_stream)

    def _run_stream(self):
        # 准备回调和合成器
        self._callback = _StreamCallback()
        self._synthesizer = SpeechSynthesizer(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            format=AudioFormat.PCM_22050HZ_MONO_16BIT,
            callback=self._callback
        )

        # **无需 streaming_open()**

        # 调用 LLM + TTS 流
        responses = Generation.call(
            model=LLM_MODEL,
            messages=self.messages,
            stream=True,
            incremental_output=True,
            result_format="message"
        )
        final_response = ''
        for resp in responses:
            if self._cancel_event.is_set():
                break
            if resp.status_code == HTTPStatus.OK:
                text = resp.output.choices[0]["message"]["content"]
                # print(text, end="", flush=True)
                print(f"LLM Generate: {text}", end="\n")
                final_response += text

                self._synthesizer.streaming_call(text)
        self.ws_client.send_status_update('info', final_response)
        # 合成结束
        self._synthesizer.streaming_complete()
        # 回调关闭流
        self._callback.on_close()
        print('synthesizer requestId: ', self._synthesizer.get_last_request_id())

    async def pause(self):
        # 用户/系统抢占时打断当前合成
        if self._callback:
            self._callback.stop()
        await super().pause()

    async def cancel(self):
        # 彻底取消
        if self._callback:
            self._callback.stop()
        if self._synthesizer:
            self._synthesizer.streaming_complete()
        await super().cancel()
