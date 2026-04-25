#!/usr/bin/env python3
"""動画詳細取得スクリプト - video_id から再生数・コメント数を取得して Google Sheets に追記"""

import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
SPREADSHEET_ID = "1ZXJOXm_TalrNq83BXaR0W2ilXH5JOjkLNnBgc03Qv1U"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

if not API_KEY:
    print("❌ エラー: YOUTUBE_API_KEY が設定されていません")
    exit(1)

youtube = build("youtube", "v3", developerKey=API_KEY)

def authenticate_sheets():
    """Google Sheets に認証"""
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPES)
    return gspread.authorize(creds)

def parse_duration(duration_str):
    """ISO 8601 形式の duration を秒に変換"""
    import re
    if not duration_str:
        return 0

    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds

def get_video_details(video_id):
    """動画の再生数・いいね数・コメント数・duration を取得"""
    try:
        request = youtube.videos().list(
            part="statistics,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get("items"):
            return None

        item = response["items"][0]
        stats = item["statistics"]
        duration_str = item.get("contentDetails", {}).get("duration", "PT0S")
        duration_seconds = parse_duration(duration_str)

        return {
            "view_count": stats.get("viewCount", "0"),
            "like_count": stats.get("likeCount", "0"),
            "comment_count": stats.get("commentCount", "0"),
            "duration_seconds": str(duration_seconds)
        }
    except HttpError as e:
        print(f"      ❌ API エラー: {e}")
        return None

def fetch_and_update_details():
    """Sheets から video_id を読み込んで詳細を取得・追記"""
    print("\n" + "=" * 70)
    print("動画詳細取得開始")
    print("=" * 70)

    gc = authenticate_sheets()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    # "RSS_監視" シートを取得
    try:
        worksheet = spreadsheet.worksheet("RSS_監視")
    except gspread.exceptions.WorksheetNotFound:
        print("❌ エラー：'RSS_監視' シートが見つかりません")
        return

    # すべての行を取得
    all_rows = worksheet.get_all_values()

    if not all_rows or len(all_rows) < 2:
        print("⚠️ データがありません")
        return

    # ヘッダー行を確認
    headers = all_rows[0]
    if "video_id" not in headers:
        print("❌ エラー：'video_id' 列が見つかりません")
        return

    # 詳細データ用の新しい列を追加（まだなければ）
    required_headers = ["view_count", "like_count", "comment_count", "duration_seconds"]
    headers_list = list(headers)

    for header in required_headers:
        if header not in headers_list:
            headers_list.append(header)

    # ヘッダー行を必ず更新（データ書き込み前に確保）
    worksheet.update(range_name="A1", values=[headers_list])
    headers = headers_list

    video_id_index = headers.index("video_id")

    # 詳細データ列の index を取得
    view_count_index = headers.index("view_count")
    like_count_index = headers.index("like_count")
    comment_count_index = headers.index("comment_count")
    duration_index = headers.index("duration_seconds")

    print(f"\n📊 {len(all_rows) - 1} 本の動画の詳細を取得中...\n")

    updated_count = 0
    updates = []

    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) <= video_id_index or not row[video_id_index]:
            continue

        video_id = row[video_id_index]

        print(f"[{i-1:3d}] 📹 {video_id}...", end="", flush=True)

        details = get_video_details(video_id)

        if details:
            # 詳細データをセルに追加
            col_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            view_cell = f"{col_letters[view_count_index]}{i}"
            like_cell = f"{col_letters[like_count_index]}{i}"
            comment_cell = f"{col_letters[comment_count_index]}{i}"
            duration_cell = f"{col_letters[duration_index]}{i}"

            updates.append({"range": view_cell, "values": [[details["view_count"]]]})
            updates.append({"range": like_cell, "values": [[details["like_count"]]]})
            updates.append({"range": comment_cell, "values": [[details["comment_count"]]]})
            updates.append({"range": duration_cell, "values": [[details["duration_seconds"]]]})

            duration_sec = int(details["duration_seconds"])
            video_type = "🎬 Shorts" if duration_sec <= 60 else "📹 通常"
            print(f" ✅ (再生数: {details['view_count']}, 時間: {duration_sec}秒, {video_type})")
            updated_count += 1
        else:
            print(" ❌")

    # バッチ更新（Google Sheets API の書き込み制限を回避）
    if updates:
        print(f"\n📤 {updated_count} 本のデータを Sheets に書き込み中...")
        worksheet.batch_update(updates)

    print("\n" + "=" * 70)
    print(f"✅ 更新完了: {updated_count} 本の動画を更新")
    print("=" * 70)
    print(f"\n💰 API quota 使用量: 約 {updated_count} ユニット")

if __name__ == "__main__":
    fetch_and_update_details()
    print("\n✅ 動画詳細取得完了！")
