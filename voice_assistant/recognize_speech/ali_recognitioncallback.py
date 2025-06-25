import pyaudio
from dashscope.audio.asr import RecognitionCallback, RecognitionResult

class MyRecognitionCallback(RecognitionCallback):
    """
    自定义回调类，处理实时识别事件。
    在此类中收集识别文本，并在需要时通知主线程结束或返回。
    """

    def __init__(self):
        super().__init__()
        self.final_text = ""       # 存放最终识别的文本
        self.buffered_text = ""    # 存放本次会话中的累计文本
        self.is_open = False
        self.mic = None            # PyAudio实例
        self.stream = None         # 音频流

    def on_open(self) -> None:
        """
        打开音频流进行实时识别
        """
        print('RecognitionCallback: on_open()')
        self.is_open = True

        # self.mic = pyaudio.PyAudio()
        # device_index = 2  # 根据你的实际麦克风设备进行调整
        #
        # try:
        #     self.stream = self.mic.open(format=pyaudio.paInt16,
        #                                 channels=1,
        #                                 rate=16000,
        #                                 input=True,
        #                                 frames_per_buffer=3200,
        #                                 input_device_index=device_index)
        #     print(f"Opened audio stream on device {device_index}")
        # except Exception as e:
        #     print(f"Failed to open audio stream: {e}")
        #     self.stream = None

    def on_close(self) -> None:
        """
        关闭音频流和清理资源
        """
        print('RecognitionCallback: on_close()')
        self.is_open = False
        #
        # if self.stream is not None:
        #     try:
        #         self.stream.stop_stream()
        #         self.stream.close()
        #         print("Audio stream closed.")
        #     except Exception as e:
        #         print(f"Error closing stream: {e}")
        #     self.stream = None
        #
        # if self.mic is not None:
        #     try:
        #         self.mic.terminate()
        #         print("PyAudio terminated.")
        #     except Exception as e:
        #         print(f"Error terminating PyAudio: {e}")
        #     self.mic = None

    def on_event(self, result: RecognitionResult) -> None:
        """
        Dashscope 在识别到语音片段后，会多次调用 on_event，
        result.get_sentence() 返回一个dict，包含文本信息。
        可以把连续的句子拼起来，也可只使用最新的一次文本。
        """
        sentence_dict = result.get_sentence()
        sentence_text = sentence_dict.get('text', '')
        print(f"OnEvent recognized sentence: {sentence_text}")

        # 累加文本
        self.buffered_text = sentence_text
        self.final_text = sentence_text
        # 检查 sentence_end 是否为 True，表示当前句子已结束
        if sentence_dict.get('sentence_end', False):
            print("Sentence ended. Returning recognized text.")
            self.final_text = sentence_text
            print(f"Final recognized text: {self.final_text}")


    def on_error(self, result: RecognitionResult) -> None:
        print("Error recognized. Returning recognized text.")