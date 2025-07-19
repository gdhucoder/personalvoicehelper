# mp3_player20250719.py
import simpleaudio as sa
from pydub import AudioSegment
import threading, time
from pathlib import Path
from typing import List, Optional

class MP3Player:
    def __init__(self, files: List[Path], loop: bool = True, vol_db: int = 0, ws_client = None):
        self.files = files
        self.loop = loop
        self.vol_db = vol_db

        self.idx: int = 0
        self.play_obj: Optional[sa.PlayObject] = None
        self.paused: bool = False
        self.offset_ms: int = 0
        self._start_ts: float = 0.0

        self._monitor_th: Optional[threading.Thread] = None
        self._monitor_stop: bool = False
        self.lock = threading.Lock()
        # 新增：专门标记歌单是否在“激活”状态
        self._playlist_active = False

        # add ws_client
        self.ws_client = ws_client

    # ------------ 内部方法 ------------
    def _load_segment(self) -> AudioSegment:
        seg = AudioSegment.from_file(self.files[self.idx]) + self.vol_db
        return seg.set_channels(2).set_frame_rate(44100)

    def _play_segment(self, seg: AudioSegment, offset: int = 0) -> sa.PlayObject:
        raw = seg[offset:].raw_data
        self._start_ts = time.time()
        return sa.play_buffer(
            raw,
            num_channels=seg.channels,
            bytes_per_sample=seg.sample_width,
            sample_rate=seg.frame_rate,
        )

    def _start_monitor(self, remaining_ms: float):
        # 停止旧线程（仅对非当前线程执行 join）
        old_th = self._monitor_th
        if old_th and old_th.is_alive():
            self._monitor_stop = True
            if old_th is not threading.current_thread():
                old_th.join(timeout=0.1)

        # 重置标志，启动新线程
        self._monitor_stop = False

        def monitor():
            start = time.time()
            while not self._monitor_stop and (time.time() - start) * 1000 < remaining_ms:
                if self.paused:
                    return
                time.sleep(0.1)
            if not self._monitor_stop:
                self._on_track_end()

        self._monitor_th = threading.Thread(target=monitor, daemon=True)
        self._monitor_th.start()

    def _on_track_end(self):
        if self.loop:
            self.next()

    # ------------ 播放控制 ------------
    def _start_play(self, offset_ms: int):
        seg = self._load_segment()
        self.play_obj = self._play_segment(seg, offset_ms)
        self.paused = False
        msg = f"▶️ Now Playing [{self.idx+1}/{len(self.files)}]: {self.files[self.idx].name}"
        print(msg)
        self.ws_client.send_status_update('info', msg)
        self._start_monitor(seg.duration_seconds * 1000 - offset_ms)

    def play(self):
        with self.lock:
            if self.play_obj and self.play_obj.is_playing():
                return
            self._playlist_active = True
            self._start_play(self.offset_ms)

    def pause(self):
        with self.lock:
            if not self.play_obj or self.paused:
                return
            # 标记歌单未激活（即暂停状态）
            self._playlist_active = False
            try:
                elapsed_ms = int(self.play_obj.get_time() * 1000)
            except AttributeError:
                elapsed_ms = int((time.time() - self._start_ts) * 1000)
            self.offset_ms += elapsed_ms
            self.play_obj.stop()
            self.paused = True
            print(f"⏸️ Paused @ {self.offset_ms} ms")

    def stop(self):
        with self.lock:
            # 标记歌单未激活
            self._playlist_active = False
            if self.play_obj:
                self.play_obj.stop()
            self.play_obj = None
            self.paused = False
            self.offset_ms = 0
            self._monitor_stop = True
            print("⏹️ Stopped")

    def next(self):
        with self.lock:
            if self.play_obj:
                self.play_obj.stop()
            self.paused = False
            self.offset_ms = 0
            self.idx = (self.idx + 1) % len(self.files)
        self._start_play(0)

    def prev(self):
        with self.lock:
            if self.play_obj:
                self.play_obj.stop()
            self.paused = False
            self.offset_ms = 0
            self.idx = (self.idx - 1) % len(self.files)
        self._start_play(0)

    def set_volume(self, db_delta: int):
        with self.lock:
            # 记录当前位置
            current_offset = self.offset_ms
            if self.play_obj and self.play_obj.is_playing():
                try:
                    current_offset += int(self.play_obj.get_time() * 1000)
                except AttributeError:
                    current_offset += int((time.time() - self._start_ts) * 1000)

            # 更新音量并从当前位置重播
            self.vol_db += db_delta
            print(f"🔊 Volume Δ {db_delta} dB → offset={self.vol_db}")
            if self.play_obj:
                self.play_obj.stop()
            self.offset_ms = current_offset
            self._start_play(self.offset_ms)

    # ------------ 新增：播放单次文件（用于 TTS） ------------
    # def play_file(self, path: Path, wait: bool = False, resume_playlist: bool = True):
    #     """
    #     播放一个单独的 mp3 文件（如 TTS 结果），播放结束后可恢复原歌单。
    #     :param path: mp3 文件路径
    #     :param wait: True 时阻塞直到播放结束
    #     :param resume_playlist: True 时播放完毕后继续歌单
    #     """
    #
    #     def _play_once():
    #         # 暂停/停止当前歌单
    #         with self.lock:
    #             playing = self.play_obj and self.play_obj.is_playing()
    #             if playing:
    #                 self.play_obj.stop()
    #         # 播放 TTS 文件
    #         seg = AudioSegment.from_file(path) + self.vol_db
    #         play_obj = sa.play_buffer(
    #             seg.raw_data,
    #             num_channels=seg.channels,
    #             bytes_per_sample=seg.sample_width,
    #             sample_rate=seg.frame_rate,
    #         )
    #         print(f"▶️ Now Playing {path.name}")
    #         play_obj.wait_done()
    #         # 恢复歌单
    #         if resume_playlist and playing:
    #             self.play()
    #
    #     # 后台线程播放，避免阻塞
    #     threading.Thread(target=_play_once, daemon=True).start()

    def play_file(self, was_playing:bool, path: Path, resume_playlist: bool = True):
        """
        播放单个 mp3（如 TTS），播放完毕后仅在：
          1) resume_playlist=True
          2) 调用前 _playlist_active==True
        时恢复歌单。
        """

        def _play_once():
            # 1) 记录调用前歌单激活状态，杀死旧监控并停止当前播放
            with self.lock:
                was_active = was_playing
                print(f"[play_file lock] was_active={was_active}")
                # 停监控
                self._monitor_stop = True
                if self._monitor_th and self._monitor_th.is_alive():
                    old = self._monitor_th
                    if old is not threading.current_thread():
                        old.join(timeout=0.1)
                # 停当前播放
                if self.play_obj:
                    self.play_obj.stop()
                    self.play_obj = None

            print(f"[play_file] was_active={was_active}, resume_playlist={resume_playlist}")

            # 2) 播放 TTS
            seg = AudioSegment.from_file(path) + self.vol_db
            play_obj = sa.play_buffer(
                seg.raw_data,
                num_channels=seg.channels,
                bytes_per_sample=seg.sample_width,
                sample_rate=seg.frame_rate,
            )
            print(f"▶️ Now Playing (TTS): {path.name}")
            play_obj.wait_done()
            print(f"▶️ TTS done: {path.name}")

            # 3) 仅在调用前歌单激活且允许恢复时启动歌单
            if resume_playlist and was_active:
                print("[play_file] Restoring playlist…")
                self.play()
            else:
                print("[play_file] Not restoring playlist")

        threading.Thread(target=_play_once, daemon=True).start()


if __name__ == "__main__":
    mp3_paths = list(Path("../mp3s").glob("*.mp3"))   # 把 mp3 放这个目录
    player = MP3Player(mp3_paths, loop=True)

    print("Commands: p=play, s=pause, r=resum, n=next, b=prev, t=playtts, +=vol+, -=vol-, q=quit")
    while True:
        cmd = input(">> ").strip().lower()
        if cmd == "p":
            player.play()
        elif cmd == "s":
            player.pause()
        elif cmd == "r":
            player.play()
        elif cmd == "n":
            player.next()
        elif cmd == "b":
            player.prev()
        elif cmd == "+":
            player.set_volume(+3)      # 每次 +3dB
        elif cmd == "-":
            player.set_volume(-3)
        elif cmd == "t":
            # ... 程序运行中，当拿到 TTS 生成的 mp3 路径后：
            tts_path = Path("/home/hugd/privateprojects/personalvoicehelper/voice_assistant/resource/common_tts/loongstella/好的.mp3")
            player.play_file(tts_path, resume_playlist=True)
        elif cmd == "q":
            player.stop_flag = True
            player.stop()
            break
