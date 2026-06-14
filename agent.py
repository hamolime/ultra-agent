import os
import json
from datetime import datetime
from groq import Groq
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chats_memory = {}

def run_agent(user_chat_id, user_message, is_image=False, image_data=None, scheduler_callback=None):
    if not client: return "خطأ في الاتصال بـ Groq."

    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_long_term = manage_long_term_memory(user_chat_id, action="get")

    # تهيئة الذاكرة النقية بالنصوص فقط منعا لأي تضارب للموديلات
    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a smart Telegram AI Agent with a Planner layer.\n"
                    "Speak naturally, calm and intelligent. Reply in the user's slang/style.\n\n"
                    f"LONG-TERM MEMORY:\n{user_long_term}\n\n"
                    f"CURRENT TIME RIGHT NOW: {current_time_str}\n\n"
                    "TOOLS INSTRUCTIONS:\n"
                    "- To search online for updates, use 'web_search'.\n"
                    "- To remember personal facts forever, use 'save_memory'.\n"
                    "- To schedule reminders (e.g. 'فكرني بعد 5 دقايق'), calculate the exact time and use 'schedule_task' formatted EXACTLY as: task_text | YYYY-MM-DD HH:MM:SS\n"
                    "Format planning response ONLY as:\n"
                    "[THINKING: reason]\n"
                    "[TOOL: tool_name | ARGUMENT: data]\n"
                    "If no tool is needed, just answer directly."
                )
            }
        ]

    try:
        # لو المدخل صورة، هنشغل موديل الرؤية منفصل وندمج "وصفها" في الذاكرة بنص نقي!
        if is_image:
            vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
            vision_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": "Analyze and describe this image in full detail and natural Arabic language:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]}
            ]
            completion = client.chat.completions.create(model=vision_model, messages=vision_messages, temperature=0.4)
            image_description = completion.choices[0].message.content
            
            # دمج الوصف والرد في الذاكرة كنصوص نقية آمنة 100%
            chats_memory[user_chat_id].append({"role": "user", "content": "[User sent an image]"})
            chats_memory[user_chat_id].append({"role": "assistant", "content": image_description})
            return image_description

        # المدخلات النصية العادية وفويس نوتس
        model_name = "llama-3.3-70b-versatile"
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})

        if len(chats_memory[user_chat_id]) > 20:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]

        completion = client.chat.completions.create(model=model_name, messages=chats_memory[user_chat_id], temperature=0.3)
        raw_response = completion.choices[0].message.content
        print(f"\n🧠 [AGENT LOG]:\n{raw_response}\n")

        if "[TOOL:" in raw_response:
            tool_name = ""
            argument = ""
            for line in raw_response.split("\n"):
                if "[TOOL:" in line: tool_name = line.split("[TOOL:")[1].split("|")[0].strip()
                if "ARGUMENT:" in line: argument = line.split("ARGUMENT:")[1].replace("]", "").strip()

            tool_result = ""
            if tool_name == "web_search" and argument:
                tool_result = web_search(argument)
            elif tool_name == "save_memory" and argument:
                key_val = argument.split("is") if "is" in argument else [argument, "true"]
                tool_result = manage_long_term_memory(user_chat_id, action="save", key=key_val[0].strip(), value=key_val[1].strip())
            elif tool_name == "schedule_task" and argument and scheduler_callback:
                try:
                    parts = argument.split("|")
                    tool_result = scheduler_callback(parts[0].strip(), parts[1].strip())
                except Exception as e: tool_result = f"خطأ وقت الجدولة: {str(e)}"

            if tool_result:
                chats_memory[user_chat_id].append({"role": "assistant", "content": raw_response})
                chats_memory[user_chat_id].append({"role": "user", "content": f"[SYSTEM TOOL OUTPUT]: {tool_result}\nGive the final natural response now."})
                
                final_comp = client.chat.completions.create(model=model_name, messages=chats_memory[user_chat_id], temperature=0.5)
                final_response = final_comp.choices[0].message.content
                
                chats_memory[user_chat_id] = chats_memory[user_chat_id][:-2]
                chats_memory[user_chat_id].append({"role": "assistant", "content": final_response})
                return final_response

        chats_memory[user_chat_id].append({"role": "assistant", "content": raw_response})
        return raw_response

    except Exception as e:
        print(f"Error in Agent: {e}")
        # لو حصل أي تهنيج نلجأ لتصفير مؤقت للهيستوري عشان السيستم ميعلقش
        if user_chat_id in chats_memory: del chats_memory[user_chat_id]
        return "حصل دروب في الذاكرة ونظفتها، ابعتلي طلبك تاني كدا يا غالي وهتلاقيني طلقة."
