import ccxt
import pandas as pd
import pandas_ta as ta
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
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
        df['EMA50'] = ta.ema(df['close'], length=50)
        df['EMA200'] = ta.ema(df['close'], length=200)
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
app.title = "Altcoin Trend Analyzer"

app.layout = html.Div([
    html.H2("📈 Altcoin Trend Dashboard (RSI, MACD, EMA, BTC Dominance)"),
    dcc.Interval(id='interval', interval=5*60*1000, n_intervals=0),
    html.Div(id='dominance'),
    html.Div(id='signals'),
    dcc.Tabs(id='tabs', value=SYMBOLS[0], children=[
        dcc.Tab(label=symbol, value=symbol) for symbol in SYMBOLS
    ]),
    dcc.Graph(id='chart')
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

            line = f"{symbol}:"
            if rsi > 70:
                line += f" 🔴 RSI {rsi:.1f} (Overbought)"
            elif rsi < 30:
                line += f" 🟢 RSI {rsi:.1f} (Oversold)"
            else:
                line += f" ⚪ RSI {rsi:.1f}"

            line += " | " + ("🟢 MACD Bullish" if macd > signal else "🔴 MACD Bearish")
            line += " | " + ("📈 EMA Bullish" if ema50 > ema200 else "📉 EMA Bearish")

            signals.append(html.Div(line, style={'marginBottom': '10px'}))
    return signals

@app.callback(
    Output('chart', 'figure'),
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
