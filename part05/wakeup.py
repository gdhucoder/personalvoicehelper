import pvporcupine
import pyaudio
import struct
import configparser
from datetime import datetime



# config parser
config = configparser.ConfigParser()
# load config
config.read('../env/config.ini')

porcupine_access_key = config.get('listener', 'pvporcupine_access_key') # key

custom_keyword_franky_path = config.get('listener', 'custom_keyword_franky')

porcupine = pvporcupine.create(keyword_paths=[custom_keyword_franky_path],
                               keywords=["franky"],
                               access_key=porcupine_access_key,
                               sensitivities=[0.7])

pa = pyaudio.PyAudio()

audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length)

print("Listening for 'picovoice'...")

try:
    while True:
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        result = porcupine.process(pcm)

        if result >= 0:
            # 获取当前日期和时间
            now = datetime.now()
            # 格式化为字符串
            formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f'🔔{formatted_date} 唤醒词检测到！执行唤醒动作...')
            # 调用你助手的主逻辑模块
except KeyboardInterrupt:
    print("关闭中...")

finally:
    audio_stream.stop_stream()
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
