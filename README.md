# afallo2.com

AllO2 碳市場情報網站。使用 [HugoBlox](https://github.com/HugoBlox/kit) 建置，推到 `main` 後由 GitHub Actions 自動發佈到 GitHub Pages。

## 內容區塊

| 資料夾 | 網站區塊 | 來源排程 |
|---|---|---|
| `content/news/` | 市場動態 | 【每日】qcintel 碳市場快訊閱讀（公開版） |
| `content/reports/weekly/` | 市場週報 | 【每週一】市場資訊週報 |
| `content/reports/scan/` | 碳市場掃描 | Carbon market weekly scan（每週四，公開版） |
| `content/blog/` | 文章 | Facebook 專頁周報（每週五） |

## 排程任務如何同步網站

每個任務最後執行一次：

```bash
cd <afallo2-site 本機路徑>
git checkout main && git pull
python tools/publish.py news   公開版.md
python tools/publish.py weekly 公開版.md --attach 市場資訊週報.docx
python tools/publish.py scan   公開版.md
python tools/publish.py blog   文章.md --attach 圖卡.png
```

- 含有禁止發佈字詞的段落、條列項目、表格列會整段刪除；標題含字詞、刪完沒有內容、或 .docx 附件含字詞時，該則（或該附件）不發佈。
- 刪除後再檢查一次，確定乾淨才推到 `main`，約 2 分鐘後上線。
- 找不到清單時不發佈。

## 禁止發佈清單

清單只存在執行排程的電腦上：`~/.afallo2/blocklist.txt`，一行一個字詞，`#` 開頭為註解。不放進這個程式庫，也不放進 GitHub 的任何設定。`tools/publish.py` 推送前在本機比對，找不到清單就不發佈。

## 本機預覽

```bash
pnpm install
hugo server
```
