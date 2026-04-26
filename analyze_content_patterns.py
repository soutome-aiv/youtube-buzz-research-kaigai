#!/usr/bin/env python3
"""Claude Code 動画の企画パターン分析（最適化版）
- 直近1ヶ月活発な30チャンネル
- 各チャンネル15動画取得
- TOP100 = バズスコア80本 + 再生数20本
"""

import os
import json
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    print("❌ エラー: YOUTUBE_API_KEY が設定されていません")
    exit(1)

youtube = build("youtube", "v3", developerKey=API_KEY)

CONTENT_PATTERNS = {
    "チュートリアル": ["tutorial", "how to", "how-to", "始め方", "入門", "ガイド", "guide"],
    "実装例": ["build", "create", "implement", "building", "実装", "開発", "develop"],
    "トレンド・ニュース": ["news", "update", "release", "新機能", "announcement", "発表", "トレンド"],
    "比較": ["vs", "comparison", "compare", "比較", "違い", "difference"],
    "事例紹介": ["case study", "example", "demo", "事例", "ユースケース", "use case"],
    "Tips・技術": ["tips", "trick", "hack", "best practice", "テクニック", "コツ"],
    "プロジェクト紹介": ["project", "showcase", "プロジェクト", "作品", "ポートフォリオ"],
    "AI活用": ["ai", "artificial intelligence", "machine learning", "claude", "ai活用"],
    "統合・連携": ["integration", "api", "connect", "連携", "統合"],
    "レビュー": ["review", "opinion", "thought", "レビュー", "感想", "評価"],
}

def classify_content(title, description):
    """動画タイトル・説明文から企画パターンを分類"""
    text = (title + " " + description).lower()
    matches = {}
    for pattern, keywords in CONTENT_PATTERNS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                matches[pattern] = matches.get(pattern, 0) + 1
    return max(matches, key=matches.get) if matches else "その他"

def calculate_buzz_score(view_count, subscriber_count):
    """バズ度スコアを計算（再生数/登録者数）"""
    try:
        views = int(view_count)
        subs = int(subscriber_count)
        return round((views / subs) * 100, 2) if subs > 0 else 0
    except:
        return 0

def get_channel_videos(channel_id, max_results=15):
    """チャンネルの最新動画を取得"""
    try:
        request = youtube.search().list(
            channelId=channel_id,
            part="snippet",
            type="video",
            maxResults=max_results,
            order="date"
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            print(f"      ⚠️ 動画0件")
        return items
    except HttpError as e:
        print(f"      ❌ API エラー: {e}")
        return []
    except Exception as e:
        print(f"      ❌ 予期しないエラー: {e}")
        return []

def get_video_details(video_id):
    """動画の詳細情報を取得"""
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        )
        response = request.execute()
        if not response.get("items"):
            return None
        video = response["items"][0]
        return {
            "title": video["snippet"]["title"],
            "description": video["snippet"]["description"],
            "view_count": video["statistics"].get("viewCount", "0"),
            "like_count": video["statistics"].get("likeCount", "0"),
            "published_at": video["snippet"]["publishedAt"],
        }
    except HttpError as e:
        print(f"      ❌ API エラー: {e}")
        return None

def get_active_channels(channels_data, days=30):
    """直近N日で投稿が活発な30チャンネルを抽出"""
    cutoff_date = (datetime.now() - timedelta(days=days)).date()
    active_channels = []

    for size, channels in channels_data["classified"].items():
        for channel in channels:
            channel_id = channel["channel_id"]
            channel_title = channel["title"]
            subs = channel["subscriber_count"]

            # 最新1動画を取得して投稿日を確認
            videos = get_channel_videos(channel_id, max_results=1)
            if videos:
                published_at = videos[0]["snippet"]["publishedAt"][:10]
                if published_at >= cutoff_date.isoformat():
                    active_channels.append({
                        "channel_id": channel_id,
                        "title": channel_title,
                        "subscriber_count": subs,
                        "size": size,
                        "latest_post": published_at
                    })

    # 投稿日が新しい順に30チャンネルを選定
    active_channels = sorted(active_channels, key=lambda x: x["latest_post"], reverse=True)[:30]
    return active_channels

