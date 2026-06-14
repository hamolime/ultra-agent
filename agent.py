import os
import json
from datetime import datetime
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

SYSTEM_PROMPT = """
أنت مساعد ذكي اسمه جارفيس.

قواعد مهمة:
- لو السؤال عن أسعار / أخبار / معلومات حديثة → استخدم web_search
- لا تخترع بيانات
- لو استخدمت أدوات، اعتمد عليها فقط
- لو مش متأكد قول "مش متأكد"
- ردودك تكون قصيرة وبسيطة
"""

def simple_planner(msg: str):
    msg = msg.lower()
    return {
        "search": any(x in msg for x in ["سعر", "ذهب", "دولار", "اخبار", "price", "news"]),
        "memory": "افتكر" in msg or "remember" in msg
    }

def run_agent(user_chat_id, user_message, is_image=False, image_data=None, scheduler_callback=None):
    if not client:
        return "Groq API مش شغال"

    long_mem = manage_long_term_memory(user_chat_id, "get")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {"role": "system", "content": SYSTEM_PROMPT + f"\n\nMemory:\n{long_mem}\nTime:{now}"}
        ]

    # IMAGE
    if is_image:
        try:
            res = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "اشرح الصورة ببساطة"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }],
                temperature=0.3
            )
            return res.choices[0].message.content
        except:
            return "مش قادر أفهم الصورة دلوقتي"

    chats_memory[user_chat_id].append({"role": "user", "content": user_message})

    if len(chats_memory[user_chat_id]) > 20:
        chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

    plan = simple_planner(user_message)

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_memory[user_chat_id],
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
                        "description": "حفظ معلومة",
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

        msg = completion.choices[0].message

        # TOOL HANDLING
        if msg.tool_calls:
            chats_memory[user_chat_id].append(msg)

            tool_context = []

            for call in msg.tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments or "{}")

                if name == "web_search":
                    result = web_search(args.get("query", user_message))

                elif name == "save_memory":
                    result = manage_long_term_memory(
                        user_chat_id,
                        "save",
                        key=args.get("fact", ""),
                        value="true"
                    )

                else:
                    result = "tool error"

                tool_context.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result
                })

            final = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=chats_memory[user_chat_id] + tool_context,
                temperature=0.4
            )

            answer = final.choices[0].message.content
        else:
            answer = msg.content

        chats_memory[user_chat_id].append({"role": "assistant", "content": answer})
        return answer

    except Exception as e:
        print("ERROR:", e)
        try:
            return client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3
            ).choices[0].message.content
        except:
            return "حصل مشكلة مؤقتة جرب تاني"
