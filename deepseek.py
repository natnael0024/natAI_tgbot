from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests, os
import logging
from datetime import datetime
import psycopg2
from openai import OpenAI

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_API_KEY')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SI = os.getenv('SI')
MAX_HISTORY_SIZE = 5
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=DEEPSEEK_API_KEY,
)
# FastAPI App
app = FastAPI()

# Webhook Payload Structure
class TelegramUpdate(BaseModel):
    update_id: int
    message: dict

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
        # logger.debug(f"Received update: {update}")
        chat_id = update.message["chat"]["id"]
        text = update.message["text"]
        username = update.message["from"].get("username", "No_username")
        logger.info(f"{datetime.now()}: 👤 user({username}): {text}")

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
        """, (username,))

        conn.commit()

        cursor.close()
        conn.close()

        logger.info(f"{datetime.now()}: User {username} added to database.")
    except Exception as e:
        logger.error(f"Error while adding user {username} to db: {e}")

# Function to Send Message to Telegram
def send_message(chat_id, text, parse_mode='Markdown'):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": parse_mode
        }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
    else:
        print(f"Message sent successfully: {response.json()}")
    return response.json()

# Function to send an image with a caption
def send_image_with_caption(chat_id, image_path, caption=None):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    payload = {'chat_id': chat_id, 'photo': image_path, 'caption': caption}
    response = requests.post(url, data=payload)
    return response.json()
    
# Function to delete a message
def delete_message(chat_id, message_id):
    url = f"{TELEGRAM_API_URL}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    response = requests.post(url, json=payload)
    return response.json()  # Return the response for further processing

def send_typing_action(chat_id):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    payload = {
        "chat_id": chat_id,
        "action": "typing"  # Set the action to typing
    }
    response = requests.post(url, json=payload)
    return response.json()


# model
# def chatt(text):
#     chat = chat_model.start_chat(history=formatted_history)
#     message_with_dots =
chat_history = {}

# Message Processing Logic
def process_message(chat_id,text,username):
    add_visitor_to_db(username)
    if username not in chat_history:
        chat_history[username] = []
    if len(chat_history[username]) > MAX_HISTORY_SIZE:
        chat_history[username].pop(0)
    
    chat_history[username].append({"role": "user", "content": text})

    if text.lower() == "/start":
        return send_image_with_caption(chat_id, 'https://nataichat.onrender.com/natAi-logo-nobg.png', "Welcome to the NatAI Telegram Bot!" )
    elif text.lower() == "hello" or text.lower() == "hi":
        return send_message(chat_id,"Hello, How can I help you today?")
    elif text.lower() == "/donate":
        return send_message(chat_id,
        "Thank you for considering a donation! Here are the ways you can support me:\n"
        "1. Telebirr: `0941559518`\n"
        "Your support helps me continue my work!"
        )
    else:
        try:
            # Indicate typing
            message_with_dots = send_message(chat_id, 'typing...')
            send_typing_action(chat_id)
            
            # DeepSeek request
            try:
                completion = client.chat.completions.create(
                    model="deepseek/deepseek-r1:free",
                    messages=chat_history[username],  
                    stream=False 
                )

                model_reply = completion.choices[0].message.content
                chat_history[username].append({
                    "role": "assistant",
                    "content": model_reply
                })
            
                send_message(chat_id, model_reply)
                delete_message(chat_id, message_with_dots['result']['message_id'])
            
            except Exception as e:
                logger.error(f"Error in chat handler: {e}")
                send_message(chat_id, "Sorry, I couldn't process your request.")

        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            send_message(chat_id, "Sorry, I couldn't process your request.")