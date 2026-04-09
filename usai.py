# ＝＝＝＝＝＝1.import區＝＝＝＝＝＝

# ===== 標準庫 =====
import os
import json
import logging
import base64

from pathlib import Path

from dotenv import load_dotenv

# ===== 第三方套件 =====
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from openai import OpenAI

# ===== Email / Gmail API =====
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()  # 👈 同時印到終端機
    ]
)
# ===== 基本設定 =====

BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"
TOKEN_PATH = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ===== Gmail Service =====

def get_gmail_service():
    creds = None

    # 先讀 token.json（如果存在）
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # 如果 token 過期但可刷新，就嘗試刷新
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            logging.warning("token refresh 失敗，刪除舊 token.json，重新授權")
            if TOKEN_PATH.exists():
                TOKEN_PATH.unlink()
            creds = None

    # 如果沒有有效憑證，就重新走 OAuth 登入
    if not creds or not creds.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(f"找不到 credentials.json：{CREDENTIALS_PATH}")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

# ===== 寄信函式 =====



# ＝＝＝＝＝＝2.工具函式區＝＝＝＝＝＝

# ===============================
# 🔴 市場判斷（最優先）
# ===============================

import math

def is_missing(value):
    if value is None:
        return True
    if value == "":
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def get_safe_value(results, key, field):
    value = results.get(key, {}).get(field, None)
    if is_missing(value):
        return None
    return value



def generate_risk_text(vix, vix_change, us10y, dxy):
    risk_score = 0
    valid_count = 0

    # VIX 絕對值
    if not is_missing(vix):
        valid_count += 1
        if vix > 25:
            risk_score += 2
        elif vix > 20:
            risk_score += 1

    # VIX 趨勢
    if not is_missing(vix_change):
        valid_count += 1
        if vix_change > 5:
            risk_score += 1
        elif vix_change < -5:
            risk_score -= 1

    # 利率
    if not is_missing(us10y):
        valid_count += 1
        if us10y > 4.3:
            risk_score += 1

    # 美元
    if not is_missing(dxy):
        valid_count += 1
        if dxy > 105:
            risk_score += 1

    if valid_count < 2:
        return "⚠️ 風險資料不足，暫以觀望看待"

    if risk_score >= 3:
        return "🔴 市場風險偏高，建議降低持股"
    elif risk_score == 2:
        return "🟡 市場仍有波動，建議謹慎操作"
    else:
        return "🟢 市場情緒穩定，風險可控"


def evaluate_market(results):
    nasdaq_change = get_safe_value(results, "NASDAQ", "change")
    sox_change = get_safe_value(results, "費城半導體", "change")
    vix_change = get_safe_value(results, "VIX", "change")
    us10y_price = get_safe_value(results, "美國10年期公債殖利率", "price")

    market_data = {
        "nasdaq_change": nasdaq_change,
        "sox_change": sox_change,
        "vix_change": vix_change,
        "us10y_price": us10y_price
    }

    valid_count = sum(1 for v in market_data.values() if not is_missing(v))
    total_count = len(market_data)
    valid_ratio = valid_count / total_count if total_count > 0 else 0

    if valid_ratio < 0.6:
        return "⚠️ 市場資料不足"

    # 利率優先
    if not is_missing(us10y_price) and us10y_price > 4.3:
        return "💣 利率壓力偏高"

    # 恐慌上升
    if not is_missing(vix_change) and vix_change > 5:
        return "⚠️ 市場恐慌升溫"

    # 科技主導
    if (
        not is_missing(nasdaq_change)
        and not is_missing(sox_change)
        and nasdaq_change > 0
        and sox_change > 0
    ):
        return "🔥 科技股偏多"

    return "🤔 市場震盪整理"


