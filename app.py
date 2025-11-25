from flask import Flask

print("✅ app.py loaded")

server = Flask(__name__)

print("✅ server object created")

@server.route("/")
def test():
    return "Server is OK"
