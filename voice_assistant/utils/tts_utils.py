import configparser
from pathlib import Path

import re
import hashlib
from dashscope.audio.tts_v2 import *
import dashscope

# 读取配置
cfg = configparser.ConfigParser()
cfg.read('/home/hugd/privateprojects/personalvoicehelper/env/config.ini')

dashscope.api_key = cfg.get('llmapi', 'aliyun_api_key')

# --------------- 工具函数 ---------------
def generate_hash_file_name(text: str) -> str:
    # 去掉常见标点
    cleaned = re.sub(r'[*=，。！？“”‘’（）【】、；：]', '', text)
    # 哈希前6位
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()[:6]


def speech_synthesize(text: str, out_dir: Path = Path("/home/hugd/privateprojects/personalvoicehelper/tmp/speechsynth")) -> Path:
    """
    调用 DashScope TTS，同步生成或复用 MP3 文件。
    返回生成的 mp3 路径。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    name = generate_hash_file_name(text)
    path = out_dir / f"{name}.mp3"
    if path.exists():
        print(f"[TTS] 文件已存在: {path.name}")
    else:
        print(f"[TTS] 生成新文件: {path.name}")
        # dashscope.api_key = "your_api_key"  # 如需手动设置
        synth = SpeechSynthesizer(model="cosyvoice-v1", voice="longxiaochun")
        audio = synth.call(text)
        with open(path, "wb") as f:
            f.write(audio)
    return path
