from flask import Flask, jsonify, render_template

app = Flask(__name__)

# آدرس کانال مورد نظر
CHANNEL_USERNAME = "@HODHOD500"

@app.route('/')
def index():
    return render_template("index.html", channel=CHANNEL_USERNAME)

@app.route('/check_membership')
def check_membership():
    # اینجا می‌توانید منطق واقعی بررسی عضویت را اضافه کنید
    # فعلا برای تست، عضویت را True و اعتبار را 5 قرار می‌دهیم
    return jsonify({
        "is_member": True,
        "credits": 5,
        "required_channels": [CHANNEL_USERNAME]
    })

if __name__ == '__main__':
    app.run(debug=True)
