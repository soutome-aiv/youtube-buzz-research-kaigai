#!/usr/bin/env python3
"""企画パターン分析（フィルタ版 v2）- 全情報を含む"""

import csv
import json
from collections import defaultdict
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1ZXJOXm_TalrNq83BXaR0W2ilXH5JOjkLNnBgc03Qv1U"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

FILTER_KEYWORDS = {
    "AI系": ["AI", "Claude", "LLM", "機械学習", "自動化", "生成", "アシスタント"],
    "Claude Code系": ["Claude Code", "Code", "プログラミング", "開発", "コード", "エンジニア"],
    "生産性・効率化": ["生産性", "効率化", "時短", "最適化", "オートメーション", "ワークフロー", "タスク自動化"],
}

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

def matches_filter(title):
    """タイトルがフィルタキーワードに該当するかチェック"""
    title_lower = title.lower()
    for category, keywords in FILTER_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return True
    return False

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

def generate_thumbnail_url(video_id):
    """video_id からサムネイル URL を生成"""
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

def main():
    print("\n" + "=" * 70)
    print("企画パターン分析（フィルタ版 v2）- 全情報付き")
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
    print(f"\n📋 Sheets からデータを読み込み中...")

    # 必須列を確認
    required_cols = ["channel_id", "channel_name", "video_id", "title", "view_count", "comment_count", "like_count", "published", "translated_title", "duration_seconds"]
    available_cols = {col: headers.index(col) if col in headers else None for col in required_cols}

    # translated_title がなければ title を使用
    title_col_idx = available_cols.get("translated_title") or available_cols.get("title")

    if title_col_idx is None:
        print(f"❌ エラー：'title' 列が見つかりません")
        return

    all_videos = []
    pattern_stats = defaultdict(lambda: {"count": 0, "avg_buzz": 0, "videos": []})
    filtered_count = 0

    print(f"\n📊 {len(all_rows) - 1} 本の動画からフィルタリング中...\n")

    for i, row in enumerate(all_rows[1:], start=1):
        if len(row) <= max([v for v in available_cols.values() if v is not None]):
            continue

        channel_id = row[available_cols["channel_id"]]
        channel_name = row[available_cols["channel_name"]]
        video_id = row[available_cols["video_id"]]
        title = row[title_col_idx]
        view_count = row[available_cols["view_count"]] if available_cols["view_count"] else "0"
        comment_count = row[available_cols["comment_count"]] if available_cols["comment_count"] else "0"
        like_count = row[available_cols["like_count"]] if available_cols["like_count"] else "0"
        published = row[available_cols["published"]] if available_cols["published"] else ""
        duration_seconds = int(row[available_cols["duration_seconds"]]) if available_cols["duration_seconds"] and row[available_cols["duration_seconds"]] else 0

        # フィルタリング
        if not matches_filter(title):
            continue

        # ✅ Shorts を除外（60秒以下）
        if duration_seconds <= 60:
            continue

        filtered_count += 1

        # チャンネルの登録者数を取得
        subscriber_count = get_channel_subscriber_count(channels_data, channel_id)
        if subscriber_count == 0:
            continue

        pattern = classify_content(title)
        buzz_score = calculate_buzz_score(view_count, subscriber_count)

        if filtered_count % 25 == 0:
            print(f"[{filtered_count:3d}] 📹 {title[:50]}... (バズスコア: {buzz_score})")

        video_type = "Shorts" if duration_seconds <= 60 else "通常動画"
        duration_minutes = duration_seconds // 60

        video_data = {
            "channel": channel_name,
            "channel_id": channel_id,
            "video_id": video_id,
            "video_title": title,  # 日本語翻訳版
            "original_title": row[available_cols["title"]] if available_cols["title"] else "",  # 元の英語タイトル
            "pattern": pattern,
            "views": int(view_count) if view_count else 0,
            "likes": int(like_count) if like_count else 0,
            "comments": int(comment_count) if comment_count else 0,
            "subscriber_count": subscriber_count,
            "buzz_score": buzz_score,
            "published": published[:10] if published else "",  # YYYY-MM-DD形式
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_minutes,
            "video_type": video_type,
            "thumbnail_url": generate_thumbnail_url(video_id),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        }

        all_videos.append(video_data)
        pattern_stats[pattern]["count"] += 1
        pattern_stats[pattern]["videos"].append(video_data)

        current_videos = pattern_stats[pattern]["videos"]
        avg_buzz = sum(v["buzz_score"] for v in current_videos) / len(current_videos)
        pattern_stats[pattern]["avg_buzz"] = round(avg_buzz, 2)

    print("\n" + "=" * 70)
    print(f"✅ フィルタ完了: {filtered_count} 本の関連動画を抽出")
    print(f"✅ 分析対象: {len(all_videos)} 本")
    print("=" * 70)

    if len(all_videos) == 0:
        print("⚠️ フィルタ条件に該当する動画がありません")
        return

    # バズスコア順にソート
    all_videos_sorted = sorted(all_videos, key=lambda x: x["buzz_score"], reverse=True)

    # CSV出力
    csv_file = "analyzed_videos_filtered_v2.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["rank", "channel", "video_title", "pattern", "views", "likes", "comments", "subscriber_count", "buzz_score", "published", "video_id"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rank, video in enumerate(all_videos_sorted[:100], 1):
            writer.writerow({
                "rank": rank,
                "channel": video["channel"],
                "video_title": video["video_title"],
                "pattern": video["pattern"],
                "views": video["views"],
                "likes": video["likes"],
                "comments": video["comments"],
                "subscriber_count": video["subscriber_count"],
                "buzz_score": video["buzz_score"],
                "published": video["published"],
                "video_id": video["video_id"],
            })

    print(f"\n📊 CSV 出力: {csv_file}")

    # JSON出力（ダッシュボード用）
    json_file = "buzz_videos_data.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_count": len(all_videos),
            "videos": all_videos_sorted[:100],
            "patterns": {
                pattern: {
                    "count": stats["count"],
                    "avg_buzz_score": stats["avg_buzz"],
                }
                for pattern, stats in sorted(pattern_stats.items(), key=lambda x: x[1]["avg_buzz"], reverse=True)
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"📋 JSON 出力: {json_file}")

    print("\n" + "=" * 70)
    print("📈 企画パターン統計（バズスコア順）")
    print("=" * 70)

    sorted_patterns = sorted(pattern_stats.items(), key=lambda x: x[1]["avg_buzz"], reverse=True)

    for pattern, stats in sorted_patterns:
        print(f"\n{pattern}")
        print(f"  出現数: {stats['count']}本")
        print(f"  平均バズスコア: {stats['avg_buzz']}")

    print("\n✅ 企画パターン分析完了！")
    print(f"📊 ダッシュボード用データ: {json_file}")

if __name__ == "__main__":
    main()
