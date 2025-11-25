import os
import io
import json
import base64
import requests # برای بررسی عضویت (نیازمند توکن واسط)
from flask import Flask, render_template, request, jsonify

# --- تنظیمات ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secure-key')

# ⚠️ کلیدهای واقعی خود را تنظیم کنید
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN") # توکن واسط برای چک عضویت

# لیست کانال‌هایی که کاربر باید عضو آن‌ها باشد (آیدی کانال بدون @)
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"] 

# --- وضعیت و اعتبار کاربر ---
# (در محیط واقعی باید از پایگاه داده استفاده شود)
user_data = {} 

def get_user_state(user_id):
    """مقداردهی اولیه و بازگرداندن داده‌های کاربر."""
    if user_id not in user_data:
        # 3 اعتبار دیفالت برای تست
        user_data[user_id] = {'credits': 3, 'is_member': False, 'gemini_file_id': None}
    return user_data[user_id]

def check_eitaa_membership(user_id: int, channel_id: str) -> bool:
    """
    بررسی عضویت در کانال از طریق یک API واسط (مثلاً EitaaYar).
    ⚠️ این قسمت فرضی است و به در دسترس بودن API واسط معتبر بستگی دارد.
    """
    if not EITAA_BOT_TOKEN:
        print("هشدار: EITAA_BOT_TOKEN تنظیم نشده. عضویت همیشه True فرض می‌شود.")
        return True # اگر توکن واسط نیست، برای تست True فرض می‌کنیم
        
    url = "https://eitaayar.ir/api/checkMembership" 
    
    try:
        response = requests.post(url, data={
            'token': EITAA_BOT_TOKEN,
            'channel': channel_id,
            'user_id': user_id
        }, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            # ⚠️ بسته به پاسخ API واسط، منطق را تنظیم کنید
            return result.get('status', 'not_member') == 'member'
        
    except requests.RequestException as e:
        print(f"خطا در ارتباط با API واسط ایتا: {e}")
        return False
    return False

# --- اتصال به Gemini ---
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_KEY":
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        gemini_client = None
        print("هشدار: GEMINI_API_KEY تنظیم نشده.")
except Exception as e:
    gemini_client = None
    print(f"خطا در ساخت کلاینت Gemini: {e}")

# =========================================================
# مسیرهای Frontend
# =========================================================
@app.route('/')
def mini_app():
    """ارائه صفحه HTML برنامک ایتا."""
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
    
    # ۲. ست کردن اعتبار دیفالت (اگر اولین بار باشد)
    if all_member and user_state['credits'] == 0:
        # اگر کاربر عضو شد و اعتبار صفر داشت، یک اعتبار تست بدهیم (اختیاری)
        user_state['credits'] = 1 
        
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
        return jsonify({'error': 'AI_DISABLED', 'message': 'سرویس ویرایش عکس غیرفعال است.'}), 503

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
        image_bytes = base64.b64decode(base64_image.split(',')[1])
        photo_data = io.BytesIO(image_bytes)
        photo_data.name = "uploaded_image.jpeg" # نام‌گذاری برای تشخیص MIME
    except Exception:
        return jsonify({'error': 'INVALID_IMAGE', 'message': 'فرمت عکس نامعتبر است.'}), 400
        
    gemini_file_id = None
    try:
        # ۳. آپلود در Gemini
        gemini_file = gemini_client.files.upload(file=photo_data) 
        gemini_file_id = gemini_file.name
        
        # ۴. فراخوانی مدل (Image-to-Image Editing)
        system_instruction = "You are an expert image editor. Based on the user's prompt, edit the provided image to fulfill the request. If the model cannot output an edited image directly, provide a highly descriptive text response detailing the necessary visual changes and why they are effective."

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash', # یا یک مدل Multimodal قوی‌تر
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
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({'error': 'SERVER_ERROR', 'message': 'خطای داخلی سرور.'}), 500
        
    finally:
        # ۶. پاکسازی فایل Gemini
        if gemini_file_id:
            try:
                gemini_client.files.delete(name=gemini_file_id)
            except Exception:
                pass # نادیده گرفتن خطای پاکسازی


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
    # ⚠️ در اینجا باید اتصال به درگاه پرداخت انجام شود.
    # فرض می‌کنیم پرداخت موفق بوده است:
    user_state['credits'] += amount
    
    return jsonify({
        'status': 'success',
        'message': f'{amount} اعتبار با موفقیت به حساب شما افزوده شد.',
        'new_credits': user_state['credits']
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)