# app.py

# === بخش ۱: تعریف مینیمال برای Gunicorn ===
# ⚠️ فقط ایمپورت‌های ضروری Flask و تعریف 'server' در سطح بالا بمانند.
from flask import Flask
import os 
import io 
import json
import base64
import requests
# ... (اگر ایمپورت دیگری در ابتدا دارید، آن را بیاورید) ...

# ⚠️ تعریف شیء Flask باید اولین متغیر قابل مشاهده باشد.
server = Flask(__name__) 


# === بخش ۲: منطق، متغیرها و Routeها (در داخل یک تابع) ===

# این تابع شامل تمام منطق پیچیده و پرخطر است.
def configure_app(server):
    
    # 1. ایمپورت Gemini (حساس ترین بخش)
    GEMINI_AVAILABLE = False
    try:
        from google import genai 
        from google.genai.errors import APIError
        GEMINI_AVAILABLE = True
    except ImportError:
        pass 

    # 2. متغیرهای محیطی و تنظیمات
    # ... (کل کدهای مدیریت GEMINI_API_KEY، EITAA_BOT_TOKEN، و REQUIRED_CHANNELS) ...
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
    EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN") 
    REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"] 

    # 3. توابع کمکی
    # ... (توابع get_user_state و check_eitaa_membership) ...
    user_data = {} 
    def get_user_state(user_id):
        if user_id not in user_data:
            user_data[user_id] = {'credits': 3, 'is_member': False, 'gemini_file_id': None}
        return user_data[user_id]
        
    def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
        if not EITAA_BOT_TOKEN or EITAA_BOT_TOKEN == "YOUR_EITAA_YAR_TOKEN":
            return True
        # ... (منطق requests) ...
        return False
    
    # 4. اتصال به Gemini
    # ... (منطق gemini_client = genai.Client(...)) ...
    gemini_client = None
    if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_KEY":
        try:
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            pass
            
    # 5. تمام Route ها با دکوراتور @server.route
    # ... (Route های @server.route('/')، @server.route('/api/status') و غیره) ...
    from flask import render_template # ایمپورت render_template را داخل تابع می آوریم
    
    @server.route('/')
    def mini_app():
        return render_template('index.html')
    
    # ... (ادامه Route ها) ...
    
    # ⚠️ حتماً تمام کدهای داخل تابع configure_app باید دارای تورفتگی (Indentation) صحیح باشند.


# === بخش ۳: اجرای تنظیمات ===
# Gunicorn این خط را اجرا می‌کند و برنامه را نهایی می‌کند.
configure_app(server)
