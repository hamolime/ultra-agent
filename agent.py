import os
import requests
from groq import Groq

# قراءة المفتاح بأمان
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# قاموس لحفظ ذاكرة المحادثة لكل مستخدم
chats_memory = {}

def run_agent(user_chat_id, user_message, is_image=False, image_data=None):
    """تشغيل الـ Agent بشخصيتك المفضلة الموزونة ودعم الذاكرة والصور"""
    if not GROQ_API_KEY:
        return "خطأ: لم يتم العثور على GROQ_API_KEY في إعدادات الأمان."

    client = Groq(api_key=GROQ_API_KEY)
    
    # تهيئة الشخصية المفضلة بالمللي جوه الذاكرة
    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a smart and natural Telegram AI.\n\n"
                    "- Speak naturally like a real person.\n"
                    "- Understand Arabic, English, Egyptian Franco, Egyptian Arabic slang, mixed Arabic and English, Typos and misspelled words.\n"
                    "- Reply in the same language and style as the user.\n"
                    "- Be helpful, calm, and intelligent.\n"
                    "- Don't be too formal.\n"
                    "- Don't act like a best friend.\n"
                    "- Don't act robotic or academic.\n"
                    "- Keep replies natural and realistic.\n"
                    "- If the user jokes, joke lightly.\n"
                    "- If the user is serious, be serious.\n"
                    "- Keep most replies short unless explanation is needed.\n"
                    "Always try to infer the user's intent even if the message has spelling mistakes or messy typing."
                )
            }
        ]

    if is_image:
        # موديل الصور الشغال والمستقر عندك
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze and explain this image naturally and intelligently:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    else:
        # موديل النصوص المستقر
        model_name = "llama-3.3-70b-versatile"
        
        # إضافة رسالة المستخدم للذاكرة
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})
        
        # حماية الذاكرة من التضخم
        if len(chats_memory[user_chat_id]) > 16:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-15:]
            
        messages = chats_memory[user_chat_id]

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.6, # تقليل الـ temperature يخليه هادي وذكي وموزون وميألفش
        )
        
        response_text = completion.choices[0].message.content
        
        # حفظ الرد في الذاكرة
        if not is_image:
            chats_memory[user_chat_id].append({"role": "assistant", "content": response_text})
            
        return response_text
        
    except Exception as e:
        try:
            fallback_model = "meta-llama/llama-4-scout-17b-16e-instruct" if is_image else "llama3-8b-8192"
            completion = client.chat.completions.create(
                model=fallback_model,
                messages=messages,
                temperature=0.6,
            )
            return completion.choices[0].message.content
        except:
            return f"حدث خطأ أثناء معالجة الطلب في Groq: {str(e)}"
