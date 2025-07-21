# voice_assistant/nlu.py

import re
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from datetime import timedelta

class CommandParser:
    """
    基于关键词和正则的简单NLU，将文本映射为 (intent, params)。
    """

    def __init__(self):
        # 意图到关键词列表的映射
        self.intents = {
            "play_music":       [r"播放(音乐)?", r"\bplay\b"],
            # stop -> pause
            "pause_music":      [r"暂停", r"\bpause\b", r"停止(播放)?", r"\bstop\b"],
            "resume_music":     [r"继续", r"\bresume\b", r"恢复"],
            "next_track":       [r"下一(曲|首|句)", r"\bnext\b"],
            "prev_track":       [r"上一(曲|首|句)", r"\b(previous|prev)\b"],
            # "stop_music":       [r"停止(播放)?", r"\bstop\b"],
            "stop_music":       [r"停止(播放)?", r"\bstop\b"],
            "weather":          [r"天气", r"\bweather\b"],
            "chat_with_ai":     [r"请问", r"你能(告诉我|说说)吗",r"我想(问|聊)", r"我们来聊",],
            "volume_up":        [r"音量(加|上)?", r"\b(vol(up|\+))\b", r"大声点", r"大点声"],
            "volume_down":      [r"音量(减|小)?", r"\b(vol(down|\-))\b", r"小声点", r"小点声"],
            "tts":              [r"说(.*)", r"\btell me\b"],  # capture text
            "image_understand":  [r"这个图(.*)"],
            "get_time":         [r"现在.*点", r"\btime\b"],
            "get_date":         [r"今.*(日期|几号)", r"\bdate\b"],
            "set_timer":        [r"定时(\d+)分钟", r"set a (\d+) minute timer"],
            "add_reminder":     [
                                    r"提醒我(?P<raw>.+)"   # 只抓整句，不再切分 time/text
                                ],
            "remove_reminder":  [r"删除第?(?P<index>\d+|[一二三四五六七八九十]+)条?提醒[。？！]*"],
            "list_reminders":   [r"(列出|查看)提醒"],
            "cancel_timer":     [r"取消定时", r"stop timer"],
            "set_alarm":        [r"(\d+)(点|:)\d*.*闹钟", r"set alarm at (\d+)(am|pm)?"],
            "get_news":         [r"新闻", r"news"],
            "search_web":       [r"搜索(.+)", r"search for (.+)"],
            "define_word":      [r"定义(.+)", r"what does (.+) mean"],
            "translate":        [r"翻译(.+)为?英文?", r"translate (.+) to (.+)"],
            "help":             [r"帮助", r"\bhelp\ "],
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
                m = re.search(p, txt)
                if m:
                    # 对音量意图，尝试抽取数值
                    if intent in ("volume_up", "volume_down"):
                        num = self._extract_number(txt) or 3
                        direction = 1 if intent == "volume_up" else -1
                        return "set_volume", {"delta_db": direction * num}
                    if intent == "get_date":
                        now = datetime.now()
                        weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
                        text = (
                            f"今天是{now.year}年{now.month}月{now.day}日，"
                            f"星期{weekday_map[now.weekday()]}。"
                        )
                        return "get_date", {"date_text": text}
                    if intent == "get_time":
                        now = datetime.now()
                        hour = now.hour
                        minute = now.minute
                        time_text = f"现在是{hour}点{minute}分。"
                        return "get_time", {"time_text": time_text}
                    if intent == "add_reminder":
                        raw = m.group("raw")
                        when, text = self._parse_datetime_and_text(raw)
                        if when is None:
                            return "unknown", {}
                        return "add_reminder", {"when": when, "text": text}
                    if intent == "remove_reminder":
                        index_str = m.group("index")
                        if index_str.isdigit():
                            idx = int(index_str)
                        else:
                            idx = self.chinese_to_int(index_str)
                        return "remove_reminder", {"idx": idx}

                    if intent == "list_reminders":
                        return "list_reminders", {}
                    return intent, {}

        if len(text) > 10 and not re.search(r"(音乐|天气|播放|暂停)", text):
            return  "chat_with_ai", {}
        # 3) 未匹配上
        return "unknown", {}

    def _parse_datetime(self, s: str) -> datetime:
        s = s.strip().replace(" ", "")
        now = datetime.now()

        # 1. 相对时间
        if "分钟后" in s or "小时后" in s:
            unit, delta = ("minutes", int(re.search(r"(\d+)分钟", s).group(1))) if "分钟后" in s else \
                ("hours", int(re.search(r"(\d+)小时", s).group(1)))
            return now + timedelta(**{unit: delta})

        # 2. 标准化替换（不去掉“下午/上午”等）
        s = s.replace("年", "-").replace("月", "-").replace("日", " ").replace("号", " ")

        # 3. 相对日期
        days_offset = 0
        day_terms = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}
        for term, offset in day_terms.items():
            if term in s:
                days_offset = offset
                s = s.replace(term, "")
                break

        # 4. 时间段
        period_offset = 0
        period_map = {"上午": 0, "中午": 12, "下午": 12, "晚": 12, "pm": 12}
        for term, offset in period_map.items():
            if term in s:
                period_offset = offset
                s = s.replace(term, "")
                break

        # 5. 中文数字 -> 阿拉伯
        cn_num = {"两": "2", "一": "1", "二": "2", "三": "3", "四": "4",
                  "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        for cn, ar in cn_num.items():
            s = s.replace(cn, ar)

        # 6. 匹配时间
        hour = minute = 0
        time_match = re.search(r"(\d+)[:点\.](\d{1,2})", s)
        if time_match:
            hour, minute = map(int, time_match.groups())
        else:
            m = re.search(r"(\d+)(?:点|时)?", s)
            if m:
                hour = int(m.group(1))

        # 7. 叠加时间段偏移
        if 1 <= hour <= 11 and period_offset == 12:
            hour += 12
        elif hour == 12 and period_offset == 0:
            hour = 0  # 凌晨12点

        # 8. 处理“半/一刻/三刻”
        if "半" in s and minute == 0:
            minute = 30
        elif "一刻" in s:
            minute = 15
        elif "三刻" in s:
            minute = 45

        # 9. 生成最终时间
        target = now + timedelta(days=days_offset)
        return target.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_datetime_and_text(self, raw: str) -> Tuple[Optional[datetime], str]:
        """
        从“提醒我xxxx”中抽出时间和剩余文本
        返回 (datetime, text) 或 (None, raw)
        """
        now = datetime.now()

        # 1. 相对时间：中文数字 + 分钟后/小时后
        # 统一匹配：中文或阿拉伯数字 + 分钟/小时后
        rel_pattern = re.compile(
            r"(?P<num>(?:半|[零一二三四五六七八九十百千]+|\d+(?:\.\d+)?))"
            r"(?P<unit>分钟|小时)后"
        )

        m = rel_pattern.search(raw)
        if m:
            num_str = m.group("num")
            unit = m.group("unit")

            # 中文数字映射
            cn2digit = {
                "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
                "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
                "半": 0.5
            }
            if num_str in cn2digit:
                value = cn2digit[num_str]
            else:
                value = float(num_str)

            delta = timedelta(minutes=value) if unit == "分钟" else timedelta(hours=value)
            when = (now + delta).replace(microsecond=0)

            # 完整剔除时间段
            text = rel_pattern.sub("", raw).strip()
            return when, f"相对时间{text}"
        # 2. 绝对时间：后天下午两点、明天上午8点、7月15日14:30 ...
        # 先找“今天/明天/后天/大后天”
        day_offset = 0
        day_map = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}
        for kw, off in day_map.items():
            if kw in raw:
                day_offset = off
                raw = raw.replace(kw, "")
                break

        # 时间段
        period_offset = 0
        period_map = {"上午": 0, "早上": 0, "中午": 12, "下午": 12, "晚上": 12}
        for kw, off in period_map.items():
            if kw in raw:
                period_offset = off
                raw = raw.replace(kw, "")
                break

        # 中文数字 → 阿拉伯（先长后短）
        """把文本里的中文数字整体转成阿拉伯数字"""
        # 先按长度倒序，防止“十二”被拆成“十”+“二”
        cn_tokens = [
            ("二十", "20"), ("二十一", "21"), ("二十二", "22"), ("二十三", "23"), ("二十四", "24"),
            ("十二", "12"),
            ("十", "10"), ("十一", "11"), ("十三", "13"), ("十四", "14"),
            ("十五", "15"), ("十六", "16"), ("十七", "17"), ("十八", "18"), ("十九", "19"),
            ("零", "0"), ("一", "1"), ("二", "2"), ("三", "3"), ("四", "4"),
            ("五", "5"), ("六", "6"), ("七", "7"), ("八", "8"), ("九", "9"),
            ("两", "2"),
        ]
        for cn, ar in cn_tokens:
            raw = raw.replace(cn, ar)
            # print(f"{cn},{ar},{raw}")

        # 匹配时间
        hour = minute = 0
        m = re.search(r"(\d{1,2})[:点\.](\d{1,2})", raw)
        if m:
            hour, minute = map(int, m.groups())
        else:
            m = re.search(r"(\d{1,2})(?:点|时)?", raw)
            if m:
                hour = int(m.group(1))

        # 12小时制修正
        if 1 <= hour <= 11 and period_offset == 12:
            hour += 12
        elif hour == 12 and period_offset == 0:
            hour = 0

        # 半、一刻、三刻
        if "半" in raw and minute == 0:
            minute = 30
        elif "一刻" in raw:
            minute = 15
        elif "三刻" in raw:
            minute = 45

        # 日期计算
        target = now + timedelta(days=day_offset)
        try:
            when = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None, raw

        # 去掉已匹配的时间片段
        text = re.sub(r"\d{1,2}[:点\.]?\d{0,2}|半|一刻|三刻", "", raw).strip()
        return when, text

    def chinese_to_int(self, chinese_str):
        # 中文数字到阿拉伯数字的映射表
        chinese_to_arabic = {
            "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
            "十": 10, "百": 100, "千": 1000, "万": 10000
        }
        """
        将中文数字字符串转换为阿拉伯数字
        """
        result = 0
        temp = 0
        for char in reversed(chinese_str):
            if char in chinese_to_arabic:
                value = chinese_to_arabic[char]
                if value >= 10:
                    temp = temp * value
                else:
                    temp += value
            else:
                raise ValueError(f"无法识别的中文数字: {char}")
        result += temp
        return result

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
        "foobar",
        "请问",
        "提醒我明天8点吃药",
        "提醒我下午3点半开会",
        "提醒我下午四点半参加线上会议",
        "提醒我今晚8点半给妈妈打电话",
        "提醒我中午12点吃午饭",
        "提醒我18点去看电影",
        "提醒我30分钟后开会",
        "提醒我半小时后去超市",
        "提醒我30分钟后去超市",
        "提醒我后天14点面试",
        "提醒我后天下午两点面试",
        "提醒我明天下午两点面试",
        "提醒我34分钟后面试",
        "这个图说的是什么",
        # "提醒我十五分钟后去喝水",
        # "提醒我一小时后去洗手",
        # "提醒我十二点去洗手",
    ]
    for t in tests:
        intent, params = parser.parse(t)
        # if intent == "add_reminder":
            # print(params['when'].strftime("%H:%M"))
        print(f"{t!r} → intent={intent}, params={params}")
