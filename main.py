@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)

        pair = data.get("pair", "").upper()
        market = data.get("market", "")

        if not pair:
            return jsonify({"error": "Pair required"}), 400

        # Binance symbol format
        symbol = pair.replace("/", "")

        # ===== LIVE PRICE =====
        price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        price_res = requests.get(price_url).json()
        price = float(price_res["price"])

        # ===== CANDLES =====
        kline_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        klines = requests.get(kline_url).json()
        closes = [float(k[4]) for k in klines]

        # ===== EMA =====
        def ema(values, period=14):
            k = 2 / (period + 1)
            ema_val = values[0]
            for v in values:
                ema_val = v * k + ema_val * (1 - k)
            return round(ema_val, 2)

        # ===== RSI =====
        def rsi(values, period=14):
            gains = []
            losses = []
            for i in range(1, len(values)):
                diff = values[i] - values[i - 1]
                if diff > 0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))

            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period

            if avg_loss == 0:
                return 100

            rs = avg_gain / avg_loss
            return round(100 - (100 / (1 + rs)), 2)

        ema_val = ema(closes)
        rsi_val = rsi(closes)

        # ===== AI LOGIC =====
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
            "trend": trend
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
