import logging

from config import REPORT_TXT_PATH, REPORT_HTML_PATH
from market_data import (
    fetch_market_data,
    fetch_cnbc_news,
    load_stock_candidates,
)
from strategy import (
    generate_risk_text,
    evaluate_market,
    calculate_strategy,
)
from stock_selector import (
    pick_recommendation_categories,
    pick_top_stocks,
)
from report_builder import (
    build_summary_line,
    build_report_console,
    build_report_file,
    build_report_html,
)
from email_sender import send_email_gmail_api


logging.basicConfig(level=logging.INFO)


def main():
    print("========== 任務開始 ==========")

    # ===== 1. 抓市場資料 =====
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
        "CRB指數": ["^CRB", "DBC"],
    }

    results = {}
    for name, symbols in symbols_map.items():
        results[name] = fetch_market_data(symbols)

    # ===== 2. 市場判斷 =====
    market_status = evaluate_market(results)

    vix = results.get("VIX", {}).get("price", 0)
    vix_change = results.get("VIX", {}).get("change", 0)
    us10y = results.get("美國10年期公債殖利率", {}).get("price", 0)
    dxy = results.get("美元指數", {}).get("price", 0)

    risk_text = generate_risk_text(vix, vix_change, us10y, dxy)
    alerts = [f"⚠️ {risk_text}"]

    strategy, confidence = calculate_strategy(results, alerts)

    # ===== 3. 新聞 =====
    news_titles, news_text = fetch_cnbc_news()

    # ===== 4. 選股 =====
    selected_categories = pick_recommendation_categories(results, news_text)

    sorted_stocks, featured_text, recommended_text = pick_top_stocks(
        results,
        stock_candidates,
        selected_categories
    )

    # ===== 5. AI（先用簡化版）=====
    ai_result = "偏多布局，聚焦AI與半導體族群"

    # ===== 6. 報告 =====
    summary_line = build_summary_line(market_status)

    report_console = build_report_console(
        results, summary_line, strategy, confidence,
        alerts, news_titles, featured_text, recommended_text, ai_result
    )

    report_file = build_report_file(
        results, summary_line, strategy, confidence,
        alerts, news_titles, featured_text, recommended_text, ai_result
    )

    report_html = build_report_html(
        results, summary_line, strategy, confidence,
        alerts, news_titles, featured_text, recommended_text, ai_result
    )

    print(report_console)

    # ===== 7. 存檔 =====
    with open(REPORT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(report_file)

    with open(REPORT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(report_html)

    print("✅ report.txt 已產生")
    print("✅ report.html 已產生")

    # ===== 8. 寄信 =====
    send_email_gmail_api(
        to_email="jacky312619@gmail.com",
        subject="📊 每日美股盤前策略報告",
        html_body=report_html,
        plain_body=report_file
    )

    print("========== 任務結束 ==========")


if __name__ == "__main__":
    main()