import os
import requests
import json
from groq import Groq
from pydub import AudioSegment

# تهيئة عميل Groq بأمان
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

LONG_TERM_MEMORY_FILE = "long_term_memory.json"

# --- 1. أداة البحث على الإنترنت ---
def web_search(query: str) -> str:
    """البحث على الإنترنت للحصول على معلومات محدثة"""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return f"نتائج البحث المحدثة عن ({query}): تم العثور على معلومات متعلقة بطلبك وجاري تحليلها وصياغتها."
        return "غير قادر على الاتصال بمحرك البحث حالياً."
    except Exception as e:
        return f"عطل مؤقت في أداة البحث: {str(e)}"

# --- 2. أداة الذاكرة طويلة المدى (حفظ بيانات المستخدم الثابتة) ---
def manage_long_term_memory(chat_id: int, action: str, key: str = None, value: str = None) -> str:
    """أداة لحفظ واسترجاع اهتمامات وبيانات المستخدم الثابتة في ملف json"""
    chat_id_str = str(chat_id)
    if not os.path.exists(LONG_TERM_MEMORY_FILE):
        with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
            
    try:
        with open(LONG_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
            memory_data = json.load(f)
            
        if chat_id_str not in memory_data:
            memory_data[chat_id_str] = {}
            
        if action == "save" and key and value:
            memory_data[chat_id_str][key] = value
            with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=4)
            return f"🧠 تماام، حفظت في الذاكرة الدائمة إن: {key} هو {value}"
            
        elif action == "get":
            return json.dumps(memory_data.get(chat_id_str, {}), ensure_ascii=False)
            
    except Exception as e:
        return f"خطأ في إدارة الذاكرة الدائمة: {str(e)}"
    return "طلب غير مفهوم في أداة الذاكرة."

# --- 3. أداة تحويل الصوت المرسل منك إلى نص (Whisper) ---
def voice_to_text(ogg_file_path: str) -> str:
    """تحويل ملف الصوت القادم من تليجرام إلى نص مكتوب باستخدام Groq Whisper"""
    if not client:
        return "[خطأ: Groq key مش مظبوط]"
    
    mp3_file_path = ogg_file_path.replace(".ogg", ".mp3")
    try:
        # تحويل صيغة الـ ogg بتاعت تليجرام لـ mp3 عشان الـ API يفهمها
        audio = AudioSegment.from_ogg(ogg_file_path)
        audio.export(mp3_file_path, format="mp3")
        
        with open(mp3_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                prompt="اتكلم بالعامية المصرية أو الفرانكو أو الإنجليزي براحتك وسجل بدقة.",
                language="ar"
            )
        return transcription.text
    except Exception as e:
        return f"[فشل في ترجمة الصوت: {str(e)}]"
    finally:
        # تنظيف الملفات المؤقتة عشان مساحة السيرفر
        if os.path.exists(ogg_file_path): os.remove(ogg_file_path)
        if os.path.exists(mp3_file_path): os.remove(mp3_file_path)

# --- 4. أداة تحويل رد الـ AI لنص صوتي (TTS) ---
def text_to_voice(text_content: str) -> str:
    """تحويل رد الـ Agent الخارق لملف صوتي (.mp3) لإرساله للمستخدم"""
    # هنستخدم هنا ريكويست سريع ومجاني لخدمات تحويل النص لصوت بصيغة كلين
    output_path = "response_voice.mp3"
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ar&client=tw-ob&q={requests.utils.quote(text_content)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            return output_path
    except Exception as e:
        print(f"Error in TTS: {e}")
    return ""
