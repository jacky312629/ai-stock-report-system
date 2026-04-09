import json
import logging

import requests
import yfinance as yf
from bs4 import BeautifulSoup

from config import client, STOCK_CANDIDATES_PATH


def fetch_market_data(symbol_list):
    for symbol in symbol_list:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")

            if len(hist) < 2:
                continue

            latest = hist.iloc[-1]
            prev = hist.iloc[-2]

            price = latest["Close"]
            change = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100

            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2)
            }

        except Exception:
            continue

    return {
        "symbol": None,
        "price": None,
        "change": None,
        "error": "無法取得資料"
    }


def translate_to_traditional_chinese(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"請把這句話翻譯成自然的繁體中文，只輸出翻譯結果：{text}"
                }
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.warning(f"翻譯失敗: {e}")
        return text


def fetch_cnbc_news():
    url = "https://www.cnbc.com/world/?region=world"
    headers = {"User-Agent": "Mozilla/5.0"}

    news_titles = []

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        news = soup.select("a.Card-title")

        count = 0
        for item in news:
            title = item.text.strip()
            if len(title) > 20:
                translated_title = translate_to_traditional_chinese(title)
                news_titles.append(translated_title)
                count += 1

            if count >= 5:
                break

    except Exception as e:
        logging.warning(f"新聞抓取失敗: {e}")

    if not news_titles:
        logging.warning("抓不到新聞")
        return [], "無新聞資料"

    return news_titles, "\n".join(news_titles)


def load_stock_candidates():
    try:
        with open(STOCK_CANDIDATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"找不到 {STOCK_CANDIDATES_PATH}，改用空推薦池")
        return {"categories": {}}
    except json.JSONDecodeError as e:
        logging.error(f"stock_candidates.json JSON 格式錯誤: {e}")
        return {"categories": {}}