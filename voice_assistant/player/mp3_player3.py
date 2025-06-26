# mp3_player.py

import threading
import time
from pathlib import Path
import simpleaudio as sa
from pydub import AudioSegment

class MP3Player:
    def __init__(self, files: list[Path], loop: bool = True, vol_db: int = 0):
        self.files = files
        self.loop = loop
        self.vol_db = vol_db

        self.idx = 0
        self.play_obj: sa.PlayObject | None = None
        self.paused = False
        self.offset_ms = 0
        self._start_ts = 0.0

        self._monitor_th: threading.Thread | None = None
        self._monitor_stop = False
        self.lock = threading.Lock()

        # —— 新增：标记背景歌单激活状态 —— #
        self._playlist_active = False

    # —— 内部方法保持不变 —— #
    def _load_segment(self, path: Path) -> AudioSegment:
        return AudioSegment.from_file(path) + self.vol_db

    def _play_segment(self, seg: AudioSegment, offset: int = 0) -> sa.PlayObject:
        self._start_ts = time.time()
        return sa.play_buffer(
            seg[offset:].raw_data,
            num_channels=seg.channels,
            bytes_per_sample=seg.sample_width,
            sample_rate=seg.frame_rate,
        )

    def _start_monitor(self, remaining_ms: float):
        old = self._monitor_th
        if old and old.is_alive():
            self._monitor_stop = True
            if old is not threading.current_thread():
                old.join(timeout=0.1)
        self._monitor_stop = False

        def _mon():
            start = time.time()
            while not self._monitor_stop and (time.time() - start)*1000 < remaining_ms:
                if self.paused:
                    return
                time.sleep(0.1)
            if not self._monitor_stop and self.loop:
                self.next()

        self._monitor_th = threading.Thread(target=_mon, daemon=True)
        self._monitor_th.start()

    def _start_play(self, offset_ms: int):
        path = self.files[self.idx]
        seg = self._load_segment(path)
        self.play_obj = self._play_segment(seg, offset_ms)
        self.paused = False
        print(f"▶️ Now Playing [{self.idx+1}/{len(self.files)}]: {path.name}")
        self._start_monitor(seg.duration_seconds*1000 - offset_ms)

    # —— 公共控制接口 —— #
    def play(self):
        with self.lock:
            if self.play_obj and self.play_obj.is_playing():
                return
            # 激活背景歌单
            self._playlist_active = True
            self._start_play(self.offset_ms)

    def pause(self):
        with self.lock:
            if not self.play_obj or self.paused:
                return
            # 标记非激活
            self._playlist_active = False
            try:
                elapsed = int(self.play_obj.get_time()*1000)
            except AttributeError:
                elapsed = int((time.time()-self._start_ts)*1000)
            self.offset_ms += elapsed
            self.play_obj.stop()
            self.paused = True
            print(f"⏸️ Paused @ {self.offset_ms} ms")

    def stop(self):
        with self.lock:
            # 标记非激活
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
            self.offset_ms = 0
            self.paused = False
            self._playlist_active = True
            self.idx = (self.idx + 1) % len(self.files)
        self._start_play(0)

    def prev(self):
        with self.lock:
            if self.play_obj:
                self.play_obj.stop()
            self.offset_ms = 0
            self.paused = False
            self._playlist_active = True
            self.idx = (self.idx - 1) % len(self.files)
        self._start_play(0)

    def set_volume(self, db_delta: int):
        with self.lock:
            off = self.offset_ms
            if self.play_obj and self.play_obj.is_playing():
                try:
                    off += int(self.play_obj.get_time()*1000)
                except AttributeError:
                    off += int((time.time()-self._start_ts)*1000)
            self.vol_db += db_delta
            print(f"🔊 Volume Δ {db_delta} dB → vol_db={self.vol_db}")
            if self.play_obj:
                self.play_obj.stop()
            self.offset_ms = off
            self._start_play(self.offset_ms)

    # —— 核心改造：play_file —— #
    def play_file(self, path: Path, resume_playlist: bool = True):
        """
        播放单个 mp3（如 TTS 播报）。
        结束后仅在：
          1) resume_playlist=True
          2) 调用前 _playlist_active=True
        时恢复背景歌单（调用 play()）。
        """
        def _play_once():
            # 1) 记录并清理旧监控、旧播放
            with self.lock:
                was_active = self._playlist_active
                self._monitor_stop = True
                if self._monitor_th and self._monitor_th.is_alive():
                    old = self._monitor_th
                    if old is not threading.current_thread():
                        old.join(timeout=0.1)
                if self.play_obj:
                    self.play_obj.stop()
                    self.play_obj = None

            print(f"[play_file] was_active={was_active}, resume={resume_playlist}")

            # 2) 同步播放 TTS
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

            # 3) 恢复歌单
            if resume_playlist and was_active:
                print("[play_file] Restoring playlist…")
                self.play()
            else:
                print("[play_file] Not restoring playlist")

        threading.Thread(target=_play_once, daemon=True).start()
