#!/usr/bin/env python3
"""企画パターン分析スクリプト（Google Sheets 版）- RSS + videos.list データ から企画パターンを分析"""

import csv
import json
from collections import defaultdict
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1ZXJOXm_TalrNq83BXaR0W2ilXH5JOjkLNnBgc03Qv1U"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

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

def authenticate_sheets():
    """Google Sheets に認証"""
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPES)
    return gspread.authorize(creds)

def classify_content(title):
    """動画タイトルから企画パターンを分類"""
    text = title.lower()
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

def get_channel_subscriber_count(channels_data, channel_id):
    """チャンネルの登録者数を取得"""
    for size, channels in channels_data.get("classified", {}).items():
        for ch in channels:
            if ch["channel_id"] == channel_id:
                return int(ch.get("subscriber_count", 0))
    return 0

def main():
    print("\n" + "=" * 70)
    print("企画パターン分析（Sheets 版）")
    print("=" * 70)

    # チャンネル情報を読み込み
    with open("claude_code_channels.json", "r", encoding="utf-8") as f:
        channels_data = json.load(f)

    # Google Sheets から動画データを読み込み
    gc = authenticate_sheets()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet("RSS_監視")

    all_rows = worksheet.get_all_values()
    if not all_rows or len(all_rows) < 2:
        print("⚠️ データがありません")
        return

    headers = all_rows[0]
    print(f"\n📋 Sheets からデータを読み込み中... (ヘッダー: {headers})")

    # 必須列を確認
    required_cols = ["channel_id", "channel_name", "video_id", "title", "view_count", "comment_count"]
    for col in required_cols:
        if col not in headers:
            print(f"❌ エラー：'{col}' 列が見つかりません")
            return

    col_indices = {col: headers.index(col) for col in required_cols}

    all_videos = []
    pattern_stats = defaultdict(lambda: {"count": 0, "avg_buzz": 0, "videos": []})

    print(f"\n📊 {len(all_rows) - 1} 本の動画を分析中...\n")

    for i, row in enumerate(all_rows[1:], start=1):
        if len(row) <= max(col_indices.values()) or not row[col_indices["video_id"]]:
            continue

        channel_id = row[col_indices["channel_id"]]
        channel_name = row[col_indices["channel_name"]]
        video_id = row[col_indices["video_id"]]
        title = row[col_indices["title"]]
        view_count = row[col_indices["view_count"]]
        comment_count = row[col_indices["comment_count"]]

        # チャンネルの登録者数を取得
        subscriber_count = get_channel_subscriber_count(channels_data, channel_id)
        if subscriber_count == 0:
            continue

        pattern = classify_content(title)
        buzz_score = calculate_buzz_score(view_count, subscriber_count)

        if i % 50 == 0:
            print(f"[{i:3d}] 📹 {title[:40]}... (バズスコア: {buzz_score})")

        video_data = {
            "channel": channel_name,
            "channel_id": channel_id,
            "video_title": title,
            "video_id": video_id,
            "pattern": pattern,
            "views": int(view_count) if view_count else 0,
            "comments": int(comment_count) if comment_count else 0,
            "buzz_score": buzz_score,
        }

        all_videos.append(video_data)
        pattern_stats[pattern]["count"] += 1
        pattern_stats[pattern]["videos"].append(video_data)

        current_videos = pattern_stats[pattern]["videos"]
        avg_buzz = sum(v["buzz_score"] for v in current_videos) / len(current_videos)
        pattern_stats[pattern]["avg_buzz"] = round(avg_buzz, 2)

    print("\n" + "=" * 70)
    print(f"✅ 分析完了: {len(all_videos)} 本の動画を分析")
    print("=" * 70)

    # TOP 100 = バズスコア80 + 再生数20
    csv_file = "analyzed_videos.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rank_type", "channel", "video_title", "pattern", "views", "comments", "buzz_score"])
        writer.writeheader()

        buzz_sorted = sorted(all_videos, key=lambda x: x["buzz_score"], reverse=True)[:80]
        for video in buzz_sorted:
            writer.writerow({
                "rank_type": "バズスコア",
                "channel": video["channel"],
                "video_title": video["video_title"],
                "pattern": video["pattern"],
                "views": video["views"],
                "comments": video["comments"],
                "buzz_score": video["buzz_score"]
            })

        views_sorted = sorted(all_videos, key=lambda x: x["views"], reverse=True)[:20]
        for video in views_sorted:
            writer.writerow({
                "rank_type": "再生数",
                "channel": video["channel"],
                "video_title": video["video_title"],
                "pattern": video["pattern"],
                "views": video["views"],
                "comments": video["comments"],
                "buzz_score": video["buzz_score"]
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
            "analyzed_at": datetime.now().isoformat(),
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
