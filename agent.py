import os
import json
from groq import Groq
# استيراد العضلات والأدوات اللي عملناها
from tools import web_search, manage_long_term_memory

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ذاكرة الجلسة الحالية (Short-term memory)
chats_memory = {}

def run_agent(user_chat_id, user_message, is_image=False, image_data=None):
    """
    عقل الـ Agent والـ Planner (Decision Layer):
    بياخد الرسالة، يحللها، يقرر الأداة المناسبة، ينفذها، ويسجل تفكيره.
    """
    if not client:
        return "خطأ: لم يتم العثور على GROQ_API_KEY في إعدادات الأمان."

    user_chat_id_str = str(user_chat_id)

    # 1. استدعاء الذاكرة طويلة المدى عشان الـ AI يعرف هو بيكلم مين (اسمك، اهتماماتك)
    user_long_term = manage_long_term_memory(user_chat_id, action="get")

    # 2. تهيئة الذاكرة قصيرة المدى للشات الحالي لو مش موجودة
    if user_chat_id not in chats_memory:
        chats_memory[user_chat_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a smart and natural Telegram AI Agent System with a built-in Planner layer.\n\n"
                    f"PERSONALITY & STYLE:\n"
                    "- Speak naturally like a real person.\n"
                    "- Understand Arabic, English, Egyptian Franco, Egyptian Arabic slang, mixed Arabic and English, Typos, and misspelled words.\n"
                    "- Reply in the same language and style as the user.\n"
                    "- Be helpful, calm, and intelligent.\n"
                    "- Don't be too formal. Don't act like a best friend. Don't act robotic or academic.\n"
                    "- Keep most replies short unless a detailed explanation or tool output is needed.\n"
                    "Always infer the user's intent even with messy typing.\n\n"
                    f"LONG-TERM MEMORY (Facts about this user):\n"
                    f"{user_long_term}\n\n"
                    "DECISION MAKING & TOOLS INSTRUCTIONS:\n"
                    "Before answering, analyze if you need to use a tool:\n"
                    "- If the user asks about current info, weather, news, or tech info, use 'web_search'.\n"
                    "- If the user tells you a personal fact to remember for later (e.g., 'I love Python', 'My name is Ahmed'), use 'save_memory'.\n"
                    "To use a tool, respond ONLY in this format for planning:\n"
                    "[THINKING: Reason why you need the tool]\n"
                    "[TOOL: tool_name | ARGUMENT: your_search_query_or_memory_data]\n"
                    "If no tool is needed, just answer the user directly in your natural style."
                )
            }
        ]

    # تجهيز الموديل المناسب حسب نوع الدخل
    if is_image:
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages = [
            chats_memory[user_chat_id][0],  # System prompt
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze, describe, and infer from this image intelligently and naturally:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    else:
        model_name = "llama-3.3-70b-versatile"
        chats_memory[user_chat_id].append({"role": "user", "content": user_message})
        
        # حماية ليميت الذاكرة
        if len(chats_memory[user_chat_id]) > 20:
            chats_memory[user_chat_id] = [chats_memory[user_chat_id][0]] + chats_memory[user_chat_id][-18:]
        messages = chats_memory[user_chat_id]

    try:
        # --- الخطوة 1: التخطيط والتحليل (The Planning Phase) ---
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.4, # تقليل التمبليتشر للتفكير المنطقي الحكيم
        )
        
        raw_response = completion.choices[0].message.content
        
        # طباعة تفكير البوت في السيرفر (Logging/Debug Brain) عشان تراقبه وهو بيفكر
        print(f"\n🧠 [AGENT BRAIN LOG] User Said: {user_message}")
        print(f"🤔 [PLANNER THINKING]:\n{raw_response}\n")

        # --- الخطوة 2: فحص واكتشاف الـ Tools (Tool Execution Phase) ---
        if "[TOOL:" in raw_response:
            tool_name = ""
            argument = ""
            
            # استخراج اسم الأداة والـ Argument بكود أمان بسيط
            for line in raw_response.split("\n"):
                if "[TOOL:" in line:
                    tool_name = line.split("[TOOL:")[1].split("|")[0].strip()
                if "ARGUMENT:" in line:
                    argument = line.split("ARGUMENT:")[1].replace("]", "").strip()

            tool_result = ""
            # تشغيل الأداة المطلوبة بناءً على قرار عقل الـ AI
            if tool_name == "web_search" and argument:
                print(f"⚡ [EXECUING TOOL]: Launching Web Search for: {argument}")
                tool_result = web_search(argument)
            elif tool_name == "save_memory" and argument:
                print(f"⚡ [EXECUING TOOL]: Saving to Long-Term Memory: {argument}")
                # حفظ في صيغة مفتاح وقيمة تلقائياً
                key_val = argument.split("is") if "is" in argument else [argument, "true"]
                tool_result = manage_long_term_memory(user_chat_id, action="save", key=key_val[0].strip(), value=key_val[1].strip())

            # دمج نتيجة الأداة ورجوعها للموديل عشان يصيغ الرد النهائي للمستخدم
            if tool_result:
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": f"[SYSTEM TOOL OUTPUT]: {tool_result}\nNow give the final natural reply to the user based on this tool output."})
                
                final_completion = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.6,
                )
                final_response = final_completion.choices[0].message.content
                if not is_image:
                    chats_memory[user_chat_id].append({"role": "assistant", "content": final_response})
                return final_response

        # لو مفيش أداة محتاجة تشتغل، هيرد بالرد الطبيعي علطول
        if not is_image:
            chats_memory[user_chat_id].append({"role": "assistant", "content": raw_response})
        return raw_response

    except Exception as e:
        print(f"❌ Error in Agent Brain: {e}")
        return "حصل دروب بسيط في تفكيري، ابعتلي تاني كدا يا غالي."
