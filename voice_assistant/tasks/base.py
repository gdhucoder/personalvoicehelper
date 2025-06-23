import asyncio
import heapq


import asyncio

class AsyncVoiceTask:
    def __init__(self, name: str, priority: int, preemptive: bool = False):
        self.name = name
        self.priority = priority
        self.preemptive = preemptive
        self._cancel_event = asyncio.Event()
        self._paused_event = asyncio.Event()
        self._paused_event.set()  # 默认未暂停

    def pause(self):
        self._paused_event.clear()

    def resume(self):
        self._paused_event.set()

    def cancel(self):
        self._cancel_event.set()

    async def execute(self):
        raise NotImplementedError("请在子类中实现")


class PlayMusicTask(AsyncVoiceTask):
    async def execute(self):
        print(f"[Music] Playing {self.name}")
        for i in range(20):
            await asyncio.sleep(0.2)
            await self._paused_event.wait()
            if self._cancel_event.is_set():
                print(f"[Music] Canceled: {self.name}")
                return
            print(f"[Music] ... {i}")
        print(f"[Music] Finished: {self.name}")

class TTSPlaybackTask(AsyncVoiceTask):
    async def execute(self):
        print(f"[TTS] Speaking: {self.name}")
        for i in range(5):
            await asyncio.sleep(0.2)
            if self._cancel_event.is_set():
                print(f"[TTS] Canceled: {self.name}")
                return
        print(f"[TTS] Finished: {self.name}")