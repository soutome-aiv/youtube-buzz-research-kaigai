#!/usr/bin/env python3
"""Claude Code 関連チャンネル大量スキャン"""

import os
import csv
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

# .env ファイルから API キーをロード
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    print("❌ エラー: YOUTUBE_API_KEY が設定されていません")
    exit(1)

youtube = build("youtube", "v3", developerKey=API_KEY)

# 検索キーワード（複数パターン）
KEYWORDS = [
    "Claude Code",
    "Claude API",
    "Anthropic Claude",
    "Claude AI development",
    "Claude tutorial",
    "Claude programming",
    "Anthropic AI",
]

def classify_channel_size(subscriber_count):
    """登録者数によるチャンネル規模分類"""
    try:
        count = int(subscriber_count)
        if count > 1000000:
            return "大型 (>100万)"
        elif count >= 100000:
            return "中型 (10万～100万)"
        else:
            return "小型 (<10万)"
    except:
        return "不明"

def search_channels_by_keyword(keyword, max_results=10):
    """キーワードでチャンネルを検索"""
    try:
        request = youtube.search().list(
            q=keyword,
            part="snippet",
            type="channel",
            maxResults=max_results,
            order="relevance",
            regionCode="US"
        )
        response = request.execute()
        return response.get("items", [])
    except HttpError as e:
        print(f"❌ {keyword} 検索エラー: {e}")
        return []

def get_channel_details(channel_id):
    """チャンネルの詳細情報を取得"""
    try:
        request = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            return None

        channel = response["items"][0]
        snippet = channel["snippet"]
        stats = channel["statistics"]

        return {
            "channel_id": channel_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:100],
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscriber_count": stats.get("subscriberCount", "0"),
            "video_count": stats.get("videoCount", "0"),
            "view_count": stats.get("viewCount", "0"),
        }
    except HttpError as e:
        print(f"❌ チャンネル詳細取得エラー (ID: {channel_id}): {e}")
        return None

def main():
    print("\n" + "=" * 60)
    print("Claude Code 関連チャンネル 大量スキャン開始")
    print("=" * 60)

    all_channels = {}  # チャンネルID をキーに重複排除

    # 各キーワードで検索
    for keyword in KEYWORDS:
        print(f"\n🔍 検索中: '{keyword}'")
        search_results = search_channels_by_keyword(keyword, max_results=15)

        for item in search_results:
            channel_id = item["snippet"]["channelId"]

            # 重複チェック
            if channel_id in all_channels:
                print(f"  ⚠️ スキップ (重複): {item['snippet']['title']}")
                continue

            # チャンネル詳細取得
            print(f"  📥 取得中: {item['snippet']['title']}")
            details = get_channel_details(channel_id)

            if details:
                all_channels[channel_id] = details
                print(f"    ✅ 成功 | 登録者: {details['subscriber_count']}")
            else:
                print(f"    ❌ スキップ")

    print(f"\n" + "=" * 60)
    print(f"✅ スキャン完了: 合計 {len(all_channels)} チャンネル取得")
    print("=" * 60)

    if not all_channels:
        print("❌ チャンネルが見つかりません")
        return

    # 規模別分類
    classified = {"大型 (>100万)": [], "中型 (10万～100万)": [], "小型 (<10万)": []}

    for channel_id, info in all_channels.items():
        size = classify_channel_size(info["subscriber_count"])
        info["size"] = size
        if size in classified:
            classified[size].append(info)

    # CSV で出力
    output_file = "claude_code_channels.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["channel_id", "title", "size", "subscriber_count", "video_count", "view_count", "description"])
        writer.writeheader()

        for channel_id, info in all_channels.items():
            writer.writerow({
                "channel_id": info["channel_id"],
                "title": info["title"],
                "size": info.get("size", "不明"),
                "subscriber_count": info["subscriber_count"],
                "video_count": info["video_count"],
                "view_count": info["view_count"],
                "description": info["description"]
            })

    print(f"\n📊 CSV 出力: {output_file}")

    # 規模別サマリー表示
    print("\n" + "=" * 60)
    print("📈 規模別チャンネル分類")
    print("=" * 60)

    for size in ["大型 (>100万)", "中型 (10万～100万)", "小型 (<10万)"]:
        channels = classified[size]
        print(f"\n{size}: {len(channels)} チャンネル")
        for info in sorted(channels, key=lambda x: int(x["subscriber_count"]) if x["subscriber_count"].isdigit() else 0, reverse=True)[:5]:
            print(f"  • {info['title']} ({info['subscriber_count']} 登録者)")

    # JSON でも出力（Google Sheets 連携用）
    output_json = "claude_code_channels.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "scanned_at": datetime.now().isoformat(),
            "total_channels": len(all_channels),
            "classified": {
                size: [
                    {
                        "channel_id": ch["channel_id"],
                        "title": ch["title"],
                        "subscriber_count": ch["subscriber_count"],
                        "video_count": ch["video_count"],
                        "view_count": ch["view_count"]
                    }
                    for ch in classified[size]
                ]
                for size in classified
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"\n📋 JSON 出力: {output_json}")
    print("\n✅ すべての出力完了！")

if __name__ == "__main__":
    main()
