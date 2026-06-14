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

    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a smart Telegram AI Agent System with an internal JSON Planner layer.\n"
                    "Speak naturally in Egyptian Arabic slang. Be calm and intelligent.\n\n"
                    f"LONG-TERM MEMORY:\n{user_long_term}\n\n"
                    f"CURRENT TIME: {current_time_str}\n\n"
                    "CRITICAL INSTRUCTION:\n"
                    "You must respond ONLY in a valid JSON format with three keys: 'thinking', 'tool_name', and 'argument'.\n"
                    "Available tools:\n"
                    "- 'web_search': For updates, news, or current live prices (argument is the search query).\n"
                    "- 'save_memory': To save personal user facts forever (argument is the fact).\n"
                    "- 'schedule_task': To set reminders (argument is exactly: task_text | YYYY-MM-DD HH:MM:SS).\n"
                    "- 'none': If no tool is needed and you want to reply directly (put your natural response in the 'thinking' key).\n\n"
                    "Example response format if a tool is needed:\n"
                    "{\n  \"thinking\": \"I need to search for gold prices\",\n  \"tool_name\": \"web_search\",\n  \"argument\": \"سعر الذهب اليوم في مصر\"\n}\n"
                    "Example response if no tool is needed:\n"
                    "{\n  \"thinking\": \"يا هلا بيك يا ريس، منورني النهاردة!\",\n  \"tool_name\": \"none\",\n  \"argument\": \"\"\n}"
                )
            }
        ]

    try:
        # --- 1. نظام الرؤية والتذكر الحديدي للصور ---
        if is_image and image_data:
            vision_model = "llama-3.2-11b-vision-preview"
            vision_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": "اشرح وحلل هذه الصورة بالتفصيل وبالعامية المصرية الذكية:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]}
            ]
            completion = client.chat.completions.create(model=vision_model, messages=vision_messages, temperature=0.4)
            image_description = completion.choices[0].message.content
            
            # زرع الوصف في الذاكرة الموحدة كـ "سياق نصي دائم ومؤكد" عشان يفتكره علطول
            chats_memory[user_chat_id].append({"role": "user", "content": "[المستخدم أرسل صورة ليتم تحليلها وتذكرها]"})
            chats_memory[user_chat_id].append({"role": "assistant", "content": f"[أنا شفت الصورة دي وشرحها هو]: {image_description}"})
            return image_description

        # --- 2. نظام النصوص والفويس نوت مع الـ JSON Planner ---
        model_name = "llama-3.3-70b-versatile"
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})

        if len(chats_memory[user_chat_id]) > 25:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-22:]

        # إجبار الموديل على الرد بصيغة JSON نظيفة لمنع التداخل والتفكير الخارجي
        completion = client.chat.completions.create(
            model=model_name, 
            messages=chats_memory[user_chat_id], 
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        plan = json.loads(completion.choices[0].message.content)
        print(f"\n🧠 [INTERNAL JSON PLANNER]:\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n")

        tool_name = plan.get("tool_name", "none")
        argument = plan.get("argument", "")
        direct_reply = plan.get("thinking", "حصلت لخبطة بسيطة.")

        if tool_name != "none" and argument:
            tool_result = ""
            if tool_name == "web_search":
                tool_result = web_search(argument)
            elif tool_name == "save_memory":
                key_val = argument.split("is") if "is" in argument else [argument, "true"]
                tool_result = manage_long_term_memory(user_chat_id, action="save", key=key_val[0].strip(), value=key_val[1].strip())
            elif tool_name == "schedule_task" and scheduler_callback:
                try:
                    parts = argument.split("|")
                    tool_result = scheduler_callback(parts[0].strip(), parts[1].strip())
                except: tool_result = "فشلت الجدولة التلقائية."

            if tool_result:
                # تغذية الموديل بالنتيجة ليصيغ الرد النهائي الطبيعي للشات
                chats_memory[user_chat_id].append({"role": "assistant", "content": f"[System]: Tool {tool_name} output: {tool_result}"})
                chats_memory[user_chat_id].append({"role": "user", "content": "بناءً على نتيجة الأداة السابقة، اكتب الرد النهائي الطبيعي للمستخدم بالعامية وبدون أي صيغ أو كود."})
                
                final_comp = client.chat.completions.create(model=model_name, messages=chats_memory[user_chat_id], temperature=0.5)
                final_response = final_comp.choices[0].message.content
                
                # تنظيف الذاكرة والاحتفاظ بالرد النهائي الصافي فقط
                chats_memory[user_chat_id] = chats_memory[user_chat_id][:-2]
                chats_memory[user_chat_id].append({"role": "assistant", "content": final_response})
                return final_response

        # لو الرد مباشر بدون أدوات، بناخد النص الصافي من خانة الـ thinking
        chats_memory[user_chat_id].append({"role": "assistant", "content": direct_reply})
        return direct_reply

    except Exception as e:
        print(f"Error in Agent Logic: {e}")
        # تصفير أمان عند الكراش المفاجئ
        if user_chat_id in chats_memory: del chats_memory[user_chat_id]
        return "عقلي هنج ثانية ونظفت الذاكرة، ابعتلي طلبك تاني كدا يا غالي."
