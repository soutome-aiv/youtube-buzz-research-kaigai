#!/bin/bash
# YouTube リサーチ自動化パイプライン

cd /Users/masaki.1119/Movies/株式会社AIVEST/海外YTリサーチ

# スクリプト実行
case "$1" in
  rss)
    python3 fetch_rss_feeds.py
    ;;
  details)
    python3 fetch_video_details.py
    ;;
  analysis)
    python3 analyze_content_patterns_v2.py
    ;;
  *)
    echo "使用方法: $0 {rss|details|analysis}"
    exit 1
    ;;
esac
