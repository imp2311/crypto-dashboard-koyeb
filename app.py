import ccxt
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objs as go
import base64
import logging

# === CONFIG ===
EXCEL_FILE = 'data/assets.xlsx'
TIMEFRAME = '1h'
exchange = ccxt.binance()
logging.basicConfig(level=logging.INFO)

# === DASH INIT ===
app = Dash(__name__)
app.title = "📊 Altcoin Signal Dashboard"

# === LOAD EXCEL ===
def load_assets():
    try:
        df = pd.read_excel(EXCEL_FILE)
        df = df.dropna(subset=['Symbol'])
        df['Valore'] = df['Valore'].astype(float)

        liqu_usdt = df['Liquidità_USDT'].iloc[0] if 'Liquidità_USDT' in df.columns else None
        liqu_aed = df['Liquidità_AED'].iloc[0] if 'Liquidità_AED' in df.columns else None

        return df, liqu_usdt, liqu_aed
    except Exception as e:
        logging.error(f"Errore nel file Excel: {e}")
        return pd.DataFrame(columns=['Symbol', 'Valore']), None, None

# === INDICATORS ===
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
        logging.warning(f"{symbol} non disponibile: {e}")
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

# === LAYOUT ===
app.layout = html.Div([
    html.H2("📈 Altcoin Signal Dashboard", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📤 Trascina qui il file Excel o clicca per caricare']),
        style={
            'width': '90%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': 'auto'
        },
        multiple=False
    ),
    html.Div(id='upload-status'),
    html.Br(),

    html.Button('Aggiorna manualmente', id='btn-update', n_clicks=0,
                style={'margin': '10px auto', 'display': 'block'}),

    html.Div(id='liquidity-info'),
    dcc.Interval(id='interval', interval=5*60*1000, n_intervals=0),
    html.Div(id='signals-table')
])

# === CALLBACK: Upload ===
@app.callback(
    Output('upload-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def save_uploaded_file(contents, filename):
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        with open(EXCEL_FILE, 'wb') as f:
            f.write(decoded)
        return html.Div(f"✅ File '{filename}' caricato correttamente.")
    return ""

# === CALLBACK: Liquidity ===
@app.callback(
    Output('liquidity-info', 'children'),
    Input('interval', 'n_intervals'),
    Input('btn-update', 'n_clicks')
)
def update_liquidity(n_intervals, n_clicks):
    _, usdt, aed = load_assets()
    if usdt and aed:
        return html.H4(f"💰 Liquidità: {usdt} USDT | {aed} AED", style={'textAlign': 'center'})
    else:
        return html.H4("⚠️ Liquidità non disponibile nel file.", style={'textAlign': 'center', 'color': 'red'})

# === CALLBACK: Signals Table ===
@app.callback(
    Output('signals-table', 'children'),
    Input('interval', 'n_intervals'),
    Input('btn-update', 'n_clicks')
)
def update_signals(n_intervals, n_clicks):
    asset_df, _, _ = load_assets()
    rows = []

    for _, row in asset_df.iterrows():
        symbol = row['Symbol']
        valore = row['Valore']
        df = get_indicators(symbol)
        signal, indicators = generate_signal(df)

        if indicators:
            row_el = html.Tr([
                html.Td(symbol),
                html.Td(f"${valore:,.2f}"),
                html.Td(indicators['RSI']),
                html.Td(indicators['MACD']),
                html.Td(indicators['MACD_SIGNAL']),
                html.Td(f"{indicators['EMA50']} / {indicators['EMA200']}"),
                html.Td(signal, style={'color': 'green' if signal == 'BUY' else 'red' if signal == 'SELL' else 'gray'})
            ])
        else:
            row_el = html.Tr([html.Td(symbol), html.Td(f"${valore:,.2f}"), html.Td("No data", colSpan=5)])
        rows.append(row_el)

    return html.Table([
        html.Thead(html.Tr([
            html.Th("Symbol"),
            html.Th("Valore"),
            html.Th("RSI"),
            html.Th("MACD"),
            html.Th("MACD Signal"),
            html.Th("EMA50/200"),
            html.Th("Segnale")
        ])),
        html.Tbody(rows)
    ], style={'width': '100%', 'textAlign': 'center', 'marginTop': '20px'})

# === RUN ===
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)
