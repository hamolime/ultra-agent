import os
import time
import telebot
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent import run_agent
from scheduler import schedule_a_task, load_saved_reminders

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0")) if os.environ.get("ADMIN_CHAT_ID") else None

bot = telebot.TeleBot(TELEGRAM_TOKEN)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

threading.Thread(target=lambda: HTTPServer(("0.0.0.0", 7860), DummyHandler).serve_forever(), daemon=True).start()

def send_msg(chat_id, text):
    try:
        bot.send_message(chat_id, text)
    except:
        pass

# TEXT
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
        return

    try:
        bot.send_chat_action(message.chat.id, "typing")

        answer = run_agent(message.chat.id, message.text)

        if not answer:
            answer = "مفيش رد دلوقتي"

        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

# PHOTO
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
        return

    try:
        file = bot.get_file(message.photo[-1].file_id)
        data = bot.download_file(file.file_path)
        img = base64.b64encode(data).decode()

        answer = run_agent(message.chat.id, "", is_image=True, image_data=img)

        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"Image error: {str(e)}")

# VOICE OFF (ممكن ترجعها بعدين)
if __name__ == "__main__":
    print("Bot Running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
