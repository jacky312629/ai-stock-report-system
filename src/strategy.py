def generate_risk_text(vix, vix_change, us10y, dxy):
    risk_score = 0

    vix = vix or 0
    vix_change = vix_change or 0
    us10y = us10y or 0
    dxy = dxy or 0

    # VIX 絕對值
    if vix > 25:
        risk_score += 2
    elif vix > 20:
        risk_score += 1

    # VIX 趨勢
    if vix_change > 5:
        risk_score += 1
    elif vix_change < -5:
        risk_score -= 1

    # 利率
    if us10y > 4.3:
        risk_score += 1

    # 美元
    if dxy > 105:
        risk_score += 1

    if risk_score >= 3:
        return "🔴 市場風險偏高，建議降低持股"
    elif risk_score == 2:
        return "🟡 市場仍有波動，建議謹慎操作"
    else:
        return "🟢 市場情緒穩定，風險可控"


def evaluate_market(results):
    nasdaq_change = results.get("NASDAQ", {}).get("change", 0) or 0
    sox_change = results.get("費城半導體", {}).get("change", 0) or 0
    vix_change = results.get("VIX", {}).get("change", 0) or 0
    us10y_price = results.get("美國10年期公債殖利率", {}).get("price", 0) or 0

    # 利率優先
    if us10y_price > 4.3:
        return "💣 利率壓力偏高"

    # 恐慌上升
    if vix_change > 5:
        return "⚠️ 市場恐慌升溫"

    # 科技主導
    if nasdaq_change > 0 and sox_change > 0:
        return "🔥 科技股偏多"

    return "🤔 市場震盪整理"


def calculate_strategy(results, alerts):
    score = 0

    sox = results.get("費城半導體", {}).get("change", 0) or 0
    nasdaq = results.get("NASDAQ", {}).get("change", 0) or 0
    vix = results.get("VIX", {}).get("change", 0) or 0
    yield10 = results.get("美國10年期公債殖利率", {}).get("change", 0) or 0

    if sox > 1:
        score += 2
    elif sox > 0:
        score += 1
    else:
        score -= 2

    if nasdaq > 0:
        score += 1
    else:
        score -= 1

    if vix > 2:
        score -= 2
    elif vix > 0:
        score -= 1

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