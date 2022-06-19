# Import modules and packages
from flask import (
    Flask,
    request,
    render_template,
    
    url_for
)
import sqlite3
from flask import Response,send_file,make_response,redirect
import pickle
import numpy as np
import json
from scipy.spatial import distance
# import the json utility package since we will be working with a JSON object
import boto3
import json
from sqlalchemy import create_engine
import pandas as pd
import sqlalchemy
from flask import jsonify
import requests

global tabela_para_exportar
global tabela_global
tabela_global =None
tabela_para_exportar =None
global my_database
my_database = 'wellington.db'

application = Flask(__name__)

@application.route('/')
def index():
    return render_template('index.html')


def compute_RA(df,tempo_teste,tempo_ciclo):
    i = 0
    lista_max = []
    lista_min = []

    while i<tempo_teste:

        df_slice = df.iloc[i:i+tempo_ciclo]

        df_max = df_slice.max()
        df_min = df_slice.min()

        lista_max.append(df_max)
        lista_min.append(df_min)

        df2 = pd.DataFrame(lista_max)
        df3 = pd.DataFrame(lista_min)

        i = i+tempo_ciclo
        
        Ra = (df2-df3)/df3     
    return Ra
    
import pandas as pd
@application.route("/upload", methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        tempo_teste=1260
        tempo_ciclo=105 
        nome=''
        classe=''
        input_val = request.form
        if input_val != None:
            tempo_teste=int(input_val['tempo_teste'])
            tempo_ciclo=int(input_val['tempo_ciclo'])                 
            nome=input_val['fName']
            classe=input_val['cName']    
        f = request.files['file']
        data_xls = pd.read_excel(f)
        df_ra=compute_RA(data_xls.iloc[:, list(range(1,5))],tempo_teste,tempo_ciclo)
        df_ra.insert(0,"Ciclo",df_ra.index)
        df_ra.insert(0,"Classe",classe)
        df_ra.insert(0,"Nome",nome)
        
        
        global tabela_global
        tabela_global =df_ra
        tabela1 = data_xls.to_html(classes="styled-table",index=False)
        tabela2 = df_ra.to_html(classes="styled-table",index=False)
        button = '''<button type="button" onClick="window.location.href='/export'">Exportar Resposta Relativa!</button> \
            <button type="button" onClick="window.location.href='/upload'">Nova carga</button>\
            <button type="button" onClick="window.location.href='/save_database'">Salvar no banco de dados</button>
          '''
        return render_template('upload.html',tabela1=tabela1,tabela2=tabela2,button=button)
    return render_template('upload.html')


@application.route("/save_database")
def save_records():
    engine = sqlalchemy.create_engine('sqlite:///'+my_database, echo=False)
    global tabela_global
    print("salvando tabela no banco de dados")
    print(tabela_global)
    tabela_global.to_sql('mytable', con=engine, if_exists='append')
    return redirect('/show_data')

@application.route("/show_data", methods=['GET', 'POST'])
def show_database():
    if request.method == 'POST':
        input_val = request.form
        # Read sqlite query results into a pandas DataFrame
        con = sqlite3.connect(my_database)
        nome = input_val['Nome']
        nome="'"+nome+"'"
        query= "SELECT * FROM mytable where Nome = "+nome
        df = pd.read_sql_query(query, con)
        global tabela_para_exportar
        tabela_para_exportar = df
        df=df.drop(['index'],axis=1)
        tabela3 = df.to_html(classes="styled-table",index=False)
        button = '''<button type="button" onClick="window.location.href='/export_file'">Exportar</button>
          '''
        return render_template('show_data.html',tabela3=tabela3,button=button)
    return render_template('show_data.html')


@application.route("/export_file")
def export_records_file():
    global tabela_para_exportar
    resp = make_response(tabela_para_exportar.to_csv(index=False))
    resp.headers["Content-Disposition"] = "attachment; filename=resposta_relativa_db.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

@application.route("/export")
def export_records():
    global tabela_global
    resp = make_response(tabela_global.to_csv(index=False))
    resp.headers["Content-Disposition"] = "attachment; filename=resposta_relativa.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

@application.route('/', methods=['POST'])
def get_input_values():
    val = request.form['my_form']

def call_aws_api(vals):

    lambda_client = boto3.client('lambda',region_name='us-west-2',aws_access_key_id="MyID",
                            aws_secret_access_key="secret_access")
    test_event = {
        "firstName": str(vals[0]),
        "lastName": str(vals[1])
    }
    response = lambda_client.invoke(
        FunctionName='HelloWorldFunction',
        Payload=json.dumps(test_event),
    )
    answer=response['Payload'].read().decode("utf-8")
    # ['body']
    return answer

@application.route('/predict', methods=['POST', 'GET'])
def predict():
    if request.method == 'GET':
        return 'The URL /predict is accessed directly. Go to the main page firstly'

    if request.method == 'POST':
        input_val = request.form

        if input_val != None:
            # collecting values
            vals = []
            for key, value in input_val.items():
                vals.append(value)
        answear = call_aws_api(vals)

        return render_template(
            'predict.html', result_value=f'Resultado '+answear
            # 'predict.html', result_value=f'Segment = #{index_min}'
            )

@application.route("/show_data_api",  methods=['POST', 'GET'])
def show_get_data_api():
    if request.method == 'POST':
        nome = request.form['arquivo']
        params={'arquivo':str(nome)}
        response = requests.get("http://192.168.15.45/ra_api",params=params)
        df = pd.DataFrame(response.json()['data'])
        df=df.drop(['index'],axis=1)
        tabela3 = df.to_html(classes="styled-table",index=False)
        button = '''<button type="button" onClick="window.location.href='/export_file'">Exportar</button>
            '''
        return render_template('show_data_api.html',tabela3=tabela3,button=button)
    elif request.method == 'GET':
        return render_template('show_data_api.html')
    
    
@application.route("/ra_api", methods=['GET'])
def get_data_api():
    # Read sqlite query results into a pandas DataFrame
    con = sqlite3.connect(my_database)
    nome = request.args.get("arquivo")
    nome="'"+nome+"'"
    query= "SELECT * FROM mytable where Nome = "+nome
    df = pd.read_sql_query(query, con)
    df=df.drop(['index'],axis=1)
    result = df.to_json(orient="table")
    parsed = json.loads(result)
    return json.dumps(parsed, indent=4) 
    


if __name__ == '__main__':
    application.run(host='0.0.0.0', port=80, debug=True)





