import os
import io
import uuid
import sqlite3
from pathlib import Path
from PIL import Image
from flask import Flask, jsonify, render_template, request, send_from_directory, abort
import requests
from werkzeug.utils import secure_filename

# ---------- تنظیمات ----------
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"
DB_PATH = BASE_DIR / "users.db"

# محیطی / پیکربندی
CHANNEL_USERNAME = "@HODHOD500"
DEFAULT_CREDITS = 5
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8MB max
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

# سرویس‌های AI (در صورت وجود)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SD_API_URL = os.getenv("SD_API_URL")  # مثال: http://127.0.0.1:7860

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ---------- دیتابیس ساده برای نگهداری اعتبار (مثال) ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        credits INTEGER DEFAULT ?
    )""", (DEFAULT_CREDITS,))
    conn.commit()
    conn.close()

def get_credits(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO users (user_id, credits) VALUES (?, ?)", (user_id, DEFAULT_CREDITS))
        conn.commit()
        credits = DEFAULT_CREDITS
    else:
        credits = row[0]
    conn.close()
    return credits

def adjust_credits(user_id: str, delta: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (delta, user_id))
    if c.rowcount == 0 and delta >= 0:
        c.execute("INSERT INTO users (user_id, credits) VALUES (?, ?)", (user_id, delta))
    conn.commit()
    conn.close()


# ---------- کمکی‌ها ----------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def save_image_file(file_storage, folder: Path) -> Path:
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    out_name = f"{uuid.uuid4().hex}.{ext}"
    out_path = folder / out_name
    file_storage.save(out_path)
    # verify image
    try:
        Image.open(out_path).verify()
    except Exception:
        out_path.unlink(missing_ok=True)
        raise
    return out_path


# ---------- اتصال به سرویس‌های هوش مصنوعی ----------
def process_with_sdapi(input_path: Path, prompt: str) -> Path:
    """
    استفاده از Stable Diffusion WebUI SDAPI (local). 
    فرض: SD_API_URL مثل http://127.0.0.1:7860
    endpoint: /sdapi/v1/img2img
    """
    url = f"{SD_API_URL.rstrip('/')}/sdapi/v1/img2img"
    with open(input_path, "rb") as f:
        files = {"init_images": f}
        payload = {
            "prompt": prompt,
            "sampler_name": "Euler a",
            "steps": 20,
            "cfg_scale": 7.0,
            "denoising_strength": 0.6
        }
        resp = requests.post(url, data={"options": str(payload)}, files=files, timeout=120)
    resp.raise_for_status()
    # پاسخ ممکن است base64 یا zip؛ برای مثال ساده فرض می‌کنیم تصویر باینری بازگشت کند
    # اگر API شما متفاوت است، این قسمت را برحسب خروجی SD وب‌یوآی تنظیم کن
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.png"
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path

def process_with_openai(input_path: Path, prompt: str) -> Path:
    """
    نمونه‌ی ساده از تماس به OpenAI Images Edit. 
    توجه: با توجه به تغییرات API ممکن است نیاز به بروزرسانی داشته باشد.
    اینجا از requests استفاده شده تا برایت قابل ویرایش باشد.
    """
    api_key = OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY تنظیم نشده")
    url = "https://api.openai.com/v1/images/edits"
    files = {
        "image[]": open(input_path, "rb"),
    }
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    resp.raise_for_status()
    j = resp.json()
    # این نمونه فرض می‌کند پاسخ حاوی base64 در j['data'][0]['b64_json']
    import base64
    b64 = j["data"][0].get("b64_json") or j["data"][0].get("b64_json")
    if not b64:
        raise RuntimeError("خروجی تصویر در پاسخ موجود نیست")
    image_data = base64.b64decode(b64)
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.png"
    with open(out_path, "wb") as f:
        f.write(image_data)
    return out_path


def process_image(input_path: Path, prompt: str) -> Path:
    """
    این تابع تصمیم می‌گیرد از کدام سرویس استفاده کند.
    اولویت: SD_API_URL -> OPENAI_API_KEY
    """
    if SD_API_URL:
        return process_with_sdapi(input_path, prompt)
    elif OPENAI_API_KEY:
        return process_with_openai(input_path, prompt)
    else:
        raise RuntimeError("هیچ سرویس هوش‌مصنوعی پیکربندی نشده. متغیر محیطی SD_API_URL یا OPENAI_API_KEY را ست کن.")


# ---------- روترها ----------
@app.route("/")
def index():
    # در index لینک به کانال کامل می‌دهیم (مثال eitaa)
    channel_link = f"https://eitaa.com/{CHANNEL_USERNAME.replace('@','')}"
    return render_template("index.html", channel=channel_link)


@app.route("/check_membership")
def check_membership():
    # توجه: در حالت واقعی از token/session یا user_id استفاده کن
    user = request.args.get("user_id", "test_user")
    # شبیه‌سازی: همیشه عضو فرض کن
    is_member = True
    credits = get_credits(user)
    return jsonify({
        "success": True,
        "is_member": is_member,
        "credits": credits,
        "channel": CHANNEL_USERNAME
    })


@app.route("/upload", methods=["POST"])
def upload():
    """
    endpoint برای آپلود عکس و prompt:
    فرم باید فیلدهای:
      - image (file)
      - prompt (text)
      - user_id (opt)
    """
    user = request.form.get("user_id", "test_user")
    prompt = request.form.get("prompt", "").strip()
    if "image" not in request.files:
        return jsonify({"success": False, "error": "تصویری ارسال نشده"}), 400
    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "فایل نامعتبر"}), 400
    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "فرمت فایل مجاز نیست"}), 400

    # اعتبار کاربر را بررسی کن
    credits = get_credits(user)
    if credits <= 0:
        return jsonify({"success": False, "error": "اعتبار کافی نیست"}), 402

    try:
        in_path = save_image_file(file, UPLOAD_DIR)
    except Exception as e:
        return jsonify({"success": False, "error": f"خطا در ذخیره تصویر: {e}"}), 400

    try:
        out_path = process_image(in_path, prompt or "photo enhancement")
    except Exception as e:
        # حذف فایل ورودی در صورت نیاز
        in_path.unlink(missing_ok=True)
        return jsonify({"success": False, "error": f"خطا در پردازش تصویر: {e}"}), 500

    # کاهش اعتبار (مثال: -1 credit per edit)
    adjust_credits(user, -1)

    # برگرداندن مسیر خروجی (از طریق static)
    rel = f"/static/outputs/{out_path.name}"
    return jsonify({"success": True, "output_url": rel, "remaining_credits": get_credits(user)})


@app.route("/static/outputs/<path:filename>")
def static_outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


# ---------- شروع ----------
if __name__ == "__main__":
    init_db()
    # برای توسعه localhost: app.run(debug=True) — در production از gunicorn استفاده کنید
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
