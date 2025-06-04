import os
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import logging

EXCEL_FILE = "data/assets.xlsx"

# Assicura che la cartella esista
os.makedirs("data", exist_ok=True)

# Funzione per caricare dati da Excel
def load_assets():
    try:
        df = pd.read_excel(EXCEL_FILE)
        # Controlla colonne essenziali
        expected_cols = {'Symbol', 'Valore', 'Liquidità_USDT', 'Liquidità_AED'}
        if not expected_cols.issubset(set(df.columns)):
            logging.error(f"Colonne mancanti in {EXCEL_FILE}, aspettate: {expected_cols}")
            return pd.DataFrame()
        return df
    except Exception as e:
        logging.error(f"Errore nel file Excel: {e}")
        return pd.DataFrame()

# Funzione semplice di esempio per segnale buy/sell/hold basata su valore investito
def signal_from_valore(val):
    if pd.isna(val):
        return "No Data"
    if val > 50000:
        return "SELL"
    elif val > 10000:
        return "HOLD"
    else:
        return "BUY"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("Dashboard Investimenti e Liquidità Altcoin"),
    html.Hr(),

    # Upload file Excel
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Trascina o ',
            html.A('seleziona un file Excel (.xlsx)')
        ]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center', 'margin-bottom': '15px',
        },
        multiple=False,
        accept='.xlsx'
    ),

    dbc.Button("Aggiorna dati manualmente", id="refresh-button", color="primary", className="mb-3"),

    html.Div(id="upload-status", style={"color": "green", "margin-bottom": "10px"}),

    # Tabella con dati e segnali
    dash_table.DataTable(
        id='table-assets',
        columns=[
            {"name": "Symbol", "id": "Symbol"},
            {"name": "Valore (USD)", "id": "Valore", "type": "numeric", "format": {"specifier": ".2f"}},
            {"name": "Liquidità (USDT)", "id": "Liquidità_USDT", "type": "numeric", "format": {"specifier": ".2f"}},
            {"name": "Liquidità (AED)", "id": "Liquidità_AED", "type": "numeric", "format": {"specifier": ".2f"}},
            {"name": "Segnale", "id": "Segnale"},
        ],
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'filter_query': '{Segnale} = "BUY"'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'filter_query': '{Segnale} = "SELL"'},
                'backgroundColor': '#f8d7da',
                'color': '#721c24'
            },
            {
                'if': {'filter_query': '{Segnale} = "HOLD"'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            },
        ]
    ),

    dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0)  # refresh ogni 60s
], fluid=True)


@app.callback(
    Output('upload-status', 'children'),
    Output('table-assets', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    Input('refresh-button', 'n_clicks'),
    Input('interval-refresh', 'n_intervals'),
    prevent_initial_call=True
)
def update_output(contents, filename, refresh_clicks, n_intervals):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Se caricamento file
    if triggered_id == 'upload-data' and contents is not None:
        content_type, content_string = contents.split(',')
        import base64
        import io

        try:
            decoded = base64.b64decode(content_string)
            # Salva il file caricato in data/assets.xlsx
            with open(EXCEL_FILE, 'wb') as f:
                f.write(decoded)
            df = load_assets()
            if df.empty:
                return "File caricato, ma dati non validi o vuoti.", []
            # Calcola segnale
            df['Segnale'] = df['Valore'].apply(signal_from_valore)
            return f"File '{filename}' caricato con successo.", df.to_dict('records')
        except Exception as e:
            return f"Errore nel caricamento file: {e}", []

    # Se refresh manuale o automatico
    elif triggered_id in ['refresh-button', 'interval-refresh']:
        df = load_assets()
        if df.empty:
            return "Errore nel caricamento dati da file.", []
        df['Segnale'] = df['Valore'].apply(signal_from_valore)
        return "Dati aggiornati.", df.to_dict('records')

    return dash.no_update


if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8080)
