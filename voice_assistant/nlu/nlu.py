# voice_assistant/nlu.py

import re
from typing import Tuple, Dict, Any

class CommandParser:
    """
    基于关键词和正则的简单NLU，将文本映射为 (intent, params)。
    """

    def __init__(self):
        # 意图到关键词列表的映射
        self.intents = {
            "play_music":       [r"播放(音乐)?", r"\bplay\b"],
            "pause_music":      [r"暂停", r"\bpause\b"],
            "resume_music":     [r"继续", r"\bresume\b", r"恢复"],
            "next_track":       [r"下一(曲|首)", r"\bnext\b"],
            "prev_track":       [r"上一(曲|首)", r"\b(previous|prev)\b"],
            "stop_music":       [r"停止(播放)?", r"\bstop\b"],
            "weather":          [r"天气", r"\bweather\b"],
            "volume_up":        [r"音量(加|上)?", r"\b(vol(up|\+))\b", r"大声点", r"大点声"],
            "volume_down":      [r"音量(减|小)?", r"\b(vol(down|\-))\b", r"小声点", r"小点声"],
            "tts":              [r"说(.*)", r"\btell me\b"],  # capture text
            "get_time":         [r"现在.*点", r"\btime\b"],
            "get_date":         [r"今.*(日期|几号)", r"\bdate\b"],
            "set_timer":        [r"定时(\d+)分钟", r"set a (\d+) minute timer"],
            "cancel_timer":     [r"取消定时", r"stop timer"],
            "set_alarm":        [r"(\d+)(点|:)\d*.*闹钟", r"set alarm at (\d+)(am|pm)?"],
            "get_news":         [r"新闻", r"news"],
            "search_web":       [r"搜索(.+)", r"search for (.+)"],
            "define_word":      [r"定义(.+)", r"what does (.+) mean"],
            "translate":        [r"翻译(.+)为?英文?", r"translate (.+) to (.+)"],
            "help":             [r"帮助", r"\bhelp\b"],
            "exit":             [r"(再见|拜拜)", r"\bbye\b"],
            "open_app":         [r"打开(.+)", r"launch (.+)"],
            "control_light":    [r"(打开|关闭)(客厅|卧室)灯", r"(turn on|turn off) lights"],
        }
        # 用于提取 tts 文本的正则
        self.re_tts = re.compile(r"^(?:说|tell me to\s*)(?P<text>.+)$", re.IGNORECASE)

    def parse(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        返回 (intent, params)。
        如果无法识别任何 intent，返回 ("unknown", {}).
        """
        txt = text.strip().lower()

        # 1) 特殊处理 TTS：优先捕获
        m = self.re_tts.match(txt)
        if m:
            return "tts", {"text": m.group("text").strip()}

        # 2) 遍历其它意图
        for intent, patterns in self.intents.items():
            if intent == "tts":
                continue
            for p in patterns:
                if re.search(p, txt):
                    # 对音量意图，尝试抽取数值
                    if intent in ("volume_up", "volume_down"):
                        num = self._extract_number(txt) or 3
                        direction = 1 if intent == "volume_up" else -1
                        return "set_volume", {"delta_db": direction * num}
                    return intent, {}

        # 3) 未匹配上
        return "unknown", {}

    def _extract_number(self, txt: str) -> int:
        """
        从文本中提取第一个数字（如“音量加10”），无则返回 None。
        """
        m = re.search(r"(\d+)", txt)
        return int(m.group(1)) if m else None


if __name__ == "__main__":
    parser = CommandParser()
    tests = [
        "播放音乐",
        "pause",
        "下一曲",
        "上一首",
        "暂停",
        "继续",
        "tell me the time",
        "说你好世界",
        "音量加5",
        "音量减3",
        "天气",
        "告诉我天气",
        "今日天气",
        "大声点",
        "小声点",
        "大点声",
        "小点声",
        "foobar"
    ]
    for t in tests:
        intent, params = parser.parse(t)
        print(f"{t!r} → intent={intent}, params={params}")
