from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1 style="text-align:center; margin-top:50px; font-family:Arial;">
        Flipper — LIVE Python eBay Flipping App
    </h1>
    <p style="text-align:center; font-size:18px;">
        Barcode scanner → AI profit → Buy on eBay via EPN
    </p>
    <hr>
    <p style="text-align:center;">
        <strong>Status:</strong> LIVE & Ready for eBay API Review<br>
        <strong>EPN Campaign ID:</strong> 5339126153<br>
        <strong>App ID:</strong> StephenT-Flipper-PRD-988d256be-0928a4a9<br>
        <strong>Python 3.11</strong> | Sandbox APIs Active
    </p>
    <p style="text-align:center; color:green;">
        <em>Growth Check in progress — production access requested</em>
    </p>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # ← AUTO PORT FOR RENDER
    app.run(host='0.0.0.0', port=port, debug=False)