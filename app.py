import os
import io
import json
import base64
import requests
from flask import Flask, render_template, request, jsonify

# --- ۱. تعریف آبجکت Flask (نام تغییر یافته به 'server') ---
# Gunicorn از این آبجکت استفاده می‌کند: gunicorn app:server
server = Flask(__name__) 
server.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secure-key')

# --- ۲. تنظیمات و متغیرهای محیطی ---
GEMINI_AVAILABLE = False
try:
    from google import genai 
    from google.genai.errors import APIError
    GEMINI_AVAILABLE = True
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN") 
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"] 

# --- ۳. مدیریت وضعیت کاربر (Dummy Data) ---
user_data = {} 

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'credits': 3, 'is_member': False, 'gemini_file_id': None}
    return user_data[user_id]

# --- ۴. توابع کمکی ---
def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
    if not EITAA_BOT_TOKEN or EITAA_BOT_TOKEN == "YOUR_EITAA_YAR_TOKEN":
        print("هشدار: EITAA_BOT_TOKEN تنظیم نشده. عضویت همیشه True فرض می‌شود.")
        return True
        
    url = "https://eitaayar.ir/api/checkMembership" 
    
    try:
        response = requests.post(url, data={
            'token': EITAA_BOT_TOKEN,
            'channel': channel_id,
            'user_id': user_id
        }, timeout=5)
        
        if response.status_code == 200:
            return response.json().get('status', 'not_member') == 'member'
        
    except requests.RequestException:
        return False
    return False

# --- ۵. اتصال به Gemini ---
gemini_client = None
if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_KEY":
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ اتصال به Gemini برقرار شد.")
    except Exception as e:
        print(f"❌ خطا در ساخت کلاینت Gemini: {e}")
else:
    print("⚠️ GEMINI_API_KEY تنظیم نشده یا کتابخانه در دسترس نیست. فراخوانی‌های AI کار نخواهد کرد.")


# =========================================================
# مسیرهای (Routes) Flask (از 'server' به جای 'app' استفاده شود)
# =========================================================
@server.route('/')
def mini_app():
    """ارائه صفحه HTML برنامک ایتا از پوشه templates."""
    return render_template('index.html')


@server.route('/api/status', methods=['POST'])
def get_status():
    """بررسی عضویت و اعتبار کاربر."""
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
        'status': 'ok',
        'is_member': all_member,
        'required_channels': REQUIRED_CHANNELS,
        'credits': user_state['credits']
    })


@server.route('/api/process_image', methods=['POST'])
def process_image():
    """پردازش عکس با Gemini."""
    if gemini_client is None:
        return jsonify({'error': 'AI_DISABLED', 'message': 'سرویس ویرایش عکس غیرفعال است.'}), 503

    data = request.get_json()
    user_id = str(data.get('user_id'))
    base64_image = data.get('image')
    prompt = data.get('prompt')
    user_state = get_user_state(user_id)
    
    if user_state['credits'] <= 0:
        return jsonify({'error': 'NO_CREDIT', 'message': 'اعتبار شما به پایان رسیده است.'}), 402
        
    user_state['credits'] -= 1
    
    try:
        image_bytes = base64.b64decode(base64_image.split(',')[1]) 
        photo_data = io.BytesIO(image_bytes)
        photo_data.name = "uploaded_image.jpeg" 
    except Exception:
        return jsonify({'error': 'INVALID_IMAGE', 'message': 'فرمت عکس نامعتبر است.'}), 400
        
    gemini_file_id = None
    try:
        gemini_file = gemini_client.files.upload(file=photo_data) 
        gemini_file_id = gemini_file.name
        
        system_instruction = "You are an expert image editor. Describe the changes concisely."

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        result_text = response.text
        
        return jsonify({
            'status': 'success',
            'result': result_text,
            'remaining_credits': user_state['credits']
        })

    except APIError as e:
        return jsonify({'error': 'GEMINI_ERROR', 'message': f'خطای سرویس هوش مصنوعی: {e}'}), 500
        
    finally:
        if gemini_file_id:
            try:
                gemini_client.files.delete(name=gemini_file_id)
            except Exception:
                pass 
        
@server.route('/api/buy_credit', methods=['POST'])
def buy_credit():
    """مسیر فرضی برای خرید اعتبار."""
    data = request.get_json()
    user_id = str(data.get('user_id'))
    amount = data.get('amount', 10) 
    
    user_state = get_user_state(user_id)
    user_state['credits'] += amount
    
    return jsonify({
        'status': 'success',
        'message': f'{amount} اعتبار با موفقیت به حساب شما افزوده شد.',
        'new_credits': user_state['credits']
    })
