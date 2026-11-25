#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建置前檢查：content/ 裡若出現禁止發佈清單的字詞，建置失敗，網站維持舊版。

清單從環境變數 PUBLISH_BLOCKLIST 讀取（GitHub Secret），一行或逗號分隔一個字詞。
輸出只說明哪個檔案命中，不印出字詞本身，避免清單出現在公開的建置紀錄裡。
"""
import os
import re
import sys
import zipfile
from pathlib import Path

words = [w.strip().lower() for w in re.split(r"[\n,]", os.environ.get("PUBLISH_BLOCKLIST", ""))
         if w.strip() and not w.strip().startswith("#")]
if not words:
    print("::warning::未設定 PUBLISH_BLOCKLIST，略過禁止發佈檢查")
    sys.exit(0)

bad = []
for p in Path(sys.argv[1] if len(sys.argv) > 1 else "content").rglob("*"):
    if p.suffix.lower() in (".md", ".html", ".yaml", ".yml", ".txt", ".csv"):
        text = p.read_text(encoding="utf-8", errors="ignore")
    elif p.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(p) as z:
                text = re.sub(r"<[^>]+>", "", z.read("word/document.xml").decode("utf-8", "ignore"))
        except Exception:
            continue
    else:
        continue
    n = sum(1 for w in words if w in text.lower())
    if n:
        bad.append((p, n))

for p, n in bad:
    print(f"::error file={p}::此檔案含 {n} 個禁止發佈字詞")
sys.exit(1 if bad else 0)
