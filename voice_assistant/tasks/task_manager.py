import asyncio, heapq
from typing import Optional

# ---------- Task Base ----------
class BaseTask:
    def __init__(self, name, priority, resumable=False):
        self.name, self.priority, self.resumable = name, priority, resumable
        self._evt = asyncio.Event(); self._evt.set()
        self._task: Optional[asyncio.Task] = None   # 协程句柄

    async def run(self): ...                       # 子类实现

    async def start_once(self):
        if self._task is None:                     # 只创建一次
            self._task = asyncio.create_task(self.run())
        return self._task

    async def pause(self):
        if self.resumable:
            print(f"[{self.name}] Paused")
            self._evt.clear()
        else:                                      # 一次性任务直接取消
            self._task.cancel()

    async def resume(self):
        if self.resumable:
            print(f"[{self.name}] Resumed")
            self._evt.set()

    async def _wait(self):
        await self._evt.wait()

# ---------- Concrete Tasks ----------
class MusicTask(BaseTask):
    def __init__(self, ticks=10):
        super().__init__("Music", priority=1, resumable=True)
        self.ticks = ticks; self.i = 0

    async def run(self):
        print("[Music] Start")
        while self.i < self.ticks:
            await self._wait()
            print(f"[Music] ... {self.i}")
            await asyncio.sleep(0.4)
            self.i += 1
        print("[Music] Finished")

class TTSTask(BaseTask):
    def __init__(self, text):
        super().__init__(f"TTS:{text}", priority=10, resumable=False)
        self.text = text

    async def run(self):
        print(f"[TTS] {self.text}")
        await asyncio.sleep(1.2)
        print(f"[TTS] Done: {self.text}")

# ---------- Scheduler ----------
class AudioScheduler:
    def __init__(self):
        self.running: Optional[BaseTask] = None
        self.paused_stack = []
        self.queue = []                            # max-heap: (-priority, task)

    def enqueue(self, task: BaseTask):
        heapq.heappush(self.queue, (-task.priority, task))

    async def loop(self):
        while True:
            # 新任务 → 如果 idle 则启动
            if self.running is None and self.queue:
                _, nxt = heapq.heappop(self.queue)
                await nxt.start_once()
                self.running = nxt

            # 抢占
            if self.running and self.queue:
                top_pri, top_task = self.queue[0]
                if -top_pri > self.running.priority:          # higher priority
                    heapq.heappop(self.queue)
                    await self.running.pause()
                    if self.running.resumable:
                        self.paused_stack.append(self.running)
                    self.running = top_task
                    await top_task.start_once()

            # 当前任务结束？
            if self.running and self.running._task.done():
                self.running = None
                # 恢复最后一个被暂停的音乐（如果有）
                while self.paused_stack and self.running is None:
                    music = self.paused_stack.pop()
                    await music.resume()
                    self.running = music

            await asyncio.sleep(0.05)

# ---------- DEMO ----------
async def main():
    sch = AudioScheduler()
    asyncio.create_task(sch.loop())

    sch.enqueue(MusicTask(10))
    await asyncio.sleep(1)
    sch.enqueue(TTSTask("Hello, how can I help you?"))
    await asyncio.sleep(0.8)
    sch.enqueue(TTSTask("New Notification!"))

    # 等全部任务做完
    await asyncio.sleep(8)

if __name__ == "__main__":
    asyncio.run(main())
