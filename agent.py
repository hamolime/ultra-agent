import os
import json
from datetime import datetime
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

# 🧠 SMART SYSTEM PROMPT (Brain Rules)
SYSTEM_PROMPT = """
أنت مساعد ذكي اسمه جارفيس.

قبل أي رد اتبع القواعد دي بدقة:

1- لو السؤال عن أسعار / أخبار / معلومات حديثة → استخدم web_search
2- لو المستخدم طلب تخزين معلومة → استخدم save_memory
3- لو في صورة → تعامل معها بصريًا فقط
4- لو مش محتاج أدوات → جاوب مباشرة
5- حاول تفكر قبل الرد خطوة خطوة داخليًا

أسلوبك:
- عامية مصرية بسيطة
- ذكي لكن مش رسمي زيادة
- إجابات قصيرة إلا لو مطلوب شرح
"""

def simple_planner(user_message: str):
    """🧠 مرحلة التخطيط البسيطة"""
    msg = user_message.lower()

    return {
        "need_search": any(k in msg for k in ["سعر", "اخبار", "الذهب", "الدولار", "price", "news"]),
        "need_memory": "افتكر" in msg or "remember" in msg,
        "need_general": True
    }


def run_agent(user_chat_id, user_message, is_image=False, image_data=None, scheduler_callback=None):
    if not client:
        return "خطأ في Groq API"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🔵 LONG TERM MEMORY
    user_long_term = manage_long_term_memory(user_chat_id, action="get")

    # 🧠 INIT MEMORY
    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + f"\n\nالذاكرة:\n{user_long_term}\nالوقت: {current_time}"
            }
        ]

    # 📌 IMAGE HANDLING
    if is_image and image_data:
        vision_model = "llama-3.2-11b-vision-preview"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "اشرح الصورة دي بالعربي العامي بشكل بسيط"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]

        try:
            res = client.chat.completions.create(
                model=vision_model,
                messages=messages,
                temperature=0.3
            )
            answer = res.choices[0].message.content

            chats_memory[user_chat_id].append({"role": "assistant", "content": answer})
            return answer

        except:
            return "مش قادر أحلل الصورة دلوقتي حاول تاني"

    # 🧠 ADD USER MESSAGE
    chats_memory[user_chat_id].append({"role": "user", "content": user_message})

    # 🔥 LIMIT MEMORY
    if len(chats_memory[user_chat_id]) > 20:
        chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

    # 🧠 PLANNER STEP
    plan = simple_planner(user_message)

    # 🧠 TOOL-AWARE PROMPT
    tool_hint = f"""
خطة التنفيذ:
{json.dumps(plan, ensure_ascii=False)}

استخدم الأدوات عند الحاجة فقط.
"""

    messages = chats_memory[user_chat_id] + [
        {"role": "system", "content": tool_hint}
    ]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "بحث على الإنترنت",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "save_memory",
                        "description": "حفظ معلومة عن المستخدم",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fact": {"type": "string"}
                            },
                            "required": ["fact"]
                        }
                    }
                }
            ],
            tool_choice="auto",
            temperature=0.4
        )

        response = completion.choices[0].message
        tool_calls = response.tool_calls

        # 🔧 TOOL EXECUTION
        if tool_calls:
            chats_memory[user_chat_id].append(response)

            for tool_call in tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")

                if name == "web_search":
                    result = web_search(args.get("query", user_message))

                elif name == "save_memory":
                    result = manage_long_term_memory(
                        user_chat_id,
                        action="save",
                        key=args.get("fact", ""),
                        value="true"
                    )

                else:
                    result = "unknown tool"

                chats_memory[user_chat_id].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": result
                })

            final = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=chats_memory[user_chat_id],
                temperature=0.4
            )

            answer = final.choices[0].message.content

        else:
            answer = response.content

        chats_memory[user_chat_id].append({"role": "assistant", "content": answer})
        return answer

    except Exception as e:
        try:
            fallback = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": user_message}],
                temperature=0.4
            )
            return fallback.choices[0].message.content
        except:
            return "حصل ضغط في السيرفر حاول تاني"
