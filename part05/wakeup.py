import pvporcupine
import pyaudio
import struct

porcupine = pvporcupine.create(keyword_paths=None, keywords=["picovoice"], access_key="你的AccessKey")

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
            print("🔔 唤醒词检测到！执行唤醒动作...")
            # 调用你助手的主逻辑模块
except KeyboardInterrupt:
    print("关闭中...")

finally:
    audio_stream.stop_stream()
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
