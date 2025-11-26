from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/status", methods=["POST"])
def status():
    data = request.get_json()
    # نمونه پاسخ شبیه‌سازی شده
    return jsonify({
        "is_member": True,
        "credits": 5,
        "required_channels": []
    })

@app.route("/api/process_image", methods=["POST"])
def process_image():
    data = request.get_json()
    # فقط شبیه‌سازی پردازش تصویر
    return jsonify({
        "status": "success",
        "result": "تصویر شما با موفقیت ویرایش شد!",
        "remaining_credits": 4
    })

@app.route("/api/buy_credit", methods=["POST"])
def buy_credit():
    data = request.get_json()
    new_credits = data.get("amount", 0)
    return jsonify({"new_credits": new_credits})
