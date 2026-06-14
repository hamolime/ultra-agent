FROM python:3.10-slim

# تثبيت الأدوات الأساسية للنظام ومعالجة الصوت ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ ملف المكتبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# المنفذ اللي هيشتغل عليه السيرفر الوهمي لـ Railway
EXPOSE 7860

CMD ["python", "bot.py"]