def calculate_strategy(results, alerts):
    score = 0

    sox = get_safe_value(results, "費城半導體", "change")
    nasdaq = get_safe_value(results, "NASDAQ", "change")
    vix = get_safe_value(results, "VIX", "change")
    yield10 = get_safe_value(results, "美國10年期公債殖利率", "change")

    market_data = {
        "sox": sox,
        "nasdaq": nasdaq,
        "vix": vix,
        "yield10": yield10
    }

    valid_count = sum(1 for v in market_data.values() if not is_missing(v))
    total_count = len(market_data)
    valid_ratio = valid_count / total_count if total_count > 0 else 0

    if valid_ratio < 0.6:
        return "⚠️ 資料不足（暫不提供操作建議）", None

    if not is_missing(sox):
        if sox > 1:
            score += 2
        elif sox > 0:
            score += 1
        else:
            score -= 2

    if not is_missing(nasdaq):
        if nasdaq > 0:
            score += 1
        else:
            score -= 1

    if not is_missing(vix):
        if vix > 2:
            score -= 2
        elif vix > 0:
            score -= 1

    if not is_missing(yield10):
        if yield10 > 0.3:
            score -= 2
        elif yield10 > 0:
            score -= 1

    score -= len(alerts)

    if score >= 3:
        return "🚀 偏多操作（可積極）", score
    elif score >= 0:
        return "🙂 中性偏多（謹慎做多）", score
    elif score >= -3:
        return "⚠️ 偏保守（降低持股）", score
    else:
        return "❌ 偏空（觀望為主）", score


# ===============================
# 🟡 個股邏輯
# ===============================


def get_position_suggestion(strategy):
    if strategy in ["偏多", "積極偏多", "多方"]:
        return "偏多操作（建議持股 60~70%）"
    elif strategy in ["中性偏多"]:
        return "中性偏多操作（建議持股 50~60%）"
    elif strategy in ["中性"]:
        return "中性操作（建議持股 30~50%）"
    elif strategy in ["偏空", "保守", "空方"]:
        return "偏保守操作（建議持股 20~30%）"
    else:
        return "中性操作（建議持股 30~50%）"


def get_stock_action_label(rank, score):
    """
    依照名次與分數決定：
    - 定位：主攻 / 次主軸 / 觀察
    - 動作：可分批布局 / 拉回可接 / 等轉強
    - 型態：突破型 / 趨勢型 / 觀察型
    """
    if rank == 1:
        return "主攻", "可分批布局", "突破型"
    elif rank == 2:
        return "次主軸", "拉回可接", "趨勢型"
    else:
        return "觀察", "等轉強", "觀察型"


def build_top3_strategy_block(strategy, top_stocks):
    lines = []

    position_text = get_position_suggestion(strategy)
    lines.append("【今日操作策略】")
    lines.append(f"👉 {position_text}")
    lines.append("")
    lines.append("【精選3檔（優先順序）】")

    medal_icons = ["🥇", "🥈", "🥉"]

    if not top_stocks:
        lines.append("暫無明確精選標的")
        return "\n".join(lines)

    for i, stock in enumerate(top_stocks[:3]):
        name = stock.get("name", "未命名個股")
        score = stock.get("score", 0)
        reason = stock.get("reason", "具觀察價值")

        role, action_text, stock_type = get_stock_action_label(i + 1, score)
        medal = medal_icons[i]

        lines.append(f"{medal} {role}：{name} → {action_text}（{stock_type}）")
        lines.append(f"　　理由：{reason}")
        lines.append("")  # 空行讓版面好看

    return "\n".join(lines).strip()


def calculate_stock_score(cat, stock, sox_change, nasdaq_change, tsm_change, vix_change, dbc_change, crb_change):
    score = 0
    tags = stock.get("tags", [])

    # 1. 個股基礎分：priority 越前面越高
    score += max(0, 6 - stock.get("priority", 5))

    # 2. 類股主題基礎分
    category_base_score = {
        "ai": 8,
        "ip": 8,
        "server": 7,
        "cooling": 7,
        "cpo": 7,
        "steel": 5,
        "plastic": 5,
        "defensive": 4
    }
    score += category_base_score.get(cat, 3)

    # 3. 市場條件加權
    if cat in ["ai", "ip", "server", "cooling", "cpo"]:
        if sox_change > 1.5:
            score += 5
        elif sox_change > 0.8:
            score += 4
        elif sox_change > 0:
            score += 2
        else:
            score -= 3

        if nasdaq_change > 1:
            score += 2
        elif nasdaq_change < 0:
            score -= 1

        if tsm_change > 1:
            score += 2
        elif tsm_change < 0:
            score -= 1

    elif cat == "steel":
        if dbc_change > 1 or crb_change > 1:
            score += 4
        elif dbc_change > 0 or crb_change > 0:
            score += 2
        else:
            score -= 1

    elif cat == "plastic":
        if dbc_change > 1 or crb_change > 1:
            score += 3
        elif dbc_change > 0 or crb_change > 0:
            score += 1
        else:
            score -= 1

    elif cat == "defensive":
        if vix_change > 3:
            score += 4
        elif vix_change > 0:
            score += 2
        else:
            score -= 1

    # 4. tags 補強
    if "AI" in tags and sox_change > 0:
        score += 1
    if "ASIC" in tags and sox_change > 0.8:
        score += 1
    if "高速傳輸" in tags and sox_change > 0.8:
        score += 1
    if "光通訊" in tags and sox_change > 0.8:
        score += 1
    if "液冷" in tags and cat == "cooling":
        score += 1
    if "高股息" in tags and vix_change > 0:
        score += 1
    if "原物料" in tags and (dbc_change > 0.5 or crb_change > 0.5):
        score += 1

    return score


