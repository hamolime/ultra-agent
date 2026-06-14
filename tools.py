import os
import requests
import json
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

LONG_TERM_MEMORY_FILE = "long_term_memory.json"

def web_search(query: str) -> str:
    """أداة بحث مرنة ومحمية من الكراش"""
    try:
        url = f"https://text.pollinations.ai/search?q={requests.utils.quote(query)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200 and r.text:
            return f"نتائج البحث الحية عن ({query}):\n{r.text[:600]}"
        return "لم أتمكن من جلب نتائج حية، استخدم معرفتك العامة للرد."
    except Exception as e:
        print(f"Search warning: {e}")
        return "عطل مؤقت في أداة البحث، استخدم معرفتك العامة الحالية للرد."

def manage_long_term_memory(chat_id: int, action: str, key: str = None, value: str = None) -> str:
    chat_id_str = str(chat_id)
    if not os.path.exists(LONG_TERM_MEMORY_FILE):
        with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
    try:
        with open(LONG_TERM_MEMORY_FILE, "r", encoding="utf-8") as f: memory_data = json.load(f)
        if chat_id_str not in memory_data: memory_data[chat_id_str] = {}
        if action == "save" and key and value:
            memory_data[chat_id_str][key] = value
            with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f: json.dump(memory_data, f, ensure_ascii=False, indent=4)
            return f"🧠 حفظت: {key} هو {value}"
        elif action == "get":
            return json.dumps(memory_data.get(chat_id_str, {}), ensure_ascii=False)
    except Exception as e: return "{}"
    return "{}"

def voice_to_text(ogg_file_path: str) -> str:
    if not client: return "[خطأ Groq key]"
    from pydub import AudioSegment
    mp3_file_path = ogg_file_path.replace(".ogg", ".mp3")
    try:
        audio = AudioSegment.from_ogg(ogg_file_path)
        audio.export(mp3_file_path, format="mp3")
        with open(mp3_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file, model="whisper-large-v3", language="ar"
            )
        return transcription.text
    except Exception as e: return f"[فشل ترجمة الصوت: {str(e)}]"
    finally:
        if os.path.exists(ogg_file_path): 
            try: os.remove(ogg_file_path)
            except: pass
        if os.path.exists(mp3_file_path): 
            try: os.remove(mp3_file_path)
            except: pass

def text_to_voice(text_content: str) -> str:
    """دالة تحويل النص إلى صوت فائقة الاستقرار ومحمية من كراش السيرفرات"""
    output_path = "response_voice.mp3"
    try:
        clean_text = text_content.replace("*", "").replace("_", "").replace("[", "").replace("]", "")
        clean_text = clean_text[:250] # تقصير لسرعة الاستجابة
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ar-EG&client=tw-ob&q={requests.utils.quote(clean_text)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=8)
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            return output_path
    except Exception as e: 
        print(f"TTS Error: {e}")
    return ""
