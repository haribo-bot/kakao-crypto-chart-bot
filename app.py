from flask import Flask, request, jsonify, send_file, abort
import requests
import pandas as pd
import mplfinance as mpf
import io

app = Flask(__name__)

# ===== SYMBOL MAP =====
SYMBOL_MAP = {
    "fcb":  ("BTCUSDT",  "BTC 1m"),
    "feth": ("ETHUSDT",  "ETH 1m"),
    "fsol": ("SOLUSDT",  "SOL 1m"),
    "flink": ("LINKUSDT", "LINK 1m"),
}

# ===== CHART STYLE =====
market_colors = mpf.make_marketcolors(
    up="#26a69a",
    down="#ef5350",
    edge="inherit",
    wick="inherit",
    volume="in"
)

chart_style = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    marketcolors=market_colors,
    facecolor="#0b1220",
    figcolor="#020617",
    gridcolor="#111827",
    gridstyle=":",
    rc={
        "axes.edgecolor": "#374151",
        "axes.labelcolor": "#9ca3af",
        "xtick.color": "#9ca3af",
        "ytick.color": "#9ca3af"
    }
)

# ===== BINANCE DATA =====
def get_klines(symbol: str, interval: str = "1m", limit: int = 80):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(
        data,
        columns=[
            "time","open","high","low","close","volume",
            "close_time","qv","trades","tb_base","tb_quote","ignore"
        ]
    )
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df.set_index("time", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df

# ===== PNG Chart =====
@app.route("/chart-image/<symbol>")
def chart_image(symbol):
    symbol = symbol.upper()
    allowed = {v[0] for v in SYMBOL_MAP.values()}
    if symbol not in allowed:
        abort(404)

    df = get_klines(symbol, "1m", 80)

    buf = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        style=chart_style,
        volume=True,
        figratio=(16, 9),
        figscale=1.2,
        datetime_format="%H:%M",
        xrotation=0,
        tight_layout=True,
        savefig=buf
    )
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ===== Kakao Webhook =====
@app.route("/kakao/chart", methods=["POST"])
def kakao_chart():
    body = request.get_json()
    utter = body.get("userRequest", {}).get("utterance", "").strip().lower()

    if utter not in SYMBOL_MAP:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "지원 명령어: fcb / feth / fsol / flink"
                    }
                }]
            }
        })

    symbol, label = SYMBOL_MAP[utter]

    domain = request.url_root.rstrip("/")
    image_url = f"{domain}/chart-image/{symbol}"

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleImage": {
                        "imageUrl": image_url,
                        "altText": f"{label}"
                    }
                }
            ]
        }
    })

@app.route("/")
def home():
    return "Kakao Crypto Chart Bot Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
