# app.py
from flask import Flask, render_template
import os
import requests

# =====================================
# 1. تعریف Flask برای Gunicorn
# =====================================
server = Flask(__name__)


# =====================================
# 2. پیکربندی اصلی برنامه
# =====================================
class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    EITAA_BOT_TOKEN = os.getenv("EITAA_BOT_TOKEN", "")
    REQUIRED_CHANNELS = ["hodhod500_amoozesh", "hodhod500_ax"]


# =====================================
# 3. تابع راه‌اندازی اپ
# =====================================
def configure_app(app: Flask):

    # ---------- بررسی در دسترس بودن Gemini ----------
    GEMINI_AVAILABLE = False
    genai = None

    try:
        from google import genai
        from google.genai.errors import APIError
        GEMINI_AVAILABLE = True
    except ImportError:
        print("⚠️ کتابخانه Gemini نصب نیست")

    # ---------- اتصال به Gemini ----------
    gemini_client = None
    if GEMINI_AVAILABLE and Config.GEMINI_API_KEY:
        try:
            gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
        except Exception as e:
            print("خطا در اتصال به Gemini:", e)

    # ---------- مدیریت داده کاربران ----------
    user_data = {}

    def get_user_state(user_id: str):
        if user_id not in user_data:
            user_data[user_id] = {
                "credits": 3,
                "is_member": False,
                "gemini_file_id": None
            }
        return user_data[user_id]

    # ---------- بررسی عضویت در ایتا ----------
    def check_eitaa_membership(user_id: str, channel_id: str) -> bool:
        if not Config.EITAA_BOT_TOKEN:
            return True

        try:
            url = f"https://eitaa.ir/bot{Config.EITAA_BOT_TOKEN}/getChatMember"
            params = {"chat_id": f"@{channel_id}", "user_id": user_id}
            response = requests.get(url, params=params, timeout=10).json()

            status = response.get("result", {}).get("status")
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            print("خطا در بررسی عضویت:", e)
            return False


    # =====================================
    # 4. Route ها
    # =====================================
    @app.route("/")
    def home():
        return render_template("index.html")


    @app.route("/api/status")
    def status():
        return {
            "status": "ok",
            "gemini_available": GEMINI_AVAILABLE
        }


# =====================================
# 5. اجرای نهایی اپ برای Gunicorn
# =====================================
configure_app(server)
