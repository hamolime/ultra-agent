import os
import time 
import telebot
import base64
import threading  
from telebot import apihelper
from http.server import BaseHTTPRequestHandler, HTTPServer

# استدعاء الملفات الخاصة بك كما هي تماماً
from agent import run_agent
from scheduler import schedule_a_task, load_saved_reminders

# ضبط وقت الانتظار لخوادم تليجرام فوراً لمنع الـ Timeout
apihelper.READ_TIMEOUT = 60
apihelper.CONNECT_TIMEOUT = 60

# إنشاء واجهة وهمية عشان Hugging Face يقلب Running
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<h1>Bot is Running Perfectly!</h1>")

def run_dummy_server():
    try:
        server = HTTPServer(('0.0.0.0', 7860), DummyHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Error in dummy server: {e}")

# تشغيل الواجهة الوهمية في الخلفية
threading.Thread(target=run_dummy_server, daemon=True).start()

# قراءة التوكن والمعرف من الـ Secrets (يدعم الاسمين للتأكيد)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID_STR = os.environ.get("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR) if ADMIN_CHAT_ID_STR else None

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def send_scheduled_msg(chat_id, text):
    """إرسال التذكير المتجدول"""
    try:
        bot.send_message(chat_id, text)
    except Exception as e:
        print(f"Error sending scheduled message: {e}")

# التعامل مع الصور وتحليلها بعقل Groq Vision
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not ADMIN_CHAT_ID or message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "🔐 عذراً، أنا مساعد شخصي مقفل لصاحب البوت فقط.")
        return

    bot.send_chat_action(message.chat.id, 'upload_document')
    bot.reply_to(message, "⚡ جاري سحب الصورة وتحليلها بعقل Groq الخارق لـ Vision...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        answer = run_agent("", is_image=True, image_data=base64_image)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"❌ حصلت مشكلة أثناء معالجة الصورة: {str(e)}")

# التعامل مع النصوص والجدولة والدردشة العادية
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not ADMIN_CHAT_ID or message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "🔐 عذراً، أنا مساعد شخصي مقفل لصاحب البوت فقط.")
        return

    user_input = message.text

    # نظام الجدولة الفوري
    if user_input.startswith("جدول:"):
        try:
            parts = user_input.replace("جدول:", "").split("|")
            task = parts[0].strip()
            time_str = parts[1].strip()
            
            res = schedule_a_task(task, time_str, send_notification_func=send_scheduled_msg, chat_id=message.chat.id)
            bot.reply_to(message, res)
            return
        except:
            bot.reply_to(message, "⚠️ اكتبها بالفورمات ده يا ريس:\n\nجدول: اسم المهمة | YYYY-MM-DD HH:MM:SS\n\nمثال:\nجدول: ميعاد الدوا | 2026-06-15 21:00:00")
            return

    # الرد العادي والذكاء الاصطناعي
    bot.send_chat_action(message.chat.id, 'typing')
    answer = run_agent(user_input)
    bot.reply_to(message, answer)

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("CRITICAL ERROR: TELEGRAM_TOKEN environment variable not set!")
    else:
        print("🤖 الـ Agent الخارق شغال بنجاح ومستنيك على تليجرام...")
        
        # تشغيل المنبهات والمواعيد القديمة في الخلفية بأمان تام
        if ADMIN_CHAT_ID:
            threading.Thread(
                target=load_saved_reminders, 
                args=(send_scheduled_msg, ADMIN_CHAT_ID), 
                daemon=True
            ).start()
            
        # تشغيل استقبال الرسائل بلوبر حماية ضد الـ Timeout
        while True:
            try:
                print("🔄 جاري الاتصال بخوادم تليجرام...")
                bot.infinity_polling(timeout=40, long_polling_timeout=20)
            except Exception as e:
                print(f"⚠️ حصل هزة في الشبكة ({e})، هجرب تاني كمان 5 ثواني...")
                time.sleep(5)
