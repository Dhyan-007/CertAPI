from io import StringIO
from flask import Flask, make_response, request, jsonify, session, send_file
from flask_migrate import Migrate
from dotenv import load_dotenv
from extensions import db, bcrypt
from models import User
import pandas as pd
from functools import reduce
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt.init_app(app)
migrate = Migrate(app, db)

def get_static_directory():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!'}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'message': 'User already exists!'}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['username'] = username
        print("Company Name: ", username)
        return jsonify({'message': 'Login successful!'}), 200
    return jsonify({'message': 'Invalid username or password!'}), 401

@app.route('/customer/as2_connections', methods=['GET'])
def customer_as2_connections():
    if 'username' not in session:
        return jsonify({'message': 'User not logged in!'}), 401

    companyName = session['username']
    partnerName = request.args.get('partnerName')

    if not partnerName:
        return jsonify({'message': 'Partner name is required!'}), 400

    output_file = 'output.xlsx'
    result_df = pd.DataFrame()

    as2_connections_directory = get_static_directory()
    for filename in os.listdir(as2_connections_directory):
        filePath = os.path.join(as2_connections_directory, filename)
        df = pd.read_excel(filePath)
        df['Description_Lower'] = df['Description'].astype(str).str.lower()
        partnerName_lower = partnerName.lower()
        filtered_df = df[(df['Company_Name'] == companyName) & (df['Description_Lower'].str.contains(partnerName_lower, na=False))]
        filtered_df = filtered_df.drop(columns=['Description_Lower'])
        result_df = pd.concat([result_df, filtered_df], ignore_index=True)
    
    if result_df.empty:
            return jsonify({'message': 'Connection details not found!'}), 404
    else:
        result_df.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True, download_name='output.xlsx')
    
@app.route('/internal/customer_as2_connections', methods=['GET'])
def get_cutomer_as2_connections():
    as2_url_destination = request.args.get('as2UrlDestination', '')
    as2_id_tp = request.args.get('as2IdTp', '')

    params = {
        'Destination': as2_url_destination,
        'AS2_ID_TP': as2_id_tp
    }

    params = {k:v for k, v in params.items() if v}

    if not params:
        return jsonify({'message': 'Please enter one of the fields!'}), 400

    result_df = pd.DataFrame()

    as2_connections_directory = get_static_directory()
    for filename in os.listdir(as2_connections_directory):
        filePath = os.path.join(as2_connections_directory, filename)
        df = pd.read_excel(filePath)
        if len(params) == 1:
            column_name, param = next(iter(params.items()))
            filtered_df = df[(df[column_name] == param)]
        else:
            conditions = [(df[column_name] == param) for column_name, param in params.items()]
            combined_condition = reduce(lambda x, y: x & y, conditions)
            filtered_df = df[combined_condition]
        result_df = pd.concat([result_df, filtered_df], ignore_index=True)
    
    if result_df.empty:
            return jsonify({'message': 'Connection details not found!'}), 404
    else:
        result_dict = result_df.to_dict(orient='records')
        return jsonify(result_dict)


if __name__ == '__main__':
    port = int(os.getenv('PORT'))
    host = os.getenv('HOST')
    app.run(host=host, port=port, debug=True)
