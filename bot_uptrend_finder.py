import time
import pandas as pd
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# Initialize Binance client (public endpoints)
client = Client()

TIMEFRAME = Client.KLINE_INTERVAL_4HOUR  # 4-hour candles
RSI_MIN = 10
RSI_MAX = 80
MIN_VOLUME_USDT = 5_000_000  # Minimum $5M 24h volume

# List of stablecoins and pegged tokens to skip
EXCLUDE_TOKENS = [
    'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'BUSDUSDT', 
    'DAIUSDT', 'UUSDUSDT', 'RLUSDUSDT', 'USDEUSDT', 'USD1USDT'
]

def get_binance_usdt_pairs():
    """Fetch active trading pairs on Binance, filtering out stablecoins."""
    tickers = client.get_ticker()
    valid_pairs = []
    
    for t in tickers:
        symbol = t['symbol']
        volume = float(t['quoteVolume'])
        
        # Keep spot USDT pairs with enough volume, skipping UP/DOWN tokens and stablecoins
        if symbol.endswith('USDT') and not symbol.endswith(('UPUSDT', 'DOWNUSDT')):
            if symbol not in EXCLUDE_TOKENS and volume >= MIN_VOLUME_USDT:
                valid_pairs.append(symbol)
                
    return valid_pairs

def check_uptrend(symbol):
    """Evaluate RSI range and Moving Average alignment."""
    try:
        klines = client.get_klines(symbol=symbol, interval=TIMEFRAME, limit=100)
        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        
        # Calculate Indicators via 'ta' library
        df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
        df['EMA_20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
        df['EMA_50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
        
        latest = df.iloc[-1]
        close = latest['close']
        rsi = latest['RSI']
        ema_20 = latest['EMA_20']
        ema_50 = latest['EMA_50']
        
        # Uptrend Rules:
        # 1. RSI is between 50 and 60
        # 2. Price > EMA 20 > EMA 50 (Bullish structure)
        if (RSI_MIN <= rsi <= RSI_MAX) and (close > ema_20 > ema_50):
            return {
                'symbol': symbol,
                'price': close,
                'rsi': round(rsi, 2),
                'ema_20': round(ema_20, 4),
                'ema_50': round(ema_50, 4)
            }
            
    except Exception:
        return None
    
    return None

def main():
    print("Fetching active USDT crypto pairs on Binance...")
    symbols = get_binance_usdt_pairs()
    print(f"Scanning {len(symbols)} coins on the 4h timeframe...\n")
    
    matches = []
    for symbol in symbols:
        result = check_uptrend(symbol)
        if result:
            matches.append(result)
            print(f"Match Found: {result['symbol']} | Price: ${result['price']} | RSI: {result['rsi']}")
        time.sleep(0.05)
        
    print("\n" + "="*45)
    print(f"Scan Complete. Found {len(matches)} uptrend coins:")
    print("="*45)
    for m in matches:
        print(f"Coin: {m['symbol']:<12} Price: ${m['price']:<10} RSI: {m['rsi']}")

if __name__ == "__main__":
    main()