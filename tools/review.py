#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""審稿員的自動檢查：用詞、數字格式、參考資訊、標點。

規則來源：team/風格指南.md（標「🔧 自動檢查」的項目）。
事實是否正確由審稿員查核，這支程式不判斷。

用法：
    python tools/review.py 稿件.md [更多稿件.md ...]
    python tools/review.py 稿件.md --fix      # 自動修正確定的錯誤後再檢查

結束碼：0 = 沒有錯誤（可能有提醒）；1 = 有錯誤；2 = 找不到檔案。
"""
import argparse
import re
import sys
from pathlib import Path

CJK = r"一-鿿"

# (錯誤寫法的正規式, 正確寫法, 說明)。這些可以用 --fix 自動修正。
FIXABLE = [
    (r"自願行碳市場", "自願性碳市場", "用詞"),
    (r"自願碳市場", "自願性碳市場", "用詞"),
    (r"tCO2e", "tCO₂e", "下標"),
    (r"(?<![A-Za-z])CO2(?![0-9A-Za-z])", "CO₂", "下標"),
    (r"\[以(ICVCM|IETA|ICROA|Verra|SBTi|IPCC)", r"[\1", "參考資訊連結名稱多了「以」"),
    (r"^(?:\*\*)?(?:參考資訊|參考資料|資料來源|Reference)(?:\*\*)?\s*[：:]\s*(?=\[)(?<!^\*\*參考資訊\*\*：)",
     "**參考資訊**：", "參考資訊標題格式應為「**參考資訊**：」"),
    (r"(\)) ?\. ?(\[)", r"\1．\2", "參考資訊分隔符號應為全形「．」"),
    (rf"(?<=[{CJK}]),(?=[{CJK}])", "，", "中文間用全形逗號"),
    (rf"(?<=[{CJK}]):(?=[{CJK}])", "：", "中文間用全形冒號"),
    (rf"(?<=[{CJK}]);(?=[{CJK}])", "；", "中文間用全形分號"),
]

# 只提醒、不自動改（要看上下文）
WARNINGS = [
    (r"(?<!「)碳權(?!」|交易所|顧問)", "內文建議用「碳信用」；服務名稱、機構名稱（臺灣碳權交易所）或解釋名詞時可保留「碳權」"),
    (r"\$\s?\d", "金額建議寫成「X 美元」"),
    (r"\d\s?USD", "金額建議寫成「X 美元」"),
    (r"暴漲|崩盤|史上最", "避免誇大用語，除非有數據支持"),
    (r"值得關注", "請寫出具體判斷，而不只是「值得關注」"),
]

REQUIRED_FRONT = ["title", "date", "summary"]


def mask_urls(line):
    """把網址換成等長空白，避免網址裡的字被誤判。"""
    return re.sub(r"\]\([^)]*\)|https?://\S+", lambda m: " " * len(m.group()), line)


def split_front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text, 0
    return m.group(1), text[m.end():], m.group(0).count("\n")


def check(text):
    errors, warns = [], []
    front, body, offset = split_front(text)

    if front is not None:
        for key in REQUIRED_FRONT:
            if not re.search(rf"^{key}:\s*\S", front, re.M):
                errors.append((1, f"front matter 缺少「{key}」"))

    lines = body.split("\n")
    for i, raw in enumerate(lines, start=offset + 1):
        line = mask_urls(raw)
        for pat, right, why in FIXABLE:
            # 參考資訊相關規則要看網址前後的括號，所以用原文比對
            target = raw if "[" in pat or "\\)" in pat else line
            for m in re.finditer(pat, target):
                after = right if "\\" not in right else re.sub(pat, right, m.group())
                errors.append((i, f"{why}：「{m.group().strip()}」→「{after}」"))
        for pat, why in WARNINGS:
            for m in re.finditer(pat, line):
                warns.append((i, f"{why}：「{m.group()}」"))
        # 四位數以上沒有千分位（年份 1900–2100 除外）
        for m in re.finditer(r"(?<![\dA-Za-z,.])\d{4,}(?![\d,.])", line):
            n = m.group()
            if len(n) == 4 and 1900 <= int(n) <= 2100:
                continue
            errors.append((i, f"四位數以上加千分位：「{n}」→「{int(n):,}」"))
        # 百分比前後多了空格
        for m in re.finditer(r"\d\s+%", line):
            errors.append((i, f"百分比不空格：「{m.group()}」"))

    refs = [l for l in lines if l.startswith("**參考資訊**")]
    if not refs and not re.search(r"^(?:\*\*)?(?:參考資料|資料來源|Reference)", body, re.M):
        errors.append((0, "缺少「**參考資訊**：」段落，所有數字都要有來源"))
    for l in refs:
        if not re.search(r"\]\(https?://", l):
            errors.append((0, "參考資訊沒有任何網址連結"))

    return errors, warns


def fix(text):
    front, body, _ = split_front(text)
    head = text[: len(text) - len(body)]
    out = []
    for raw in body.split("\n"):
        # 先保護網址，修完再放回去
        urls = []

        def keep(m):
            urls.append(m.group())
            return f"\x00{len(urls) - 1}\x00"

        line = re.sub(r"(?<=\]\()[^)]*(?=\))", keep, raw)
        for pat, right, _ in FIXABLE:
            line = re.sub(pat, right, line)
        line = re.sub(r"\x00(\d+)\x00", lambda m: urls[int(m.group(1))], line)
        out.append(line)
    return head + "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="AllO2 稿件自動檢查")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--fix", action="store_true", help="自動修正確定的錯誤")
    a = ap.parse_args()

    total_err = 0
    for f in a.files:
        p = Path(f)
        if not p.is_file():
            print(f"找不到檔案：{f}", file=sys.stderr)
            sys.exit(2)
        text = p.read_text(encoding="utf-8")
        if a.fix:
            fixed = fix(text)
            if fixed != text:
                p.write_text(fixed, encoding="utf-8")
                print(f"已自動修正：{f}")
                text = fixed
        errors, warns = check(text)
        errors = list(dict.fromkeys(errors))
        warns = list(dict.fromkeys(warns))
        total_err += len(errors)
        status = "✅ 通過" if not errors else f"❌ 錯誤 {len(errors)}"
        print(f"\n## {f}　{status}　提醒 {len(warns)}")
        for n, msg in errors:
            print(f"  錯誤　第 {n} 行　{msg}" if n else f"  錯誤　{msg}")
        for n, msg in warns:
            print(f"  提醒　第 {n} 行　{msg}")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
