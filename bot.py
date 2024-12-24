from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests, os

# Telegram Bot Token from BotFather
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# FastAPI App
app = FastAPI()

# Webhook Payload Structure
class TelegramUpdate(BaseModel):
    update_id: int
    message: dict

# Set Webhook
@app.on_event("startup")
async def set_webhook():
    webhook_url = "https://yourdomain.com/webhook"  # Replace with your domain
    webhook_endpoint = f"{TELEGRAM_API_URL}/setWebhook"
    response = requests.post(webhook_endpoint, json={"url": webhook_url})
    if response.status_code == 200:
        print("Webhook set successfully!")
    else:
        print("Failed to set webhook:", response.text)

# Webhook Endpoint
@app.post("/webhook")
async def webhook(update: TelegramUpdate):
    try:
        chat_id = update.message["chat"]["id"]
        text = update.message["text"]

        # Process Message and Send Response
        response_text = process_message(text)
        send_message(chat_id, response_text)

    except Exception as e:
        print("Error processing update:", e)

    return {"status": "ok"}

# Function to Send Message to Telegram
def send_message(chat_id, text):
    print(text)
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


# Message Processing Logic
def process_message(text):
    if text.lower() == "/start":
        return "Welcome to the FastAPI Telegram Bot!"
    elif text.lower() == "hello":
        return "Hello! How can I help you today?"
    else:
        return "I'm not sure how to respond to that. Try /start or 'hello'."
