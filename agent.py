import os
import json
from datetime import datetime
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

# تعريف الأدوات بشكل رسمي لـ Groq ليفهمها السيرفر تلقائياً
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "استخدم هذه الأداة للبحث على الإنترنت عن الأخبار الحية، الأسعار اليومية، الطقس، أو التحديثات الجديدة.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "موضوع أو جملة البحث"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "حفظ معلومة شخصية أو حقيقة عن المستخدم في الذاكرة الدائمة (مثل اسمه، عمله، اهتماماته).",
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
                    "أنت الآن مساعد ذكي خارق وخاص على تليجرام.\n"
                    "تحدث بالعامية المصرية الطبيعية بذكاء وهدوء (كأنك صديق حقيقي، بدون رسميات وبدون كتابة رموز أو تفكير داخلي للمستخدم).\n"
                    f"الذاكرة طويلة المدى للمستخدم:\n{user_long_term}\n"
                    f"توقيتك الحالي الآن: {current_time_str}\n"
                    "عندما يطلب المستخدم منبه أو تذكير (مثل: فكرني بعد ساعة)، احسب الوقت بدقة واستدعي أداة الجدولة إن وجدت، وإلا وجهه."
                )
            }
        ]

    try:
        # --- 1. التعامل الحاسم مع الصور وضمان بقائها في الذاكرة ---
        if is_image and image_data:
            vision_model = "llama-3.2-11b-vision-preview"
            vision_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": "اشرح وحلل هذه الصورة بالتفصيل وبالعامية المصرية الذكية وبدون أي كود:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]}
            ]
            completion = client.chat.completions.create(model=vision_model, messages=vision_messages, temperature=0.4)
            image_description = completion.choices[0].message.content
            
            # زرع وصف الصورة في الذاكرة النصية عشان يفتكرها في الرسايل الجاية
            chats_memory[user_chat_id].append({"role": "user", "content": "[أنا أرسلت لك صورة الآن]"})
            chats_memory[user_chat_id].append({"role": "assistant", "content": f"[أنا رأيت الصورة ووصفها الدقيق هو]: {image_description}"})
            return image_description

        # --- 2. التعامل الذكي مع النصوص والفويس نوت عبر الـ Official Tools ---
        model_name = "llama-3.3-70b-versatile"
        
        # حماية من كتابة المستخدم للأوامر اليدوية
        if "فكرني" in user_message or "جدول" in user_message or "منبه" in user_message:
            if scheduler_callback:
                # لو كلام جدولة سريع، بنخليه يروح للـ Agent يحسبه ويصيغه
                pass

        chats_memory[user_chat_id].append({"role": "user", "content": user_message})

        if len(chats_memory[user_chat_id]) > 20:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

        # طلب الرد من جروق مع تمرير الأدوات الرسمية لمنع خروج الـ JSON بره
        completion = client.chat.completions.create(
            model=model_name,
            messages=chats_memory[user_chat_id],
            tools=tools_definition,
            tool_choice="auto",
            temperature=0.4
        )
        
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        # لو جروق قرر يستدعي أداة (تفكير داخلي حقيقي مخفي عن الشات)
        if tool_calls:
            chats_memory[user_chat_id].append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_result = ""
                if function_name == "web_search":
                    query = function_args.get("query", "")
                    print(f"⚡ [Official Tool] Launching Web Search for: {query}")
                    tool_result = web_search(query)
                elif function_name == "save_memory":
                    fact = function_args.get("fact", "")
                    tool_result = manage_long_term_memory(user_chat_id, action="save", key=fact, value="true")
                
                # إرسال نتيجة الأداة المخفية لجروق ليصيغ الرد النهائي النظيف
                chats_memory[user_chat_id].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })
            
            final_completion = client.chat.completions.create(
                model=model_name,
                messages=chats_memory[user_chat_id],
                temperature=0.5
            )
            final_reply = final_completion.choices[0].message.content
            chats_memory[user_chat_id].append({"role": "assistant", "content": final_reply})
            return final_reply

        # لو رد عادي بدون أدوات
        final_reply = response_message.content
        chats_memory[user_chat_id].append({"role": "assistant", "content": final_reply})
        return final_reply

    except Exception as e:
        print(f"Error in Official Agent Logic: {e}")
        # حماية: لو حصل كراش مفاجئ بنرجع رد ذكي بدون تصفير كامل للهيستوري لو أمكن
        return "معلش يا غالي، حصلت لخبطة سريعة في السيرفر، جرب ابعتلي طلبك تاني كدا."
