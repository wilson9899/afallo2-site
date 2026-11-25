---
title: 'AllO2 碳市場情報'
date: 2026-11-25
type: landing

sections:
  - block: hero
    content:
      eyebrow: AllO2 碳市場情報
      title: 每天讀懂國際[碳市場]
      text: 我們每日追蹤國際碳市場、碳權標準與各國政策，整理成繁體中文的快訊、週報與專題，協助台灣企業掌握碳權採購與減碳決策所需的資訊。
      primary_action:
        text: 看今日市場動態
        url: /news/
        icon: newspaper
      secondary_action:
        text: 閱讀市場週報
        url: /reports/weekly/
        icon: document-text
    design:
      spacing:
        padding: ['6rem', 0, '4rem', 0]

  - block: features
    id: features
    content:
      subtitle: 內容更新頻率
      title: 四種內容，各自準時更新
      text: 網站內容由固定排程產出，排程完成後會自動同步到網站。
      items:
        - name: 市場動態（每日）
          icon: bolt
          description: 每天早上整理國際碳市場的新聞標題與重點，並附上原文連結。
        - name: 市場週報（每週一）
          icon: document-text
          description: 回顧上週價格、交易、標準與政策的重要變化，可下載 Word 版本。
        - name: 碳市場掃描（每週四）
          icon: magnifying-glass
          description: 聚焦台灣企業關心的國外碳權認可準則、新方法學與新專案類型。
        - name: 文章（每週五）
          icon: pencil-square
          description: 以淺顯的方式說明碳權採購、碳中和宣告與相關實務問題。
    design:
      layout: grid
      css_class: "bg-gray-50 dark:bg-gray-900/50"

  - block: collection
    id: news
    content:
      title: 最新市場動態
      count: 5
      filters:
        folders:
          - news
      archive:
        enable: true
        text: 所有市場動態
        link: /news/
    design:
      view: date-title-summary
      columns: 1

  - block: collection
    id: weekly
    content:
      title: 市場週報
      count: 3
      filters:
        folders:
          - reports/weekly
      archive:
        enable: true
        text: 所有週報
        link: /reports/weekly/
    design:
      view: card
      columns: 3

  - block: collection
    id: scan
    content:
      title: 碳市場掃描
      count: 3
      filters:
        folders:
          - reports/scan
      archive:
        enable: true
        text: 所有掃描報告
        link: /reports/scan/
    design:
      view: card
      columns: 3

  - block: collection
    id: blog
    content:
      title: 文章
      count: 3
      filters:
        folders:
          - blog
      archive:
        enable: true
        text: 所有文章
        link: /blog/
    design:
      view: card
      columns: 3

  - block: cta-card
    id: contact
    content:
      title: 想討論碳權採購或減碳規劃？
      text: 歡迎透過 Facebook 專頁與我們聯繫。
      button:
        text: 前往 Facebook 專頁
        url: https://www.facebook.com/profile.php?id=61571855224086
    design:
      card:
        css_class: "bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600 text-white shadow-2xl"
---
