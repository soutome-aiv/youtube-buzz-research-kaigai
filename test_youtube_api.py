#!/usr/bin/env python3
"""YouTube Data API テストスクリプト"""

import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# .env ファイルから API キーをロード
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    print("❌ エラー: YOUTUBE_API_KEY が設定されていません")
    exit(1)

# YouTube API クライアント初期化
youtube = build("youtube", "v3", developerKey=API_KEY)

def test_search_channels():
    """Claude Code 関連チャンネルを検索"""
    try:
        print("\n🔍 テスト 1: チャンネル検索")
        print("=" * 50)

        request = youtube.search().list(
            q="Claude Code",
            part="snippet",
            type="channel",
            maxResults=5,
            order="relevance"
        )
        response = request.execute()

        if not response.get("items"):
            print("⚠️  チャンネルが見つかりませんでした")
            return

        print(f"✅ 見つかった チャンネル数: {len(response['items'])}\n")

        for i, item in enumerate(response["items"], 1):
            channel_title = item["snippet"]["title"]
            channel_id = item["snippet"]["channelId"]
            print(f"{i}. {channel_title}")
            print(f"   Channel ID: {channel_id}\n")

    except HttpError as e:
        print(f"❌ API エラー: {e}")

def test_get_channel_details():
    """チャンネル詳細情報を取得"""
    try:
        print("\n📊 テスト 2: チャンネル詳細情報取得")
        print("=" * 50)

        # Anthropic の公式チャンネル ID
        channel_id = "UCV03SRZXJEz-hchIAogeJOg"

        request = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            print("❌ チャンネル情報が見つかりません")
            return

        channel = response["items"][0]
        snippet = channel["snippet"]
        stats = channel["statistics"]

        print(f"チャンネル名: {snippet['title']}")
        print(f"説明: {snippet['description'][:100]}...")
        print(f"登録者数: {stats['subscriberCount']}")
        print(f"動画数: {stats['videoCount']}")
        print(f"総再生数: {stats['viewCount']}")
        print(f"✅ チャンネル詳細取得成功！\n")

    except HttpError as e:
        print(f"❌ API エラー: {e}")

def test_search_videos():
    """Claude Code 関連の動画を検索"""
    try:
        print("\n🎬 テスト 3: 動画検索")
        print("=" * 50)

        request = youtube.search().list(
            q="Claude Code",
            part="snippet",
            type="video",
            maxResults=5,
            order="relevance",
            regionCode="US"
        )
        response = request.execute()

        if not response.get("items"):
            print("⚠️  動画が見つかりませんでした")
            return

        print(f"✅ 見つかった動画数: {len(response['items'])}\n")

        for i, item in enumerate(response["items"], 1):
            video_title = item["snippet"]["title"]
            video_id = item["snippet"]["videoId"]
            print(f"{i}. {video_title}")
            print(f"   Video ID: {video_id}\n")

    except HttpError as e:
        print(f"❌ API エラー: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("YouTube Data API テスト開始")
    print("=" * 50)

    test_search_channels()
    test_get_channel_details()
    test_search_videos()

    print("\n" + "=" * 50)
    print("✅ すべてのテスト完了！")
    print("=" * 50)
