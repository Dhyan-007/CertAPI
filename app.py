from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def find_connection_details(connection_name):
    url = "https://confighub.b2b.ibm.com/ssauth/api/jwt/login"
    headers = {"Content-Type": "application/json"}

    username = os.getenv('API_USERNAME')
    password = os.getenv('API_PASSWORD')

    data = {"username": username, "password": password}

    response = requests.post(url, json=data, headers=headers)
    token = response.cookies["refresh_token"]

    authori = "Bearer " + token +"" 

    base_url = 'https://confighub.b2b.ibm.com/ssapigateway/api/listexpiringsslcertificates'
    query_string1 = 'Accept = application/json'
    query_string2 = 'expirationDays=400d'

    url = base_url + '?' + query_string1 +'&' + query_string2
    headers = {'Authorization': authori}

    r = requests.get(url, headers=headers)
    data=r.json()['data']

    all_connection_data = []

    connection_names = []
    for item in data:
            connection_names_list = []
            for connection in item['usedByConnections']:
                if connection['connectionName'] not in connection_names:
                    connection_names.append(connection['connectionName'])
                connection_names_list.append(connection['connectionName'])
            item['connection_names_list'] = connection_names_list

    for connectionName in connection_names:
        new_record = {
            "connectionName": connectionName,
            "certificate_names": []
        }
        not_seen = {"CTE": True, "PROD": True}
        for item in data:
            if connectionName in item['connection_names_list']:
                new_record["certificate_names"].append(item['sslCertName'])
                if new_record.get('ownedCompanyName') is None:
                    new_record['ownedCompanyName'] = item['ownedCompanyName']
                if new_record.get('belongsTo') is None:
                    new_record['belongsTo'] = item['belongsTo']
                for connection in item['usedByConnections']:
                    if connection['connectionName'] == connectionName and not_seen[connection['environment']]:
                            env = connection['environment']
                            new_record[f'expiredCertName_{env}'] = item['sslCertName'] 
                            new_record[f'environment_{env}'] = env
                            if connection.get('protocol') is None:
                                new_record['protocol'] = "API"
                            elif new_record.get('protocol') is None:
                                new_record['protocol'] = connection['protocol']
                            new_record[f'sslCertVersion_{env}'] =  connection['sslCertVersion']
                            new_record[f'daysLeftToExpire_{env}'] = connection['daysLeftToExpire']
                            new_record[f'expirationDateTime_{env}'] = connection['expirationDateTime']
                            not_seen[env] = False
        all_connection_data.append(new_record)

    for conn in all_connection_data:
        if conn["connectionName"] == connection_name:
            return conn
    
    return None


@app.route('/api/get_connection_details', methods=['GET'])
def get_connection_details():
    connection_name = request.args.get('connectionName')
    
    if not connection_name:
        return jsonify({'error': 'Connection name is required'}), 400
    
    connection_details = find_connection_details(connection_name)

    if connection_details:
        return jsonify(connection_details), 200
    else:
        return jsonify({'error': 'Connection name is invalid'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
