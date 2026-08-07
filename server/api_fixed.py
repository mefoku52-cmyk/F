import os
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        data = request.json
        username = data.get("username", "")
        password = data.get("password", "")

        admin_user = os.environ.get("ADMIN_USER", "admin")
        admin_pass = os.environ.get("ADMIN_PASSWORD", "CHANGE_ME")

        if username == admin_user and password == admin_pass:
            return jsonify({"status": "success", "token": "secure_token"})
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
