import os
import time
import telebot
import base64
import threading
from datetime import datetime
from telebot import apihelper
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent import run_agent
from scheduler import schedule_a_task, load_saved_reminders
from tools import voice_to_text, text_to_voice

apihelper.READ_TIMEOUT = 60
apihelper.CONNECT_TIMEOUT = 60

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<h1>Agent System Pro is Live!</h1>")

def run_dummy_server():
    try:
        server = HTTPServer(('0.0.0.0', 7860), DummyHandler)
        server.serve_forever()
    except Exception as e: print(f"Server error: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID_STR = os.environ.get("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR) if ADMIN_CHAT_ID_STR else None

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def send_scheduled_msg(chat_id, text):
    try: bot.send_message(chat_id, text)
    except Exception as e: print(f"Notification error: {e}")

def make_schedule_callback(chat_id):
    def callback(task_text, time_str):
        return schedule_a_task(task_text, time_str, send_notification_func=send_scheduled_msg, chat_id=chat_id)
    return callback

# --- 1. معالجة الفويس نوت الحقيقية ---
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not ADMIN_CHAT_ID or message.chat.id != ADMIN_CHAT_ID: return
    bot.send_chat_action(message.chat.id, 'record_audio')
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        ogg_path = f"voice_{message.message_id}.ogg"
        with open(ogg_path, 'wb') as f: f.write(downloaded_file)
            
        user_text = voice_to_text(ogg_path)
        if user_text.startswith("[فشل"):
            bot.reply_to(message, user_text)
            return
            
        bot.reply_to(message, f"🎤 *سمعتك:* {user_text}", parse_mode="Markdown")
        
        bot.send_chat_action(message.chat.id, 'typing')
        answer = run_agent(message.chat.id, user_text, scheduler_callback=make_schedule_callback(message.chat.id))
        
        # تشغيل الفويس غصب عنه بناء على رد الـ Agent الحقيقي
        bot.send_chat_action(message.chat.id, 'record_audio')
        voice_path = text_to_voice(answer)
        if voice_path and os.path.exists(voice_path):
            with open(voice_path, 'rb') as audio:
                bot.send_voice(message.chat.id, audio)
            os.remove(voice_path)
        else:
            bot.reply_to(message, answer)
    except Exception as e: 
        bot.reply_to(message, f"❌ خطأ سيرفر الفويس: {str(e)}")

# --- 2. معالجة الصور الحقيقية ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not ADMIN_CHAT_ID or message.chat.id != ADMIN_CHAT_ID: return
    bot.send_chat_action(message.chat.id, 'upload_document')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        answer = run_agent(message.chat.id, "", is_image=True, image_data=base64_image)
        bot.reply_to(message, answer)
    except Exception as e: 
        bot.reply_to(message, f"❌ خطأ سيرفر الصور: {str(e)}")

# --- 3. معالجة النصوص الحقيقية ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not ADMIN_CHAT_ID or message.chat.id != ADMIN_CHAT_ID: return
    bot.send_chat_action(message.chat.id, 'typing')
    
    answer = run_agent(message.chat.id, message.text, scheduler_callback=make_schedule_callback(message.chat.id))
    bot.reply_to(message, answer)

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        print("🤖 تم تطهير البوت والـ Agent الحديدي جاهز...")
        if ADMIN_CHAT_ID:
            threading.Thread(target=load_saved_reminders, args=(send_scheduled_msg, ADMIN_CHAT_ID), daemon=True).start()
        while True:
            try: bot.infinity_polling(timeout=40, long_polling_timeout=20)
            except: time.sleep(5)