def generate_reason(cat, stock, sox_change, dbc_change, crb_change, vix_change):
    reason_parts = []

    reason_tag = stock.get("reason_tag", "").strip()

    sox_change = sox_change or 0
    dbc_change = dbc_change or 0
    crb_change = crb_change or 0
    vix_change = vix_change or 0

    if reason_tag:
        reason_parts.append(reason_tag)

    if cat == "ip":
        reason_parts.append("矽智財族群受惠高速傳輸升級")
    elif cat == "ai":
        reason_parts.append("AI運算需求延續帶動ASIC商機")
    elif cat == "server":
        reason_parts.append("AI伺服器仍是市場主線之一")
    elif cat == "cooling":
        reason_parts.append("伺服器功耗提升推升散熱需求")
    elif cat == "cpo":
        reason_parts.append("高速傳輸升級帶動光通訊題材")

    if cat in ["ip", "ai", "server", "cooling", "cpo"]:
        if sox_change > 0.8:
            reason_parts.append("費半明顯轉強")
        elif sox_change > 0:
            reason_parts.append("費半維持偏強")
        else:
            reason_parts.append("費半偏弱宜追蹤續強度")

    final_parts = []
    for part in reason_parts:
        if part and part not in final_parts:
            final_parts.append(part)

    return "；".join(final_parts[:3])


def pick_recommendation_categories(results, news_text):
    selected = []

    sox = results.get("費城半導體", {}).get("change", 0) or 0
    nasdaq = results.get("NASDAQ", {}).get("change", 0) or 0

    # AI / 半導體主線
    if sox > 0 or nasdaq > 0:
        selected.extend(["ai", "ip", "server"])

    # 防呆（至少有東西）
    if not selected:
        selected = ["ai"]

    return selected


