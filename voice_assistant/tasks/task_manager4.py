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
    def __init__(self, mp3_dir: Path, loop_playlist: bool = True):

        files = sorted(mp3_dir.glob("*.mp3"))
        if not files:
            raise FileNotFoundError(f"No mp3 under {mp3_dir}")

        self.audio_player = MP3Player(
            files,
            loop=loop_playlist
        )

        self.running: Optional[AsyncVoiceTask] = None
        self.paused_stack: List[AsyncVoiceTask] = []
        self.queue: List[tuple[int, int, AsyncVoiceTask]] = []
        # 同优先级任务排序
        self._counter = 0

    def enqueue(self, task: AsyncVoiceTask):
        # 注入同一个播放器
        if hasattr(task, 'player'):
            task.player = self.audio_player
        # 每次入队都增加 counter，保证即使优先级相同也能通过 counter 排序
        self._counter += 1
        heapq.heappush(self.queue, (-task.priority, self._counter, task))

    def cancel_task(self, task: AsyncVoiceTask):
        # 1) 如果是正在运行的任务
        if self.running is task:
            asyncio.create_task(task.cancel())
            self.running = None
        # 2) 如果在队列里，删掉它
        else:
            # 重建队列，过滤掉要取消的 task
            self.queue = [
                (pri, cnt, t) for (pri, cnt, t) in self.queue if t is not task
            ]
            heapq.heapify(self.queue)

    def pause_music(self):
        """直接暂停背景歌单"""
        self.audio_player.pause()

    def resume_music(self):
        """直接继续背景歌单"""
        self.audio_player.play()

    def next_track(self):
        """跳到下一首"""
        self.audio_player.next()

    def prev_track(self):
        """跳到上一首"""
        self.audio_player.prev()

    def pause_current(self):
        """
        手动暂停当前运行的任务，并把它入 paused_stack。
        wake_and_recognize 中“暂停”命令就应该调用这个方法。
        """
        if self.running:
            # 1) 先暂停任务（会调用 MP3Player.pause()）
            asyncio.create_task(self.running.pause())
            # 2) 入栈，等待后续 resume
            if self.running.resumable:
                self.paused_stack.append(self.running)
            self.running = None


    async def loop(self):
        while True:
            # 1) idle 时启动下一个任务
            if self.running is None and self.queue:
                _,_, nxt = heapq.heappop(self.queue)
                nxt.start()
                self.running = nxt

            # 2) 抢占逻辑：只暂停，不入栈
            if self.running and self.queue:
                top_pri, _, top_task = self.queue[0]
                if -top_pri > self.running.priority:
                    heapq.heappop(self.queue)
                    # 仅暂停，不保存到 paused_stack
                    await self.running.pause()
                    # 切换到新任务
                    self.running = top_task
                    top_task.start()

            # 3) 当前任务结束？恢复手动暂停的任务
            if self.running and self.running._task.done():
                self.running = None
                # 只恢复 paused_stack（只有手动pause的任务会在这里）
                while self.paused_stack and self.running is None:
                    prev = self.paused_stack.pop()
                    await prev.resume()
                    self.running = prev

            await asyncio.sleep(0.05)

class PlayMusicTask(AsyncVoiceTask):
    def __init__(self, ws_client = None):
        super().__init__(name="PlayMusic", priority=1, resumable=True)
        # files = sorted(music_dir.glob("*.mp3"))
        # if not files:
        #     raise FileNotFoundError(f"No mp3 under {music_dir}")
        self.player = None
        self.ws_client = ws_client

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


