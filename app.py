from flask import Flask, request, jsonify
import requests
import json
import threading
from byte import Encrypt_ID, encrypt_api
import asyncio
import aiohttp
from google.protobuf.json_format import MessageToJson
import uid_generator_pb2
import like_count_pb2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii

app = Flask(__name__)

# Function to load tokens from external API
def load_tokens():
    try:
        response = requests.get("https://raw.githubusercontent.com/ffwlxd/ffwlxd-spam/main/spam_ind.json")
        if response.status_code == 200:
            tokens = [item["token"] for item in response.json()]
            return tokens
        return []
    except Exception as e:
        print(f"Error loading tokens: {e}")
        return []

# Encryption functions for player info
def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except:
        return None

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except:
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    encrypted_uid = encrypt_message(protobuf_data)
    return encrypted_uid

async def get_player_info(uid, token):
    try:
        encrypted_uid = enc(uid)
        if not encrypted_uid:
            return None
            
        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        edata = bytes.fromhex(encrypted_uid)
        
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers, ssl=False) as response:
                if response.status != 200:
                    return None
                hex_data = await response.read()
                binary = bytes.fromhex(hex_data.hex())
                items = like_count_pb2.Info()
                items.ParseFromString(binary)
                jsone = MessageToJson(items)
                data_info = json.loads(jsone)
                return str(data_info.get('AccountInfo', {}).get('PlayerNickname', ''))
    except:
        return None

def send_friend_request(uid, token, results):
    encrypted_id = Encrypt_ID(uid)
    payload = f"08a7c4839f1e10{encrypted_id}1801"
    encrypted_payload = encrypt_api(payload)

    url = "https://client.ind.freefiremobile.com/RequestAddingFriend"
    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB50",
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
    
    if not uid:
        return jsonify({"error": "uid parameter is required"}), 400

    tokens = load_tokens()
    if not tokens:
        return jsonify({"error": "No tokens found from API"}), 500

    # Get player name (using first token)
    player_name = asyncio.run(get_player_info(uid, tokens[0]))

    results = {"success": 0, "failed": 0}
    threads = []

    for token in tokens[:100]:  # Limit to 100 requests
        thread = threading.Thread(target=send_friend_request, args=(uid, token, results))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_requests = results["success"] + results["failed"]
    status = 1 if results["success"] != 0 else 2  # 1 if success, 2 if all failed

    response_data = {
        "success_count": results["success"],
        "failed_count": results["failed"],
        "status": status
    }
    
    if player_name:
        response_data["player_name"] = player_name

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)