def pick_top_stocks(results, stock_candidates, selected_categories):
    categories = stock_candidates.get("categories", {})
    stock_result = []

    sox_change = results.get("費城半導體", {}).get("change", 0) or 0
    nasdaq_change = results.get("NASDAQ", {}).get("change", 0) or 0
    tsm_change = results.get("台積電ADR", {}).get("change", 0) or 0
    vix_change = results.get("VIX", {}).get("change", 0) or 0
    dbc_change = results.get("原物料ETF", {}).get("change", 0) or 0
    crb_change = results.get("CRB指數", {}).get("change", 0) or 0

    # 先跑主選類股
    for cat in selected_categories:
        category = categories.get(cat)
        if not category:
            continue

        stocks = category.get("stocks", [])

        for stock in stocks:
            if not stock.get("enabled", True):
                continue

            score = calculate_stock_score(
                cat,
                stock,
                sox_change,
                nasdaq_change,
                tsm_change,
                vix_change,
                dbc_change,
                crb_change
            )

            reason_text = generate_reason(
                cat,
                stock,
                sox_change,
                dbc_change,
                crb_change,
                vix_change
            )

            stock_result.append({
                "id": stock.get("id", ""),
                "name": stock["name"],
                "category": cat,
                "sector": stock.get("sector", ""),
                "score": score,
                "reason": reason_text,
                "tags": stock.get("tags", [])
            })

    # 如果股票不足，自動補其他類股
    if len(stock_result) < 8:
        existing_names = {stock["name"] for stock in stock_result}

        for cat, category in categories.items():
            if cat in selected_categories:
                continue

            stocks = category.get("stocks", [])

            for stock in stocks:
                if not stock.get("enabled", True):
                    continue
                if stock["name"] in existing_names:
                    continue

                score = calculate_stock_score(
                    cat,
                    stock,
                    sox_change,
                    nasdaq_change,
                    tsm_change,
                    vix_change,
                    dbc_change,
                    crb_change
                )

                # 非主選類股稍微降權，避免搶到主選類股前面
                score -= 2

                reason_text = generate_reason(
                    cat,
                    stock,
                    sox_change,
                    dbc_change,
                    crb_change,
                    vix_change
                )

                stock_result.append({
                    "id": stock.get("id", ""),
                    "name": stock["name"],
                    "category": cat,
                    "sector": stock.get("sector", ""),
                    "score": score,
                    "reason": reason_text,
                    "tags": stock.get("tags", [])
                })

                existing_names.add(stock["name"])

                if len(stock_result) >= 8:
                    break

            if len(stock_result) >= 8:
                break

    def get_priority(item):
        cat = item["category"]
        name = item["name"]
        category = categories.get(cat, {})
        stocks = category.get("stocks", [])
        for stock in stocks:
            if stock.get("name") == name:
                return stock.get("priority", 99)
        return 99

    sorted_stocks = sorted(
    stock_result,
    key=lambda x: (x["score"], -get_priority(x)),
    reverse=True
    )
    top_stocks = sorted_stocks[:3]

    print("總股票數:", len(sorted_stocks))

    # 精選 3 檔
    featured_stocks = sorted_stocks[:3]

    featured_roles = ["主攻", "次主軸", "觀察"]

    featured_text = "\n".join([
        f"{featured_roles[i]}：{s['name']}\n　　理由：{s['reason']}"
        for i, s in enumerate(featured_stocks)
    ]) if featured_stocks else ""

    # 推薦觀察最多 5 檔
    watch_stocks = sorted_stocks[3:]
    if len(watch_stocks) > 5:
        watch_stocks = watch_stocks[:5]

    recommended_text = "\n".join([
        f"- {s['name']}｜{s['reason']}"
        for s in watch_stocks
    ]) if watch_stocks else ""

    recommended_text = "\n".join([
        f"- {s['name']}｜{s['reason']}"
        for s in watch_stocks
    ]) if watch_stocks else ""

    print("featured_stocks:", [s["name"] for s in featured_stocks])
    print("watch_stocks:", [s["name"] for s in watch_stocks])

    return sorted_stocks, featured_text, recommended_text

# ===============================
# 🟢 其他工具
# ===============================

def fetch_market_data(symbol_list):
    import yfinance as yf

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


