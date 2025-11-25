# app.py
import os
import requests
from flask import Flask, render_template

# ===============================
# ✅ تعریف صحیح برای Gunicorn
# ===============================
server = Flask(__name__)   # این MUST در سطح بالا باشد


# ===============================
# تنظیمات
# ===============================
class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    EITAA_BOT_TOKEN = os.getenv("EITAA_BOT_TOKEN", "")
    REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"]


# ===============================
# پیکربندی اپ
# ===============================
def configure_app(app: Flask):

    # ---------- بررسی Gemini ----------
    GEMINI_AVAILABLE = False
    genai = None

    try:
        from google import genai
        GEMINI_AVAILABLE = True
    except ImportError:
        print("⚠️ کتابخانه Gemini نصب نیست")

    # ---------- اتصال Gemini ----------
    gemini_client = None
    if GEMINI_AVAILABLE and Config.GEMINI_API_KEY:
        try:
            gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
        except Exception as e:
            print("خطا در اتصال Gemini:", e)

    # ---------- دیتا کاربران ----------
    user_data = {}

    def get_user_state(user_id: str):
        if user_id not in user_data:
            user_data[user_id] = {
                "credits": 3,
                "is_member": False,
                "gemini_file_id": None
            }
        return user_data[user_id]

    # ---------- بررسی عضویت ایتا ----------
    def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
        if not Config.EITAA_BOT_TOKEN:
            return True

        try:
            url = f"https://eitaa.ir/bot{Config.EITAA_BOT_TOKEN}/getChatMember"
            params = {"chat_id": f"@{channel_id}", "user_id": user_id}
            r = requests.get(url, params=params, timeout=10).json()
            status = r.get("result", {}).get("status")
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            print("خطا در عضویت:", e)
            return False

    # ===============================
    # ✅ Route ها
    # ===============================
    @app.route("/")
    def home():
        return "✅ Server is running successfully"

    @app.route("/api/status")
    def status():
        return {
            "status": "ok",
            "gemini_available": GEMINI_AVAILABLE
        }


# ✅ اجرای تنظیمات
configure_app(server)
