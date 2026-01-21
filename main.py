import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time

# =====================
# 環境変数
# =====================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
    raise RuntimeError("LINEのトークンまたはUser IDが設定されていません")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PRICE_FILE = "prices.json"

# =====================
# 共通処理
# =====================
def extract_price(text: str) -> int:
    return int(re.sub(r"[^\d]", "", text))

def send_line_message(message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()

def load_previous_prices():
    if not os.path.exists(PRICE_FILE):
        return {}
    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_prices(prices):
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

# =====================
# 各サイト価格取得
# =====================
def get_yodobashi(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    name = soup.select_one("#products_maintitle").text.strip()
    price = extract_price(soup.select_one("#js_mtn_purchase_price").text)
    return name, price

def get_biccamera(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    name = soup.select_one("h1").text.strip()
    price = extract_price(soup.select_one(".bcs_price").text)
    return name, price

def get_amazon(url):
    r = requests.get(url, headers=HEADERS, timeout=15)

    # Botブロック検知
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")

    # 商品名
    title = soup.select_one("#productTitle")
    if not title:
        raise RuntimeError("商品タイトル取得失敗")
    name = title.text.strip()

    # 在庫切れ判定
    availability = soup.select_one("#availability")
    if availability and "在庫切れ" in availability.text:
        raise RuntimeError("在庫切れ")

    # 価格セレクタ（優先順）
    price_selectors = [
        ".a-price .a-offscreen",     # 通常・セール
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".a-price-whole"
    ]

    price = None
    for selector in price_selectors:
        tag = soup.select_one(selector)
        if tag and tag.text.strip():
            price = extract_price(tag.text)
            break

    if price is None:
        raise RuntimeError("価格取得失敗")

    return name, price


# =====================
# 監視商品
# =====================
PRODUCTS = [
    {
        "site": "yodobashi",
        "url": "https://www.yodobashi.com/product/100000001009241489/",
        "target": 120000
    },
    {
        "site": "yodobashi",
        "url": "https://www.yodobashi.com/product/100000001008502373/",
        "target": 40000
    },
       {
        "site": "yodobashi",
        "url": "https://www.yodobashi.com/product/100000001009158696/",
        "target": 120000
    },

        {
        "site": "bic",
        "url": "https://www.biccamera.com/bc/item/14294487/",
        "target": 120000
    },
    {
        "site": "bic",
        "url": "https://www.biccamera.com/bc/item/12987157/",
        "target": 40000
    },
       {
        "site": "bic",
        "url": "https://www.biccamera.com/bc/item/14152913/",
        "target": 120000
    },

    {
        "site": "amazon",
        "url": "https://www.amazon.co.jp/Eufy-%E3%83%A6%E3%83%BC%E3%83%95%E3%82%A3-%E3%80%90%E3%83%AD%E3%83%BC%E3%83%A9%E3%83%BC%E3%83%A2%E3%83%83%E3%83%97-%E5%85%A8%E8%87%AA%E5%8B%95%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%8B%E3%83%B3%E3%82%B0%E3%82%B9%E3%83%86%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3-%E3%83%A2%E3%83%83%E3%83%97%E6%B4%97%E6%B5%84%E3%83%BB%E4%B9%BE%E7%87%A5/dp/B0F9JGVSDX/",
        "target": 120000
    },
    {
        "site": "amazon",
        "url": "https://www.amazon.co.jp/%E3%83%86%E3%82%A3%E3%83%95%E3%82%A1%E3%83%BC%E3%83%AB-%E9%AB%98%E7%81%AB%E5%8A%9B%EF%BC%93%E6%AC%A1%E5%85%83IH-%E3%81%8A%E7%B1%B3%E3%81%AE%E8%8A%AF%E3%81%BE%E3%81%A7%E4%B8%80%E6%B0%97%E3%81%AB%E7%9B%B4%E7%81%AB%E7%82%8A%E3%81%8D-%E9%81%A0%E8%B5%A4%E5%A4%96%E7%B7%9A3DIH%E7%82%8A%E9%A3%AF%E5%99%A8%E3%80%8D%E3%82%B7%E3%83%AB%E3%83%90%E3%83%BC-RK890EJP/dp/B0D62J5BBL/",
        "target": 40000
    },
       {
        "site": "amazon",
        "url": "https://www.amazon.co.jp/gp/product/B0F4K1BSFC/",
        "target": 120000
    },
]

# =====================
# メイン処理
# =====================
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    previous_prices = load_previous_prices()
    new_prices = {}
    alerts = []

    for p in PRODUCTS:
        url = p["url"]
        site = p["site"]

        try:
            if site == "yodobashi":
                name, price = get_yodobashi(url)
            elif site == "bic":
                name, price = get_biccamera(url)
            elif site == "amazon":
                name, price = get_amazon(url)
            else:
                continue

            key = f"{site}:{url}"
            prev_price = previous_prices.get(key)

            if prev_price is not None and price != prev_price:
                if price < prev_price:
                    status = "📉 値下がり"
                else:
                    status = "📈 値上がり"

                alerts.append(
                    f"{status} 検知\n"
                    f"{name}\n"
                    f"{prev_price:,}円 → {price:,}円\n"
                    f"{url}"
                )

            new_prices[key] = price
            time.sleep(2)

        except Exception as e:
            alerts.append(f"⚠️ 取得失敗\n{url}\n{str(e)}")

    save_prices(new_prices)

    if alerts:
        send_line_message("\n\n".join(alerts))
    else:
        send_line_message(f"🟢 価格チェック完了\n⏰ {now}")

if __name__ == "__main__":
    main()