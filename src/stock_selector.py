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

    featured_stocks = sorted_stocks[:3]
    featured_labels = ["主攻股", "次主軸", "觀察補位"]

    featured_text = "\n".join([
        f"{featured_labels[i]}：{s['name']}｜{s['reason']}"
        for i, s in enumerate(featured_stocks[:3])
    ]) if featured_stocks else ""

    watch_stocks = sorted_stocks[3:]
    if len(watch_stocks) > 5:
        watch_stocks = watch_stocks[:5]

    recommended_text = "\n".join([
        f"- {s['name']}｜{s['reason']}"
        for s in watch_stocks
    ]) if watch_stocks else ""

    return sorted_stocks, featured_text, recommended_text