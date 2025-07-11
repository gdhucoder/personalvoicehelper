# demo_llm_task.py

import asyncio
from pathlib import Path

# 引入调度器与任务
from voice_assistant.tasks.task_manager4 import AudioScheduler
from voice_assistant.tasks.llm_task import LLMConversationTask

async def main():
    # 1) 初始化调度器，背景歌单目录可省略或设为你的mp3目录
    #    loop_playlist=False 表示不自动播放背景音乐
    scheduler = AudioScheduler(mp3_dir=Path("../mp3s"),
                               loop_playlist=False)

    # 2) 启动调度器后台循环
    loop = asyncio.get_running_loop()
    loop.create_task(scheduler.loop())

    # 3) 构造一条用户对话消息，触发 LLM + TTS 流式播放
    messages = [
        {"role": "user", "content": "你好，能自我介绍一下吗？"}
    ]
    llm_task = LLMConversationTask(messages)

    # 4) 把任务加入调度器
    scheduler.enqueue(llm_task)
    print("✅ 已入队 LLMConversationTask，开始对话...")

    # 5) 等待任务结束（或被打断）
    #    这里等待足够长的时间，或根据业务可改为更精细的状态监测
    await asyncio.sleep(20)

    # 6) 任务结束后，退出
    print("🔚 Demo 完成，退出程序")
    # 取消调度器循环
    # 注意：如果你希望优雅退出，可在 loop.cancel() 前等待所有任务结束
    loop.stop()

if __name__ == "__main__":
    asyncio.run(main())
