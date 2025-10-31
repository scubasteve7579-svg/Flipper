from flask import Flask, request

app = Flask(__name__)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code:
        print(f"✅ Got OAuth code: {code}")
        return "Authorization successful! You can close this window."
    else:
        return "No code found.", 400

if __name__ == "__main__":
    app.run(port=5001, debug=True)
