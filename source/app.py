from flask import Flask, request, jsonify
from flask import send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
import pandasai as pdai
from pandasai import SmartDatalake
from pandasai.llm import AzureOpenAI
from pandasai import Agent
import openai
import os
import dotenv
import json
dotenv.load_dotenv()
import matplotlib
matplotlib.use('Agg')


# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Configuration for Azure OpenAI
azure_key = "846747bd36354e50a3c8ce60cd4f4626"
azure_endpoint = "https://ithackathon-openai-dev-netapp-01.openai.azure.com/"
openai.api_key = azure_key
openai.api_base = azure_endpoint
openai.api_type = os.getenv("OPENAI_API_TYPE")
openai.api_version = os.getenv("OPENAI_API_VERSION")
openai.deployment_name = os.getenv('OPENAI_DEPLOYMENT_ID_GPT4_TURBO')

# Global variable to hold the SmartDataframe instance
agent = None
static_path_to_charts = "static/charts/"

@app.route('/')
def home():
    return "Welcome to NetAIAnalytics!"

@app.route('/upload', methods=['POST'])
def upload_file():
    dataframes = []
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})  
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            dataframes.append(df)
        elif file.filename.endswith('.xlsx'):
            excel_file = pd.ExcelFile(file_path)
            # Get the sheet names
            sheet_names = excel_file.sheet_names
            for sheet_name in sheet_names:
                # Read the sheet into a dataframe
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # Append the dataframe to the array
                dataframes.append(df)
        else:
            return jsonify({'error': 'Invalid file format'})
    else:           
        return jsonify({'error': 'Invalid file'})
    
        
    # Load File into PandasAI Agent
    global agent
    llm = AzureOpenAI(temperature=0.7, model="gpt-4-turbo", api_key=openai.api_key,deployment_name=openai.deployment_name)
    agent = SmartDatalake(dataframes, config={"llm": llm,"save_charts":"True","save_charts_path": static_path_to_charts,"open_charts":"False"})
    return jsonify({'message': 'File uploaded and processed successfully'})

@app.route('/chat/message', methods=['POST'])
def chat_message():
    data = request.json
    message = data.get('message')
    if message:
        response = handle_query(message)
        return jsonify(response)
    return jsonify({"error": "No message provided."})

def handle_query(question):
    global agent
    if question and agent is not None:
        response = agent.chat(question)
        # Check if the response is a path to a file (you may need to adjust this check)
        if isinstance(response, str) and response.endswith('.png'):
            # Move the file to the static directory
            filename = os.path.basename(response)
            file_path = "http://localhost:3000/" + static_path_to_charts + filename
            response = {'chart_url': file_path}
        # Check if the response is a DataFrame
        elif isinstance(response, pdai.smart_dataframe.SmartDataframe):
            regular_df = response.dataframe # Assuming SmartDataframe has a 'df' attribute that holds the regular DataFrame
            response = regular_df.to_json(orient='records')
            response = json.loads(response)  # Convert JSON string to a Python object
            response = {'data': response}
        # Check if the response is a string (not a path to a file)
        # elif isinstance(response, str):
        #     response = {'message': response}
        return response
    else:
        return {"error": "No question provided or CSV not uploaded."}

if __name__ == '__main__':
    app.run(debug=True)
