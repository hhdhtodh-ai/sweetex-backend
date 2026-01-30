from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Sweetex Backend Running"

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)
        pair = data.get("pair", "").strip()
        market = data.get("market", "Crypto")

        if not pair:
            return jsonify({"error": "Pair required"}), 400

        # Normalize symbol for Binance
        symbol = pair.replace("/", "").upper()

        # =====================
        # GET LIVE PRICE
        # =====================
        price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        price_res = requests.get(price_url).json()

        if "price" not in price_res:
            return jsonify({"error": "Invalid symbol or Binance API error"}), 500

        price = float(price_res["price"])

        # =====================
        # GET CANDLES
        # =====================
        kline_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        klines = requests.get(kline_url).json()

        if not isinstance(klines, list) or len(klines) < 20:
            return jsonify({"error": "Not enough market data"}), 500

        closes = []
        for k in klines:
            try:
                closes.append(float(k[4]))
            except:
                pass

        if len(closes) < 14:
            return jsonify({"error": "Insufficient candle data"}), 500

        # =====================
        # EMA
        # =====================
        def ema(values, period=14):
            k = 2 / (period + 1)
            ema_val = values[0]
            for v in values:
                ema_val = v * k + ema_val * (1 - k)
            return round(ema_val, 4)

        # =====================
        # RSI
        # =====================
        def rsi(values, period=14):
            gains = []
            losses = []
            for i in range(1, len(values)):
                diff = values[i] - values[i - 1]
                if diff >= 0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))

            if len(gains) < period or len(losses) < period:
                return 50

            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period

            if avg_loss == 0:
                return 100

            rs = avg_gain / avg_loss
            return round(100 - (100 / (1 + rs)), 2)

        ema_val = ema(closes)
        rsi_val = rsi(closes)

        # =====================
        # SMC LOGIC
        # =====================
        if rsi_val > 55 and price > ema_val:
            signal = "CALL"
            trend = "Bullish"
        elif rsi_val < 45 and price < ema_val:
            signal = "PUT"
            trend = "Bearish"
        else:
            signal = "WAIT"
            trend = "Sideways"

        return jsonify({
            "signal": signal,
            "trend": trend,
            "price": round(price, 5),
            "ema": ema_val,
            "rsi": rsi_val
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
