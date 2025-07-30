# 🎀 Franky — 边缘计算智能语音助手 / Edge‑Computing Smart Voice Assistant

---

## 🚀 简介｜Introduction

**Franky** 是一款运行在 Raspberry Pi 5 上的本地化智能语音助手，具备：

* **低功耗、低延迟、离线可用**
* **关键词唤醒 + 混合本地/云识别**
* **可抢占式多任务调度：音乐 ↔ TTS ↔ 提醒 ↔ 聊天**
* **情感化可视反馈 + 粉色萌系 WebUI**

Franky runs entirely on the edge, wake‑word to response under 200 ms, supports offline voice processing, preemptive audio scheduling, reminders, weather, LLM‑powered chat — all wrapped in a cute pink web UI your kids will love.

---

## ✨ 核心特性｜Key Features

| 编号 | 特性                 | Description                  |
| -- | ------------------ | ---------------------------- |
| 1  | 🔔 **关键词唤醒**       | 本地 Porcupine，响应快，无需联网        |
| 2  | 🎙️ **语音识别**       | 本地 Whisper & 云端备援            |
| 3  | 🗣️ **文字转语音（TTS）** | DashScope or 阿里云大模型 API，声音自然 |
| 4  | 🎵 **音频抢占调度**      | 音乐 ↔ TTS ↔ 提醒 互不打架           |
| 5  | 🤖 **NLU 意图解析**    | 支持音乐、天气、提醒、联系人查询、聊天          |
| 6  | 📆 **定时/提醒**       | 语音或 WebUI 一键设定 ⇄ 删除          |
| 7  | 🌤️ **天气查询**       | 实时 API 获取并播报                 |
| 8  | 💬 **多轮 LLM 聊天**   | Qwen‑Turbo + 流式 TTS，聊天更流畅    |
| 9  | 🌈 **粉色萌系 WebUI**  | Socket.IO 双向交互，实时可视化         |

---

## 🏗️ 架构｜Architecture

```
+------------+         +------------------+        +----------------+
|  Wake Word | --PCM-->│  Voice Frontend  │--API-->│  NLU &  Task   │
| Detection  |         │  (Python / Pi)   │        │  Scheduler     │
+------------+         +------------------+        +----------------+
       │                          │                       │
       │                          │                       ├─ MusicTask
       │                          │                       ├─ SpeakTextTask
       │                          │                       ├─ WeatherTask
       ▼                          ▼                       └─ LLMConversationTask
+-------------+            +---------------+  
|  Porcupine  |            | WebUI (Pink)  |
|  + PyAudio  |←──────────>| Socket.IO     |
+-------------+            +---------------+
```

---

## ⚙️ 环境搭建｜Setup

1. **硬件**

   * Raspberry Pi 5
   * ReSpeaker 2‑Mic Array (可选)
   * USB 麦克风 & 有线小音箱

2. **系统 & 依赖**

   ```bash
   # Raspbian / Ubuntu
   sudo apt update && sudo apt install -y python3 python3‑venv \
     libportaudio2 libportaudiocpp0 portaudio19-dev

   git clone https://github.com/yourname/franky.git
   cd franky
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **配置**
   在 `env/config.ini` 中填写：

   ```ini
   [listener]
   pvporcupine_access_key = YOUR_PICO_VOICE_KEY
   custom_keyword_franky 
   ```

4. **启动**

```bash
# 后端服务（Flask‑SocketIO）
python3 webui/server.py

# 核心守护进程
python3 assistant/main.py
打开浏览器
访问 http://<Pi_IP>:5001，你就能在粉色萌系界面中和 Franky 互动啦！
```

## 🎬 使用示例｜Quick Demo

- “Franky，播放音乐” → 背景歌单自动播放

- “Franky，今天天气怎么样” → 天气播报 + 可视化卡片

- “Franky，提醒我下午 3 点开会” → 设置提醒 & 到点播报

- WebUI 上传图片 → AI 图像理解结果实时返回

## 🤝 贡献｜Contributing

- 大家一起让 Franky 变得更可爱！

## 📄 许可证｜License

本项目采用 MIT License，欢迎任何形式的学习、改造与再分享！