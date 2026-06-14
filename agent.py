import os
import json
from datetime import datetime
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "ابحث على الإنترنت عن الأخبار الحية، الأسعار اليومية (مثل سعر الذهب أو العربيات)، أو التحديثات الجديدة.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "جملة البحث الصافية"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "حفظ حقيقة مهمة عن المستخدم في الذاكرة الدائمة.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "المعلومة المراد حفظها"}
                },
                "required": ["fact"]
            }
        }
    }
]

def run_agent(user_chat_id, user_message, is_image=False, image_data=None, scheduler_callback=None):
    if not client: return "خطأ في الاتصال بـ Groq."

    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_long_term = manage_long_term_memory(user_chat_id, action="get")

    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "أنت الآن جارفيس: مساعد ذكي خارق على تليجرام.\n"
                    "تحدث بالعامية المصرية الطبيعية كأنك صديق حقيقي وبدون رسميات.\n"
                    f"الذاكرة طويلة المدى:\n{user_long_term}\n"
                    f"التوقيت الحالي: {current_time_str}"
                )
            }
        ]

    try:
        # --- 1. معالجة الصور وضمان الحفظ في السياق النصي ---
        if is_image and image_data:
            vision_model = "llama-3.2-11b-vision-preview"
            vision_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": "اشرح هذه الصورة بالتفصيل وبالعامية المصرية وبدون أي كود:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]}
            ]
            completion = client.chat.completions.create(model=vision_model, messages=vision_messages, temperature=0.4)
            image_description = completion.choices[0].message.content
            
            chats_memory[user_chat_id].append({"role": "user", "content": "[أرسلت لك صورة]"})
            chats_memory[user_chat_id].append({"role": "assistant", "content": f"[أنا رأيت الصورة ووصفها هو]: {image_description}"})
            return image_description

        # --- 2. معالجة النصوص والفويس نوت ---
        model_name = "llama-3.3-70b-versatile"
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})

        if len(chats_memory[user_chat_id]) > 20:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

        completion = client.chat.completions.create(
            model=model_name,
            messages=chats_memory[user_chat_id],
            tools=tools_definition,
            tool_choice="auto",
            temperature=0.4
        )
        
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            chats_memory[user_chat_id].append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except:
                    function_args = {}
                
                tool_result = ""
                if function_name == "web_search":
                    query = function_args.get("query", argument if 'argument' in locals() else user_message)
                    tool_result = web_search(query)
                elif function_name == "save_memory":
                    fact = function_args.get("fact", "")
                    tool_result = manage_long_term_memory(user_chat_id, action="save", key=fact, value="true")
                
                if not tool_result: 
                    tool_result = "فشل تشغيل الأداة، جاوب من المعرفة العامة."

                chats_memory[user_chat_id].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })
            
            final_completion = client.chat.completions.create(
                model=model_name,
                messages=chats_memory[user_chat_id],
                temperature=0.4
            )
            final_reply = final_completion.choices[0].message.content
            chats_memory[user_chat_id].append({"role": "assistant", "content": final_reply})
            return final_reply

        final_reply = response_message.content
        chats_memory[user_chat_id].append({"role": "assistant", "content": final_reply})
        return final_reply

    except Exception as e:
        print(f"Error caught and bypassed: {e}")
        # خطة بديلة فورية (Fallback) عشان البوت ميسكتش أبداً لو الأدوات علقت
        try:
            fallback_comp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"رد باختصار وعامية مصرية على: {user_message}"}],
                temperature=0.4
            )
            return fallback_comp.choices[0].message.content
        except:
            return "السيرفر مضغوط ثواني يا غالي، جرب تبعت رسالتك تاني وهرد فوراً."
