# ⚠️ ۱. ساده‌سازی بالا برای تست gunicorn
from flask import Flask
import os
import io
import json
import base64
import requests

# ⚠️ ۲. تعریف app در بالاترین سطح
app = Flask(__name__) 

# ⚠️ ۳. بقیه منطق کد در تابع تنظیمات قرار می‌گیرد
def configure_app(app):
    """تمام تنظیمات، متغیرها، و Routeها اینجا تعریف می‌شوند."""
    
    # --- تنظیمات و ثابت‌ها ---
    try:
        from google import genai 
        from google.genai.errors import APIError
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False
        
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
    EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN") 
    REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"] 

    # --- مدیریت وضعیت و اعتبار کاربر (Dummy Data) ---
    user_data = {} 

    def get_user_state(user_id):
        if user_id not in user_data:
            user_data[user_id] = {'credits': 3, 'is_member': False, 'gemini_file_id': None}
        return user_data[user_id]

    # --- توابع کمکی ---
    def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
        if not EITAA_BOT_TOKEN or EITAA_BOT_TOKEN == "YOUR_EITAA_YAR_TOKEN":
            return True
            
        url = "https://eitaayar.ir/api/checkMembership" 
        try:
            response = requests.post(url, data={
                'token': EITAA_BOT_TOKEN, 'channel': channel_id, 'user_id': user_id
            }, timeout=5)
            return response.status_code == 200 and response.json().get('status', 'not_member') == 'member'
        except requests.RequestException:
            return False

    # --- اتصال به Gemini ---
    gemini_client = None
    if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_KEY":
        try:
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            pass

    # =========================================================
    # مسیرهای (Routes) Flask
    # =========================================================
    @app.route('/')
    def mini_app():
        return render_template('index.html')


    @app.route('/api/status', methods=['POST'])
    def get_status():
        data = request.get_json()
        user_id = str(data.get('user_id'))
        user_state = get_user_state(user_id)
        
        all_member = True
        for channel in REQUIRED_CHANNELS:
            if not check_eitaa_membership(user_id, channel):
                all_member = False
                break
                
        user_state['is_member'] = all_member
        
        if all_member and user_state['credits'] == 0:
            user_state['credits'] = 1 
            
        return jsonify({
            'status': 'ok', 'is_member': all_member, 'required_channels': REQUIRED_CHANNELS, 'credits': user_state['credits']
        })


    @app.route('/api/process_image', methods=['POST'])
    def process_image():
        if gemini_client is None:
            return jsonify({'error': 'AI_DISABLED', 'message': 'سرویس ویرایش عکس غیرفعال است.'}), 503

        data = request.get_json()
        user_id = str(data.get('user_id'))
        base64_image = data.get('image')
        user_state = get_user_state(user_id)
        
        if user_state['credits'] <= 0:
            return jsonify({'error': 'NO_CREDIT', 'message': 'اعتبار شما به پایان رسیده است.'}), 402
            
        user_state['credits'] -= 1
        
        # ... (ادامه منطق پردازش عکس) ...
        # [بخشی از کد حذف شده برای سادگی، اما باید در نسخه نهایی شما باشد]
        # ...
        
        return jsonify({'status': 'success', 'result': 'ویرایش آزمایشی موفق', 'remaining_credits': user_state['credits']})
    
    @app.route('/api/buy_credit', methods=['POST'])
    def buy_credit():
        # ... (منطق خرید اعتبار) ...
        data = request.get_json()
        user_id = str(data.get('user_id'))
        amount = data.get('amount', 10) 
        user_state = get_user_state(user_id)
        user_state['credits'] += amount
        return jsonify({'status': 'success', 'message': f'{amount} اعتبار با موفقیت به حساب شما افزوده شد.', 'new_credits': user_state['credits']})


# ⚠️ ۴. فراخوانی تابع تنظیمات
configure_app(app)
