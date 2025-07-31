#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phonebook.py
支持：
  1. 姓名模糊匹配（中文、全拼、首字母缩写）
  2. 手机 / 座机后 4 位精确匹配
列名：姓名 工作单位 部门 职务 手机 座机
"""

import pandas as pd
from rapidfuzz import process, fuzz
from pypinyin import lazy_pinyin, Style
from collections import defaultdict

CSV_PATH = "/home/hugd/privateprojects/personalvoicehelper/voice_assistant/resource/workcontact/工作电话簿20250724.csv"

# ---------- 索引构建 ----------
def _build_index(df: pd.DataFrame):
    name_idx   = defaultdict(list)   # 中文
    pinyin_idx = defaultdict(list)   # 全拼
    abbr_idx   = defaultdict(list)   # 缩写
    tail4_idx  = defaultdict(list)   # 后4位 -> row_id

    for idx, row in df.iterrows():
        name = str(row['姓名']).strip()
        if not name or name == 'nan':
            continue

        # 中文
        name_idx[name].append(idx)

        # 全拼
        full_py = ''.join(lazy_pinyin(name, style=Style.NORMAL))
        pinyin_idx[full_py].append(idx)

        # 缩写
        abbr_py = ''.join(lazy_pinyin(name, style=Style.FIRST_LETTER))
        abbr_idx[abbr_py].append(idx)

        # 后4位
        for col in ('手机', '座机'):
            val = str(row[col]).strip()
            if val and val != 'nan':
                tail = val[-4:].zfill(4)
                tail4_idx[tail].append(idx)

    return name_idx, pinyin_idx, abbr_idx, tail4_idx


class PhoneBook:
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path, dtype=str, encoding='gbk').fillna('')
        self.name_idx, self.pinyin_idx, self.abbr_idx, self.tail4_idx = _build_index(self.df)

    def query(self, q: str, topk=3):
        q = q.strip()
        if q.isdigit() and len(q) <= 4:               # 后4位
            rows = self.tail4_idx[q.zfill(4)]
        else:                                         # 姓名模糊
            # 合并候选
            choices = list(self.name_idx.keys()) + \
                      list(self.pinyin_idx.keys()) + \
                      list(self.abbr_idx.keys())
            hits = process.extract(q, choices,
                                   scorer=fuzz.partial_ratio,
                                   score_cutoff=70,
                                   limit=topk)
            seen = set()
            rows = []
            for match, _, _ in hits:
                for idx in (self.name_idx.get(match, []) +
                            self.pinyin_idx.get(match, []) +
                            self.abbr_idx.get(match, [])):
                    if idx not in seen:
                        seen.add(idx)
                        rows.append(idx)
        return self.df.iloc[rows].reset_index(drop=True)


# ---------- CLI ----------
def main():
    pb = PhoneBook(CSV_PATH)
    print("=== 电话簿查询（列：姓名 工作单位 部门 职务 手机 座机） ===")
    print("输入姓名关键词或号码后4位，回车查询；空行退出")
    while True:
        q = input(">>> ").strip()
        if not q:
            break
        res = pb.query(q)
        if res.empty:
            print("未找到联系人")
        else:
            print(res.to_string(index=False))

if __name__ == '__main__':
    main()