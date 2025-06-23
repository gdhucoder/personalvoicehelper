import asyncio, heapq, time
from typing import Optional

# ---------- Task 基类 ----------
class BaseTask:
    """
    priority 数值越大，优先级越高
    resumable=True 代表可被抢占后继续
    """
    def __init__(self, name: str, priority: int, resumable: bool = False):
        self.name, self.priority, self.resumable = name, priority, resumable
        self._evt = asyncio.Event(); self._evt.set()
        self._task: Optional[asyncio.Task] = None      # 协程句柄

    async def run(self):
        raise NotImplementedError

    # 只创建一次 asyncio.Task，重复调用只是返回句柄
    async def start_once(self):
        if self._task is None:
            self._task = asyncio.create_task(self.run())
        return self._task

    # 可恢复任务 → 暂停；一次性任务 → 直接取消
    async def pause(self):
        if self.resumable:
            print(f"[{ts()}] ⏸  Pause  {self.name}")
            self._evt.clear()
        else:
            self._task.cancel()

    async def resume(self):
        if self.resumable:
            print(f"[{ts()}] ▶️  Resume {self.name}")
            self._evt.set()

    # 供子类在循环中调用，用于阻塞
    async def _wait(self):
        await self._evt.wait()


# ---------- 具体任务 ----------
class MusicTask(BaseTask):
    """模拟长音乐，可被抢占后继续播放"""
    def __init__(self, ticks: int = 30):
        super().__init__("Music", priority=1, resumable=True)
        self.ticks, self.i = ticks, 0

    async def run(self):
        print(f"[{ts()}] 🎵 Music start, total {self.ticks}s")
        while self.i < self.ticks:
            await self._wait()
            # 真实场景这里播放 1 秒音频帧
            print(f"[{ts()}]   Music playing... {self.i+1}/{self.ticks}")
            await asyncio.sleep(1)
            self.i += 1
        print(f"[{ts()}] 🎵 Music finished")


class TTSTask(BaseTask):
    """模拟一次性 TTS 播报，优先级高，抢占音乐"""
    def __init__(self, text: str):
        super().__init__(f"TTS:{text}", priority=10, resumable=False)
        self.text = text

    async def run(self):
        print(f"[{ts()}] 🔊  TTS  > {self.text}")
        # 模拟 1.5 秒播报
        await asyncio.sleep(1.5)
        print(f"[{ts()}] 🔊  TTS done")


# ---------- 音频调度器 ----------
class AudioScheduler:
    """
    - queue       : 待执行的大顶堆 (-priority, task)
    - paused_stack: 按抢占顺序保存可恢复任务
    """
    def __init__(self):
        self.running: Optional[BaseTask] = None
        self.paused_stack: list[BaseTask] = []
        self.queue: list[tuple[int, BaseTask]] = []

    def enqueue(self, task: BaseTask):
        heapq.heappush(self.queue, (-task.priority, task))
        print(f"[{ts()}] ↑ Enqueue {task.name} (pri={task.priority})")

    async def loop(self):
        while True:
            # 1️⃣ 如果空闲，启动最高优先级任务
            if self.running is None and self.queue:
                _, nxt = heapq.heappop(self.queue)
                await nxt.start_once()
                self.running = nxt

            # 2️⃣ 判断是否需要抢占
            if self.running and self.queue:
                top_pri, top_task = self.queue[0]
                if -top_pri > self.running.priority:          # 更高优先级
                    heapq.heappop(self.queue)
                    await self.running.pause()
                    if self.running.resumable:
                        self.paused_stack.append(self.running)
                    self.running = top_task
                    await top_task.start_once()

            # 3️⃣ 当前任务结束？ → 恢复上一首音乐 or 拉取新任务
            if self.running and self.running._task.done():
                self.running = None
                while self.paused_stack and self.running is None:
                    prev = self.paused_stack.pop()
                    await prev.resume()
                    self.running = prev

            await asyncio.sleep(0.05)   # 稍微让出事件循环


# ---------- DEMO ----------
def ts() -> str:
    """时间戳日志"""
    return time.strftime("%H:%M:%S")

async def main():
    sch = AudioScheduler()
    asyncio.create_task(sch.loop())

    # 模拟事件：先放音乐 → 一会插播两条 TTS → 再继续音乐
    sch.enqueue(MusicTask(10))
    await asyncio.sleep(3)
    sch.enqueue(TTSTask("Hello, how can I help you?"))
    await asyncio.sleep(2)
    sch.enqueue(TTSTask("New notification arrived!"))

    # 等所有任务结束
    await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
