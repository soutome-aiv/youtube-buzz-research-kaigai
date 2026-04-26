#!/usr/bin/env python3
"""Claude Code チャンネルデータを Google Sheets に自動アップロード（バッチ処理版）"""

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets ID
SPREADSHEET_ID = "1ZXJOXm_TalrNq83BXaR0W2ilXH5JOjkLNnBgc03Qv1U"

# Google Sheets API スコープ
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def authenticate():
    """Google Sheets API に認証"""
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", SCOPES
    )
    return gspread.authorize(creds)

def clear_sheet(worksheet):
    """シートの内容をクリア"""
    worksheet.clear()

def upload_channel_list(gc, channels_data):
    """チャンネル一覧シートにアップロード（バッチ処理）"""
    print("\n📤 チャンネル一覧シートにアップロード中...")

    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    # シート取得（存在しなければ作成）
    try:
        worksheet = spreadsheet.worksheet("チャンネル一覧")
        clear_sheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="チャンネル一覧", rows=500, cols=7)

    # データ準備（ヘッダー + 全データを一度に）
    rows = [["チャンネルID", "チャンネル名", "規模分類", "登録者数", "動画数", "総再生数", "説明"]]

    for size, channels in channels_data["classified"].items():
        for channel in channels:
            row = [
                channel["channel_id"],
                channel["title"],
                size,
                channel["subscriber_count"],
                channel["video_count"],
                channel["view_count"],
                ""
            ]
            rows.append(row)

    # バッチアップロード
    worksheet.append_rows(rows)
    print(f"✅ チャンネル一覧アップロード完了（{channels_data['total_channels']} チャンネル）")

def upload_by_size(gc, channels_data):
    """規模別シートにアップロード（バッチ処理）"""
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    size_labels = ["大型チャンネル（>100万）", "中型チャンネル（10万～100万）", "小型チャンネル（<10万）"]
    size_keys = ["大型 (>100万)", "中型 (10万～100万)", "小型 (<10万)"]

    for label, key in zip(size_labels, size_keys):
        print(f"📤 {label} シートにアップロード中...")

        # シート取得（存在しなければ作成）
        try:
            worksheet = spreadsheet.worksheet(label)
            clear_sheet(worksheet)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=label, rows=500, cols=7)

        # データ準備
        rows = [["チャンネルID", "チャンネル名", "登録者数", "動画数", "総再生数", "チャンネルURL", "最新更新日"]]

        channels = channels_data["classified"].get(key, [])
        for channel in sorted(channels, key=lambda x: int(x["subscriber_count"]) if x["subscriber_count"].isdigit() else 0, reverse=True):
            row = [
                channel["channel_id"],
                channel["title"],
                channel["subscriber_count"],
                channel["video_count"],
                channel["view_count"],
                f"https://www.youtube.com/channel/{channel['channel_id']}",
                ""
            ]
            rows.append(row)

        # バッチアップロード
        if len(rows) > 1:
            worksheet.append_rows(rows)
            print(f"✅ {label} アップロード完了（{len(channels)} チャンネル）")
        else:
            print(f"⚠️ {label} にはチャンネルがありません")

def main():
    print("\n" + "=" * 60)
    print("Google Sheets 自動アップロード開始")
    print("=" * 60)

    # JSON データをロード
    with open("claude_code_channels.json", "r", encoding="utf-8") as f:
        channels_data = json.load(f)

    # Google Sheets API に認証
    print("\n🔐 Google Sheets API に認証中...")
    gc = authenticate()
    print("✅ 認証成功")

    # アップロード実行
    upload_channel_list(gc, channels_data)
    upload_by_size(gc, channels_data)

    print("\n" + "=" * 60)
    print("✅ すべてのアップロード完了！")
    print("=" * 60)
    print(f"\n🔗 Google Sheets: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

if __name__ == "__main__":
    main()
