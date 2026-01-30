from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import numpy as np

app = Flask(__name__)
CORS(app)

BINANCE_API = "https://api.binance.com/api/v3/klines"

def get_candles(symbol, interval="1m", limit=50):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    r = requests.get(BINANCE_API, params=params, timeout=10)
    data = r.json()
    closes = [float(c[4]) for c in data]
    return closes

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = deltas[deltas > 0].sum() / period
    losses = abs(deltas[deltas < 0].sum()) / period
    rs = gains / losses if losses != 0 else 0
    return round(100 - (100 / (1 + rs)), 2)

def calculate_ema(prices, period=20):
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    ema = np.convolve(prices, weights, mode='valid')
    return round(float(ema[-1]), 4)

def smc_logic(prices):
    high = max(prices[-10:])
    low = min(prices[-10:])
    last = prices[-1]
    if last > high * 0.998:
        return "Liquidity Grab (Buy Side)"
    elif last < low * 1.002:
        return "Liquidity Grab (Sell Side)"
    else:
        return "Consolidation"

@app.route("/")
def home():
    return "Sweetex Backend is LIVE 🚀"

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        pair = data.get("pair", "").replace("/", "").upper()

        prices = get_candles(pair)
        rsi = calculate_rsi(prices)
        ema = calculate_ema(prices)
        smc = smc_logic(prices)

        trend = "Uptrend" if prices[-1] > ema else "Downtrend"

        if rsi > 60 and trend == "Uptrend":
            signal = "CALL"
        elif rsi < 40 and trend == "Downtrend":
            signal = "PUT"
        else:
            signal = "WAIT"

        return jsonify({
            "signal": signal,
            "trend": trend,
            "rsi": rsi,
            "ema": ema,
            "smc": smc,
            "price": prices[-1]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

app.run(host="0.0.0.0", port=81)
