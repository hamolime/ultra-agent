import os
import requests
from groq import Groq

# قراءة المفتاح بأمان
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# قاموس لحفظ ذاكرة المحادثة لكل مستخدم (عشان مينساش)
chats_memory = {}

def run_agent(user_chat_id, user_message, is_image=False, image_data=None):
    """تشغيل الـ Agent بذاكرة متكاملة ودعم كامل للصور والنصوص"""
    if not GROQ_API_KEY:
        return "خطأ: لم يتم العثور على GROQ_API_KEY في إعدادات الأمان."

    client = Groq(api_key=GROQ_API_KEY)
    
    # تهيئة الذاكرة للمستخدم لو مش موجودة
    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {"role": "system", "content": "أنت مساعد شخصي ذكي جداً وصاحب صاحبه، تتحدث باللغة العربية وبلهجة مصرية ودودة جداً ودمك خفيف وچدع. لديك ذاكرة قوية جداً وتتذكر ما قيل في المحادثة، وتستطيع فهم طلبات الجدولة والتذكير ذكياً وتحليل الصور بدقة."}
        ]

    if is_image:
        # 👁️ الموديل الرسمي الجديد (Llama 4) لتحليل الصور في Groq
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "اشرحلي الصورة دي بالتفصيل وبالعربي وبذكاء مصري چدع:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    else:
        # 📝 الموديل المستقر المعتمد للنصوص
        model_name = "llama-3.3-70b-versatile"
        
        # إضافة رسالة المستخدم الحالية للذاكرة
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})
        
        # حماية الذاكرة عشان متكبرش وتضرب ليميت
        if len(chats_memory[user_chat_id]) > 16:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-15:]
            
        messages = chats_memory[user_chat_id]

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
        )
        
        response_text = completion.choices[0].message.content
        
        # حفظ رد البوت في الذاكرة لو كانت محادثة نصية
        if not is_image:
            chats_memory[user_chat_id].append({"role": "assistant", "content": response_text})
            
        return response_text
        
    except Exception as e:
        # خطة بديلة سريعة لو الموديل الكبير مهنج
        try:
            fallback_model = "meta-llama/llama-4-scout-17b-16e-instruct" if is_image else "llama3-8b-8192"
            completion = client.chat.completions.create(
                model=fallback_model,
                messages=messages,
                temperature=0.7,
            )
            return completion.choices[0].message.content
        except:
            return f"حدث خطأ أثناء معالجة الطلب في Groq: {str(e)}"