def send_email_gmail_api(to_email, subject, html_body, plain_body=None):
    try:
        service = get_gmail_service()

        message = MIMEMultipart("alternative")
        message["To"] = to_email
        message["Subject"] = subject

        if plain_body:
            message.attach(MIMEText(plain_body, "plain", "utf-8"))

        message.attach(MIMEText(html_body, "html", "utf-8"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        body = {"raw": raw_message}

        result = service.users().messages().send(userId="me", body=body).execute()

        logging.info("Email寄送成功（Gmail API）")
        print("📧 Email 已成功寄出（Gmail API）")
        return result

    except Exception as e:
        logging.exception(f"Email寄送失敗（Gmail API）: {e}")
        print(f"❌ Email寄送失敗: {e}")
        raise


def load_stock_candidates(filepath="stock_candidates.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"找不到 {filepath}，改用空推薦池")
        return {"categories": {}}
    except json.JSONDecodeError as e:
        logging.error(f"{filepath} JSON 格式錯誤: {e}")
        return {"categories": {}}
    

# ＝＝＝＝＝＝Main Execution Flow＝＝＝＝＝＝
# AI 自動化股票分析系統主流程
#
# 功能說明：
# - 自動抓取市場數據（美股指數、VIX、利率、原物料）
# - 建立市場風險與趨勢判斷模型
# - 根據類股邏輯與評分機制選出精選個股
# - 整合 AI 生成市場分析與操作建議
# - 輸出多格式報告（Console / TXT / HTML）
# - 透過 Gmail API 自動寄送每日報告
#
# 設計重點：
# - 模組化（市場 / 選股 / 輸出）
# - 可擴展（股票池 / 策略模型）
# - 自動化（每日定時執行）

def main():
    
    logging.info("開始抓取市場資料")

    stock_candidates = load_stock_candidates()

    symbols_map = {
        "道瓊指數": ["^DJI"],
        "NASDAQ": ["^IXIC"],
        "費城半導體": ["^SOX"],
        "台積電ADR": ["TSM"],
        "美國10年期公債殖利率": ["^TNX"],
        "美元指數": ["DX-Y.NYB"],
        "VIX": ["^VIX"],
        "原物料ETF": ["DBC"],
        "CRB指數": ["^CRB", "^TRCCRB", "^CRBQ-TC", "DBC"]
    }

    results = {}

    for name, symbol_list in symbols_map.items():
        result = fetch_market_data(symbol_list)
        results[name] = result

        if result["symbol"] is None:
            print(f"{name} 抓取失敗：{result.get('error')}")
            logging.warning(f"{name} 抓取失敗：{result.get('error')}")
        else:
            logging.info(
                f"{name} 抓取成功，使用 {result['symbol']}，"
                f"price={result['price']}，change={result['change']}%"
            )

    market_status = evaluate_market(results)

    vix = get_safe_value(results, "VIX", "price")
    vix_change = get_safe_value(results, "VIX", "change")
    us10y = get_safe_value(results, "美國10年期公債殖利率", "price")
    dxy = get_safe_value(results, "美元指數", "price")

    risk_text = generate_risk_text(vix, vix_change, us10y, dxy)

    alerts = [f"⚠️ {risk_text}"]

    if (results.get("美元指數", {}).get("change", 0) or 0) > 0.3:
        alerts.append("⚠️ 美元轉強，可能壓抑股市資金")

    if (results.get("美國10年期公債殖利率", {}).get("change", 0) or 0) > 0:
        alerts.append("⚠️ 殖利率上升，成長股壓力增加")

    if (results.get("台積電ADR", {}).get("change", 0) or 0) < -1:
        alerts.append("⚠️ 台積電ADR偏弱，留意半導體族群")

    strategy, score = calculate_strategy(results, alerts)

    data_warning = score is None

    if data_warning:
        score = 0
    
    
    logging.info("開始抓取新聞")

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
        news_text = "無新聞資料"
    else:
        news_text = "\n".join(news_titles)

    logging.info("開始選股分析")

    selected_categories = pick_recommendation_categories(results, news_text)

    if data_warning:
        sorted_stocks = []
        featured_text = "⚠️ 資料不足，今日暫不提供精選個股"
        recommended_text = "⚠️ 資料不足，今日暫不提供推薦個股"
    else:
        sorted_stocks, featured_text, recommended_text = pick_top_stocks(
            results,
            stock_candidates,
            selected_categories
        ) 


    # ＝＝＝＝＝＝3.prompt＝＝＝＝＝＝

    prompt = f"""

    你是一位「紀律嚴格的專業交易員」，請根據以下數據做出「極簡但可執行的市場判斷」。

    【重要規則（必須遵守）】
    1. 僅能使用提供的數據與新聞
    2. 每個結論必須明確，不可模糊
    3. 禁止使用「可能」「觀察」「偏向」
    4. 每點最多15字
    5. 補充說明最多30字

    句型格式：
    「策略方向＋操作建議＋標的或族群」

    ────────────────────

    【今日策略】
    {strategy}

    【市場數據】
    道瓊：{(results.get("道瓊指數", {}).get("change", 0) or 0):+.2f}%
    NASDAQ：{(results.get("NASDAQ", {}).get("change", 0) or 0):+.2f}%
    費城半導體：{(results.get("費城半導體", {}).get("change", 0) or 0):+.2f}%
    台積電ADR：{(results.get("台積電ADR", {}).get("change", 0) or 0):+.2f}%
    美債10年：{(results.get("美國10年期公債殖利率", {}).get("change", 0) or 0):+.2f}%
    美元指數：{(results.get("美元指數", {}).get("change", 0) or 0):+.2f}%
    VIX：{(results.get("VIX", {}).get("change", 0) or 0):+.2f}%
    原物料ETF：{(results.get("原物料ETF", {}).get("change", 0) or 0):+.2f}%
    CRB指數：{(results.get("CRB指數", {}).get("change", 0) or 0):+.2f}%

    【新聞摘要】
    {news_text}

    【推薦類股】
    {selected_categories}

    【推薦觀察個股】
    {recommended_text}

    - 若 VIX 上升 → 必須偏保守
    - 不可同時描述為「樂觀」

    【推薦個股使用規則】
    - 選股方向必須來自推薦清單
    - 不可選未列出的類股

    請輸出「今日操作建議」，規則如下：

    1. 不超過30字
    2. 必須包含：
    - 操作方向（偏多 / 偏空 / 保守 / 觀望）
    - 操作動作（布局 / 承接 / 減碼 / 觀望）
    - 標的或族群（如AI、半導體、伺服器等）
    3. 使用專業投資語氣
    4. 不要使用emoji
    5. 不要解釋，只輸出一句話

    ────────────────────

    【決策邏輯（必須遵守）】
    1. 先判斷市場方向
    2. 再判斷科技強弱
    3. 再判斷風險
    4. 最後選擇單一主軸

    ────────────────────

    【決策優先順序】
    1️⃣ 鋼鐵 / 塑化（原物料強）
    2️⃣ 科技（AI / 半導體）
    3️⃣ 防禦（風險升高）

    ※ 僅能選一個

    ────────────────────

    【輸出格式】
    1️⃣ 市場方向：
    （多 / 空 / 震盪）
    2️⃣ 科技股強弱：
    （一句話）
    3️⃣ 風險狀態：
    （一句話）
    4️⃣ 🎯選股方向：
    （必須與推薦股分類一致）
    5️⃣ 推薦邏輯：
    （一句話）
    6️⃣ 結論：
    （一句話）
    7️⃣ 補充說明：
    （最多30字）

    ────────────────────

    【一致性規則（必須遵守）】
    - AI結論必須與「今日策略」一致
    - 若策略為「偏空」：不得出現做多相關字詞
    - 若策略為「觀望」：不得出現任何進場或布局暗示
    - 結論中若提及個股：必須來自推薦清單
    - 推薦邏輯：必須對應市場數據或新聞
    """

    print("\n=== Market Status ===")
    print(market_status)

    print("\n=== Alerts ===")
    if alerts:
        for alert in alerts:
                print(alert)
    else:
        print("無特別風險提示")

    print("\n=== Selected Categories ===")
    print(selected_categories)

    print("\n=== Featured Stocks ===")
    for s in sorted_stocks[:3]:
        print(s)

    print("\n=== Recommended Text ===")
    print(recommended_text)

    print("\n=== Strategy ===")
    print(strategy)
    print("Score:", score)


# ＝＝＝＝＝＝4.呼叫ＡＩ＝＝＝＝＝＝

    logging.info("開始呼叫 OpenAI 分析")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位嚴格執行紀律的專業交易員，只輸出結論，不解釋過程"
                },
                {"role": "user", "content": prompt}
            ]
        )
        ai_result = response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"AI呼叫失敗: {e}")
        ai_result = "AI分析暫時無法取得，請參考下方數據判斷"


