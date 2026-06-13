import json
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

REMINDERS_FILE = "reminders.json"
if not os.path.exists(REMINDERS_FILE):
    with open(REMINDERS_FILE, "w") as f:
        json.dump([], f)

scheduler = BackgroundScheduler()
scheduler.start()

def save_reminder_to_file(task, run_time_str):
    with open(REMINDERS_FILE, "r") as f:
        data = json.load(f)
    data.append({"task": task, "time": run_time_str})
    with open(REMINDERS_FILE, "w") as f:
        json.dump(data, f)

def schedule_a_task(task_details, run_time_str, send_notification_func, chat_id):
    """دالة لجدولة التذكيرات"""
    try:
        run_time = datetime.strptime(run_time_str, "%Y-%m-%d %H:%M:%S")
        scheduler.add_job(
            send_notification_func, 
            'date', 
            run_date=run_time, 
            args=[chat_id, f"⏰ تذكير متجدول بنجاح يا ريس:\n\n{task_details}"]
        )
        save_reminder_to_file(task_details, run_time_str)
        return f"✅ تم حفظ وجدولة المَهمة بنجاح:\n'{task_details}'\nالموعد: {run_time_str}"
    except Exception as e:
        return f"❌ حصلت مشكلة في ظبط الوقت، اتأكد من الفورمات الصبح: YYYY-MM-DD HH:MM:SS"

def load_saved_reminders(send_notification_func, chat_id):
    """استرجاع المواعيد القديمة في حالة ريستارت السيرفر"""
    with open(REMINDERS_FILE, "r") as f:
        data = json.load(f)
    
    now = datetime.now()
    for item in data:
        try:
            run_time = datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")
            if run_time > now:
                scheduler.add_job(
                    send_notification_func, 
                    'date', 
                    run_date=run_time, 
                    args=[chat_id, f"⏰ تذكير متجدول مسترجع:\n\n{item['task']}"]
                )
        except:
            continue