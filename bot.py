def get_ai_analysis(symbol, name, price, pct_24h, market_cap, volume):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Анализ недоступен: нет API ключа"
    
    prompt = (
        f"Ты криптовалютный аналитик. Монета {symbol} ({name}):\n"
        f"- Цена: ${price:,.4f} USD\n"
        f"- Изменение за 24ч: {pct_24h:.2f}%\n"
        f"- Рыночная капитализация: ${market_cap/1e9:.1f}B\n"
        f"- Объём за 24ч: ${volume/1e6:.0f}M\n\n"
        f"Дай анализ в 3 предложениях: почему упала, это возможность для покупки или ловушка, какой риск.\n"
        f"В конце на новой строке напиши одно слово: ПОКУПАТЬ или ОСТОРОЖНО или ИЗБЕГАТЬ"
    )
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        data = res.json()
        if "content" in data and len(data["content"]) > 0:
            return data["content"][0].get("text", "Анализ недоступен")
        else:
            print(f"API ответ: {data}")
            return "Анализ временно недоступен"
    except Exception as e:
        print(f"AI error: {e}")
        return "Анализ временно недоступен"
