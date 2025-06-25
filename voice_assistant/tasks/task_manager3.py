import asyncio, heapq, time
from typing import Optional
from voice_assistant.player.mp3_player import  MP3Player
from pathlib import Path
from typing import List, Optional

# from voice_assistant.tasks.base import AsyncVoiceTask
class AsyncVoiceTask:
    def __init__(self, name: str, priority: int = 1, resumable: bool = True):
        self.name = name
        self.priority = priority
        self.resumable = resumable
        self._paused_event = asyncio.Event()
        self._cancel_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def execute(self):
        raise NotImplementedError

    async def run(self):
        try:
            await self.execute()
        except asyncio.CancelledError:
            pass

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self.run())
        return self._task

    async def pause(self):
        self._paused_event.set()

    async def resume(self):
        self._paused_event.clear()

    async def cancel(self):
        self._cancel_event.set()
        if self._task:
            self._task.cancel()

class AudioScheduler:
    def __init__(self):
        self.running: Optional[AsyncVoiceTask] = None
        self.paused_stack: List[AsyncVoiceTask] = []
        self.queue: List[tuple[int, AsyncVoiceTask]] = []

    def enqueue(self, task: AsyncVoiceTask):
        heapq.heappush(self.queue, (-task.priority, task))

    async def loop(self):
        while True:
            # start next if idle
            if self.running is None and self.queue:
                _, nxt = heapq.heappop(self.queue)
                nxt.start()
                self.running = nxt

            # preempt if higher priority arrives
            if self.running and self.queue:
                top_pri, top_task = self.queue[0]
                if -top_pri > self.running.priority:
                    heapq.heappop(self.queue)
                    await self.running.pause()
                    if self.running.resumable:
                        self.paused_stack.append(self.running)
                    self.running = top_task
                    top_task.start()

            # if done, resume last paused
            if self.running and self.running._task.done():
                self.running = None
                while self.paused_stack and self.running is None:
                    prev = self.paused_stack.pop()
                    await prev.resume()
                    self.running = prev

            await asyncio.sleep(0.05)





class PlayMusicTask(AsyncVoiceTask):
    def __init__(self, music_dir: Path):
        super().__init__(name="PlayMusic", priority=1, resumable=True)
        files = sorted(music_dir.glob("*.mp3"))
        if not files:
            raise FileNotFoundError(f"No mp3 under {music_dir}")
        self.player = MP3Player(files, loop=True)

    async def execute(self):
        print(f"[MusicTask] start, {len(self.player.files)} tracks")
        self.player.play()
        while True:
            if self._cancel_event.is_set():
                self.player.stop()
                print("[MusicTask] canceled")
                return
            if self._paused_event.is_set():
                self.player.pause()
                # 等待 paused_event 被 clear()（即收到 resume 命令）
                while self._paused_event.is_set():
                    await asyncio.sleep(0.1)
                # 清除后恢复播放
                self.player.play()
            await asyncio.sleep(0.1)

    # external control
    def cmd_pause(self):    asyncio.create_task(self.pause())
    def cmd_resume(self):   asyncio.create_task(self.resume())
    def cmd_next(self):     self.player.next()
    def cmd_prev(self):     self.player.prev()
    def cmd_stop(self):
        # 1) 同步先停掉播放器s
        self.player.stop()
        # 2) 返回 cancel() 协程，供外部调度
        return self.cancel()

    def cmd_vol_up(self, db: int = 3):
        """每次提升 db dB"""
        self.player.set_volume(+db)

    def cmd_vol_down(self, db: int = 3):
        """每次降低 db dB"""
        self.player.set_volume(-db)


