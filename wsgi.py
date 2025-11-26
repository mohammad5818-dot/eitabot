from flask import Flask

print("🔥 WSGI FILE LOADED 🔥")

server = Flask(__name__)

@server.route("/")
def home():
    return "✅ WSGI WORKING"
