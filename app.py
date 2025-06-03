import ccxt
import pandas as pd
import numpy as np
import yfinance as yf
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import logging

# Setup log
logging.basicConfig(level=logging.INFO)

SYMBOLS = ['ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'XRP/USDT']
TIMEFRAME = '1h'

exchange = ccxt.binance()

def get_indicators(symbol):
    try:
        logging.info(f"Fetching data for {symbol}")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['RSI'] = ta_rsi(df['close'], 14)
        df['MACD'], df['MACD_SIGNAL'] = ta_macd(df['close'])
        df['EMA50'] = ta_ema(df['close'], 50)
        df['EMA200'] = ta_ema(df['close'], 200)
        return df
    except Exception as e:
        logging.error(f"Errore con {symbol}: {e}")
        return None

def ta_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ta_macd(series, fast=12, slow=26, signal=9):
    fast_ema = series.ewm(span=fast).mean()
    slow_ema = series.ewm(span=slow).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line

def ta_ema(series, period):
    return series.ewm(span=period).mean()

def get_btc_dominance():
    try:
        data = yf.download("^BTC.D", period="1d", interval="1h")
        if data.empty:
            return "N/A"
        return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        logging.error(f"Errore Dominance BTC: {e}")
        return "N/A"

# --- DASH APP ---
app = Dash(__name__)
server = app.server  # WSGI for Koyeb

app.layout = html.Div([
    html.H2("📈 Altcoin Trend Dashboard"),
    dcc.Interval(id='interval', interval=5*60*1000, n_intervals=0),
    html.Div(id='dominance'),
    html.Div(id='signals'),
    dcc.Tabs(id='tabs', value=SYMBOLS[0], children=[
        dcc.Tab(label=symbol, value=symbol) for symbol in SYMBOLS
    ]),
    dcc.Graph(id='rsi-macd-ema-graph')
])

@app.callback(
    Output('dominance', 'children'),
    Input('interval', 'n_intervals')
)
def update_dominance(n):
    dom = get_btc_dominance()
    return html.H4(f"👑 BTC Dominance attuale: {dom}%")

@app.callback(
    Output('signals', 'children'),
    Input('interval', 'n_intervals')
)
def update_signals(n):
    signals = []
    try:
        for symbol in SYMBOLS:
            df = get_indicators(symbol)
            if df is None or df.empty:
                signals.append(html.Div(f"No data for {symbol}", style={'color': 'red'}))
                continue
            
            latest = df.iloc[-1]
            rsi = latest['RSI']
            macd = latest['MACD']
            signal = latest['MACD_SIGNAL']
            ema50 = latest['EMA50']
            ema200 = latest['EMA200']

            trend = f"{symbol}:"

            # RSI
            if rsi > 70:
                trend += f" 🔴 RSI {rsi:.1f} (Overbought)"
            elif rsi < 30:
                trend += f" 🟢 RSI {rsi:.1f} (Oversold)"
            else:
                trend += f" ⚪ RSI {rsi:.1f}"

            # MACD
            trend += f" | {'🟢 MACD Bullish' if macd > signal else '🔴 MACD Bearish'}"

            # EMA
            trend += f" | {'📈 EMA Bullish (50 > 200)' if ema50 > ema200 else '📉 EMA Bearish (50 < 200)'}"

            signals.append(html.Div(trend, style={'marginBottom': '10px'}))
    except Exception as e:
        logging.error(f"Errore callback signals: {e}")
        signals.append(html.Div(f"Errore: {str(e)}", style={'color': 'red'}))
    return signals

@app.callback(
    Output('rsi-macd-ema-graph', 'figure'),
    Input('tabs', 'value')
)
def update_graph(symbol):
    try:
        df = get_indicators(symbol)
        if df is None or df.empty:
            return go.Figure(layout={'title': f"Nessun dato disponibile per {symbol}"})
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], name='RSI'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD'], name='MACD'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_SIGNAL'], name='MACD Signal'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA50'], name='EMA 50', line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA200'], name='EMA 200', line=dict(dash='dot')))
        fig.update_layout(title=f"📊 Indicatori per {symbol}", yaxis_title="Valori", xaxis_title="Ora")
        return fig
    except Exception as e:
        logging.error(f"Errore callback grafico: {e}")
        return go.Figure(layout={'title': f"Errore: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
