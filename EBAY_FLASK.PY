#!/usr/bin/env python3
"""
ebay_oauth_server.py

Usage:
  # export your secrets first (do NOT hardcode client secret in code)
  export EBAY_CLIENT_ID="StephenT-Flipper-PRD-988d256be-0928a4a9"
  export EBAY_CLIENT_SECRET="PRD-a13b478403d-f288-45ef-9275-c12a"
  export EBAY_RUNAME="Flipper-StephenT-Flippe-huzrpjxwi"   # your RuName
  export LOCA_URL="https://bitter-jars-thank.loca.lt"      # your loca.lt HTTPS base URL
  python ebay_oauth_server.py

Make sure loca.lt is running and forwarding to port 8000:
  lt --port 8000
"""
from flask import Flask, request, redirect, url_for, render_template_string
import os
import requests
import base64
import json
import sys

app = Flask(__name__)

# Load configuration from environment
CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
RUNAME = os.getenv("EBAY_RUNAME")
LOCA_URL = os.getenv("LOCA_URL")
PORT = int(os.getenv("PORT", "8000"))

if not CLIENT_ID or not CLIENT_SECRET or not RUNAME or not LOCA_URL:
    print("ERROR: Please set EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_RUNAME and LOCA_URL env vars.")
    sys.exit(1)

# eBay endpoints
AUTH_URL_BASE = "https://auth.ebay.com/oauth2/authorize"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Simple page with a button to start OAuth
INDEX_HTML = """
<!doctype html>
<title>Flipper eBay OAuth</title>
<h2>Flipper — eBay Production OAuth Helper</h2>
<p>Click to start the OAuth flow (production).</p>
<a href="{{ auth_url }}"><button>Start eBay OAuth</button></a>
<hr>
<p>After approving, eBay will redirect to <code>{{ callback_example }}</code></p>
"""

@app.route("/")
def index():
    # Construct the authorize URL using the RuName in redirect_uri
    # include a minimal scope; change/add scopes as needed (space separated, URL-encoded)
    scopes = "https://api.ebay.com/oauth/api_scope"
    auth_url = (
        f"{AUTH_URL_BASE}?client_id={CLIENT_ID}"
        f"&redirect_uri={RUNAME}"
        f"&response_type=code"
        f"&scope={requests.utils.requote_uri(scopes)}"
    )
    callback_example = f"{LOCA_URL}/callback"
    return render_template_string(INDEX_HTML, auth_url=auth_url, callback_example=callback_example)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        return f"Error from eBay: {error}", 400
    if not code:
        return "No authorization code found in query string.", 400

    print("\n✅ OAuth code received:\n", code, "\n")

    # Exchange the auth code for access token (production)
    basic_auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_auth}"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        # IMPORTANT: use the RuName (not the full loca URL) for redirect_uri parameter
        "redirect_uri": RUNAME
    }

    resp = requests.post(TOKEN_URL, headers=headers, data=data)
    try:
        resp.raise_for_status()
    except Exception as e:
        # show response details for debugging
        print("Token exchange failed:", resp.status_code, resp.text)
        return f"Token exchange failed: {resp.status_code} - {resp.text}", 500

    token_response = resp.json()
    print("\n✅ Token response:\n", json.dumps(token_response, indent=2))

    # Save tokens to file
    with open("tokens.json", "w") as f:
        json.dump(token_response, f, indent=2)

    return (
        "<h3>Authorization successful!</h3>"
        "<p>Token response printed to terminal and saved to <code>tokens.json</code>.</p>"
        "<p>You can safely close this window.</p>"
    )

if __name__ == "__main__":
    # bind to 0.0.0.0 so loca.lt can forward requests
    app.run(host="0.0.0.0", port=PORT, debug=True)
