import webrtcvad
import pyaudio
import collections
import sys
import signal

# 配置参数
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # 单声道
SAMPLE_RATE = 16000  # 16kHz采样率
FRAME_DURATION_MS = 30  # 30ms帧
CHUNK = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 每帧的样本数
SILENCE_THRESHOLD = 10  # 连续静音帧阈值

# 初始化VAD
vad = webrtcvad.Vad()
vad.set_mode(3)  # 设置灵敏度 (0-3, 3最严格)


class AudioProcessor:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.speech_frames = collections.deque(maxlen=50)  # 保存最近的语音检测结果

    def start(self):
        """开始录音和处理"""
        self.running = True
        self.stream = self.pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._callback
        )
        print("开始语音活动检测，按Ctrl+C停止...")
        self.stream.start_stream()

    def stop(self):
        """停止录音和处理"""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()

    def _callback(self, in_data, frame_count, time_info, status):
        """PyAudio回调函数，处理音频数据"""
        if not self.running:
            return (None, pyaudio.paComplete)

        # 使用VAD检测语音
        is_speech = vad.is_speech(in_data, SAMPLE_RATE)
        self.speech_frames.append(is_speech)

        # 计算最近帧的语音活动比例
        speech_ratio = sum(self.speech_frames) / len(self.speech_frames)

        # 判断当前是否有语音活动
        if is_speech:
            sys.stdout.write("\r检测到语音活动! [活跃度: {:.1%}] ".format(speech_ratio))
        else:
            sys.stdout.write("\r静音中... [活跃度: {:.1%}] ".format(speech_ratio))
        sys.stdout.flush()

        return (None, pyaudio.paContinue)

    def run(self):
        """运行主循环"""
        try:
            self.start()
            while self.running and self.stream.is_active():
                pass
        except KeyboardInterrupt:
            print("\n正在停止...")
            self.stop()


def main():
    processor = AudioProcessor()

    # 注册信号处理函数，确保程序可以优雅退出
    def signal_handler(sig, frame):
        print("\n收到终止信号，正在停止...")
        processor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 开始处理
    processor.run()


if __name__ == "__main__":
    main()