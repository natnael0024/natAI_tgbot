from datetime import date
import telebot
import google.generativeai as genai
import logging
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")
SI = os.getenv('SI')
MAX_HISTORY_SIZE = 5

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "candidate_count": 1,
    "temperature": 0.9,
    "top_p":1,
    "top_k":1,
    "max_output_tokens":10
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
    generation_config=generation_config,
    safety_settings=safety_settings
    )


bot = telebot.TeleBot(TELEGRAM_BOT_API_KEY)

# function to connect to db
def connect_to_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# function to add a user to db
def add_visitor_to_db(username):
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        # Insert the username into the database if not already present
        cursor.execute("""
            INSERT INTO telegrambot_visitors (username)
            VALUES (%s)
            ON CONFLICT (username) DO NOTHING;
        """, (username,))

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cursor.close()
        conn.close()

        logger.info(f"User {username} added to database.")

    except Exception as e:
        logger.error(f"Error while adding user {username} to database: {e}")

# /start command handler
@bot.message_handler(commands=['start'])
def start(message):
    # Send a welcome message to the user
    try:
      bot.send_photo(message.chat.id, photo='https://nataichat.onrender.com/natAi-logo-nobg.png', caption="Welcome to Naty's AI bot aka natAI")
    except Exception as e:
      logger.error(f"{date.now()} Error in /start handler: {e}")
      bot.send_message(message.chat.id, "Sorry, something went wrong!")

chat_history = {}

# chat function
@bot.message_handler(func=lambda message: True)
def chatt(message):
    try:
      username = message.from_user.username
      add_visitor_to_db(username)
      if username not in chat_history:
         chat_history[username] = []
      if len(chat_history[username]) > MAX_HISTORY_SIZE:
        chat_history[username].pop(0)

      chat_history[username].append({
        "role": "user",
        "parts": [{"text": message.text}]
        })
      
      formatted_history = [
        {
            "role": entry["role"],
            "parts": entry["parts"]
        }
        for entry in chat_history[username]
      ]

      chat = chat_model.start_chat(history=formatted_history)

      message_with_dots = bot.send_message(message.chat.id,"typing..." )
      response = chat.send_message(message.text)
      chat_history[username].append({
        "role": "model",
        "parts": [{"text": message.text}]
        })
      logger.info(f"user({username}): {message.text}")
      logger.info(f"natAI: {response.text}")
      bot.send_message(message.chat.id, response.text)
      bot.delete_message(message_with_dots.chat.id, message_with_dots.message_id)
      
    except Exception as e:
        logger.error(f"Error in chatt handler: {e}")
        bot.send_message(message.chat.id, "Sorry, I couldn't process your request.")

# Start polling
try:
    bot.polling()
except Exception as e:
    logger.error(f"Error starting bot polling: {e}")