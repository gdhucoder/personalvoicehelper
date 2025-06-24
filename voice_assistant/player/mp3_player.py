# mp3_player.py
import simpleaudio as sa
from pydub import AudioSegment
import threading, time
from pathlib import Path
from typing import List, Optional

class MP3Player:
    def __init__(self, files: List[Path], loop: bool = True, vol_db: int = 0):
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
        print(f"▶️ Now Playing [{self.idx+1}/{len(self.files)}]: {self.files[self.idx].name}")
        self._start_monitor(seg.duration_seconds * 1000 - offset_ms)

    def play(self):
        with self.lock:
            if self.play_obj and self.play_obj.is_playing():
                return
            self._start_play(self.offset_ms)

    def pause(self):
        with self.lock:
            if not self.play_obj or self.paused:
                return
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


if __name__ == "__main__":
    mp3_paths = list(Path("../mp3s").glob("*.mp3"))   # 把 mp3 放这个目录
    player = MP3Player(mp3_paths, loop=True)

    print("Commands: p=play, s=pause, r=resum, n=next, b=prev, +=vol+, -=vol-, q=quit")
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
        elif cmd == "q":
            player.stop_flag = True
            player.stop()
            break
