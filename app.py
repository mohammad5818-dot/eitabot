import os
import io
import json
import base64
import requests
from flask import Flask, render_template, request, jsonify

# ⚠️ مهم: برای استفاده از gemini_client در سطح بالا، باید ایمپورت شوند.
try:
    from google import genai 
    from google.genai.errors import APIError
except ImportError:
    print("❌ خطای ایمپورت: google-genai نصب نشده است.")

# --- تنظیمات و مقداردهی اولیه Flask (برای رفع خطای gunicorn.errors.AppImportError) ---
# آبجکت 'app' باید در سطح بالای فایل تعریف شود تا Gunicorn آن را پیدا کند.
app = Flask(__name__) 
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secure-key')

# --- ثابت‌ها ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN") 

# لیست کانال‌هایی که کاربر باید عضو آن‌ها باشد (آیدی کانال بدون @)
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"] 

# --- مدیریت وضعیت و اعتبار کاربر (در محیط واقعی باید از پایگاه داده استفاده شود) ---
user_data = {} 

def get_user_state(user_id):
    """مقداردهی اولیه و بازگرداندن داده‌های کاربر."""
    if user_id not in user_data:
        # 3 اعتبار دیفالت برای تست
        user_data[user_id] = {'credits': 3, 'is_member': False, 'gemini_file_id': None}
    return user_data[user_id]

def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
    """بررسی عضویت در کانال از طریق یک API واسط (فرضی)."""
    if not EITAA_BOT_TOKEN or EITAA_BOT_TOKEN == "YOUR_EITAA_YAR_TOKEN":
        print("هشدار: EITAA_BOT_TOKEN تنظیم نشده. عضویت همیشه True فرض می‌شود.")
        return True
        
    url = "https://eitaayar.ir/api/checkMembership" # آدرس فرضی API واسط
    
    try:
        response = requests.post(url, data={
            'token': EITAA_BOT_TOKEN,
            'channel': channel_id,
            'user_id': user_id
        }, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('status', 'not_member') == 'member'
        
    except requests.RequestException as e:
        print(f"خطا در ارتباط با API واسط ایتا: {e}")
        return False
    return False

# --- اتصال به Gemini ---
gemini_client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_KEY":
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ اتصال به Gemini برقرار شد.")
    except Exception as e:
        print(f"❌ خطا در ساخت کلاینت Gemini: {e}")
else:
    print("⚠️ GEMINI_API_KEY تنظیم نشده است. فراخوانی‌های AI کار نخواهد کرد.")


# =========================================================
# مسیرهای Frontend
# =========================================================
@app.route('/')
def mini_app():
    """ارائه صفحه HTML برنامک ایتا."""
    # فایل 'index.html' را از پوشه 'templates' بارگذاری می‌کند.
    return render_template('index.html')


# =========================================================
# مسیر API: بررسی وضعیت و عضویت
# =========================================================
@app.route('/api/status', methods=['POST'])
def get_status():
    """بررسی عضویت در کانال‌ها و اعتباردهی اولیه."""
    data = request.get_json()
    user_id = str(data.get('user_id'))
    user_state = get_user_state(user_id)
    
    # ۱. بررسی عضویت در تمامی کانال‌ها
    all_member = True
    for channel in REQUIRED_CHANNELS:
        if not check_eitaa_membership(user_id, channel):
            all_member = False
            break
            
    user_state['is_member'] = all_member
    
    # ۲. ست کردن اعتبار دیفالت 
    if all_member and user_state['credits'] == 0:
        user_state['credits'] = 1 # اعتبار تست
        
    return jsonify({
        'status': 'ok',
        'is_member': all_member,
        'required_channels': REQUIRED_CHANNELS,
        'credits': user_state['credits']
    })


# =========================================================
# مسیر API: دریافت عکس و پرامپت، و پردازش با Gemini
# =========================================================
@app.route('/api/process_image', methods=['POST'])
def process_image():
    """دریافت عکس و پرامپت، پردازش و بازگرداندن نتیجه."""
    if gemini_client is None:
        return jsonify({'error': 'AI_DISABLED', 'message': 'سرویس ویرایش عکس غیرفعال است. کلید Gemini را بررسی کنید.'}), 503

    data = request.get_json()
    user_id = str(data.get('user_id'))
    base64_image = data.get('image')
    prompt = data.get('prompt')
    user_state = get_user_state(user_id)
    
    # ۱. چک اعتبار و کسر
    if user_state['credits'] <= 0:
        return jsonify({'error': 'NO_CREDIT', 'message': 'اعتبار شما به پایان رسیده است.'}), 402
        
    user_state['credits'] -= 1
    
    # ۲. تبدیل Base64 به شیء فایل
    try:
        # حذف پیشوند Base64
        image_bytes = base64.b64decode(base64_image.split(',')[1]) 
        photo_data = io.BytesIO(image_bytes)
        photo_data.name = "uploaded_image.jpeg" 
    except Exception:
        return jsonify({'error': 'INVALID_IMAGE', 'message': 'فرمت عکس نامعتبر است.'}), 400
        
    gemini_file_id = None
    try:
        # ۳. آپلود در Gemini
        gemini_file = gemini_client.files.upload(file=photo_data) 
        gemini_file_id = gemini_file.name
        
        # ۴. فراخوانی مدل 
        system_instruction = "You are an expert image editor. Based on the user's prompt, edit the provided image to fulfill the request. Describe the changes concisely."

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        # ۵. بازگرداندن خروجی (در اینجا، خروجی فقط متن فرض می‌شود)
        result_text = response.text
        
        return jsonify({
            'status': 'success',
            'result': result_text,
            'remaining_credits': user_state['credits']
        })

    except APIError as e:
        print(f"Gemini API Error: {e}")
        return jsonify({'error': 'GEMINI_ERROR', 'message': f'خطای سرویس هوش مصنوعی. {e}'}), 500
        
    finally:
        # ۶. پاکسازی فایل آپلود شده
        if gemini_file_id:
            try:
                gemini_client.files.delete(name=gemini_file_id)
            except Exception:
                pass
        
# =========================================================
# مسیر API: خرید اعتبار (صرفاً برای نمایش)
# =========================================================
@app.route('/api/buy_credit', methods=['POST'])
def buy_credit():
    """مسیر فرضی برای خرید اعتبار."""
    data = request.get_json()
    user_id = str(data.get('user_id'))
    amount = data.get('amount', 10) 
    
    user_state = get_user_state(user_id)
    # ⚠️ در اینجا باید اتصال به درگاه پرداخت و تأیید پرداخت انجام شود.
    user_state['credits'] += amount
    
    return jsonify({
        'status': 'success',
        'message': f'{amount} اعتبار با موفقیت به حساب شما افزوده شد.',
        'new_credits': user_state['credits']
    })

# ⚠️ این بخش (if __name__ == '__main__':) برای اجرای با Gunicorn حذف شده یا ساده شده است.
# Gunicorn مستقیماً آبجکت 'app' را در سطح بالا بارگذاری می‌کند.
