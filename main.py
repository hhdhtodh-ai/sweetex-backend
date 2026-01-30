from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)

        pair = data.get("pair")
        market = data.get("market", "Crypto")

        if not pair:
            return jsonify({"error": "Pair required"}), 400

        # Normalize symbol
        symbol = pair.replace("/", "").upper()

        # ===== Live Price =====
        price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        price_res = requests.get(price_url).json()

        if "price" not in price_res:
            return jsonify({"error": "Invalid trading pair"}), 400

        price = float(price_res["price"])

        # ===== Candles =====
        kline_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
        klines = requests.get(kline_url).json()

        closes = [float(k[4]) for k in klines]

        # ===== Indicators =====
        def ema(values, period=14):
            k = 2 / (period + 1)
            ema_val = values[0]
            for v in values[1:]:
                ema_val = (v * k) + (ema_val * (1 - k))
            return round(ema_val, 5)

        def rsi(values, period=14):
            gains = []
            losses = []

            for i in range(1, len(values)):
                diff = values[i] - values[i - 1]
                if diff > 0:
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

        # ===== Smart Money Logic =====
        if rsi_val > 55 and price > ema_val:
            signal = "CALL"
            trend = "Bullish"
            smc = "Buy Side Liquidity Grab"
        elif rsi_val < 45 and price < ema_val:
            signal = "PUT"
            trend = "Bearish"
            smc = "Sell Side Liquidity Grab"
        else:
            signal = "WAIT"
            trend = "Sideways"
            smc = "Consolidation Zone"

        return jsonify({
            "pair": pair,
            "market": market,
            "signal": signal,
            "trend": trend,
            "rsi": rsi_val,
            "ema": ema_val,
            "smc": smc,
            "price": round(price, 5)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
