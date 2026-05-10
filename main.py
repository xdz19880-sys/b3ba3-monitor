import os
import requests
import time
from datetime import datetime
from flask import Flask
import threading

app = Flask(__name__)

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
URL = "https://www.adhahi.dz/register"
CHECK_INTERVAL = 30  # ثواني

last_status = None
is_running = False

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def send_telegram(message):
    try:
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(api_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        log(f"خطأ في الإرسال: {e}")
        return False

def check_availability():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        page = response.text.lower()
        
        # كلمات تشير لعدم التوفر
        unavailable = ['غير متوفر', 'مكتمل', 'لا يوجد حجز', 'نفدت', 'disabled', 'closed', 'full']
        # كلمات تشير للتوفر  
        available = ['متوفر', 'متاح', 'سجل', 'register', 'available', 'open']
        
        is_unavailable = any(word in page for word in unavailable)
        is_available = any(word in page for word in available)
        
        # إذا كان الموقع يحتوي على نموذج تسجيل فهو متاح
        has_form = '<form' in page and ('name' in page or 'email' in page or 'phone' in page)
        
        current = is_available or (has_form and not is_unavailable)
        return current
        
    except Exception as e:
        log(f"خطأ في الفحص: {e}")
        return None

def monitor_loop():
    global last_status, is_running
    is_running = True
    
    log("🚀 بدأت المراقبة!")
    
    # إشعار البدء
    send_telegram("🔔 <b>بدأت مراقبة الحجز</b>\n\n📍 الموقع: " + URL + "\n⏱️ كل 30 ثانية")
    
    while is_running:
        status = check_availability()
        
        if status is not None and status != last_status:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if status:
                msg = f"""🎉 <b>الحجز متوفر الآن!</b>

📍 الموقع: {URL}
⚡ سارع بالتسجيل!

📅 {now}"""
            else:
                msg = f"""⚠️ <b>الحجز غير متوفر</b>

📍 الموقع: {URL}
📅 {now}"""
            
            send_telegram(msg)
            last_status = status
            log(f"تغير الحالة: {'متوفر' if status else 'غير متوفر'}")
        
        time.sleep(CHECK_INTERVAL)

@app.route('/')
def home():
    status_text = "متوفر ✅" if last_status else "غير متوفر ❌" if last_status == False else "جاري الفحص..."
    return f"""
    <h1>🤖 Adhahi Monitor</h1>
    <p>الحالة: {status_text}</p>
    <p>آخر فحص: {datetime.now().strftime('%H:%M:%S')}</p>
    """

@app.route('/health')
def health():
    return {"status": "ok", "monitoring": is_running}

if __name__ == '__main__':
    # تشغيل المراقبة في خيط منفصل
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    # تشغيل الخادم
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)