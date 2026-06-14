import os
import json
from datetime import datetime, timedelta
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

def run_agent(user_chat_id, user_message, is_image=False, image_data=None, scheduler_callback=None):
    if not client:
        return "خطأ في الاتصال بـ Groq."

    # حساب الوقت الحالي بالسيرفر لمساعدة البوت في الجدولة التلقائية
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_long_term = manage_long_term_memory(user_chat_id, action="get")

    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a smart Telegram AI Agent with a Planner layer.\n\n"
                    "STYLE:\n"
                    "- Speak naturally, calm and intelligent. Don't be formal, robotic, or overly friendly.\n"
                    "- Understand Arabic, Franco, and slang. Reply in the user's style.\n"
                    "- Keep answers concise unless detailed info is requested.\n\n"
                    f"LONG-TERM MEMORY:\n{user_long_term}\n\n"
                    f"CURRENT TIME RIGHT NOW: {current_time_str}\n\n"
                    "TOOLS INSTRUCTIONS:\n"
                    "Analyze if you need to use a tool before answering:\n"
                    "- To search online (news, weather, latest updates), use 'web_search'.\n"
                    "- To remember a personal fact forever, use 'save_memory'.\n"
                    "- To schedule a reminder (e.g., 'فكرني بعد 5 دقايق اغسل العربية'), calculate the target time based on CURRENT TIME, and use 'schedule_task'.\n\n"
                    "Format your planning response ONLY like this if a tool is needed:\n"
                    "[THINKING: reason]\n"
                    "[TOOL: tool_name | ARGUMENT: argument_data]\n"
                    "If 'schedule_task' is selected, the ARGUMENT must be exactly: task_text | YYYY-MM-DD HH:MM:SS\n"
                    "If no tool is needed, just reply directly."
                )
            }
        ]

    # دمج الصور وردودها في الذاكرة الموحدة لمنع النسيان
    if is_image:
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
        # صياغة محتوى الصورة ليدخل الشات هيستوري بشكل طبيعي
        image_content = [
            {"type": "text", "text": "Analyze and remember this image carefully:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
        chats_memory[user_chat_id].append({"role": "user", "content": image_content})
    else:
        model_name = "llama-3.3-70b-versatile"
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})

    # حماية حجم الذاكرة
    if len(chats_memory[user_chat_id]) > 20:
        chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=chats_memory[user_chat_id],
            temperature=0.3,
        )
        raw_response = completion.choices[0].message.content
        print(f"\n🧠 [AGENT LOG]:\n{raw_response}\n")

        if "[TOOL:" in raw_response:
            tool_name = ""
            argument = ""
            for line in raw_response.split("\n"):
                if "[TOOL:" in line:
                    tool_name = line.split("[TOOL:")[1].split("|")[0].strip()
                if "ARGUMENT:" in line:
                    argument = line.split("ARGUMENT:")[1].replace("]", "").strip()

            tool_result = ""
            if tool_name == "web_search" and argument:
                tool_result = web_search(argument)
            elif tool_name == "save_memory" and argument:
                key_val = argument.split("is") if "is" in argument else [argument, "true"]
                tool_result = manage_long_term_memory(user_chat_id, action="save", key=key_val[0].strip(), value=key_val[1].strip())
            elif tool_name == "schedule_task" and argument and scheduler_callback:
                try:
                    parts = argument.split("|")
                    task_text = parts[0].strip()
                    time_str = parts[1].strip()
                    # استدعاء دالة الجدولة عبر البوت
                    tool_result = scheduler_callback(task_text, time_str)
                except Exception as e:
                    tool_result = f"فشل تنسيق وقت الجدولة: {str(e)}"

            if tool_result:
                # إرجاع نتيجة الأداة لعقل الموديل ليصيغ الرد النهائي ويحفظه بالذاكرة
                chats_memory[user_chat_id].append({"role": "assistant", "content": raw_response})
                chats_memory[user_chat_id].append({"role": "user", "content": f"[SYSTEM TOOL OUTPUT]: {tool_result}\nGive the final natural response now."})
                
                final_comp = client.chat.completions.create(
                    model=model_name,
                    messages=chats_memory[user_chat_id],
                    temperature=0.5,
                )
                final_response = final_comp.choices[0].message.content
                
                # استبدال آخر رسائل المساعد بالرد النهائي النظيف لتنظيف الهيستوري
                chats_memory[user_chat_id] = chats_memory[user_chat_id][:-2]
                chats_memory[user_chat_id].append({"role": "assistant", "content": final_response})
                return final_response

        # حفظ الرد العادي في الذاكرة الموحدة (نصوص أو صور)
        chats_memory[user_chat_id].append({"role": "assistant", "content": raw_response})
        return raw_response

    except Exception as e:
        print(f"Error in Agent: {e}")
        return "حصلت لخبطة بسيطة في عقلي، ابعتلي تاني كدا."
