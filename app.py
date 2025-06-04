import dash
from dash import html, dcc, Input, Output, State
import pandas as pd

# Crea l'app Dash
app = dash.Dash(__name__)

# Layout semplice con upload file e tabella
app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Button('Carica file Excel'),
        multiple=False
    ),
    html.Div(id='output-data-upload')
])

# Funzione per leggere il file excel caricato
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    import base64
    import io
    decoded = base64.b64decode(content_string)
    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return html.Div(['Formato non supportato'])
    except Exception as e:
        return html.Div(['Errore nel leggere il file: ', str(e)])

    return html.Div([
        html.H5(filename),
        dcc.Graph(
            figure={
                'data': [{
                    'type': 'table',
                    'header': {'values': list(df.columns)},
                    'cells': {'values': [df[col] for col in df.columns]}
                }]
            }
        )
    ])

# Callback per caricare e mostrare il contenuto
@app.callback(Output('output-data-upload', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))
def update_output(contents, filename):
    if contents is not None:
        return parse_contents(contents, filename)
    return "Carica un file Excel"

# Qui il punto chiave, sostituire app.run_server con app.run
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
