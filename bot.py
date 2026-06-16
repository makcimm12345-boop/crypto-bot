import os, time, requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8931407638:AAGuyw7brHwUvR5Vz__9Q-fjaK-qoeqDaqw")
CHAT_ID        = os.environ.get("CHAT_ID", "353874888")
THRESHOLD      = float(os.environ.get("THRESHOLD", "-5.0"))
INTERVAL_MIN   = int(os.environ.get("INTERVAL_MIN", "30"))

COINS = [
    {"id": "bitcoin",       "symbol": "BTC",  "name": "Bitcoin"},
    {"id": "ethereum",      "symbol": "ETH",  "name": "Ethereum"},
    {"id": "solana",        "symbol": "SOL",  "name": "Solana"},
    {"id": "ripple",        "symbol": "XRP",  "name": "XRP"},
    {"id": "cardano",       "symbol": "ADA",  "name": "Cardano"},
    {"id": "avalanche-2",   "symbol": "AVAX", "name": "Avalanche"},
    {"id": "chainlink",     "symbol": "LINK", "name": "Chainlink"},
    {"id": "polkadot",      "symbol": "DOT",  "name": "Polkadot"},
]

alerted = {}
ALERT_COOLDOWN = 4 * 3600

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def fetch_prices():
    ids = ",".join(c["id"] for c in COINS)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids}&vs_currencies=usd"
        f"&include_24hr_change=true"
        f"&include_24hr_vol=true"
        f"&include_market_cap=true"
    )
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        print(f"CoinGecko error: {e}")
        return None

def get_ai_analysis(symbol, name, price, pct_24h, market_cap, volume):
api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_KEY", "")    if not api_key:
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

def format_price(price):
    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"

def scan():
    now = datetime.now()
    print(f"[{now.strftime('%H:%M')}] Сканирование {len(COINS)} монет...")
    data = fetch_prices()
    if not data:
        print("Нет данных от CoinGecko")
        return
    for coin in COINS:
        cid     = coin["id"]
        symbol  = coin["symbol"]
        name    = coin["name"]
        info    = data.get(cid, {})
        price      = info.get("usd", 0)
        pct_24h    = info.get("usd_24h_change", 0)
        market_cap = info.get("usd_market_cap", 0)
        volume     = info.get("usd_24h_vol", 0)
        print(f"  {symbol}: {pct_24h:.2f}%")
        if pct_24h <= THRESHOLD:
            last_alert = alerted.get(cid, 0)
            if time.time() - last_alert < ALERT_COOLDOWN:
                print(f"  → уже уведомлён недавно, пропуск")
                continue
            print(f"  → СИГНАЛ! Получаю ИИ анализ...")
            analysis = get_ai_analysis(symbol, name, price, pct_24h, market_cap, volume)
            text_upper = analysis.upper()
            if "ПОКУПАТЬ" in text_upper:
                emoji = "🟢"
            elif "ИЗБЕГАТЬ" in text_upper:
                emoji = "🔴"
            else:
                emoji = "🟡"
            msg = (
                f"{emoji} *КРИПТО СИГНАЛ: {symbol}*\n"
                f"📉 Падение за 24ч: *{pct_24h:.2f}%*\n"
                f"💰 Цена: *{format_price(price)}*\n"
                f"📊 Капитализация: ${market_cap/1e9:.1f}B\n"
                f"📦 Объём 24ч: ${volume/1e6:.0f}M\n\n"
                f"🤖 *ИИ Анализ:*\n{analysis}\n\n"
                f"⏰ {now.strftime('%d.%m.%Y %H:%M')} UTC"
            )
            if send_telegram(msg):
                alerted[cid] = time.time()
                print(f"  → Уведомление отправлено!")
    print("Сканирование завершено.\n")

def main():
    print("=== Crypto Scanner Bot запущен ===")
    sent = send_telegram(
        "✅ *Crypto Scanner Bot запущен!*\n\n"
        f"🔍 Слежу за {len(COINS)} монетами: "
        + ", ".join(c["symbol"] for c in COINS) + "\n"
        f"📉 Порог падения: {abs(THRESHOLD):.0f}%\n"
        f"⏰ Сканирование каждые {INTERVAL_MIN} минут\n\n"
        "Жди уведомлений!"
    )
    print(f"Стартовое сообщение: {'OK' if sent else 'ОШИБКА'}")
    scan()
    while True:
        time.sleep(INTERVAL_MIN * 60)
        scan()

if __name__ == "__main__":
    main()
