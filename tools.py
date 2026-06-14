import os
import requests
import json
from groq import Groq
from datetime import datetime, timedelta

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

LONG_TERM_MEMORY_FILE = "long_term_memory.json"

# --- 1. أداة البحث الذكي المستقرة ---
def web_search(query: str) -> str:
    """البحث على الإنترنت بشكل مستقر عبر API مفتوح"""
    try:
        # استخدام API بديل ومستقر للبحث السريع
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return f"نتائج البحث عن ({query}): {abstract}"
            
            # كخطة بديلة لو مفيش ملخص
            related = data.get("RelatedTopics", [])
            if related and "Text" in related[0]:
                return f"نتائج البحث عن ({query}): {related[0]['Text']}"
        return f"لم أجد نتائج مباشرة لـ {query}، جاري الاعتماد على التحليل الذكي."
    except Exception as e:
        return f"عطل في أداة البحث: {str(e)}"

# --- 2. أداة الذاكرة طويلة المدى ---
def manage_long_term_memory(chat_id: int, action: str, key: str = None, value: str = None) -> str:
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
            return f"🧠 حفظت في الذاكرة: {key} هو {value}"
        elif action == "get":
            return json.dumps(memory_data.get(chat_id_str, {}), ensure_ascii=False)
    except Exception as e:
        return f"خطأ ذاكرة: {str(e)}"
    return "{}"

# --- 3. أداة تحويل الصوت لنص ---
def voice_to_text(ogg_file_path: str) -> str:
    if not client: return "[خطأ Groq key]"
    from pydub import AudioSegment
    mp3_file_path = ogg_file_path.replace(".ogg", ".mp3")
    try:
        audio = AudioSegment.from_ogg(ogg_file_path)
        audio.export(mp3_file_path, format="mp3")
        with open(mp3_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                language="ar"
            )
        return transcription.text
    except Exception as e:
        return f"[فشل ترجمة الصوت: {str(e)}]"
    finally:
        if os.path.exists(ogg_file_path): os.remove(ogg_file_path)
        if os.path.exists(mp3_file_path): os.remove(mp3_file_path)

# --- 4. تحسين جودة الصوت والسرعة (TTS المطور) ---
def text_to_voice(text_content: str) -> str:
    """تحويل النص إلى صوت بنبرة أفضل وأسرع"""
    output_path = "response_voice.mp3"
    try:
        # استخدام خدمة صوتية محسنة وتدعم اللهجات بشكل أسرع ونبرة طبيعية
        clean_text = text_content.replace("*", "").replace("_", "")
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ar&client=tw-ob&ttsspeed=1&q={requests.utils.quote(clean_text)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            return output_path
    except Exception as e:
        print(f"Error TTS: {e}")
    return ""
