#!/usr/bin/env python3
"""RSS フィード監視スクリプト - 30チャンネルの新規投稿を Google Sheets に自動記録"""

import feedparser
import csv
from datetime import datetime
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Google Sheets 認証
SPREADSHEET_ID = "1ZXJOXm_TalrNq83BXaR0W2ilXH5JOjkLNnBgc03Qv1U"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def authenticate_sheets():
    """Google Sheets に認証"""
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPES)
    return gspread.authorize(creds)

def fetch_rss_feeds():
    """RSS フィードから新規投稿を取得"""
    print("\n" + "=" * 70)
    print("RSS フィード監視開始")
    print("=" * 70)

    # TOP 30 チャンネルの RSS URL を読み込み
    channels = []
    with open("rss_channels_top30.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channels.append({
                "channel_id": row["channel_id"],
                "channel_name": row["channel_name"],
                "rss_url": row["rss_url"]
            })

    all_videos = []

    # 各チャンネルから最新投稿を取得
    for i, ch in enumerate(channels, 1):
        print(f"[{i:2d}/30] 📺 {ch['channel_name']}...", end="", flush=True)

        try:
            feed = feedparser.parse(ch["rss_url"])

            # 最新5本の投稿を取得
            for entry in feed.entries[:5]:
                video_id = entry.id.split("yt:video:")[1] if "yt:video:" in entry.id else "N/A"

                all_videos.append({
                    "channel_id": ch["channel_id"],
                    "channel_name": ch["channel_name"],
                    "video_id": video_id,
                    "title": entry.title,
                    "published": entry.published,
                    "fetched_at": datetime.now().isoformat()
                })

            print(" ✅")
        except Exception as e:
            print(f" ❌ エラー: {e}")

    print("\n" + "=" * 70)
    print(f"✅ 取得完了: {len(all_videos)} 本の動画を取得")
    print("=" * 70)

    return all_videos

def upload_to_sheets(videos):
    """取得した動画を Google Sheets に追記"""
    print("\n📤 Google Sheets にアップロード中...")

    gc = authenticate_sheets()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    # "RSS_監視" シートを取得
    try:
        worksheet = spreadsheet.worksheet("RSS_監視")
        # 既存データをクリア（ヘッダーは保持）
        if worksheet.row_count > 1:
            worksheet.delete_rows(2, worksheet.row_count)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="RSS_監視", rows=10000, cols=6)

    # ヘッダーが無い場合は追加
    if not worksheet.cell(1, 1).value:
        headers = ["channel_id", "channel_name", "video_id", "title", "published", "fetched_at"]
        worksheet.insert_rows([headers], 1)

    # 動画データを追記
    rows = []
    for video in videos:
        rows.append([
            video["channel_id"],
            video["channel_name"],
            video["video_id"],
            video["title"],
            video["published"],
            video["fetched_at"]
        ])

    if rows:
        worksheet.append_rows(rows)
        print(f"✅ {len(rows)} 本の動画を追記しました")
    else:
        print("⚠️ 追記する動画がありません")

if __name__ == "__main__":
    videos = fetch_rss_feeds()
    upload_to_sheets(videos)
    print("\n✅ RSS 監視完了！")
