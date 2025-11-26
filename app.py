# app.py
from flask import Flask, request, jsonify, render_template
import os
import base64

# ========================
# تنظیمات سرور
# ========================
server = Flask(__name__)

# متغیرهای محیطی
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN")
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"]

# ذخیره‌سازی وضعیت کاربر (موقتی، برای دیتابیس واقعی باید جایگزین شود)
user_data = {}

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'credits': 3, 'is_member': True}  # فرض می‌کنیم همه عضو هستند
    return user_data[user_id]

# ========================
# Route ها
# ========================
@server.route("/")
def index():
    return render_template("index.html")


@server.route("/api/status", methods=["POST"])
def status():
    data = request.json
    user_id = data.get("user_id")
    user_state = get_user_state(user_id)
    
    return jsonify({
        "is_member": user_state['is_member'],
        "credits": user_state['credits'],
        "required_channels": REQUIRED_CHANNELS
    })


@server.route("/api/process_image", methods=["POST"])
def process_image():
    data = request.json
    user_id = data.get("user_id")
    image_base64 = data.get("image")
    prompt = data.get("prompt")
    
    user_state = get_user_state(user_id)
    
    if user_state['credits'] <= 0:
        return jsonify({"status": "error", "message": "اعتبار کافی نیست."})
    
    # ========== اتصال به Gemini ==========
    result_url = f"https://fake-ai-result.com/{user_id}"  # نمونه خروجی شبیه‌سازی
    
    # کم کردن اعتبار
    user_state['credits'] -= 1
    
    return jsonify({
        "status": "success",
        "result": result_url,
        "remaining_credits": user_state['credits']
    })


@server.route("/api/buy_credit", methods=["POST"])
def buy_credit():
    data = request.json
    user_id = data.get("user_id")
    amount = int(data.get("amount", 0))
    
    user_state = get_user_state(user_id)
    user_state['credits'] += amount
    
    return jsonify({"new_credits": user_state['credits']})

