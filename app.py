import ccxt
import pandas as pd
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
import logging

# Setup
logging.basicConfig(level=logging.INFO)
exchange = ccxt.binance()

EXCEL_FILE = 'assets.xlsx'
TIMEFRAME = '1h'

def load_assets():
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.dropna(subset=['Symbol'])
        df['Valore'] = df['Valore'].astype(float)

        # Legge liquidità da Excel se presente
        liquidita_usdt = df['Liquidità_USDT'].iloc[0] if 'Liquidità_USDT' in df.columns else None
        liquidita_aed = df['Liquidità_AED'].iloc[0] if 'Liquidità_AED' in df.columns else None

        return df, liquidita_usdt, liquidita_aed
    except Exception as e:
        logging.error(f"Errore nel file Excel: {e}")
        return pd.DataFrame(columns=['Symbol', 'Valore']), None, None

def get_indicators(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)

        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9).mean()

        df['EMA50'] = df['close'].ewm(span=50).mean()
        df['EMA200'] = df['close'].ewm(span=200).mean()

        return df
    except Exception as e:
        logging.error(f"Errore su {symbol}: {e}")
        return None

def generate_signal(df):
    if df is None or df.empty:
        return "NO DATA", None

    latest = df.iloc[-1]
    rsi = latest['RSI']
    macd = latest['MACD']
    signal = latest['MACD_SIGNAL']
    ema50 = latest['EMA50']
    ema200 = latest['EMA200']

    decision = "NEUTRAL"
    if rsi < 30 and macd > signal and ema50 > ema200:
        decision = "BUY"
    elif rsi > 70 and macd < signal and ema50 < ema200:
        decision = "SELL"

    return decision, {
        "RSI": round(rsi, 1),
        "MACD": round(macd, 2),
        "MACD_SIGNAL": round(signal, 2),
        "EMA50": round(ema50, 2),
        "EMA200": round(ema200, 2)
    }

# === DASHBOARD ===
app = Dash(__name__)
app.title = "📊 Altcoin Dashboard"

app.layout = html.Div([
    html.H2("📈 Altcoin Signal Dashboard - USD", style={'textAlign': 'center'}),
    dcc.Interval(id='interval', interval=5*60*1000, n_intervals=0),
    html.Button('Aggiorna manualmente', id='btn-update', n_clicks=0, style={'margin': '10px auto', 'display': 'block'}),
    html.Div(id='liquidity-info'),
    html.Br(),
    html.Div(id='signals-table')
])

@app.callback(
    Output('liquidity-info', 'children'),
    Input('interval', 'n_intervals'),
    Input('btn-update', 'n_clicks')
)
def update_liquidity(n_intervals, n_clicks):
    asset_df, liquidita_usdt, liquidita_aed = load_assets()
    if liquidita_usdt is not None and liquidita_aed is not None:
        return html.Div([
            html.H4(f"💰 Liquidità USDT: {liquida_usdt} | Liquidità AED: {liquida_aed}",
                    style={'textAlign': 'center', 'color': '#2A7D46'})
        ])
    else:
        return html.Div([
            html.H4("💰 Liquidità non definita nel file Excel", style={'textAlign': 'center', 'color': 'red'})
        ])

@app.callback(
    Output('signals-table', 'children'),
    Input('interval', 'n_intervals'),
    Input('btn-update', 'n_clicks')
)
def update_table(n_intervals, n_clicks):
    asset_df, _, _ = load_assets()
    rows = []

    for _, row in asset_df.iterrows():
        symbol = row['Symbol']
        valore = row['Valore']
        df = get_indicators(symbol)
        decision, indicators = generate_signal(df)

        if indicators:
            table_row = html.Tr([
                html.Td(symbol),
                html.Td(f"${valore:,.2f}"),
                html.Td(indicators["RSI"]),
                html.Td(indicators["MACD"]),
                html.Td(indicators["MACD_SIGNAL"]),
                html.Td(f'{indicators["EMA50"]} / {indicators["EMA200"]}'),
                html.Td(decision, style={
                    'color': 'green' if decision == 'BUY' else 'red' if decision == 'SELL' else 'gray',
                    'fontWeight': 'bold'
                })
            ])
        else:
            table_row = html.Tr([
                html.Td(symbol),
                html.Td(f"${valore:,.2f}"),
                html.Td("No Data", colSpan=5)
            ])

        rows.append(table_row)

    return html.Table([
        html.Thead(html.Tr([
            html.Th("Symbol"),
            html.Th("Valore (USD)"),
            html.Th("RSI"),
            html.Th("MACD"),
            html.Th("MACD Signal"),
            html.Th("EMA50 / EMA200"),
            html.Th("Segnale")
        ])),
        html.Tbody(rows)
    ], style={'width': '100%', 'textAlign': 'center', 'border': '1px solid #ccc'})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)
