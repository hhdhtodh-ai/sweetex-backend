# =========================
# Sweetex AI - Render Ready Backend
# =========================

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BINANCE_API = "https://api.binance.com/api/v3/klines"

# =========================
# INDICATORS
# =========================

def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = prices[0]
    for price in prices:
        ema_val = price * k + ema_val * (1 - k)
    return round(ema_val, 4)

def rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# =========================
# MARKET DATA
# =========================

def get_prices(symbol):
    url = f"{BINANCE_API}?symbol={symbol}&interval=1m&limit=100"
    data = requests.get(url, timeout=10).json()
    closes = [float(c[4]) for c in data]
    return closes

# =========================
# SIGNAL ENGINE
# =========================

def analyze_market(prices):
    ema50 = ema(prices, 50)
    rsi14 = rsi(prices, 14)
    current = prices[-1]

    trend = "Bullish" if current > ema50 else "Bearish"

    if trend == "Bullish" and rsi14 < 70:
        signal = "BUY"
    elif trend == "Bearish" and rsi14 > 30:
        signal = "SELL"
    else:
        signal = "WAIT"

    confidence = 50
    if signal == "BUY":
        confidence = min(90, int(60 + (70 - rsi14)))
    elif signal == "SELL":
        confidence = min(90, int(60 + (rsi14 - 30)))

    return signal, trend, confidence

# =========================
# API ROUTE
# =========================

@app.route("/signal")
def signal():
    pair = request.args.get("pair", "BTC/USDT")
    symbol = pair.replace("/", "")

    try:
        prices = get_prices(symbol)
        signal, trend, confidence = analyze_market(prices)

        return jsonify({
            "market": "Crypto",
            "pair": pair,
            "signal": signal,
            "trend": trend,
            "confidence": confidence
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# RENDER COMPATIBLE RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