# ＝＝＝＝＝＝5.報告組裝＝＝＝＝＝＝


    if "偏多" in market_status:
        summary_line = "偏多操作，聚焦AI與半導體族群"
    elif "偏空" in market_status:
        summary_line = "偏空應對，減碼高估值族群"
    else:
        summary_line = "保守觀望，等待趨勢明確"

    top3_strategy_block = build_top3_strategy_block(strategy, sorted_stocks)   

    top_stock_text = featured_text if featured_text else "目前無精選個股"
    recommended_stock_text = recommended_text if recommended_text else "目前無推薦觀察股"

    line_main = "═" * 58
    line_sub = "─" * 58


    # =========================
    # Console 版
    # =========================

    report_console = ""
    report_console += f"\n{line_main}\n"
    report_console += "📊  美股盤前策略報告\n"
    report_console += f"{line_main}\n\n"

    report_console += f"{top3_strategy_block}\n\n"

    report_console += "【市場儀表板】\n"
    report_console += f"{line_sub}\n"

    valid_changes = [
        abs(d["change"]) for d in results.values()
        if d.get("change") is not None
    ]
    max_change = max(valid_changes) if valid_changes else 1

    for name, data in results.items():
        change = data.get("change")
        price = data.get("price")

        if change is None or price is None:
            report_console += f"• {name:<12} 資料不足\n"
            continue

        if change > 0:
            color = "\033[91m"
            arrow = "▲"
        elif change < 0:
            color = "\033[92m"
            arrow = "▼"
        else:
            color = ""
            arrow = "•"

        reset = "\033[0m"
        bar_length = int((abs(change) / max_change) * 16) if max_change > 0 else 0
        bar = "█" * bar_length

        color_line = f"{color}{arrow} {name:<12} {price:>8.2f}   ({change:+6.2f}%)  {bar}{reset}\n"
        report_console += color_line

    report_console += f"\n【今日操作建議】\n{line_sub}\n"
    report_console += f"{summary_line}\n\n"

    report_console += f"【今日策略】\n{line_sub}\n"
    report_console += f"{strategy}\n"
    report_console += f"策略分數：{score}\n\n"

    report_console += f"【風險提醒】\n{line_sub}\n"
    if alerts:
        for a in alerts:
            report_console += f"• {a}\n"
    else:
        report_console += "• 無特別風險提示\n"

    report_console += f"\n【美股新聞】\n{line_sub}\n"
    if news_titles:
        for i, title in enumerate(news_titles[:3], start=1):
            report_console += f"{i}. {title}\n"
    else:
        report_console += "無新聞資料\n"


    report_console += f"\n【推薦觀察個股】\n{line_sub}\n"
    report_console += f"{recommended_stock_text}\n"

    report_console += f"\n【AI 分析】\n{line_sub}\n"
    report_console += f"{ai_result}\n"

    report_console += f"\n{line_main}\n"

