import os
import pandas as pd
from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Cria pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def consolidar_dados(caminho_csv, caminho_excel):
    df_csv = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
    df_excel = pd.read_excel(caminho_excel, sheet_name='Historico_adiantamento')

    df_csv['valor'] = df_csv['valor'].str.replace(',', '.').astype(float)
    consolidado_ifood = df_csv.groupby('id_da_pessoa_entregadora').agg({
        'recebedor': 'first',
        'praca': 'first',
        'subpraca': 'first',
        'valor': 'sum'
    }).reset_index().rename(columns={
        'id_da_pessoa_entregadora': 'uuid',
        'recebedor': 'nome',
        'valor': 'valor_ifood'
    })

    df_excel['valores'] = pd.to_numeric(df_excel['valores'], errors='coerce')
    consolidado_adiantamento = df_excel.groupby('idEntregador')['valores'].sum().reset_index()
    consolidado_adiantamento = consolidado_adiantamento.rename(columns={
        'idEntregador': 'uuid',
        'valores': 'adiantamentos_trampay'
    })

    resultado = pd.merge(consolidado_ifood, consolidado_adiantamento, on='uuid', how='left')
    resultado['adiantamentos_trampay'] = resultado['adiantamentos_trampay'].fillna(0)
    resultado['total'] = (resultado['valor_ifood'] - resultado['adiantamentos_trampay']).round(2)
    return resultado

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        excel_file = request.files['excel_file']

        if csv_file and excel_file:
            csv_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(csv_file.filename))
            excel_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(excel_file.filename))

            csv_file.save(csv_path)
            excel_file.save(excel_path)

            resultado = consolidar_dados(csv_path, excel_path)
            resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resultado_consolidado.xlsx')
            resultado.to_excel(resultado_path, index=False)

            return redirect(url_for('download_resultado'))

    return render_template('index.html')

@app.route('/download')
def download_resultado():
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'resultado_consolidado.xlsx')
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
