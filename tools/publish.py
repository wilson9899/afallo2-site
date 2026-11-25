#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把排程任務產出的「公開版」報告同步到 afallo2.com。

用法（在 afallo2-site 程式庫根目錄執行）：

    python tools/publish.py news   <公開版.md>                 # 每日市場動態
    python tools/publish.py weekly <公開版.md> --attach 週報.docx
    python tools/publish.py scan   <公開版.md>
    python tools/publish.py blog   <文章.md> --attach 圖卡.png

選項：
    --title  標題（預設取 .md 第一個 # 標題）
    --date   日期 YYYY-MM-DD（預設今天，台北時間）
    --dry-run  只檢查與寫檔，不提交也不推送

流程：
1. 讀取禁止發佈清單，比對全文（含附件 .docx 的文字）。
   清單來源依序為：環境變數 PUBLISH_BLOCKLIST、--blocklist 指定的檔案、
   ~/.afallo2/blocklist.txt。清單一行一個關鍵字，# 開頭為註解。
   清單絕不放進這個公開程式庫。
2. 有命中：整段刪除。含有清單字詞的段落、條列項目、表格列一律刪掉，
   標題含有字詞則整則不發佈。.docx 附件含有字詞就不附上。
   刪除後若沒有剩下內容，整則不發佈。
3. 刪除後再檢查一次，確定沒有任何字詞，才提交並推送到 main，
   網站約 2 分鐘後更新。
4. 找不到清單：不發佈，結束碼為 2，避免漏網。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPE = timezone(timedelta(hours=8))

KINDS = {
    "news":   ("content/news",           "市場動態"),
    "weekly": ("content/reports/weekly", "市場週報"),
    "scan":   ("content/reports/scan",   "碳市場掃描"),
    "blog":   ("content/blog",           "文章"),
}


def load_blocklist(path_arg):
    env = os.environ.get("PUBLISH_BLOCKLIST", "")
    text = None
    if env.strip():
        text = env
    else:
        for p in [path_arg, Path.home() / ".afallo2" / "blocklist.txt"]:
            if p and Path(p).expanduser().is_file():
                text = Path(p).expanduser().read_text(encoding="utf-8")
                break
    if text is None:
        return None
    words = []
    for line in re.split(r"[\n,]", text):
        w = line.strip()
        if w and not w.startswith("#"):
            words.append(w)
    return words


def docx_text(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", "", xml)
    except Exception:
        return ""


def find_hits(text, words):
    low = text.lower()
    return sorted({w for w in words if w.lower() in low})


def redact(body, words):
    """刪除含有清單字詞的段落、條列項目或表格列。回傳 (新內文, 刪除數)。"""
    out, removed = [], 0
    for block in re.split(r"(\n\s*\n)", body):
        if not find_hits(block, words):
            out.append(block)
            continue
        lines = block.split("\n")
        if all(re.match(r"^\s*([-*+]|\d+[.)]|\|)", l) or not l.strip() for l in lines):
            # 條列或表格：只刪命中的那幾行
            kept = [l for l in lines if not find_hits(l, words)]
            removed += len(lines) - len(kept)
            out.append("\n".join(kept))
        else:
            removed += 1
    text = "".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, removed


def split_front_matter(md):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", md, re.S)
    if m:
        return m.group(1), m.group(2)
    return "", md


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def first_heading(body):
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return m.group(1).strip() if m else None


def summarize(body, n=80):
    for para in re.split(r"\n\s*\n", body):
        t = para.strip()
        if not t or t.startswith(("#", "|", "!", "-", "*", ">")):
            continue
        t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
        t = re.sub(r"[*_`]", "", t).replace("\n", " ")
        return t[:n] + ("…" if len(t) > n else "")
    return ""


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check,
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=KINDS)
    ap.add_argument("source")
    ap.add_argument("--title")
    ap.add_argument("--date")
    ap.add_argument("--attach", action="append", default=[])
    ap.add_argument("--blocklist")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = Path(a.source).expanduser()
    md = src.read_text(encoding="utf-8")
    fm, body = split_front_matter(md)
    date = a.date or datetime.now(TPE).strftime("%Y-%m-%d")
    folder, label = KINDS[a.kind]

    title = a.title or first_heading(body) or f"{label} {date}"
    # 標題已放進 front matter，移除內文中重複的第一個 # 標題
    body = re.sub(r"^#\s+.+\n+", "", body.lstrip(), count=1)

    # 1. 禁止發佈清單：命中的內容整段刪除
    words = load_blocklist(a.blocklist)
    if words is None:
        print("找不到禁止發佈清單，不發佈。")
        return 2
    if find_hits(title, words):
        print("標題含有禁止發佈字詞，整則不發佈。")
        return 2
    body, removed = redact(body, words)
    attaches = []
    for att in a.attach:
        if att.lower().endswith(".docx") and find_hits(docx_text(att), words):
            print(f"附件 {Path(att).name} 含有禁止發佈字詞，不附上。")
            removed += 1
            continue
        attaches.append(att)
    a.attach = attaches
    if find_hits(body, words):
        print("刪除後仍有禁止發佈字詞，不發佈。")
        return 2
    if not summarize(body, 1) and not re.search(r"\S", re.sub(r"^#.*$", "", body, flags=re.M)):
        print("刪除後沒有剩下內容，不發佈。")
        return 2
    if removed:
        print(f"已刪除 {removed} 段含禁止發佈字詞的內容。")

    # 2. 寫入頁面
    slug = date if a.kind != "blog" else f"{date}-{re.sub(r'[^0-9A-Za-z一-鿿]+', '-', title).strip('-')[:40]}"
    page_dir = ROOT / folder / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"title: {yaml_str(title)}", f"date: {date}",
             f"summary: {yaml_str(summarize(body))}"]
    if fm.strip():
        keep = [l for l in fm.splitlines()
                if not re.match(r"^(title|date|summary):", l)]
        lines += keep
    lines.append("---")
    for att in a.attach:
        p = Path(att).expanduser()
        ext = p.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".webp"):
            shutil.copy(p, page_dir / f"featured{ext}")
        else:
            shutil.copy(p, page_dir / p.name)
            body += f"\n\n[下載 {p.name}]({p.name})\n"
    (page_dir / "index.md").write_text("\n".join(lines) + "\n\n" + body.strip() + "\n",
                                       encoding="utf-8")
    rel = page_dir.relative_to(ROOT)
    print(f"已寫入 {rel}")

    if a.dry_run:
        print("（試跑，不提交）")
        return 0

    # 3. 提交並推送
    git("fetch", "origin", "main")
    git("add", str(rel))
    msg = f"{label}：{date}"
    git("commit", "-m", msg)
    r = git("pull", "--rebase", "origin", "main", check=False)
    if r.returncode != 0:
        print(r.stderr)
        return 1
    git("push", "origin", "HEAD:main")
    print("已推送到 main，網站約 2 分鐘後更新。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
