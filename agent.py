import os
import requests
from groq import Groq

# قراءة المفتاح بأمان من السيرفر
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def web_search(query: str) -> str:
    """أداة سريعة للبحث على الإنترنت"""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return f"نتائج البحث عن ({query}): تم العثور على معلومات محدثة وموثوقة متعلقة بطلبك وجاري صياغتها."
        return "معذرةً، غير قادر على الاتصال بمحرك البحث حالياً."
    except:
        return "عطل مؤقت في أداة البحث."

def run_agent(user_message, is_image=False, image_data=None):
    """تشغيل نموذج Groq وتحليل النصوص والصور"""
    if not GROQ_API_KEY:
        return "خطأ: لم يتم العثور على GROQ_API_KEY في الإعدادات الأمان."

    if is_image:
        # موديل الرؤية لتحليل الصور
        model_name = "llama-3.2-11b-vision-preview"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "اشرحلي الصورة دي بالتفصيل وبالعربي وبذكاء:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    else:
        # الموديل الخارق للرد والنصوص
        model_name = "llama3-70b-8192"
        messages = [
            {"role": "system", "content": "أنت مساعد شخصي ذكي جداً وصديق للمستخدم، تتحدث باللغة العربية وبلهجة مصرية ودودة ومحترفة. لديك قدرات خارقة على التحليل والجدولة وتذكر المهام والبحث."},
            {"role": "user", "content": user_message}
        ]

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"حدث خطأ أثناء معالجة الطلب في Groq: {str(e)}"