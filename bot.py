from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests, os
import logging
from datetime import datetime
import psycopg2
import google.generativeai as genai


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_API_KEY')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv("DATABASE_URL")
SI = os.getenv('SI')
MAX_HISTORY_SIZE = 5
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# FastAPI App
app = FastAPI()

# Webhook Payload Structure
class TelegramUpdate(BaseModel):
    update_id: int
    message: dict


genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "candidate_count": 1,
    "temperature": 0.9,
    "top_p":1,
    "top_k":1,
    "max_output_tokens":100
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_ONLY_HIGH",
    "probability": "NEGLIGIBLE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_ONLY_HIGH",
    "probability": "NEGLIGIBLE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_ONLY_HIGH",
    "probability": "NEGLIGIBLE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_ONLY_HIGH",
    # "probability": "NEGLIGIBLE"
  },
]

chat_model = genai.GenerativeModel(
    'gemini-1.5-pro-latest',
    system_instruction=SI,
    # generation_config=generation_config,
    safety_settings=safety_settings
    )


# Set Webhook
@app.on_event("startup")
async def set_webhook():
    webhook_endpoint = f"{TELEGRAM_API_URL}/setWebhook"
    response = requests.post(webhook_endpoint, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("Webhook set successfully!")
    else:
        print("Failed to set webhook:", response.text)

# Webhook Endpoint
@app.post("/webhook")
async def webhook(update: TelegramUpdate):
    try:
        logger.debug(f"Received update: {update}")
        chat_id = update.message["chat"]["id"]
        text = update.message["text"]
        username = update["message"]["from"].get("username", "No_username")
        print(f'user: {text}')

        # Process Message and Send Response
        process_message(chat_id,text,username)

    except Exception as e:
        print("Error processing update:", e)

    return {"status": "ok"}

def connect_to_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def add_visitor_to_db(username):
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO telegrambot_visitors (username)
            VALUES (%s)
            ON CONFLICT (username) DO NOTHING;
        """, (username))

        conn.commit()

        cursor.close()
        conn.close()

        logger.info(f"{datetime.now()}: User {username} added to database.")
    except Exception as e:
        logger.error(f"Error while adding user {username} to db: {e}")

# Function to Send Message to Telegram
def send_message(chat_id, text, parse_mode='MarkdownV2'):
    print(text)
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": parse_mode
        }
    requests.post(url, json=payload)

# Function to send an image with a caption
def send_image_with_caption(chat_id, image_path, caption=None):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    with open(image_path, 'rb') as photo:
        files = {'photo': photo}
        payload = {'chat_id': chat_id, 'caption': caption}
        response = requests.post(url, data=payload, files=files)
        return response.json()
    
# Function to delete a message
def delete_message(chat_id, message_id):
    url = f"{TELEGRAM_API_URL}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    response = requests.post(url, json=payload)
    return response.json()  # Return the response for further processing

# model
# def chatt(text):
#     chat = chat_model.start_chat(history=formatted_history)
#     message_with_dots =

# Message Processing Logic
def process_message(chat_id,text,username):
    add_visitor_to_db(username)
    chat_history = {}
    if username not in chat_history:
        chat_history[username] = []
    if len(chat_history[username]) > MAX_HISTORY_SIZE:
        chat_history[username].pop(0)
    
    chat_history[username].append({
        "role":"user",
        "parts":[{"text":text}]
    })
    formatted_history = [
        {
            "role":entry['role'],
            "parts": entry['parts']
        }
        for entry in chat_history[username]
    ]

    if text.lower() == "/start":
        return send_image_with_caption(chat_id, 'https://nataichat.onrender.com/natAi-logo-nobg.png', "Welcome to the NatAI Telegram Bot!" )
    elif text.lower() == "hello" or text.lower() == "hi":
        return "Hello! How can I help you today?"
    else:
        try:
            chat = chat_model.start_chat(history=formatted_history)
            message_with_dots = send_message(chat_id, 'typing...')
            response = chat.send_message(text)
            chat_history[username].append({
                "role":"model",
                "parts":[{"text": text}]
            })
            # logs
            logger.info(f"{datetime.now()}: user({username}): {text}")
            logger.info(f"{datetime.now()}: model({username}): {response.text}")
            # send model response
            send_message(chat_id,response.text)
            delete_message(chat_id, message_with_dots['result']['message_id'])
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            send_message(chat_id, "Sorry, I couldn't process your request.")



        
