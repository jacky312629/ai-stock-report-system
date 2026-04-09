def build_summary_line(market_status):
    if "偏多" in market_status:
        return "偏多操作，聚焦AI與半導體族群"
    elif "偏空" in market_status:
        return "偏空應對，減碼高估值族群"
    else:
        return "保守觀望，等待趨勢明確"


def build_report_console(results, summary_line, strategy, confidence, alerts, news_titles, top_stock_text, recommended_stock_text, ai_result):
    line_main = "═" * 58
    line_sub = "─" * 58

    report_console = ""
    report_console += f"\n{line_main}\n"
    report_console += "📊  美股盤前策略報告\n"
    report_console += f"{line_main}\n\n"

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
    report_console += f"策略分數：{confidence}\n\n"

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

    report_console += f"\n【精選 3 檔】\n{line_sub}\n"
    report_console += f"{top_stock_text}\n"

    report_console += f"\n【推薦觀察個股】\n{line_sub}\n"
    report_console += f"{recommended_stock_text}\n"

    report_console += f"\n【AI 分析】\n{line_sub}\n"
    report_console += f"{ai_result}\n"

    report_console += f"\n{line_main}\n"

    return report_console


def build_report_file(results, summary_line, strategy, confidence, alerts, news_titles, top_stock_text, recommended_stock_text, ai_result):
    line_main = "═" * 58
    line_sub = "─" * 58

    valid_changes = [
        abs(d["change"]) for d in results.values()
        if d.get("change") is not None
    ]
    max_change = max(valid_changes) if valid_changes else 1

    report_file = ""
    report_file += f"{line_main}\n"
    report_file += "📊 美股盤前策略報告\n"
    report_file += f"{line_main}\n\n"

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
    report_file += f"【今日策略】\n{line_sub}\n{strategy}\n策略分數：{confidence}\n\n"

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

    report_file += f"\n【精選 3 檔】\n{line_sub}\n{top_stock_text}\n"
    report_file += f"\n【推薦觀察個股】\n{line_sub}\n{recommended_stock_text}\n"
    report_file += f"\n【AI 分析】\n{line_sub}\n{ai_result}\n"

    return report_file


def build_report_html(results, summary_line, strategy, confidence, alerts, news_titles, featured_text, recommended_text, ai_result):
    if "偏多" in strategy:
        strategy_color = "#d93025"
    elif "偏空" in strategy or "保守" in strategy:
        strategy_color = "#188038"
    else:
        strategy_color = "#5f6368"

    top_html = featured_text.replace("\n", "<br>") if featured_text else "目前無精選個股"
    recommended_html = recommended_text.replace("\n", "<br>") if recommended_text else "目前無推薦觀察股"
    alerts_html = "<br>".join([f"• {a}" for a in alerts]) if alerts else "無特別風險提示"
    news_html = "<br>".join(
        [f"{i}. {title}" for i, title in enumerate(news_titles[:3], start=1)]
    ) if news_titles else "無新聞資料"

    market_rows = ""
    for name, data in results.items():
        change = data.get("change")
        price = data.get("price")

        if change is None or price is None:
            market_rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{name}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">資料不足</td>
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
                <div style="font-size:20px;font-weight:700;margin-bottom:12px;">今日操作建議</div>
                <div style="font-size:18px;line-height:1.7;padding:16px;background:#f9fafb;border-left:5px solid {strategy_color};border-radius:10px;">
                    <b>{summary_line}</b>
                </div>

                <div style="height:24px;"></div>

                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    <div style="flex:1;min-width:220px;background:#f9fafb;border-radius:12px;padding:16px;">
                        <div style="font-size:14px;color:#6b7280;">今日策略</div>
                        <div style="font-size:22px;font-weight:700;margin-top:8px;color:{strategy_color};">{strategy}</div>
                        <div style="font-size:14px;color:#6b7280;margin-top:8px;">策略分數：{confidence}</div>
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

                <div style="font-size:20px;font-weight:700;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">精選 3 檔</div>
                <div style="font-size:15px;line-height:1.9;background:#f9fafb;padding:16px;border-radius:12px;">
                    {top_html}
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

    return report_html