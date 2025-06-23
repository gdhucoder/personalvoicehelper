import asyncio
import heapq
from base import  TTSPlaybackTask,PlayMusicTask
class TaskFlowManager:
    def __init__(self):
        self.task_queue = []
        self.current_task = None  # asyncio.Task
        self.running_voice_task = None  # VoiceTask

    async def add_task(self, task):
        heapq.heappush(self.task_queue, task)
        await self.check_and_run()

    async def check_and_run(self):
        if self.current_task is None or self.current_task.done():
            if self.task_queue:
                next_task = heapq.heappop(self.task_queue)
                self.running_voice_task = next_task
                self.current_task = asyncio.create_task(self.run_task(next_task))
        else:
            top_task = self.task_queue[0]
            if top_task.priority < self.running_voice_task.priority:
                print(f"[Preempt] {top_task.name} is preempting {self.running_voice_task.name}")
                self.current_task.cancel()
                await asyncio.sleep(0.1)
                next_task = heapq.heappop(self.task_queue)
                self.running_voice_task = next_task
                self.current_task = asyncio.create_task(self.run_task(next_task))

    async def run_task(self, task):
        try:
            await task.execute()
        except asyncio.CancelledError:
            print(f"[Cancelled] {task.name} was cancelled.")


async def main():
    manager = TaskFlowManager()

    await manager.add_task(PlayMusicTask("Background Music", priority=5))
    await asyncio.sleep(1)
    await manager.add_task(TTSPlaybackTask("Hello, how can I help you?", priority=1))

    await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())