import os
import logging
import PyPDF2
from flask import Flask, request, jsonify
import openai
import openai.resources
from openai.resources.beta.threads.messages import Messages
import base64
import time
from dotenv import load_dotenv,find_dotenv
import sqlite3
import json
import re



assistant_id='asst_Cja30rCMd5UhQ6klId6sLEm8'

_= load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
  raise ValueError("No OpenAI API key found in environment variables")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
model = "gpt-4-turbo"
temperature =0.3
max_tokens = 500
topic=""

def find_and_extract_json(text):
    # Regex, um einen JSON-String zu finden
    # Sucht nach einem String, der mit '{' beginnt und mit '}' endet
    print (f"ist das json? {text}")
    pattern = re.compile(r'STARTJSON(.*?)ENDJSON', re.DOTALL)

    match = pattern.search(text)
    print(f"Match: {match}")
    if match:
        json_text = match.group(1).strip()
        try:
            # Versucht, den gefundenen JSON-Text zu parsen
            data = json.loads(json_text)
            print("Gefundener JSON:", data)
            return data
        except json.JSONDecodeError:
            print("Gefundener Text ist kein gültiger JSON.")
            return None
    else:
        print("Kein JSON im Text gefunden.")
        return None

def upload_to_openai(file_path):
  with open(file_path, 'rb') as f:
      response = client.files.create(file=(file_path,f), purpose='assistants')
      print(response)
      return response.id

message_File_IDs = []  
message_File_IDs.append(upload_to_openai("QU-240596.pdf"))

def write_to_database(thread_id, assistant_id, run_id, timestamp, latest_message):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (thread_id TEXT, assistant_id TEXT, run_id TEXT, timestamp TEXT, latest_message TEXT)''')

    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
              (thread_id, assistant_id, run_id, timestamp, latest_message))

    conn.commit()
    conn.close()

# Example usage
def thread_start():
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "Analyze this file.",
                "attachments": [
                    {
                        "file_id": message_File_IDs[0],
                        "tools": [{"type": "file_search"}]
                    }
                ]
            }
        ]
    )
    return thread


def run_thread(thread_id,assistant_id, question):
    client.beta.threads.messages.create(thread_id=thread.id,
                                      role="user",
                                      content=question                                      
    )                                  
                                     
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
    print(f"Created thread with id: {thread.id}, run_Id: {run.id}")

    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")
    else:
        print("Run completed")

    message_response = client.beta.threads.messages.list(thread_id=thread.id)
    timestamp = str(time.time())
    #write_to_database(thread_id, assistant_id, run.id, timestamp, message_response.data[0])
    return message_response.data

# messages=run_thread(thread.id,assistant_id,message_File_IDs, "Bitte analysiere das anliegende Dokument")


def menu(firstCommand):
    myprompt=firstCommand
    latest_json = None
    while True:
        messages=run_thread(thread.id,assistant_id, myprompt)
        print(f"Messages: {messages}")
        latest_message = messages[0]
        latest_json = find_and_extract_json(latest_message.content[0].text.value)
        # print(f"Latest message: {latest_message.content[0].text.value}")
        print(f"Latest json: {latest_json}")

        print("1. Weiteren Befehl an den Thread senden")
        print("2. Beenden")
        choice = input("Wähle eine Option: ")

        if choice == "1":
            myprompt = input("Gib den Befehl ein: ")
        elif choice == "2":
            break
        else:
            print("Ungültige Option. Bitte wähle erneut.")
    return latest_json

thread=thread_start()
result=menu("Bitte analysiere das anliegende Dokument")
print(f"Result: {result}")

if __name__ == '__main__':
    app.run()