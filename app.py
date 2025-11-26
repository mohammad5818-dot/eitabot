import os
import base64
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- متغیرهای محیطی ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EITAA_BOT_TOKEN = os.environ.get("EITAA_BOT_TOKEN", "")
REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"]

# --- دیتابیس ساده کاربرها ---
user_data = {}  # مثال ساده، در عمل باید پایگاه داده داشته باشید

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"credits": 3, "is_member": False}
    return user_data[user_id]

# --- Route اصلی ---
@app.route("/")
def home():
    return render_template("index.html")

# --- API وضعیت کاربر ---
@app.route("/api/status", methods=["POST"])
def api_status():
    data = request.get_json()
    user_id = str(data.get("user_id"))
    state = get_user_state(user_id)

    # چک عضویت (این فقط شبیه‌سازی است)
    is_member = True if EITAA_BOT_TOKEN else False
    state["is_member"] = is_member

    return jsonify({
        "user_id": user_id,
        "is_member": is_member,
        "credits": state["credits"],
        "required_channels": REQUIRED_CHANNELS
    })

# --- API پردازش عکس ---
@app.route("/api/process_image", methods=["POST"])
def process_image():
    data = request.get_json()
    user_id = str(data.get("user_id"))
    prompt = data.get("prompt")
    image_data = data.get("image")

    state = get_user_state(user_id)

    if state["credits"] <= 0:
        return jsonify({"status": "error", "message": "اعتبار کافی ندارید."})

    # کاهش اعتبار
    state["credits"] -= 1

    # شبیه‌سازی ویرایش عکس
    result_text = f"✅ تصویر شما ویرایش شد با دستور: {prompt}"

    return jsonify({"status": "success", "result": result_text, "remaining_credits": state["credits"]})

# --- API خرید اعتبار ---
@app.route("/api/buy_credit", methods=["POST"])
def buy_credit():
    data = request.get_json()
    user_id = str(data.get("user_id"))
    amount = int(data.get("amount", 0))
    state = get_user_state(user_id)
    state["credits"] += amount
    return jsonify({"status": "success", "new_credits": state["credits"]})
