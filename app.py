import ccxt
import pandas as pd
import requests
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

        # Calcolo indicatori senza ta-lib: RSI, MACD, EMA
        # Per esempio, calcoliamo RSI manualmente
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # EMA 50 e 200
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

        return df
    except Exception as e:
        print(f"Errore con {symbol}: {e}")
        return None

def get_btc_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url)
        data = response.json()
        dominance = data['data']['market_cap_percentage']['btc']
        return round(dominance, 2)
    except Exception as e:
        print(f"Errore Dominance BTC: {e}")
        return "N/A"

app = Dash(__name__)
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
        if df is not None and not df.empty:
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
        else:
            signals.append(html.Div(f"{symbol}: Dati non disponibili", style={'marginBottom': '10px', 'color': 'red'}))
    return signals

@app.callback(
    Output('rsi-macd-ema-graph', 'figure'),
    Input('tabs', 'value')
)
def update_graph(symbol):
    df = get_indicators(symbol)
    if df is None or df.empty:
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
    # In base alla tua versione Dash, usa app.run() invece di app.run_server()
    app.run(debug=True, host='0.0.0.0', port=8080)