def main():
    print("\n" + "=" * 70)
    print("Claude Code 動画 企画パターン分析（最適化版）")
    print("=" * 70)

    cutoff_date = (datetime.now() - timedelta(days=30)).date()
    print(f"\n📅 分析対象期間: {cutoff_date} 以降")

    with open("claude_code_channels.json", "r", encoding="utf-8") as f:
        channels_data = json.load(f)

    print("\n🔍 直近1ヶ月で投稿が活発なチャンネルを特定中...")
    active_channels = get_active_channels(channels_data, days=30)
    print(f"✅ 活発なチャンネル: {len(active_channels)} 件")

    all_videos = []
    pattern_stats = defaultdict(lambda: {"count": 0, "avg_buzz": 0, "videos": []})
    debug_stats = {"total_searched": 0, "total_fetched": 0, "total_filtered": 0}

    print(f"\n📺 {len(active_channels)} チャンネルから動画取得中...")
    for i, channel in enumerate(active_channels, 1):
        channel_id = channel["channel_id"]
        channel_title = channel["title"]
        subs = channel["subscriber_count"]

        print(f"  [{i:2d}/30] 📥 {channel_title}...", end="", flush=True)

        videos = get_channel_videos(channel_id, max_results=15)
        debug_stats["total_searched"] += len(videos)

        if not videos:
            print(" (動画なし)")
            continue

        for item in videos:
            if "videoId" not in item["snippet"]:
                continue

            video_id = item["snippet"]["videoId"]
            details = get_video_details(video_id)
            if not details:
                continue

            debug_stats["total_fetched"] += 1

            pattern = classify_content(details["title"], details["description"])
            buzz_score = calculate_buzz_score(details["view_count"], subs)

            published_date_str = details["published_at"][:10]
            if published_date_str < cutoff_date.isoformat():
                debug_stats["total_filtered"] += 1
                continue

            video_data = {
                "channel": channel_title,
                "channel_id": channel_id,
                "size": channel["size"],
                "video_title": details["title"],
                "video_id": video_id,
                "pattern": pattern,
                "views": int(details["view_count"]),
                "buzz_score": buzz_score,
                "published": details["published_at"][:10],
            }

            all_videos.append(video_data)
            pattern_stats[pattern]["count"] += 1
            pattern_stats[pattern]["videos"].append(video_data)

            current_videos = pattern_stats[pattern]["videos"]
            avg_buzz = sum(v["buzz_score"] for v in current_videos) / len(current_videos)
            pattern_stats[pattern]["avg_buzz"] = round(avg_buzz, 2)

        print(" ✅")

    print("\n" + "=" * 70)
    print(f"✅ 分析完了: {len(all_videos)} 本の動画を分析")
    print("=" * 70)
    print(f"\n🔍 デバッグ情報:")
    print(f"  検索で見つかった動画: {debug_stats['total_searched']} 本")
    print(f"  詳細取得成功: {debug_stats['total_fetched']} 本")
    print(f"  日付フィルタで除外: {debug_stats['total_filtered']} 本")
    print(f"  最終分析対象: {len(all_videos)} 本")

    # TOP 100 = バズスコア80 + 再生数20
    csv_file = "analyzed_videos.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rank_type", "channel", "size", "video_title", "pattern", "views", "buzz_score", "published"])
        writer.writeheader()

        buzz_sorted = sorted(all_videos, key=lambda x: x["buzz_score"], reverse=True)[:80]
        for video in buzz_sorted:
            video["rank_type"] = "バズスコア"
            writer.writerow({
                "rank_type": video["rank_type"],
                "channel": video["channel"],
                "size": video["size"],
                "video_title": video["video_title"],
                "pattern": video["pattern"],
                "views": video["views"],
                "buzz_score": video["buzz_score"],
                "published": video["published"]
            })

        views_sorted = sorted(all_videos, key=lambda x: x["views"], reverse=True)[:20]
        for video in views_sorted:
            video["rank_type"] = "再生数"
            writer.writerow({
                "rank_type": video["rank_type"],
                "channel": video["channel"],
                "size": video["size"],
                "video_title": video["video_title"],
                "pattern": video["pattern"],
                "views": video["views"],
                "buzz_score": video["buzz_score"],
                "published": video["published"]
            })

    print(f"\n📊 CSV 出力: {csv_file}")

    print("\n" + "=" * 70)
    print("📈 企画パターン統計（バズスコア順）")
    print("=" * 70)

    sorted_patterns = sorted(pattern_stats.items(), key=lambda x: x[1]["avg_buzz"], reverse=True)

    for pattern, stats in sorted_patterns:
        print(f"\n{pattern}")
        print(f"  出現数: {stats['count']}本")
        print(f"  平均バズスコア: {stats['avg_buzz']}")

        top_videos = sorted(stats["videos"], key=lambda x: x["buzz_score"], reverse=True)[:3]
        for video in top_videos:
            print(f"    • {video['video_title'][:50]}... (バズスコア: {video['buzz_score']})")

    json_file = "content_pattern_analysis.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_videos": len(all_videos),
            "patterns": {
                pattern: {
                    "count": stats["count"],
                    "avg_buzz_score": stats["avg_buzz"],
                    "top_videos": [
                        {
                            "title": v["video_title"],
                            "channel": v["channel"],
                            "buzz_score": v["buzz_score"]
                        }
                        for v in sorted(stats["videos"], key=lambda x: x["buzz_score"], reverse=True)[:5]
                    ]
                }
                for pattern, stats in sorted_patterns
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"\n📋 JSON 出力: {json_file}")
    print("\n✅ 企画パターン分析完了！")

if __name__ == "__main__":
    main()
