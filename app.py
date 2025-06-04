import ccxt
import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

# Setup logging
logging.basicConfig(level=logging.INFO)

# Parametri generali
TIMEFRAME = '1h'
exchange = ccxt.binance()

# Cache richieste Binance
last_fetch = {}

# Caricamento lista asset da file Excel
def load_symbols(filepath='assets.xlsx'):
    try:
        df = pd.read_excel(filepath)
        symbols = df['symbol'].dropna().tolist()
        logging.info(f"Asset caricati: {symbols}")
        return symbols
    except Exception as e:
        logging.error(f"Errore nel leggere il file Excel: {e}")
        return []

# Funzione per calcolo indicatori
def get_indicators(symbol, cache_time_minutes=4):
    now = datetime.utcnow()
    if symbol in last_fetch and now - last_fetch[symbol]['time'] < timedelta(minutes=cache_time_minutes):
        return last_fetch[symbol]['data']
    
    try:
        logging.info(f"Fetching data for {symbol}")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # EMA
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()

        last_fetch[symbol] = {'data': df, 'time': now}
        return df

    except Exception as e:
        logging.error(f"Errore con {symbol}: {e}")
        return None

# Dominanza BTC
def get_btc_dominance():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/global")
        data = response.json()
        dominance = data['data']['market_cap_percentage']['btc']
        return round(dominance, 2)
    except Exception as e:
        logging.error(f"Errore Dominance BTC: {e}")
        return None

# Valutazione segnale
def evaluate_signal(symbol):
    df = get_indicators(symbol)
    if df is None or df.empty:
        return html.Div(f"{symbol}: ❌ Dati non disponibili", style={'color': 'red'})

    latest = df.iloc[-1]
    rsi = latest['RSI']
    macd = latest['MACD']
    macd_signal = latest['MACD_SIGNAL']
    ema50 = latest['EMA50']
    ema200 = latest['EMA200']

    signal = ""
    reasons = []

    if rsi < 30 and macd > macd_signal and ema50 > ema200:
        signal = "🟢 BUY"
        reasons.append("RSI oversold")
        reasons.append("MACD bullish")
        reasons.append("EMA bullish")
    elif rsi > 70 or macd < macd_signal or ema50 < ema200:
        signal = "🔴 SELL"
        if rsi > 70: reasons.append("RSI overbought")
        if macd < macd_signal: reasons.append("MACD bearish")
        if ema50 < ema200: reasons.append("EMA bearish")
    else:
        signal = "⚪ HOLD"
        reasons.append("Condizioni neutre")

    info = f"{symbol}: {signal} | " + " + ".join(reasons)
    return html.Div(info, style={'marginBottom': '10px'})

# Inizializza app
app = Dash(__name__)
app.title = "Altcoin Signal Dashboard"

app.layout = html.Div([
    html.H2("📊 Altcoin Signal Tracker da Excel"),
    dcc.Interval(id='interval', interval=5*60*1000, n_intervals=0),  # ogni 5 minuti
    html.Div(id='dominance', style={'marginBottom': '20px'}),
    html.Div(id='signals')
])

# Callback Dominance BTC
@app.callback(
    Output('dominance', 'children'),
    Input('interval', 'n_intervals')
)
def update_dominance(n):
    dom = get_btc_dominance()
    if dom is None:
        return html.H4("👑 Dominanza BTC: dati non disponibili")
    return html.H4(f"👑 Dominanza BTC: {dom}%")

# Callback segnali da Excel
@app.callback(
    Output('signals', 'children'),
    Input('interval', 'n_intervals')
)
def update_signals(n):
    symbols = load_symbols()
    if not symbols:
        return [html.Div("⚠️ Nessun asset trovato nel file assets.xlsx", style={'color': 'orange'})]
    return [evaluate_signal(symbol) for symbol in symbols]

# Avvio
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
