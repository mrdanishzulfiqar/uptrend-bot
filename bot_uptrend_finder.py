import os
import time
import requests
import schedule
import threading
import pandas as pd
from flask import Flask
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# --- FLASK WEB SERVER (Keeps Render Free Web Service Active) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

# --- SCANNER CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"

client = Client()

TIMEFRAME = Client.KLINE_INTERVAL_4HOUR
RSI_MIN = 10
RSI_MAX = 80
MIN_VOLUME_USDT = 5_000_000

EXCLUDE_TOKENS = [
    'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'BUSDUSDT', 
    'DAIUSDT', 'UUSDUSDT', 'RLUSDUSDT', 'USDEUSDT', 'USD1USDT'
]

def send_discord_alert(matches):
    if not matches:
        payload = {"content": "🔍 **Uptrend Scan Completed:** No matching coins found."}
    else:
        message = f"🚨 **Uptrend Scanner Alert ({len(matches)} Coins Found)** 🚨\n```\n"
        message += f"{'Symbol':<12} {'Price ($)':<10} {'RSI':<6}\n" + "-"*32 + "\n"
        for m in matches:
            message += f"{m['symbol']:<12} {m['price']:<10} {m['rsi']:<6}\n"
        message += "```"
        payload = {"content": message}

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Discord Error: {e}")

def get_binance_usdt_pairs():
    tickers = client.get_ticker()
    valid_pairs = []
    for t in tickers:
        symbol = t['symbol']
        volume = float(t['quoteVolume'])
        if symbol.endswith('USDT') and not symbol.endswith(('UPUSDT', 'DOWNUSDT')):
            if symbol not in EXCLUDE_TOKENS and volume >= MIN_VOLUME_USDT:
                valid_pairs.append(symbol)
    return valid_pairs

def check_uptrend(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=TIMEFRAME, limit=100)
        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        
        df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
        df['EMA_20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
        df['EMA_50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
        
        latest = df.iloc[-1]
        close = latest['close']
        rsi = latest['RSI']
        ema_20 = latest['EMA_20']
        ema_50 = latest['EMA_50']
        
        if (RSI_MIN <= rsi <= RSI_MAX) and (close > ema_20 > ema_50):
            return {'symbol': symbol, 'price': close, 'rsi': round(rsi, 2)}
    except Exception:
        return None
    return None

def run_scan():
    print("Running scheduled scan...")
    symbols = get_binance_usdt_pairs()
    matches = []
    for symbol in symbols:
        result = check_uptrend(symbol)
        if result:
            matches.append(result)
        time.sleep(0.05)
    send_discord_alert(matches)

def run_scheduler():
    run_scan()
    schedule.every(4).hours.do(run_scan)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start background scan thread
threading.Thread(target=run_scheduler, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
