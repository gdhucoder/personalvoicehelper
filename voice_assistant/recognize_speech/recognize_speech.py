import configparser
import time

import dashscope
from dashscope.audio.asr import (Recognition)

from voice_assistant.recognize_speech.ali_recognitioncallback import MyRecognitionCallback

# config parser
config = configparser.ConfigParser()
# load config
config.read('../env/config.ini')


dashscope.api_key = config.get('llmapi', 'aliyun_api_key') # 替换为你的 Dashscope API Key

print(dashscope.api_key)

def recoginze_speech(audio_stream, timeout=10):
    print("please speak your order")
    callback = MyRecognitionCallback()
    recognition = Recognition(
        model='paraformer-realtime-v2',
        format='pcm',
        sample_rate=16000,
        callback=callback
    )
    # 开始识别
    recognition.start()
    print("Recognition started, listening to microphone...")
    start_time = time.time()
    try:
        while True:
            # timeout
            if (time.time() - start_time) > timeout:
                print(f"超过 {timeout} 秒，自动结束录音。")
                break
            if audio_stream:
                try:
                    data = audio_stream.read(3200, exception_on_overflow=False)
                    recognition.send_audio_frame(data)
                except Exception as e:
                    print(f"Error reading audio stream: {e}")
                    break
            else:
                print("Audio stream not available.")
                break
            # 如果识别到一定长度文本，就认为结束
            if len(callback.buffered_text) > 30:  # 阈值可调
                print("识别到足够的文本，停止录音。")
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        recognition.stop()
        return callback.final_text