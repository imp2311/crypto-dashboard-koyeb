import ccxt
import talib
import pandas as pd
import yfinance as yf
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

SYMBOLS = ['ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'XRP/USDT']
TIMEFRAME = '1h'

exchange = ccxt.binance()

def get_indicators(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        macd, macdsignal, _ = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd
        df['MACD_SIGNAL'] = macdsignal
        df['EMA50'] = talib.EMA(df['close'], timeperiod=50)
        df['EMA200'] = talib.EMA(df['close'], timeperiod=200)
        return df
    except Exception as e:
        print(f"Errore con {symbol}: {e}")
        return None

def get_btc_dominance():
    try:
        data = yf.download("^BTC.D", period="1d", interval="1h")
        latest = data['Close'].iloc[-1]
        return round(latest, 2)
    except Exception as e:
        print(f"Errore Dominance BTC: {e}")
        return "N/A"

app = Dash(__name__)
server = app.server
app.title = "Altcoin Trend Analyzer"

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
    for symbol in SYMBOLS:
        df = get_indicators(symbol)
        if df is not None:
            latest = df.iloc[-1]
            rsi = latest['RSI']
            macd = latest['MACD']
            signal = latest['MACD_SIGNAL']
            ema50 = latest['EMA50']
            ema200 = latest['EMA200']
            close = latest['close']

            trend = f"{symbol}:"

            # RSI
            if rsi > 70:
                trend += f" 🔴 RSI {rsi:.1f} (Overbought)"
            elif rsi < 30:
                trend += f" 🟢 RSI {rsi:.1f} (Oversold)"
            else:
                trend += f" ⚪ RSI {rsi:.1f}"

            # MACD
            if macd > signal:
                trend += f" | 🟢 MACD Bullish"
            elif macd < signal:
                trend += f" | 🔴 MACD Bearish"

            # EMA
            if ema50 > ema200:
                trend += f" | 📈 EMA Bullish (50 > 200)"
            else:
                trend += f" | 📉 EMA Bearish (50 < 200)"

            signals.append(html.Div(trend, style={'marginBottom': '10px'}))
    return signals

@app.callback(
    Output('rsi-macd-ema-graph', 'figure'),
    Input('tabs', 'value')
)
def update_graph(symbol):
    df = get_indicators(symbol)
    if df is None:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], name='RSI'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD'], name='MACD'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_SIGNAL'], name='MACD Signal'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA50'], name='EMA 50', line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA200'], name='EMA 200', line=dict(dash='dot')))
    fig.update_layout(title=f"📊 Indicatori per {symbol}", yaxis_title="Valori", xaxis_title="Ora")
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)