# =========================
# TXT 版
# =========================
    report_file = ""
    report_file += f"{line_main}\n"
    report_file += "📊 美股盤前策略報告\n"
    report_file += f"{line_main}\n\n"

    report_file += f"{top3_strategy_block}\n\n"

    report_file += "【市場儀表板】\n"
    report_file += f"{line_sub}\n"

    for name, data in results.items():
        change = data.get("change")
        price = data.get("price")

        if change is None or price is None:
            report_file += f"• {name:<12} 資料不足\n"
            continue

        arrow = "▲" if change > 0 else "▼" if change < 0 else "•"
        bar_length = int((abs(change) / max_change) * 16) if max_change > 0 else 0
        bar = "█" * bar_length
        report_file += f"{arrow} {name:<12} {price:>8.2f}   ({change:+6.2f}%)  {bar}\n"

    report_file += f"\n【今日操作建議】\n{line_sub}\n{summary_line}\n\n"
    report_file += f"【今日策略】\n{line_sub}\n{strategy}\n策略分數：{score}\n\n"

    report_file += f"【風險提醒】\n{line_sub}\n"
    if alerts:
        for a in alerts:
            report_file += f"• {a}\n"
    else:
        report_file += "• 無特別風險提示\n"

    report_file += f"\n【美股新聞】\n{line_sub}\n"
    if news_titles:
        for i, title in enumerate(news_titles[:3], start=1):
            report_file += f"{i}. {title}\n"
    else:
        report_file += "無新聞資料\n"

    report_file += f"\n【推薦觀察個股】\n{line_sub}\n{recommended_stock_text}\n"
    report_file += f"\n【AI 分析】\n{line_sub}\n{ai_result}\n"


    # =========================
    # HTML 版（寄 Email 用）
    # =========================

    if "偏多" in strategy:
        strategy_color = "#d93025"
    elif "偏空" in strategy or "保守" in strategy:
        strategy_color = "#188038"
    else:
        strategy_color = "#5f6368"


    # ✅ 先建立 HTML 變數
    
    recommended_html = recommended_text.replace("\n", "<br>") if recommended_text else "目前無推薦觀察股"

    alerts_html = "<br>".join([f"• {a}" for a in alerts]) if alerts else "無特別風險提示"

    news_html = "<br>".join(
        [f"{i}. {title}" for i, title in enumerate(news_titles[:3], start=1)]
    ) if news_titles else "無新聞資料"
    

    warning_html = ""
    if data_warning:
        warning_html = """
        <div style="background:#fff3cd;color:#856404;padding:12px 16px;
                    border-radius:8px;margin-bottom:16px;font-size:14px;line-height:1.7;">
            ⚠️ 今日部分市場數據尚未更新，暫不提供明確策略判斷，以下內容僅供參考。
        </div>
        """


    # ✅ 再組 HTML

    top3_strategy_html = top3_strategy_block.replace("\n", "<br>")
    recommended_html = recommended_stock_text.replace("\n", "<br>")
    news_html = "<br>".join(news_titles[:3]) if news_titles else "無新聞資料"
    alerts_html = "<br>".join(alerts) if alerts else "無特別風險提示"


    market_rows = ""
    for name, data in results.items():
        change = data.get("change")
        price = data.get("price")

        if is_missing(change) or is_missing(price):
            market_rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{name}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">資料尚未更新</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">-</td>
            </tr>
            """
            continue

        change_color = "#d93025" if change > 0 else "#188038" if change < 0 else "#5f6368"
        market_rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{name}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{price:.2f}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;color:{change_color};font-weight:600;">{change:+.2f}%</td>
        </tr>
        """


    report_html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    </head>
    <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,'Microsoft JhengHei',sans-serif;color:#1f1f1f;">
        <div style="max-width:860px;margin:24px auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">
            
            <div style="background:#111827;color:#ffffff;padding:24px 28px;">
                <div style="font-size:26px;font-weight:700;">📊 美股盤前策略報告</div>
                <div style="font-size:14px;margin-top:8px;opacity:0.85;">自動化市場數據 × AI 分析 × 精選個股</div>
            </div>

            <div style="padding:24px 28px;">
                {warning_html}
                <div style="font-size:20px;font-weight:700;margin-bottom:12px;">今日操作建議</div>
                <div style="font-size:18px;line-height:1.7;padding:16px;background:#f9fafb;border-left:5px solid {strategy_color};border-radius:10px;">
                    <b>{summary_line}</b>
                </div>

                <div style="height:24px;"></div>

                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    <div style="flex:1;min-width:220px;background:#f9fafb;border-radius:12px;padding:16px;">
                        <div style="font-size:14px;color:#6b7280;">今日策略</div>
                        <div style="font-size:22px;font-weight:700;margin-top:8px;color:{strategy_color};">{strategy}</div>
                        <div style="font-size:14px;color:#6b7280;margin-top:8px;">策略分數：{score}</div>
                    </div>
                    <div style="flex:1;min-width:220px;background:#f9fafb;border-radius:12px;padding:16px;">
                        <div style="font-size:14px;color:#6b7280;">風險提醒</div>
                        <div style="font-size:15px;line-height:1.8;margin-top:8px;">{alerts_html}</div>
                    </div>
                </div>

                <div style="height:28px;"></div>

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">市場儀表板</div>
                <table style="width:100%;border-collapse:collapse;font-size:15px;">
                    <thead>
                        <tr style="background:#f3f4f6;">
                            <th style="text-align:left;padding:10px 12px;">項目</th>
                            <th style="text-align:left;padding:10px 12px;">價格</th>
                            <th style="text-align:left;padding:10px 12px;">漲跌幅</th>
                        </tr>
                    </thead>
                    <tbody>
                        {market_rows}
                    </tbody>
                </table>

                <div style="height:28px;"></div>

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">今日操作策略</div>
                <div style="font-size:15px;line-height:1.9;background:#fff8e1;padding:16px;border-radius:12px;">
                    {top3_strategy_html}
                </div>

                <div style="height:28px;"></div>

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">推薦觀察個股</div>
                <div style="font-size:15px;line-height:1.9;background:#f9fafb;padding:16px;border-radius:12px;">
                    {recommended_html}
                </div>

                <div style="height:28px;"></div>

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">美股新聞</div>
                <div style="font-size:15px;line-height:1.9;background:#f9fafb;padding:16px;border-radius:12px;">
                    {news_html}
                </div>

                <div style="height:28px;"></div>

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">AI 分析</div>
                <div style="font-size:15px;line-height:1.9;background:#f9fafb;padding:16px;border-radius:12px;white-space:pre-line;">
                    {ai_result}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    print(report_console)

    REPORT_TXT_PATH = BASE_DIR / "report.txt"
    REPORT_HTML_PATH = BASE_DIR / "report.html"

    with open(REPORT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(report_file)

    with open(REPORT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(report_html)

    print("\n✅ report.txt 已產生")
    print("✅ report.html 已產生")
    logging.info("程式成功完成")


    # ＝＝＝＝＝＝6.寄送 Email（Gmail API）＝＝＝＝＝＝

    logging.info("開始寄送 Email（Gmail API）")

    try:
        to_email = "jacky312619@gmail.com"
        subject = "📊 每日美股盤前策略報告"

        send_email_gmail_api(
            to_email=to_email,
            subject=subject,
            html_body=report_html
        )

        logging.info("Email寄送成功（Gmail API）")

    except Exception as e:
        print("❌ Email寄送失敗:", e)
        logging.error(f"Email寄送失敗（Gmail API）: {e}")

if __name__ == "__main__":
    try:
        print("========== 任務開始 ==========")
        main()
        print("========== 任務結束 ==========")
    except Exception as e:
        logging.exception(f"主程式執行失敗: {e}")
        print(f"❌ 主程式執行失敗: {e}")