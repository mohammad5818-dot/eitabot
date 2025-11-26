from flask import Flask, request, jsonify, render_template
import os
import base64
import requests

server = Flask(__name__)

# ===================== متغیرهای محیطی =====================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "YOUR_EITAA_YAR_TOKEN")
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"]

# ===================== داده‌های کاربران =====================
user_data = {}  # ذخیره‌سازی ساده، برای دیتابیس واقعی بهتر است

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'credits': 3, 'is_member': False}
    return user_data[user_id]

def check_eitaa_membership(user_id):
    # اگر توکن تنظیم نشده، فرض کنیم همه عضو هستند
    if not EITAA_BOT_TOKEN or EITAA_BOT_TOKEN == "YOUR_EITAA_YAR_TOKEN":
        return True
    # اینجا می‌توان API واقعی ایتا را فراخوانی کرد
    return True

# ===================== Route ها =====================
@server.route("/")
def home():
    return render_template("index.html")

@server.route("/api/status", methods=["POST"])
def status():
    data = request.json
    user_id = data.get("user_id")
    user_state = get_user_state(user_id)
    user_state['is_member'] = check_eitaa_membership(user_id)
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
    
    # ===== فراخوانی Gemini واقعی =====
    try:
        gemini_res = requests.post(
            "https://api.gemini.example.com/edit",
            json={
                "api_key": GEMINI_API_KEY,
                "image": image_base64,
                "prompt": prompt
            },
            timeout=30
        )
        gemini_res.raise_for_status()
        gemini_data = gemini_res.json()
        result_url = gemini_data.get("result_url", "")
    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای Gemini: {str(e)}"})
    
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
    amount = data.get("amount", 0)
    user_state = get_user_state(user_id)
    user_state['credits'] += amount
    return jsonify({"status": "success", "new_credits": user_state['credits']})
