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
2. 沒有命中：寫入對應資料夾，提交並推送到 main，網站約 2 分鐘後更新。
3. 有命中：不推送到 main，改推到 publish/<類型>-<日期> 分支，
   印出命中的關鍵字與建立 PR 的網址，結束碼為 2。
4. 找不到清單：一律視為命中處理（不推送到 main），避免漏網。
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


def repo_web_url():
    url = git("remote", "get-url", "origin").stdout.strip()
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return f"https://github.com/{m.group(1)}" if m else url


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

    # 1. 禁止發佈清單
    words = load_blocklist(a.blocklist)
    scan_text = title + "\n" + body
    for att in a.attach:
        if att.lower().endswith(".docx"):
            scan_text += "\n" + docx_text(att)
    if words is None:
        hits = ["（找不到禁止發佈清單）"]
    else:
        hits = find_hits(scan_text, words)

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
        print("命中：" + ("、".join(hits) if hits else "無"))
        return 2 if hits else 0

    # 3. 提交並推送
    git("fetch", "origin", "main")
    git("add", str(rel))
    msg = f"{label}：{date}"
    if hits:
        branch = f"publish/{a.kind}-{date}"
        git("checkout", "-B", branch)
        git("commit", "-m", msg + "（待審核）")
        git("push", "-u", "origin", branch, "--force")
        git("checkout", "main")
        print("命中禁止發佈清單：" + "、".join(hits))
        print("未上線。已推到分支 " + branch + "，請審核後合併：")
        print(f"{repo_web_url()}/compare/main...{branch}?expand=1")
        return 2
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
