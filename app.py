from flask import Flask, request, jsonify
import requests
import json
import threading
from byte import Encrypt_ID, encrypt_api

app = Flask(__name__)

API_KEY = "ffwlx"

def load_tokens(region):
    try:
        region = region.upper()
        if region == "IND":
            file_path = "spam_ind.json"
        elif region in {"BR", "US", "SAC", "NA"}:
            file_path = "spam_br.json"
        elif region == "EU":
            file_path = "spam_eu.json"
        elif region == "VN":
            file_path = "spam_vn.json"
        else:
            file_path = "spam_bd.json"

        with open(file_path, "r") as f:
            data = json.load(f)
            tokens = [item["token"] for item in data]
        return tokens

    except Exception as e:
        app.logger.error(f"Error loading tokens for region {region}: {e}")
        return None

def get_request_url(region):
    region = region.upper()
    if region == "IND":
        return "https://client.ind.freefiremobile.com/RequestAddingFriend"
    elif region in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/RequestAddingFriend"
    else:
        return "https://clientbp.ggblueshark.com/RequestAddingFriend"


def send_friend_request(uid, token, region, results):
    encrypted_id = Encrypt_ID(uid)
    payload = f"08a7c4839f1e10{encrypted_id}1801"
    encrypted_payload = encrypt_api(payload)
    url = get_request_url(region)

    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB48",
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": "16",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-N975F Build/PI)",
        "Host": "clientbp.ggblueshark.com",
        "Connection": "close",
        "Accept-Encoding": "gzip, deflate, br"
    }

    response = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload))

    if response.status_code == 200:
        results["success"] += 1
    else:
        results["failed"] += 1

@app.route("/send_requests", methods=["GET"])
def send_requests():
    uid = request.args.get("uid")
    region = request.args.get("region")
    api_key = request.args.get("key")

    if not api_key or api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 403

    if not uid or not region:
        return jsonify({"error": "uid and region parameters are required"}), 400

    tokens = load_tokens(region)
    if not tokens:
        return jsonify({"error": f"No tokens found for region {region}"}), 500

    results = {"success": 0, "failed": 0}
    threads = []

    for token in tokens[:110]:  # Maximum 110 requests
        thread = threading.Thread(target=send_friend_request, args=(uid, token, region, results))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_requests = results["success"] + results["failed"]
    status = 1 if results["success"] != 0 else 2

    return jsonify({
        "success_count": results["success"],
        "failed_count": results["failed"],
        "status": status
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)