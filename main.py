import os
import requests
from datetime import datetime

# ===== 環境変数 =====
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
    raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN または LINE_USER_ID が設定されていません")

# ===== LINE送信 =====
def send_line_message(message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        raise RuntimeError(f"LINE送信失敗: {res.status_code} {res.text}")

# ===== 監視商品（複数対応）=====
PRODUCTS = [
    {
        "name": "テスト商品A",
        "target_price": 10000
    },
    {
        "name": "テスト商品B",
        "target_price": 20000
    }
]

# ===== メイン処理 =====
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "🟢 Price Alert 動作確認",
        f"⏰ 実行時刻: {now}",
        "",
        "監視商品一覧:"
    ]

    for p in PRODUCTS:
        lines.append(f"- {p['name']}（目標価格 ¥{p['target_price']:,}）")

    send_line_message("\n".join(lines))

    print("LINE通知を送信しました")

# ===== 実行 =====
if __name__ == "__main__":
    main()
